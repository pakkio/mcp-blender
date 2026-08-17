"""Search and import free/CC0 3D assets from Poly Haven, ambientCG, and
Sketchfab, so the agent has an alternative to hand-modelling recognisable
real-world objects from primitives. All HTTP happens in this process; the
downloaded file lands on local disk and is handed to the existing
import_file bridge tool, so nothing on the Blender/extension side changes.
"""

import asyncio
import zipfile
from pathlib import Path
from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..assets.cache import cache_dir
from ..assets.providers.base import ProviderError
from ..assets.registry import all_providers, get_provider
from ..bridge import HEAVY_REQUEST_TIMEOUT_S, BlenderBridge
from ..errors import BridgeError, ErrorType

AssetType = Literal["MODEL", "TEXTURE", "HDRI"]
_MESH_EXTENSIONS = (".glb", ".gltf", ".fbx", ".obj", ".stl", ".usd", ".blend")
_HDRI_EXTENSIONS = (".hdr", ".exr")


class SearchOnlineAssetsParams(BaseModel):
    query: str
    asset_type: AssetType = "MODEL"
    providers: Optional[list[str]] = None
    limit: int = 10
    free_only: bool = True


class ImportOnlineAssetParams(BaseModel):
    asset_id: str
    provider: str
    target_poly_budget: Optional[int] = None
    collection_path: Optional[str] = None
    location: Optional[tuple[float, float, float]] = None
    scale_to_size: Optional[float] = None


def _extract_archive(archive_path: Path) -> Path:
    extract_dir = archive_path.with_suffix("")
    extract_dir.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive_path) as zf:
        zf.extractall(extract_dir)
    return extract_dir


