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

from .. import client_status
from ..assets.cache import cache_dir
from ..assets.providers.base import ProviderError
from ..assets.registry import all_providers, get_provider
from ..bridge import HEAVY_REQUEST_TIMEOUT_S, BlenderBridge
from ..errors import BridgeError, ErrorType
from .io_ops import Axis

AssetType = Literal["MODEL", "TEXTURE", "HDRI"]
_MESH_EXTENSIONS = (".glb", ".gltf", ".fbx", ".obj", ".stl", ".usd", ".blend")
_HDRI_EXTENSIONS = (".hdr", ".exr")


class SearchOnlineAssetsParams(BaseModel):
    query: str
    asset_type: AssetType = "MODEL"
    providers: Optional[list[str]] = None
    limit: int = 10
    free_only: bool = True


ReductionMethod = Literal["simplify", "decimate", "remesh"]


class ImportOnlineAssetParams(BaseModel):
    asset_id: str
    provider: str
    target_poly_budget: Optional[int] = None
    reduction_method: Optional[ReductionMethod] = None
    collection_path: Optional[str] = None
    location: Optional[tuple[float, float, float]] = None
    scale_to_size: Optional[float] = None
    forward_axis: Optional[Axis] = None
    up_axis: Optional[Axis] = None
    auto_orient: bool = False
    include_preview: bool = True
    # Only meaningful for AI-generated image-to-3d ids ('<provider>_img_<sha8>'):
    # the local source image the generation was seeded from. The hash in the id
    # can't recover the file bytes, so it must travel with the request.
    image_path: Optional[str] = None


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
            "the existing import_file pipeline. Pass target_poly_budget to auto-reduce over budget (10k background "
            "props, 30k hero props, 100k ceiling); reduction_method picks how: 'simplify' (default when omitted, "
            "form-preserving, falls back to a plain ratio decimate if its quality gate rejects the result), "
            "'decimate' (skip straight to the ratio decimate), or 'remesh' (voxel remesh -- destroys UVs/textures, "
            "only use on untextured/procedural-material assets). Pass collection_path to file it under a nested "
            "collection immediately (e.g. 'Furniture/Chairs'), and location/scale_to_size to place it. The result "
            "carries an 'orientation' report; downloaded assets are often authored Y-up or upside down, so pass "
            "up_axis (the file's real up axis) or auto_orient=true when the report says the model landed on its "
            "side or inverted. The result also carries vertices_count (final, post-reduction), credits (license + "
            "attribution combined), and -- unless include_preview=false -- a preview_base64 PNG of the imported result."
        ),
    )
    async def import_online_asset(
        asset_id: str,
        provider: str,
        target_poly_budget: Optional[int] = None,
        reduction_method: Optional[ReductionMethod] = None,
        collection_path: Optional[str] = None,
        location: Optional[tuple[float, float, float]] = None,
        scale_to_size: Optional[float] = None,
        forward_axis: Optional[Axis] = None,
        up_axis: Optional[Axis] = None,
        auto_orient: bool = False,
        include_preview: bool = True,
        image_path: Optional[str] = None,
    ) -> dict:
        params = ImportOnlineAssetParams(
            asset_id=asset_id,
            provider=provider,
            target_poly_budget=target_poly_budget,
            reduction_method=reduction_method,
            collection_path=collection_path,
            location=location,
            scale_to_size=scale_to_size,
            forward_axis=forward_axis,
            up_axis=up_axis,
            auto_orient=auto_orient,
            include_preview=include_preview,
            image_path=image_path,
        )

        try:
            provider_obj = get_provider(params.provider)
        except KeyError as exc:
            raise BridgeError(ErrorType.VALIDATION, str(exc)) from exc

        async with client_status.track(
            bridge, f"Downloading '{params.asset_id}' from {provider_obj.name}..."
        ) as set_status:
            dest_dir = cache_dir(params.provider, params.asset_id)
            try:
                downloaded = await provider_obj.download(
                    params.asset_id, str(dest_dir), image_path=params.image_path
                )
            except ProviderError as exc:
                return {"success": False, "message": str(exc)}

            credit = downloaded.attribution or "no attribution required"
            credits = f"{downloaded.license} — {credit}"
            await set_status(
                f"Importing '{params.asset_id}' from {provider_obj.name} "
                f"({downloaded.license}, credit: {credit})"
            )

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
                    "credits": credits,
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
                    "credits": credits,
                    "from_cache": downloaded.from_cache,
                }

            import_result = await bridge.send_request(
                "import_file",
                {
                    "filepath": str(filepath),
                    "file_format": None,
                    "forward_axis": params.forward_axis,
                    "up_axis": params.up_axis,
                    "check_orientation": True,
                    "auto_orient": params.auto_orient,
                },
                timeout=HEAVY_REQUEST_TIMEOUT_S,
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
                decimation_applied = {"tri_count_before": tri_count_before, "objects": {}}
                for name, info in infos.items():
                    if info.get("type") != "MESH":
                        continue
                    mesh_verts = info.get("mesh_data", {}).get("vertices_count", 0)
                    mesh_tris = info.get("mesh_data", {}).get("polygons_count", 0)
                    # target_poly_budget is a triangle budget; simplify_geometry works
                    # in vertices, so scale it per-object by that object's own tri/vert ratio.
                    vert_target = (
                        round(params.target_poly_budget * mesh_verts / mesh_tris) if mesh_tris > 0 else None
                    )
                    ratio = max(0.02, min(1.0, params.target_poly_budget / tri_count_before))

                    simplify_result = None
                    # method=None (unspecified) keeps the original auto behaviour: try
                    # simplify_geometry first, fall back to decimate on its gate failure.
                    # An explicit "decimate"/"remesh" skips straight past simplify.
                    if params.reduction_method in (None, "simplify") and vert_target:
                        await set_status(
                            f"Simplifying '{name}' from {mesh_verts} to {vert_target} vertices "
                            f"(asset '{params.asset_id}' from {provider_obj.name})"
                        )
                        simplify_result = await bridge.send_request(
                            "simplify_geometry",
                            {"object_name": name, "target": vert_target, "target_unit": "VERTICES"},
                            timeout=HEAVY_REQUEST_TIMEOUT_S,
                        )

                    if simplify_result and simplify_result.get("success"):
                        decimation_applied["objects"][name] = {
                            "method": "simplify_geometry",
                            "result_vertices": simplify_result.get("result_vertices"),
                        }
                    elif params.reduction_method == "remesh":
                        # Voxel size heuristic: ~50 voxels across the object's largest
                        # dimension. Rebuilds the surface from scratch and loses UVs, so
                        # this is only sane on untextured/procedural-material assets --
                        # documented as such on the tool itself, not decided silently here.
                        max_dim = max(info.get("dimensions", [1.0, 1.0, 1.0])) or 1.0
                        voxel_size = max(0.001, max_dim / 50.0)
                        await set_status(
                            f"Remeshing '{name}' (voxel {voxel_size:.4f}) "
                            f"(asset '{params.asset_id}' from {provider_obj.name})"
                        )
                        remesh_result = await bridge.send_request(
                            "remesh_mesh",
                            {"object_name": name, "mode": "VOXEL", "voxel_size": voxel_size, "apply_immediately": True},
                            timeout=HEAVY_REQUEST_TIMEOUT_S,
                        )
                        if remesh_result.get("success"):
                            decimation_applied["objects"][name] = {
                                "method": "remesh_mesh",
                                "voxel_size": voxel_size,
                                "result_vertices": remesh_result.get("result_vertices"),
                            }
                        else:
                            decimation_applied["objects"][name] = {
                                "method": "remesh_mesh",
                                "failed": True,
                                "message": remesh_result.get("message"),
                            }
                    else:
                        # simplify_geometry either wasn't attempted (no vert_target, or
                        # reduction_method="decimate") or its quality gate rejected the
                        # result with method=None -- fall back to the plain ratio decimate
                        # so a budget request still does *something*.
                        await set_status(
                            f"Decimating '{name}' to ratio {ratio:.3f} "
                            f"(asset '{params.asset_id}' from {provider_obj.name})"
                        )
                        decimate_result = await bridge.send_request(
                            "decimate_mesh",
                            {"object_name": name, "mode": "COLLAPSE", "ratio": ratio, "apply_immediately": True},
                        )
                        decimation_applied["objects"][name] = {
                            "method": "decimate_mesh",
                            "ratio": round(ratio, 4),
                            "result_vertices": decimate_result.get("result_vertices"),
                        }

            # Group every imported object under a root empty + collection so nothing
            # is ever left loose at scene root -- regardless of whether the caller
            # asked for placement. This mirrors the documented workflow ("after any
            # multi-part build, call organize_scene_hierarchy") and keeps pack-style
            # imports (FBX rigs with many parts) tidy without manual cleanup.
            group_name = params.collection_path.rsplit("/", 1)[-1] if params.collection_path else params.asset_id
            if not group_name:
                group_name = "ImportedAsset"
            collection_path = params.collection_path or f"Imports/{group_name}"

            wrapper_name = None
            if roots:
                organize_result = await bridge.send_request(
                    "organize_scene_hierarchy",
                    {
                        "groups": [
                            {
                                "name": group_name,
                                "objects": roots,
                                "root_empty": True,
                                "collection_path": collection_path,
                                "children": [],
                            }
                        ],
                        "keep_transform": True,
                        "rename_members": False,
                    },
                )
                if not organize_result.get("success"):
                    raise BridgeError(
                        ErrorType.TOOL_EXECUTION, organize_result.get("message", "organize_scene_hierarchy failed")
                    )
                wrapper_name = organize_result.get("groups", [{}])[0].get("root_empty")

                if params.scale_to_size and wrapper_name:
                    max_dim = max(
                        (max(infos[r].get("dimensions", [0, 0, 0])) for r in roots if r in infos),
                        default=0.0,
                    )
                    if max_dim > 0:
                        factor = params.scale_to_size / max_dim
                        await bridge.send_request(
                            "set_object_transform", {"name": wrapper_name, "scale": (factor, factor, factor)}
                        )

                if params.location and wrapper_name:
                    await bridge.send_request(
                        "set_object_transform", {"name": wrapper_name, "location": list(params.location)}
                    )

            # Re-fetch object info after any reduction pass so vertices_count
            # reflects reality regardless of which method (or none) ran --
            # decimate/remesh/simplify results aren't all shaped the same,
            # so this is the one source of truth rather than three of them.
            vertices_count = 0
            for obj_name in imported_objects:
                fresh_info = await bridge.send_request("get_object_info", {"name": obj_name})
                if fresh_info.get("success") and fresh_info.get("type") == "MESH":
                    vertices_count += fresh_info.get("mesh_data", {}).get("vertices_count", 0)

            preview_base64 = None
            if params.include_preview:
                preview_target = wrapper_name or (roots[0] if roots else imported_objects[0])
                await set_status(f"Capturing preview of '{params.asset_id}' from {provider_obj.name}...")
                try:
                    preview_capture = await bridge.send_request(
                        "inspect_focus_shot", {"target_object": preview_target, "include_base64": True}
                    )
                    if preview_capture.get("success"):
                        preview_base64 = preview_capture.get("image_base64")
                except Exception:  # noqa: BLE001 -- a preview is a nice-to-have, never fatal
                    pass

            orientation = import_result.get("orientation")
            message = f"Imported '{params.asset_id}' from {provider_obj.name} ({len(imported_objects)} object(s))"
            if isinstance(orientation, dict) and str(orientation.get("verdict", "")).startswith("suspect"):
                message += (
                    f" — WARNING: {orientation['verdict'].replace('suspect_', '').replace('_', ' ')}; "
                    "re-import with auto_orient=true or an explicit up_axis"
                )

            return {
                "success": True,
                "message": message,
                "orientation": orientation,
                "imported_objects": imported_objects,
                "roots": roots,
                "wrapper_object": wrapper_name,
                "collection_path": collection_path,
                "tri_count_before": tri_count_before,
                "vertices_count": vertices_count,
                "decimation_applied": decimation_applied,
                "preview_base64": preview_base64,
                "license": downloaded.license,
                "attribution": downloaded.attribution,
                "credits": credits,
                "from_cache": downloaded.from_cache,
            }

    return search_online_assets, import_online_asset
