"""Unified Super Import tool: multi-source asset search & acquisition (Poly Haven,
ambientCG, Sketchfab, direct URLs, AI models, local files) coupled with automatic,
configurable mesh simplification (form-preserving simplify_geometry, ratio
decimation, voxel remesh), target vertex budgeting, and automatic scale/ground normalization.
"""

import json
import math
import os
import re
import tempfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import bpy
from mathutils import Matrix, Vector

from .base import ToolBase

_MESH_EXTENSIONS = (".glb", ".gltf", ".fbx", ".obj", ".stl", ".usd", ".usda", ".usdc", ".blend")
_HDRI_EXTENSIONS = (".hdr", ".exr")
_USER_AGENT = "Blender-MCP-Bridge/2.0"

_POLYHAVEN_CACHE: dict[str, dict] = {}


def get_polyhaven_models_index() -> dict[str, dict]:
    """Fetch and cache Poly Haven models index."""
    global _POLYHAVEN_CACHE
    if _POLYHAVEN_CACHE:
        return _POLYHAVEN_CACHE

    api_url = "https://api.polyhaven.com/assets?t=models"
    req = urllib.request.Request(api_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _POLYHAVEN_CACHE = data
            return _POLYHAVEN_CACHE
    except Exception:
        return _POLYHAVEN_CACHE or {}


def search_polyhaven_models(query: str, limit: int = 15, offset: int = 0) -> list[dict]:
    """Search Poly Haven models ranked by relevance & popularity."""
    assets = get_polyhaven_models_index()
    if not assets:
        return []

    needle = (query or "").lower().strip()
    words = [w for w in needle.split() if w]

    if not words:
        ranked = sorted(assets.items(), key=lambda x: x[1].get("download_count", 0), reverse=True)
        top_slice = ranked[offset:offset+limit]
    else:
        scored = []
        for asset_id, info in assets.items():
            name = str(info.get("name", asset_id)).lower()
            tags = [str(t).lower() for t in info.get("tags", [])]
            cats = [str(c).lower() for c in info.get("categories", [])]
            desc = str(info.get("description", "")).lower()

            score = 0
            matched = False
            for w in words:
                if w == name or w == asset_id.lower():
                    score += 1000
                    matched = True
                elif w in name:
                    score += 300
                    matched = True
                elif any(w in t for t in tags):
                    score += 100
                    matched = True
                elif any(w in c for c in cats):
                    score += 50
                    matched = True
                elif w in desc:
                    score += 10
                    matched = True

            if matched:
                dl = info.get("download_count", 1)
                final_score = score * (1 + math.log10(max(1, dl)))
                scored.append((final_score, asset_id, info))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_slice = [(aid, inf) for _, aid, inf in scored[offset:offset+limit]]

    hits = []
    for aid, inf in top_slice:
        authors = ", ".join(inf.get("authors", {}).keys()) or "Unknown"
        hits.append({
            "id": aid,
            "provider": "polyhaven",
            "name": inf.get("name", aid),
            "polycount": inf.get("polycount", 0),
            "downloads": inf.get("download_count", 0),
            "license": "CC0",
            "credits": f"Poly Haven CC0 by {authors}",
            "thumbnail_url": inf.get("thumbnail_url", f"https://cdn.polyhaven.com/asset_img/thumbs/{aid}.png?width=256&height=256"),
            "asset_type": "MODEL",
        })

    return hits


def search_sketchfab_models(query: str, limit: int = 15, offset: int = 0) -> list[dict]:
    """Search Sketchfab models catalog via keyless public search API."""
    if not query:
        return []
    encoded_query = urllib.parse.quote_plus(query.strip())
    api_url = f"https://api.sketchfab.com/v3/search?type=models&q={encoded_query}&downloadable=true&count={limit}&offset={offset}"
    req = urllib.request.Request(api_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        hits = []
        for r in data.get("results", []):
            uid = r.get("uid")
            if not uid:
                continue
            thumbs = r.get("thumbnails", {}).get("images", [])
            thumb_url = thumbs[0].get("url") if thumbs else None
            lic = r.get("license", {}).get("label", "CC Attribution")
            user = r.get("user", {}).get("displayName") or r.get("user", {}).get("username") or "Sketchfab Creator"
            hits.append({
                "id": uid,
                "provider": "sketchfab",
                "name": r.get("name", uid),
                "polycount": r.get("vertexCount") or r.get("faceCount") or 0,
                "downloads": r.get("likeCount", 0) * 10,
                "license": lic,
                "credits": f"Sketchfab ({lic}) by {user}",
                "thumbnail_url": thumb_url,
                "asset_type": "MODEL",
            })
        return hits
    except Exception:
        return []


def search_ambientcg_assets(query: str, limit: int = 15, offset: int = 0) -> list[dict]:
    """Search ambientCG CC0 materials and assets."""
    encoded_query = urllib.parse.quote_plus(query.strip() if query else "Material")
    api_url = f"https://ambientcg.com/api/v2/full_json?q={encoded_query}&limit={limit}&sort=Popular&offset={offset}"
    req = urllib.request.Request(api_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        hits = []
        for a in data.get("foundAssets", []):
            aid = a.get("assetId")
            if not aid:
                continue
            thumb = a.get("previewImage", {}).get("256-PNG") if isinstance(a.get("previewImage"), dict) else None
            hits.append({
                "id": aid,
                "provider": "ambientcg",
                "name": a.get("displayName", aid),
                "polycount": 0,
                "downloads": a.get("downloadCount", 0) or 5000,
                "license": "CC0",
                "credits": f"ambientCG CC0 ({aid})",
                "thumbnail_url": thumb,
                "asset_type": "TEXTURE" if a.get("dataType") != "3DModel" else "MODEL",
            })
        return hits
    except Exception:
        return []


def search_all_online_models(query: str, provider: str = "ALL", limit: int = 20, offset: int = 0) -> list[dict]:
    """Search online assets across providers with unified importance ranking."""
    provider = (provider or "ALL").upper()
    all_hits = []

    if provider in ("ALL", "POLYHAVEN"):
        all_hits.extend(search_polyhaven_models(query, limit=limit, offset=offset))

    if provider in ("ALL", "SKETCHFAB"):
        all_hits.extend(search_sketchfab_models(query, limit=limit, offset=offset))

    if provider in ("ALL", "AMBIENTCG"):
        all_hits.extend(search_ambientcg_assets(query, limit=limit, offset=offset))

    # Sort merged hits by popularity / downloads
    all_hits.sort(key=lambda x: x.get("downloads", 0), reverse=True)
    return all_hits[:limit]


def download_thumbnail(asset_id: str, thumb_url: str) -> str | None:
    """Download preview thumbnail to temp directory."""
    if not thumb_url:
        return None
    thumb_dir = Path(tempfile.gettempdir()) / "mcp_blender_thumbs"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    clean_id = asset_id.replace(":", "_").replace("/", "_")
    dest_path = thumb_dir / f"{clean_id}.png"
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return str(dest_path)

    try:
        req = urllib.request.Request(thumb_url, headers={"User-Agent": _USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp, open(dest_path, "wb") as f:
            while chunk := resp.read(32 * 1024):
                f.write(chunk)
        return str(dest_path)
    except Exception:
        return None


def _extract_archive(archive_path: Path) -> Path:
    extract_dir = archive_path.with_suffix("")
    extract_dir.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path) as zf:
        zf.extractall(extract_dir)
    return extract_dir


def _find_mesh_file(extract_dir: Path) -> Path | None:
    for candidate in sorted(extract_dir.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in _MESH_EXTENSIONS:
            return candidate
    return None


def _download_url(url: str, dest_path: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp, open(dest_path, "wb") as f:
        while chunk := resp.read(64 * 1024):
            f.write(chunk)


def _get_sketchfab_token() -> str | None:
    """Get Sketchfab token from env or .env file."""
    from ..config import load_env_vars
    load_env_vars()
    return os.environ.get("SKETCHFAB_API_TOKEN")


def _download_sketchfab_asset(asset_id: str, dest_dir: Path) -> tuple[Path | None, str, str]:
    """Download Sketchfab model using API token."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    token = _get_sketchfab_token()
    if not token:
        raise ValueError(
            f"Downloading Sketchfab model '{asset_id}' requires a free SKETCHFAB_API_TOKEN. "
            "Get a free token at https://sketchfab.com/settings/password ('API Token' tab) "
            "and add it to your .env file, or select a free CC0 model from Poly Haven / ambientCG."
        )

    api_url = f"https://api.sketchfab.com/v3/models/{asset_id}/download"
    req = urllib.request.Request(
        api_url,
        headers={"User-Agent": _USER_AGENT, "Authorization": f"Token {token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Sketchfab API download error for '{asset_id}': {exc}") from exc

    gltf = data.get("gltf") or data.get("source")
    if not gltf or not gltf.get("url"):
        raise ValueError(f"No downloadable GLTF file available for Sketchfab model '{asset_id}'")

    download_url = gltf["url"]
    dest_zip = dest_dir / f"{asset_id}.zip"
    _download_url(download_url, dest_zip)
    extracted = _extract_archive(dest_zip)
    mesh_file = _find_mesh_file(extracted)
    if not mesh_file:
        raise ValueError(f"No 3D mesh file found in downloaded Sketchfab archive for '{asset_id}'")

    return mesh_file, "MODEL", f"Downloaded '{asset_id}' model from Sketchfab"


def _download_polyhaven_asset(asset_id: str, dest_dir: Path) -> tuple[Path | None, str, str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    api_url = f"https://api.polyhaven.com/files/{asset_id}"
    req = urllib.request.Request(api_url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            files_meta = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise ValueError(f"Poly Haven API error for '{asset_id}': {exc}") from exc

    if "gltf" in files_meta:
        gltf_variants = files_meta["gltf"]
        chosen_variant = None
        for res in ("1k", "2k", "raw", "4k"):
            if res in gltf_variants:
                chosen_variant = gltf_variants[res].get("gltf") or next(iter(gltf_variants[res].values()), None)
                if chosen_variant and chosen_variant.get("url"):
                    break

        if not chosen_variant or not chosen_variant.get("url"):
            raise ValueError(f"No downloadable GLTF/GLB found for Poly Haven asset '{asset_id}'")

        model_url = chosen_variant["url"]
        ext = ".glb" if model_url.lower().endswith(".glb") else ".gltf"
        model_path = dest_dir / f"{asset_id}{ext}"
        _download_url(model_url, model_path)

        for rel_path, inc in (chosen_variant.get("include") or {}).items():
            if isinstance(inc, dict) and inc.get("url"):
                inc_dest = dest_dir / rel_path
                inc_dest.parent.mkdir(parents=True, exist_ok=True)
                _download_url(inc["url"], inc_dest)

        return model_path, "MODEL", f"Downloaded '{asset_id}' model from Poly Haven"

    if "hdri" in files_meta:
        hdri_variants = files_meta["hdri"]
        chosen_entry = None
        ext = ".hdr"
        for res in ("1k", "2k", "4k"):
            if res in hdri_variants:
                for fmt in ("hdr", "exr"):
                    if fmt in hdri_variants[res] and hdri_variants[res][fmt].get("url"):
                        chosen_entry = hdri_variants[res][fmt]
                        ext = f".{fmt}"
                        break
            if chosen_entry:
                break

        if not chosen_entry:
            raise ValueError(f"No downloadable HDRI found for Poly Haven asset '{asset_id}'")

        hdri_path = dest_dir / f"{asset_id}{ext}"
        _download_url(chosen_entry["url"], hdri_path)
        return hdri_path, "HDRI", f"Downloaded '{asset_id}' HDRI from Poly Haven"

    tex_dir = dest_dir / "textures"
    tex_dir.mkdir(parents=True, exist_ok=True)
    downloaded_any = False
    for map_name, resolutions in files_meta.items():
        if isinstance(resolutions, dict):
            for res in ("1k", "2k", "4k"):
                if res in resolutions:
                    entry = resolutions[res].get("jpg") or resolutions[res].get("png") or next(iter(resolutions[res].values()), None)
                    if isinstance(entry, dict) and entry.get("url"):
                        map_ext = ".png" if "png" in entry["url"].lower() else ".jpg"
                        _download_url(entry["url"], tex_dir / f"{map_name}{map_ext}")
                        downloaded_any = True
                        break

    if not downloaded_any:
        raise ValueError(f"No downloadable texture maps found for Poly Haven asset '{asset_id}'")

    return tex_dir, "TEXTURE", f"Downloaded '{asset_id}' PBR texture set from Poly Haven"


def _download_ambientcg_asset(asset_id: str, dest_dir: Path, resolution: str = "1K") -> tuple[Path | None, str, str]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    download_url = f"https://ambientcg.com/get?file={asset_id}_{resolution}-JPG.zip"
    dest_zip = dest_dir / f"{asset_id}_{resolution}-JPG.zip"
    _download_url(download_url, dest_zip)
    extracted = _extract_archive(dest_zip)
    mesh = _find_mesh_file(extracted)
    if mesh:
        return mesh, "MODEL", f"Downloaded '{asset_id}' model from ambientCG"
    return extracted, "TEXTURE", f"Downloaded '{asset_id}' PBR texture set from ambientCG"


def normalize_objects_transform(
    objects: list[bpy.types.Object],
    target_size: float = 2.0,
    ground: bool = True,
    center_xy: bool = True,
) -> dict:
    """Normalize object scale to target_size, ground base at Z=0, and center at (0, 0)."""
    valid_objs = [obj for obj in objects if obj and obj.name in bpy.data.objects]
    if not valid_objs:
        return {"success": False, "message": "No valid objects provided"}

    # Collect all mesh objects in selection + children hierarchies
    mesh_objs = set()
    all_included = set(valid_objs)
    for obj in valid_objs:
        if obj.type == "MESH":
            mesh_objs.add(obj)
        for child in obj.children_recursive:
            all_included.add(child)
            if child.type == "MESH":
                mesh_objs.add(child)

    if not mesh_objs:
        return {"success": False, "message": "No mesh objects found in selection or children"}

    bpy.context.view_layer.update()

    min_co = Vector((float("inf"), float("inf"), float("inf")))
    max_co = Vector((float("-inf"), float("-inf"), float("-inf")))

    for obj in mesh_objs:
        for corner in obj.bound_box:
            world_co = obj.matrix_world @ Vector(corner)
            min_co.x = min(min_co.x, world_co.x)
            min_co.y = min(min_co.y, world_co.y)
            min_co.z = min(min_co.z, world_co.z)
            max_co.x = max(max_co.x, world_co.x)
            max_co.y = max(max_co.y, world_co.y)
            max_co.z = max(max_co.z, world_co.z)

    dims = max_co - min_co
    orig_max_dim = max(dims.x, dims.y, dims.z)
    if orig_max_dim <= 1e-6:
        return {"success": False, "message": "Model has zero bounding volume"}

    scale_factor = float(target_size) / float(orig_max_dim) if target_size and target_size > 0 else 1.0

    roots = [obj for obj in all_included if obj.parent not in all_included]
    center_pre = (min_co + max_co) / 2.0

    # Scale roots around center
    if abs(scale_factor - 1.0) > 1e-4:
        for root in roots:
            loc, rot, scale = root.matrix_world.decompose()
            new_loc = (loc - center_pre) * scale_factor + center_pre
            new_scale = scale * scale_factor
            root.matrix_world = (
                Matrix.Translation(new_loc)
                @ rot.to_matrix().to_4x4()
                @ Matrix.Diagonal(new_scale.to_4d())
            )

    bpy.context.view_layer.update()

    # Re-measure post-scaling bounding box
    min_co_post = Vector((float("inf"), float("inf"), float("inf")))
    max_co_post = Vector((float("-inf"), float("-inf"), float("-inf")))
    for obj in mesh_objs:
        for corner in obj.bound_box:
            world_co = obj.matrix_world @ Vector(corner)
            min_co_post.x = min(min_co_post.x, world_co.x)
            min_co_post.y = min(min_co_post.y, world_co.y)
            min_co_post.z = min(min_co_post.z, world_co.z)
            max_co_post.x = max(max_co_post.x, world_co.x)
            max_co_post.y = max(max_co_post.y, world_co.y)
            max_co_post.z = max(max_co_post.z, world_co.z)

    center_post = (min_co_post + max_co_post) / 2.0
    shift = Vector((0.0, 0.0, 0.0))
    if center_xy:
        shift.x = -center_post.x
        shift.y = -center_post.y
    if ground:
        shift.z = -min_co_post.z

    if shift.length > 1e-5:
        for root in roots:
            root.location += shift

    bpy.context.view_layer.update()

    final_dims = max_co_post - min_co_post
    new_max_dim = max(final_dims.x, final_dims.y, final_dims.z)

    return {
        "success": True,
        "scale_factor": round(scale_factor, 6),
        "orig_max_dim": round(orig_max_dim, 3),
        "new_max_dim": round(new_max_dim, 3),
        "dimensions": [round(final_dims.x, 3), round(final_dims.y, 3), round(final_dims.z, 3)],
        "grounded_z": round(min_co_post.z + shift.z, 3),
    }


class NormalizeModelTool(ToolBase):
    name = "normalize_model"
    description = (
        "Normalize object/hierarchy dimensions to real-world scale (e.g. target 2.0m max dimension), "
        "place base flush on ground (Z=0), and center horizontally at (0, 0)."
    )

    def execute(self, params: dict) -> dict:
        target_size = float(params.get("target_size", 2.0))
        ground = bool(params.get("ground", True))
        center_xy = bool(params.get("center_xy", True))

        target_names = params.get("objects")
        element = params.get("element")

        if target_names and isinstance(target_names, list):
            objs = [bpy.data.objects.get(name) for name in target_names if name in bpy.data.objects]
        elif element:
            col = bpy.data.collections.get(element)
            if col:
                objs = list(col.objects)
            else:
                obj = bpy.data.objects.get(element)
                objs = [obj] if obj else []
        else:
            objs = list(bpy.context.selected_objects) or list(bpy.context.scene.objects)

        if not objs:
            return {"success": False, "message": "No objects selected or found to normalize"}

        res = normalize_objects_transform(objs, target_size=target_size, ground=ground, center_xy=center_xy)
        if not res.get("success"):
            return res

        return {
            "success": True,
            "message": (
                f"Normalized {len(objs)} object(s): Scale {res['orig_max_dim']}m -> {res['new_max_dim']}m "
                f"(Dims: {res['dimensions'][0]} x {res['dimensions'][1]} x {res['dimensions'][2]}m, Ground Z={res['grounded_z']})"
            ),
            **res,
        }


class SuperImportTool(ToolBase):
    name = "super_import"
    description = (
        "Super Import 3D assets from multi-provider online search (Poly Haven CC0, ambientCG, "
        "Sketchfab), local files, or direct URLs, with integrated automatic mesh simplification "
        "(form-preserving simplify_geometry, ratio decimate, voxel remesh) to hit a target vertex budget, "
        "and automatic scale/ground normalization."
    )

    def execute(self, params: dict) -> dict:
        from . import TOOL_REGISTRY

        action = params.get("action", "import")
        if action == "search":
            query = params.get("query") or params.get("search_query", "")
            provider = params.get("provider", "ALL")
            limit = int(params.get("limit", 20))
            hits = search_all_online_models(query, provider=provider, limit=limit)
            return {
                "success": True,
                "message": f"Found {len(hits)} asset(s) matching '{query}' across {provider}",
                "hits": hits,
            }

        source_type = (params.get("source_type") or "SEARCH").upper()
        provider = (params.get("provider") or "ALL").upper()
        simplifier_tool = (params.get("simplifier_tool") or "SIMPLIFY").upper()
        target_vertices = params.get("target_vertices", 10000)
        auto_orient = bool(params.get("auto_orient", True))
        normalize_scale = bool(params.get("normalize_scale", True))
        target_size = float(params.get("target_size", 2.0))
        ground_to_floor = bool(params.get("ground_to_floor", True))
        center_xy = bool(params.get("center_xy", True))
        collection_name = params.get("collection_name")

        raw_filepath = params.get("filepath", "")
        raw_asset_id = params.get("asset_id", "")
        raw_url = params.get("url", "")
        raw_query = params.get("query") or params.get("search_query", "")

        # Unpack provider prefix if encoded as "provider:asset_id"
        if ":" in raw_asset_id and not (raw_asset_id.startswith("http:") or raw_asset_id.startswith("https:") or (len(raw_asset_id) > 1 and raw_asset_id[1] == ":")):
            prov_prefix, actual_id = raw_asset_id.split(":", 1)
            provider = prov_prefix.upper()
            raw_asset_id = actual_id

        # Handle search resolution if asset_id is not directly given
        if source_type in ("SEARCH", "POLYHAVEN", "AMBIENTCG", "SKETCHFAB") and not raw_asset_id and raw_query:
            hits = search_all_online_models(raw_query, provider=source_type if source_type != "SEARCH" else "ALL", limit=1)
            if not hits:
                return {"success": False, "message": f"No models found for search '{raw_query}'"}
            raw_asset_id = hits[0]["id"]
            provider = hits[0]["provider"].upper()

        if not raw_filepath and not raw_asset_id and not raw_url and not raw_query:
            return {"success": False, "message": "'filepath', 'asset_id', 'query', or 'url' is required"}

        resolved_path: Path | None = None
        asset_nature = "MODEL"
        credits_info = None

        try:
            # Sketchfab
            if provider == "SKETCHFAB" or len(raw_asset_id) == 32:
                asset_id = raw_asset_id
                cache_dir = Path(tempfile.gettempdir()) / "mcp_blender_assets" / "sketchfab" / asset_id
                resolved_path, asset_nature, _msg = _download_sketchfab_asset(asset_id, cache_dir)
                credits_info = f"Sketchfab model ('{asset_id}')"

            # ambientCG
            elif provider == "AMBIENTCG" or raw_asset_id.startswith(("Wood", "Metal", "Ground", "Bricks", "Concrete", "Tiles", "Fabric", "Rock")):
                asset_id = raw_asset_id or raw_query
                cache_dir = Path(tempfile.gettempdir()) / "mcp_blender_assets" / "ambientcg" / asset_id
                resolved_path, asset_nature, _msg = _download_ambientcg_asset(asset_id, cache_dir)
                credits_info = f"ambientCG CC0 ('{asset_id}')"

            # Poly Haven
            elif provider == "POLYHAVEN" or (source_type in ("SEARCH", "POLYHAVEN") and not raw_filepath and not raw_url and not raw_asset_id.startswith("http")):
                asset_id = raw_asset_id or raw_filepath or raw_query
                cache_dir = Path(tempfile.gettempdir()) / "mcp_blender_assets" / "polyhaven" / asset_id
                resolved_path, asset_nature, _msg = _download_polyhaven_asset(asset_id, cache_dir)
                credits_info = f"Poly Haven CC0 ('{asset_id}')"

            # Direct URL
            elif source_type in ("URL", "AI_GEN") or (raw_url or raw_filepath.startswith("http") or raw_asset_id.startswith("http")):
                url = raw_url or raw_filepath or raw_asset_id
                temp_dir = Path(tempfile.mkdtemp(prefix="mcp_super_import_"))
                filename = url.split("?")[0].split("/")[-1] or "model.glb"
                if not any(filename.lower().endswith(ext) for ext in _MESH_EXTENSIONS + (".zip",)):
                    filename += ".glb"
                dest_file = temp_dir / filename
                _download_url(url, dest_file)
                resolved_path = dest_file
                credits_info = f"URL ({url})"

            # Local File
            else:
                path_str = raw_filepath or raw_asset_id
                if not path_str:
                    return {"success": False, "message": "File path is required"}
                resolved_path = Path(path_str)
                if not resolved_path.exists():
                    return {"success": False, "message": f"File not found: '{resolved_path}'"}
                credits_info = f"Local file ({resolved_path.name})"

            if resolved_path and resolved_path.is_file() and resolved_path.suffix.lower() == ".zip":
                extracted = _extract_archive(resolved_path)
                mesh_candidate = _find_mesh_file(extracted)
                if mesh_candidate:
                    resolved_path = mesh_candidate
                else:
                    resolved_path = extracted
                    asset_nature = "TEXTURE"

            if asset_nature == "HDRI" and resolved_path:
                env_tool = TOOL_REGISTRY.get("configure_world_environment")
                if env_tool:
                    res = env_tool.execute({"hdri_path": str(resolved_path)})
                    return {
                        "success": res.get("success", False),
                        "message": f"Imported world HDRI from '{resolved_path.name}'",
                        "hdri_path": str(resolved_path),
                        "credits": credits_info,
                    }
                return {"success": False, "message": "configure_world_environment tool not found"}

            if asset_nature == "TEXTURE" or (resolved_path and resolved_path.is_dir()):
                mat_tool = TOOL_REGISTRY.get("auto_load_pbr_texture_set")
                if mat_tool:
                    mat_name = f"M_{raw_asset_id or resolved_path.name}"
                    res = mat_tool.execute({"folder_path": str(resolved_path), "material_name": mat_name})
                    return {
                        "success": res.get("success", False),
                        "message": f"Loaded PBR texture set '{mat_name}'",
                        "material_name": mat_name,
                        "credits": credits_info,
                    }
                return {"success": False, "message": "auto_load_pbr_texture_set tool not found"}

            import_tool = TOOL_REGISTRY.get("import_file")
            if not import_tool:
                return {"success": False, "message": "import_file tool not registered"}

            import_res = import_tool.execute({
                "filepath": str(resolved_path),
                "auto_orient": auto_orient,
            })
            if not import_res.get("success"):
                return {"success": False, "message": import_res.get("message", "Import failed")}

            imported_names = import_res.get("imported_objects", [])
            if not imported_names:
                return {"success": False, "message": f"No objects were imported from '{resolved_path.name}'"}

            mesh_objs = [
                bpy.data.objects[name]
                for name in imported_names
                if name in bpy.data.objects and bpy.data.objects[name].type == "MESH"
            ]
            all_imported_objs = [
                bpy.data.objects[name] for name in imported_names if name in bpy.data.objects
            ]
            verts_before = sum(len(obj.data.vertices) for obj in mesh_objs)

            simplification_log = []

            # Step 1: Mesh Simplification
            if simplifier_tool != "NONE" and target_vertices and int(target_vertices) > 0:
                budget = int(target_vertices)
                for obj in mesh_objs:
                    current_verts = len(obj.data.vertices)
                    if current_verts <= budget:
                        continue

                    if simplifier_tool == "SIMPLIFY":
                        simplify_tool = TOOL_REGISTRY.get("simplify_geometry")
                        if simplify_tool:
                            res = simplify_tool.execute({
                                "object_name": obj.name,
                                "target": budget,
                                "target_unit": "VERTICES",
                            })
                            if res.get("success"):
                                simplification_log.append(
                                    f"Simplified '{obj.name}' ({current_verts} -> {res.get('result_vertices')} verts)"
                                )
                            else:
                                decimate_tool = TOOL_REGISTRY.get("decimate_mesh")
                                ratio = max(0.01, min(1.0, budget / current_verts))
                                if decimate_tool:
                                    dec_res = decimate_tool.execute({"object_name": obj.name, "ratio": ratio})
                                    simplification_log.append(
                                        f"Decimated '{obj.name}' (ratio {ratio:.2f}) due to gate rollback"
                                    )

                    elif simplifier_tool == "DECIMATE":
                        decimate_tool = TOOL_REGISTRY.get("decimate_mesh")
                        if decimate_tool:
                            ratio = max(0.01, min(1.0, budget / current_verts))
                            res = decimate_tool.execute({"object_name": obj.name, "ratio": ratio})
                            if res.get("success"):
                                simplification_log.append(f"Decimated '{obj.name}' (ratio {ratio:.2f})")

                    elif simplifier_tool == "REMESH":
                        remesh_tool = TOOL_REGISTRY.get("remesh_mesh")
                        if remesh_tool:
                            max_dim = max(obj.dimensions) if any(obj.dimensions) else 1.0
                            voxel_size = max(0.002, max_dim / 60.0)
                            res = remesh_tool.execute({
                                "object_name": obj.name,
                                "mode": "VOXEL",
                                "voxel_size": voxel_size,
                            })
                            if res.get("success"):
                                simplification_log.append(f"Remeshed '{obj.name}' (voxel {voxel_size:.4f})")

            verts_after = sum(len(obj.data.vertices) for obj in mesh_objs)

            # Step 2: Scale & Placement Normalization
            norm_log = ""
            if normalize_scale and all_imported_objs:
                norm_res = normalize_objects_transform(
                    all_imported_objs,
                    target_size=target_size,
                    ground=ground_to_floor,
                    center_xy=center_xy,
                )
                if norm_res.get("success"):
                    norm_log = (
                        f"Rescaled {norm_res['orig_max_dim']}m -> {norm_res['new_max_dim']}m "
                        f"(Dims: {norm_res['dimensions'][0]}x{norm_res['dimensions'][1]}x{norm_res['dimensions'][2]}m, Ground Z={norm_res['grounded_z']})"
                    )

            if collection_name:
                col = bpy.data.collections.get(collection_name)
                if not col:
                    col = bpy.data.collections.new(collection_name)
                    bpy.context.scene.collection.children.link(col)
                for obj in all_imported_objs:
                    if obj.name not in col.objects:
                        col.objects.link(obj)

            summary_msg = (
                f"Super imported {len(imported_names)} object(s) from '{resolved_path.name}' "
                f"(Vertices: {verts_before:,} -> {verts_after:,})"
            )
            if norm_log:
                summary_msg += f" | {norm_log}"
            if simplification_log:
                summary_msg += f" | {'; '.join(simplification_log)}"

            return {
                "success": True,
                "message": summary_msg,
                "imported_objects": imported_names,
                "source_type": source_type,
                "provider": provider,
                "simplifier_tool": simplifier_tool,
                "target_vertices": target_vertices,
                "vertices_before": verts_before,
                "vertices_after": verts_after,
                "normalize_scale": normalize_scale,
                "target_size": target_size,
                "credits": credits_info,
                "filepath": str(resolved_path),
            }

        except Exception as exc:
            return {"success": False, "message": f"Super import failed: {exc}"}