def _find_mesh_file(extract_dir: Path) -> Optional[Path]:
    for candidate in sorted(extract_dir.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in _MESH_EXTENSIONS:
            return candidate
    return None


def register_asset_source_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="search_online_assets",
        description=(
            "Search free/CC0 online asset libraries (Poly Haven, ambientCG for textures, Sketchfab for a much larger "
            "catalog with mixed licenses) for a downloadable 3D model, texture, or HDRI. Call this BEFORE hand-modelling "
            "any recognisable real-world object -- furniture, props, vehicles, plants. Returns ranked hits with license "
            "and whether download needs a token you don't have configured."
        ),
    )
    async def search_online_assets(
        query: str,
        asset_type: AssetType = "MODEL",
        providers: Optional[list[str]] = None,
        limit: int = 10,
        free_only: bool = True,
    ) -> dict:
        params = SearchOnlineAssetsParams(
            query=query, asset_type=asset_type, providers=providers, limit=limit, free_only=free_only
        )

        candidates = [p for p in all_providers() if params.providers is None or p.name in params.providers]
        if not candidates:
            return {"success": False, "message": f"No known provider(s) matching {params.providers}"}

        async def _search_one(provider):
            try:
                hits = await provider.search(params.query, params.asset_type, params.limit)
                return provider.name, hits, None
            except ProviderError as exc:
                return provider.name, [], str(exc)
            except Exception as exc:  # noqa: BLE001 -- a flaky provider must not sink the whole search
                return provider.name, [], f"unexpected error: {exc}"

        results = await asyncio.gather(*(_search_one(p) for p in candidates))

        all_hits = []
        provider_status = {}
        for name, hits, error in results:
            provider_status[name] = {"error": error, "hit_count": len(hits)} if error else {"hit_count": len(hits)}
            all_hits.extend(hits)

        if params.free_only:
            all_hits = [h for h in all_hits if not h.requires_token]

        all_hits = all_hits[: params.limit]

        return {
            "success": True,
            "message": f"Found {len(all_hits)} asset(s) for '{params.query}'",
            "hits": [
                {
                    "id": h.id,
                    "provider": h.provider,
                    "name": h.name,
                    "asset_type": h.asset_type,
                    "license": h.license,
                    "requires_token": h.requires_token,
                    "preview_url": h.preview_url,
                    "tri_count_hint": h.tri_count_hint,
                }
                for h in all_hits
            ],
            "provider_status": provider_status,
        }

    @mcp.tool(
        name="import_online_asset",
        description=(
            "Download a searched asset (by id + provider from search_online_assets) and import it into the scene via "
            "the existing import_file pipeline. Pass target_poly_budget to auto-decimate over budget (10k background "
            "props, 30k hero props, 100k ceiling), collection_path to file it under a nested collection immediately "
            "(e.g. 'Furniture/Chairs'), and location/scale_to_size to place it."
        ),
    )
    async def import_online_asset(
        asset_id: str,
        provider: str,
        target_poly_budget: Optional[int] = None,
        collection_path: Optional[str] = None,
        location: Optional[tuple[float, float, float]] = None,
        scale_to_size: Optional[float] = None,
    ) -> dict:
        params = ImportOnlineAssetParams(
            asset_id=asset_id,
            provider=provider,
            target_poly_budget=target_poly_budget,
            collection_path=collection_path,
            location=location,
            scale_to_size=scale_to_size,
        )

        try:
            provider_obj = get_provider(params.provider)
        except KeyError as exc:
            raise BridgeError(ErrorType.VALIDATION, str(exc)) from exc

        dest_dir = cache_dir(params.provider, params.asset_id)
        try:
            downloaded = await provider_obj.download(params.asset_id, str(dest_dir))
        except ProviderError as exc:
            return {"success": False, "message": str(exc)}

        filepath = Path(downloaded.filepath)

        # Not every provider hit is a mesh: Poly Haven/ambientCG textures come
        # back as either a loose folder of PBR maps or a zip of them, and Poly
        # Haven HDRIs as a single .hdr/.exr -- none of those can go through
        # the mesh import_file pipeline below, so route them to the matching
        # Blender-side tool instead.
        texture_folder: Optional[Path] = None
        if filepath.is_dir():
            texture_folder = filepath
        elif filepath.suffix.lower() == ".zip":
            extract_dir = _extract_archive(filepath)
            mesh_file = _find_mesh_file(extract_dir)
            if mesh_file is not None:
                filepath = mesh_file
            else:
                texture_folder = extract_dir
        elif filepath.suffix.lower() in _HDRI_EXTENSIONS:
            hdri_result = await bridge.send_request("configure_world_environment", {"hdri_path": str(filepath)})
            if not hdri_result.get("success"):
                return {"success": False, "message": hdri_result.get("message", "configure_world_environment failed")}
            return {
                "success": True,
                "message": f"Imported '{params.asset_id}' from {provider_obj.name} as world HDRI",
                "hdri_path": hdri_result.get("hdri_path"),
                "license": downloaded.license,
                "attribution": downloaded.attribution,
                "from_cache": downloaded.from_cache,
            }

        if texture_folder is not None:
            material_name = f"M_{params.asset_id}"
            mat_result = await bridge.send_request(
                "auto_load_pbr_texture_set", {"folder_path": str(texture_folder), "material_name": material_name}
            )
            if not mat_result.get("success"):
                return {"success": False, "message": mat_result.get("message", "auto_load_pbr_texture_set failed")}
            return {
                "success": True,
                "message": f"Imported '{params.asset_id}' from {provider_obj.name} as PBR material '{material_name}'",
                "material_name": material_name,
                "loaded_maps": mat_result.get("loaded_maps", []),
                "license": downloaded.license,
                "attribution": downloaded.attribution,
                "from_cache": downloaded.from_cache,
            }

        import_result = await bridge.send_request(
            "import_file", {"filepath": str(filepath), "file_format": None}, timeout=HEAVY_REQUEST_TIMEOUT_S
        )
        if not import_result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, import_result.get("message", "import_file failed"))

        imported_objects = import_result.get("imported_objects", [])
        if not imported_objects:
            return {"success": False, "message": f"'{filepath.name}' imported no objects"}

        infos = {}
        for obj_name in imported_objects:
            info = await bridge.send_request("get_object_info", {"name": obj_name})
            if info.get("success"):
                infos[obj_name] = info

        roots = [
            name for name, info in infos.items()
            if info.get("parent") not in imported_objects
        ] or list(infos.keys())

        tri_count_before = sum(
            info.get("mesh_data", {}).get("polygons_count", 0)
            for info in infos.values()
        )

        decimation_applied = None
        if params.target_poly_budget and tri_count_before > params.target_poly_budget > 0:
            ratio = max(0.02, min(1.0, params.target_poly_budget / tri_count_before))
            for name, info in infos.items():
                if info.get("type") == "MESH":
                    await bridge.send_request(
                        "decimate_mesh",
                        {"object_name": name, "mode": "COLLAPSE", "ratio": ratio, "apply_immediately": True},
                    )
            decimation_applied = {"ratio": round(ratio, 4), "tri_count_before": tri_count_before}

        wrapper_name = None
        if (params.location is not None or params.scale_to_size is not None) and roots:
            wrapper_result = await bridge.send_request(
                "create_object",
                {"object_type": "EMPTY", "name": f"{params.asset_id}_import", "location": params.location or (0.0, 0.0, 0.0)},
            )
            if wrapper_result.get("success"):
                wrapper_name = wrapper_result["name"]
                await bridge.send_request(
                    "parent_objects",
                    {"parent_name": wrapper_name, "child_names": roots, "keep_transform": True, "parent_type": "OBJECT"},
                )

                if params.scale_to_size:
                    max_dim = max(
                        (max(infos[r].get("dimensions", [0, 0, 0])) for r in roots if r in infos),
                        default=0.0,
                    )
                    if max_dim > 0:
                        factor = params.scale_to_size / max_dim
                        await bridge.send_request(
                            "set_object_transform", {"name": wrapper_name, "scale": (factor, factor, factor)}
                        )

        if params.collection_path:
            segments = [s for s in params.collection_path.split("/") if s]
            parent_col = None
            for seg in segments:
                await bridge.send_request(
                    "manage_collection", {"action": "CREATE", "name": seg, "parent_collection": parent_col}
                )
                parent_col = seg
            leaf = segments[-1] if segments else None

            # Move every imported object (not just roots/wrapper) into the target
            # collection -- parenting under wrapper_name does not change an
            # object's collection membership, so children left un-relinked here
            # would stay wherever import_file's importer originally placed them.
            link_targets = list(imported_objects)
            if wrapper_name:
                link_targets.append(wrapper_name)
            for obj_name in link_targets:
                info = infos.get(obj_name)
                if info is None:
                    info = await bridge.send_request("get_object_info", {"name": obj_name})
                for existing_col in info.get("collections", []):
                    if existing_col != leaf:
                        await bridge.send_request(
                            "manage_collection",
                            {"action": "UNLINK_OBJECT", "name": existing_col, "object_name": obj_name},
                        )
                await bridge.send_request(
                    "manage_collection", {"action": "LINK_OBJECT", "name": leaf, "object_name": obj_name}
                )

        return {
            "success": True,
            "message": f"Imported '{params.asset_id}' from {provider_obj.name} ({len(imported_objects)} object(s))",
            "imported_objects": imported_objects,
            "roots": roots,
            "wrapper_object": wrapper_name,
            "collection_path": params.collection_path,
            "tri_count_before": tri_count_before,
            "decimation_applied": decimation_applied,
            "license": downloaded.license,
            "attribution": downloaded.attribution,
            "from_cache": downloaded.from_cache,
        }

    return search_online_assets, import_online_asset
