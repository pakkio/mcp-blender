"""Unified Super Import tool: multi-source asset search & acquisition (Poly Haven,
ambientCG, Sketchfab, direct URLs, AI models, local files) coupled with automatic,
configurable mesh simplification (form-preserving simplify_geometry, ratio
decimation, voxel remesh), target vertex budgeting, and automatic scale/ground normalization.
"""

import base64
import hashlib
import json
import math
import os
import re
import tempfile
import threading
import time
import urllib.error
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

# Sort orders for online search (panel dropdown + search_all_online_models).
# RELEVANCE keeps each provider's own relevance ranking (merged by downloads,
# the historical behaviour). The rest re-sort the merged hits client-side;
# Sketchfab additionally pushes DATE/POPULARITY/RATING server-side so its
# pagination stays in the same order. LICENSE ranks most-open first:
# CC0, then the CC-BY family, then other OSS licences, then unknown and
# restrictive ones (editorial/standard/all-rights-reserved) last.
SORT_OPTIONS = ("RELEVANCE", "POPULARITY", "DATE", "RATING", "VERTICES_DESC", "VERTICES_ASC", "DIMENSIONS", "LICENSE")


def _license_rank(lic) -> int:
    """Openness tier for a licence string (lower = more open)."""
    text = str(lic or "").lower().replace("cc-0", "cc0")
    if not text or text in ("unknown", "n/a", "none"):
        return 3
    if "cc0" in text or "public domain" in text or "cc-zero" in text:
        return 0
    if "cc" in text and "by" in text or "attribution" in text or "cc-by" in text:
        return 1
    oss_markers = ("mit", "apache", "bsd", "gpl", "lgpl", "mpl", "unlicense", "ofl",
                   "open font", "artistic", "eclipse", "mozilla", "open source", "open-source")
    if any(m in text for m in oss_markers):
        return 2
    restrictive = ("editorial", "standard", "all rights", "royalty", "commercial",
                   "ed$", " st", "(st)", "(ed)")
    if any(m in text for m in restrictive) or text.strip() in ("ed", "st"):
        return 4
    return 3


def _parse_epoch(value) -> int:
    """Epoch seconds from an int epoch or ISO-8601 string; 0 when unknown."""
    if not value:
        return 0
    try:
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip()
        if text.isdigit():
            return int(text)
        from datetime import datetime, timezone

        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return int(dt.replace(tzinfo=dt.tzinfo or timezone.utc).timestamp())
    except Exception:
        return 0


def _dim_max(dimensions) -> float:
    """Largest physical dimension from a PolyHaven-style [x, y(, z)] list."""
    try:
        vals = [float(v) for v in (dimensions or [])]
        return max(vals) if vals else 0.0
    except Exception:
        return 0.0


def _sort_hits(hits: list[dict], sort_by: str) -> list[dict]:
    """Client-side re-sort of search hits. Unknown sort falls back to relevance."""
    key = (sort_by or "RELEVANCE").upper()
    if key in ("POPULARITY", "RELEVANCE"):
        hits.sort(key=lambda h: h.get("downloads", 0), reverse=True)
    elif key == "DATE":
        hits.sort(key=lambda h: h.get("date_published", 0), reverse=True)
    elif key == "RATING":
        hits.sort(key=lambda h: (h.get("rating", 0), h.get("downloads", 0)), reverse=True)
    elif key == "VERTICES_DESC":
        hits.sort(key=lambda h: h.get("polycount", 0), reverse=True)
    elif key == "VERTICES_ASC":
        hits.sort(key=lambda h: h.get("polycount", 0))
    elif key == "DIMENSIONS":
        hits.sort(key=lambda h: (h.get("dim_max", 0.0), h.get("polycount", 0)), reverse=True)
    elif key == "LICENSE":
        hits.sort(key=lambda h: (_license_rank(h.get("license")), -(h.get("downloads", 0) or 0)))
    else:
        hits.sort(key=lambda h: h.get("downloads", 0), reverse=True)
    return hits


# Search filters (panel Filters box + search_all_online_models). All optional
# and combinable; providers apply them over a widened window so pagination
# keeps working, and the merged view re-filters for exactness.
FILTER_FORMATS = ("ANY", "GLB", "FBX", "OBJ")
FILTER_LICENSES = ("ANY", "CC0", "CC_BY", "OSS")
FILTER_VERT_BANDS = ("ANY", "LIGHT", "MEDIUM", "DENSE", "HEAVY")
# Vertex-count bands: light props, hero-prop range around the 50k pipeline
# default, dense scans, heavy AI generations. Lower bound 1 excludes hits
# with an unknown (0) count when a band is selected.
VERT_BANDS = {
    "LIGHT": (1, 10_000),
    "MEDIUM": (10_000, 50_000),
    "DENSE": (50_000, 200_000),
    "HEAVY": (200_000, None),
}
_LICENSE_FILTER_MAX_RANK = {"CC0": 0, "CC_BY": 1, "OSS": 2}
# Sketchfab tag slugs that advertise an original format (uploaders tag it;
# the `source` archive itself carries no format label). GLB/GLTF come from
# the archives dict instead -- verified live against api.sketchfab.com.
_KNOWN_FORMAT_TAGS = {
    "glb", "gltf", "fbx", "obj", "blend", "dae", "stl", "abc", "usd",
    "usdz", "ply", "3ds", "3dm", "mb", "ma", "c4d", "max", "x3d",
    "step", "iges", "sldprt", "sbsar",
}


def _epoch_year(epoch) -> int:
    """Calendar year of an epoch timestamp; 0 when unknown."""
    try:
        import datetime as _dt

        value = int(epoch or 0)
        return _dt.datetime.fromtimestamp(value).year if value > 0 else 0
    except Exception:
        return 0


def _match_format(hit: dict, file_format: str = "ANY") -> bool:
    """Keep hits that positively advertise the requested format.

    Poly Haven ships glTF (the download pipeline resolves a .glb/.gltf entry)
    and Sketchfab reports glb/gltf/usdz archives plus uploader format tags;
    anything else advertises nothing and is dropped when a format is picked.
    """
    fmt = (file_format or "ANY").upper()
    if fmt == "ANY":
        return True
    advertised = {str(f).lower() for f in (hit.get("formats") or [])}
    return fmt.lower() in advertised


def _match_filters(
    hit: dict,
    license_filter: str = "ANY",
    vert_band: str = "ANY",
    since_year: int = 0,
    author: str = "",
    min_faces: int = 0,
    max_faces: int = 0,
) -> bool:
    lf = (license_filter or "ANY").upper()
    if lf != "ANY" and _license_rank(hit.get("license")) > _LICENSE_FILTER_MAX_RANK.get(lf, 99):
        return False
    vb = (vert_band or "ANY").upper()
    if vb != "ANY" and vb in VERT_BANDS:
        lo, hi = VERT_BANDS[vb]
        verts = hit.get("polycount", 0) or 0
        if verts < lo or (hi is not None and verts > hi):
            return False
    try:
        face_lo = int(min_faces or 0)
    except Exception:
        face_lo = 0
    try:
        face_hi = int(max_faces or 0)
    except Exception:
        face_hi = 0
    if face_lo or face_hi:
        faces = hit.get("facecount", 0) or 0
        if faces <= 0 or faces < face_lo or (face_hi and faces > face_hi):
            return False
    try:
        year = int(since_year or 0)
    except Exception:
        year = 0
    if year and _epoch_year(hit.get("date_published", 0)) < year:
        return False
    needle = (author or "").strip().lower()
    if needle and needle not in str(hit.get("author", "") or "").lower():
        return False
    return True


def _filters_active(license_filter="ANY", vert_band="ANY", since_year=0, author="", file_format="ANY", min_faces=0, max_faces=0) -> bool:
    if (license_filter or "ANY").upper() != "ANY":
        return True
    if (vert_band or "ANY").upper() != "ANY":
        return True
    if (file_format or "ANY").upper() != "ANY":
        return True
    if (author or "").strip():
        return True
    for value in (since_year, min_faces, max_faces):
        try:
            if int(value or 0):
                return True
        except Exception:
            if value:
                return True
    return False


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


def _polyhaven_probe(asset_id: str, inf: dict) -> dict:
    """Filterable view of a Poly Haven index entry (same fields as a hit)."""
    return {
        "license": "CC0",
        "polycount": inf.get("polycount", 0),
        # The index reports a single "polycount" with no verts/faces split;
        # it doubles as the face-count proxy for min/max face filtering.
        "facecount": inf.get("polycount", 0),
        "date_published": _parse_epoch(inf.get("date_published")),
        "author": ", ".join((inf.get("authors") or {}).keys()),
        # The download pipeline resolves a .glb/.gltf entry for every model;
        # no other format is advertised by the index.
        "formats": ["glb", "gltf"],
    }


def search_polyhaven_models(query: str, limit: int = 15, offset: int = 0, sort_by: str = "RELEVANCE", file_format: str = "ANY", license_filter: str = "ANY", vert_band: str = "ANY", since_year: int = 0, author: str = "", min_faces: int = 0, max_faces: int = 0) -> list[dict]:
    """Search Poly Haven models. The whole index is local, so every sort order
    and filter paginates exactly. Rating is not provided by Poly Haven --
    hits carry rating=0; every model is CC0 with a glTF download."""
    assets = get_polyhaven_models_index()
    if not assets:
        return []

    needle = (query or "").lower().strip()
    words = [w for w in needle.split() if w]
    sort_key = (sort_by or "RELEVANCE").upper()

    def _matches(info):
        if not words:
            return True, 0
        name = str(info.get("name", "")).lower()
        tags = [str(t).lower() for t in info.get("tags", [])]
        cats = [str(c).lower() for c in info.get("categories", [])]
        desc = str(info.get("description", "")).lower()
        score = 0
        matched = False
        for w in words:
            if w == name:
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
        return matched, score

    ranked = []
    for asset_id, info in assets.items():
        matched, score = _matches(info)
        if not matched:
            continue
        dl = info.get("download_count", 1)
        relevance = score * (1 + math.log10(max(1, dl))) if words else float(info.get("download_count", 0))
        ranked.append((relevance, asset_id, info))

    if sort_key == "DATE":
        ranked.sort(key=lambda x: _parse_epoch(x[2].get("date_published")), reverse=True)
    elif sort_key in ("POPULARITY", "RATING"):
        # No per-asset rating on Poly Haven; both fall back to download count.
        ranked.sort(key=lambda x: x[2].get("download_count", 0), reverse=True)
    elif sort_key == "VERTICES_DESC":
        ranked.sort(key=lambda x: x[2].get("polycount", 0), reverse=True)
    elif sort_key == "VERTICES_ASC":
        ranked.sort(key=lambda x: x[2].get("polycount", 0))
    elif sort_key == "DIMENSIONS":
        ranked.sort(key=lambda x: (_dim_max(x[2].get("dimensions")), x[2].get("polycount", 0)), reverse=True)
    else:
        ranked.sort(key=lambda x: x[0], reverse=True)
    if _filters_active(license_filter, vert_band, since_year, author, file_format, min_faces, max_faces):
        ranked = [
            (rel, aid, inf) for rel, aid, inf in ranked
            if _match_filters(_polyhaven_probe(aid, inf), license_filter, vert_band, since_year, author, min_faces, max_faces)
            and _match_format(_polyhaven_probe(aid, inf), file_format)
        ]
    top_slice = [(aid, inf) for _, aid, inf in ranked[offset:offset+limit]]

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
            "date_published": _parse_epoch(inf.get("date_published")),
            "rating": 0,
            "views": 0,
            "dim_max": _dim_max(inf.get("dimensions")),
            "author": ", ".join((inf.get("authors") or {}).keys()),
            "formats": ["glb", "gltf"],
            "facecount": inf.get("polycount", 0),
        })

    return hits


_SKETCHFAB_SERVER_SORT = {
    "DATE": "-publishedAt",
    "POPULARITY": "-viewCount",
    "RATING": "-likeCount",
}


def _sketchfab_formats(result: dict) -> list[str]:
    """Formats a model positively advertises: glb/gltf/usdz archives plus any
    uploader tag slug naming a known original format (fbx/obj/blend/...).

    Verified live: archives keys are flavour names (glb/gltf/source/usdz),
    `file_format=` is ignored server-side, and uploaders tag originals
    (e.g. a 'dae' tag) -- so this is the reliable signal, best-effort for
    non-glb formats.
    """
    fmts = set()
    for key in (result.get("archives") or {}).keys():
        if str(key).lower() in ("glb", "gltf", "usdz"):
            fmts.add(str(key).lower())
    for tag in result.get("tags", []) or []:
        slug = str((tag or {}).get("slug", "") if isinstance(tag, dict) else tag).lower()
        if slug in _KNOWN_FORMAT_TAGS:
            fmts.add(slug)
    return sorted(fmts)


def search_sketchfab_models(query: str, limit: int = 15, offset: int = 0, sort_by: str = "RELEVANCE", file_format: str = "ANY", license_filter: str = "ANY", vert_band: str = "ANY", since_year: int = 0, author: str = "", min_faces: int = 0, max_faces: int = 0) -> list[dict]:
    """Search Sketchfab models catalog via keyless public search API.

    DATE/POPULARITY/RATING are pushed server-side (sort_by=-publishedAt/
    -viewCount/-likeCount) so pagination stays in order; everything else
    (other sorts, all filters) runs client-side over a widened window
    (limit+offset) before slicing the requested page. Face bounds go to the
    server exactly (min/max_face_count -- verified live); a vertex band
    without explicit face bounds adds a loose face-count prefilter (3x
    headroom on the upper edge -- faces run ~2x vertices) with exact
    client-side filtering after.
    """
    if not query:
        return []
    try:
        face_lo = int(min_faces or 0)
    except Exception:
        face_lo = 0
    try:
        face_hi = int(max_faces or 0)
    except Exception:
        face_hi = 0
    sort_key = (sort_by or "RELEVANCE").upper()
    client_side = (
        sort_key in ("VERTICES_DESC", "VERTICES_ASC", "DIMENSIONS", "LICENSE")
        or _filters_active(license_filter, vert_band, since_year, author, file_format, min_faces, max_faces)
    )
    encoded_query = urllib.parse.quote_plus(query.strip())
    count = limit + offset if client_side else limit
    fetch_offset = 0 if client_side else offset
    api_url = f"https://api.sketchfab.com/v3/search?type=models&q={encoded_query}&downloadable=true&count={count}&offset={fetch_offset}"
    server_sort = _SKETCHFAB_SERVER_SORT.get(sort_key)
    if server_sort:
        api_url += f"&sort_by={server_sort}"
    if face_lo or face_hi:
        # Explicit face bounds win over the band-derived heuristic below.
        if face_lo:
            api_url += f"&min_face_count={face_lo}"
        if face_hi:
            api_url += f"&max_face_count={face_hi}"
    else:
        vb = (vert_band or "ANY").upper()
        if vb in VERT_BANDS:
            lo, hi = VERT_BANDS[vb]
            api_url += f"&min_face_count={lo}"
            if hi is not None:
                api_url += f"&max_face_count={hi * 3}"
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
            lic = (r.get("license") or {}).get("label", "CC Attribution")
            user = (r.get("user") or {}).get("displayName") or (r.get("user") or {}).get("username") or "Sketchfab Creator"
            likes = r.get("likeCount", 0) or 0
            hits.append({
                "id": uid,
                "provider": "sketchfab",
                "name": r.get("name", uid),
                "polycount": r.get("vertexCount") or r.get("faceCount") or 0,
                "downloads": likes * 10,
                "license": lic,
                "credits": f"Sketchfab ({lic}) by {user}",
                "thumbnail_url": thumb_url,
                "asset_type": "MODEL",
                "date_published": _parse_epoch(r.get("publishedAt") or r.get("createdAt")),
                "rating": likes,
                "views": r.get("viewCount", 0) or 0,
                "dim_max": 0.0,
                "author": user,
                "formats": _sketchfab_formats(r),
                "facecount": r.get("faceCount", 0) or 0,
            })
        if client_side:
            hits = [
                h for h in hits
                if _match_filters(h, license_filter, vert_band, since_year, author, min_faces, max_faces)
                and _match_format(h, file_format)
            ]
            # RELEVANCE keeps the server order; other sorts re-sort the page.
            if sort_key != "RELEVANCE":
                _sort_hits(hits, sort_key)
            hits = hits[offset:offset+limit]
        return hits
    except Exception:
        return []


def search_ambientcg_assets(query: str, limit: int = 15, offset: int = 0, sort_by: str = "RELEVANCE", file_format: str = "ANY", license_filter: str = "ANY", vert_band: str = "ANY", since_year: int = 0, author: str = "", min_faces: int = 0, max_faces: int = 0) -> list[dict]:
    """Search ambientCG CC0 materials and assets.

    Verified live: sort=Popular and sort=Latest are honoured (other values
    fall back to the default order); results carry releaseDate, downloadCount
    and dimensionX/Y/Z. No author, licence-variant, rating or format data --
    every hit is CC0 with no reportable author/formats, so author/format and
    vertex-band filters exclude these hits when set.
    """
    encoded_query = urllib.parse.quote_plus(query.strip() if query else "Material")
    sort_key = (sort_by or "RELEVANCE").upper()
    client_side = sort_key not in ("RELEVANCE", "POPULARITY", "DATE") or _filters_active(
        license_filter, vert_band, since_year, author, file_format, min_faces, max_faces
    )
    fetch_limit = limit + offset if client_side else limit
    fetch_offset = 0 if client_side else offset
    server_sort = "Latest" if sort_key == "DATE" else "Popular"
    api_url = f"https://ambientcg.com/api/v2/full_json?q={encoded_query}&limit={fetch_limit}&sort={server_sort}&offset={fetch_offset}"
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
            dims = [a.get("dimensionX", 0) or 0, a.get("dimensionY", 0) or 0, a.get("dimensionZ", 0) or 0]
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
                "date_published": _parse_epoch(a.get("releaseDate") or a.get("earlyReleaseDate")),
                "rating": 0,
                "views": 0,
                "dim_max": max([float(v) for v in dims] or [0.0]),
                "author": "",
                "formats": [],
                "facecount": 0,
            })
        if client_side:
            hits = [
                h for h in hits
                if _match_filters(h, license_filter, vert_band, since_year, author, min_faces, max_faces)
                and _match_format(h, file_format)
            ]
            # RELEVANCE/POPULARITY/DATE keep the server order; the rest re-sort.
            if sort_key not in ("RELEVANCE", "POPULARITY", "DATE"):
                _sort_hits(hits, sort_key)
            hits = hits[offset:offset+limit]
        return hits
    except Exception:
        return []


def search_all_online_models(query: str, provider: str = "ALL", limit: int = 20, offset: int = 0, sort_by: str = "RELEVANCE", file_format: str = "ANY", license_filter: str = "ANY", vert_band: str = "ANY", since_year: int = 0, author: str = "", min_faces: int = 0, max_faces: int = 0) -> list[dict]:
    """Search online assets across providers, merged, filtered and sorted.

    sort_by: RELEVANCE (provider relevance, merged by popularity -- historical
    behaviour), POPULARITY (downloads), DATE (newest first), RATING (likes,
    mostly Sketchfab -- other providers carry 0), VERTICES_DESC/VERTICES_ASC
    (vertex count), DIMENSIONS (largest physical dimension, Poly Haven models),
    LICENSE (CC0 first, then CC-BY, then other OSS licences, restrictive last).

    Filters (all combinable): file_format GLB/FBX/OBJ (advertised formats only:
    Poly Haven glTF, Sketchfab archives + uploader format tags), license_filter
    CC0/CC_BY/OSS (max openness tier), vert_band LIGHT/MEDIUM/DENSE/HEAVY
    (vertex count; unknown counts excluded when set), since_year (published in
    or after this year; unknown dates excluded when set), author (substring of
    the creator name; ambientCG reports none and is excluded when set),
    min_faces/max_faces (face count bounds, 0 = no bound; exact server-side on
    Sketchfab, PolyHaven polycount doubles as the face proxy).
    """
    provider = (provider or "ALL").upper()
    sort_key = (sort_by or "RELEVANCE").upper()
    if sort_key not in SORT_OPTIONS:
        sort_key = "RELEVANCE"
    all_hits = []

    if provider in ("ALL", "POLYHAVEN"):
        all_hits.extend(search_polyhaven_models(
            query, limit=limit, offset=offset, sort_by=sort_key,
            file_format=file_format, license_filter=license_filter,
            vert_band=vert_band, since_year=since_year, author=author,
            min_faces=min_faces, max_faces=max_faces))

    if provider in ("ALL", "SKETCHFAB"):
        all_hits.extend(search_sketchfab_models(
            query, limit=limit, offset=offset, sort_by=sort_key,
            file_format=file_format, license_filter=license_filter,
            vert_band=vert_band, since_year=since_year, author=author,
            min_faces=min_faces, max_faces=max_faces))

    if provider in ("ALL", "AMBIENTCG"):
        all_hits.extend(search_ambientcg_assets(
            query, limit=limit, offset=offset, sort_by=sort_key,
            file_format=file_format, license_filter=license_filter,
            vert_band=vert_band, since_year=since_year, author=author,
            min_faces=min_faces, max_faces=max_faces))

    # Belt-and-braces merged filter (providers pre-filter their own page, but
    # the merged view guarantees the contract) then the requested sort.
    # RELEVANCE keeps the historical popularity-desc merge.
    if _filters_active(license_filter, vert_band, since_year, author, file_format, min_faces, max_faces):
        all_hits = [
            h for h in all_hits
            if _match_filters(h, license_filter, vert_band, since_year, author, min_faces, max_faces)
            and _match_format(h, file_format)
        ]
    _sort_hits(all_hits, sort_key)
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


def _has_baked_texture(objs) -> bool:
    """Whether any imported mesh carries a material with an image texture --
    the signal that Solid shading (grey, untextured-looking) would be lying
    about what actually got imported."""
    for obj in objs:
        if obj.type != "MESH":
            continue
        for mat in obj.data.materials:
            if not mat or not mat.use_nodes or not mat.node_tree:
                continue
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image is not None:
                    return True
    return False


def _switch_viewport_shading(shading_type: str) -> int:
    """Set every open 3D viewport to the given shading type. Returns how many
    were switched, so a headless/no-window caller can tell nothing happened
    rather than silently no-op'ing."""
    switched = 0
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type == "VIEW_3D":
                    space.shading.type = shading_type
                    switched += 1
    return switched


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


def _post_json(url: str, headers: dict, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={**headers, "Content-Type": "application/json", "User-Agent": _USER_AGENT},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_json(url: str, headers: dict) -> dict:
    req = urllib.request.Request(url, headers={**headers, "User-Agent": _USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# Hard wall-clock cap on the whole create+poll+download cycle, independent of
# how many iterations that takes -- per-call urlopen timeouts bound a single
# request, not the loop, so a run of slow-but-succeeding calls could otherwise
# add up to far longer than intended (see: 10+ minute in-Blender freeze this
# guards against when generation ran synchronously on the main thread).
_AI_GEN_DEADLINE_S = 480.0
_AI_GEN_POLL_INTERVAL_S = 3.0


class MeshyCancelled(ValueError):
    """Raised locally when a cancel_event fires mid-poll, so a worker thread
    stops hammering Meshy's status endpoint the moment the user hits Esc
    instead of idling out its full poll deadline for no reason."""


def _delete_request(url: str, headers: dict) -> None:
    req = urllib.request.Request(url, headers={**headers, "User-Agent": _USER_AGENT}, method="DELETE")
    try:
        urllib.request.urlopen(req, timeout=15).close()
    except urllib.error.HTTPError as exc:
        # 404 = task already finished/gone server-side, nothing to cancel.
        if exc.code not in (200, 202, 204, 404):
            raise


def cancel_meshy_task(task_id: str, label: str) -> None:
    """Best-effort: actually tell Meshy to stop a running task, rather than
    just walking away from it client-side (which previously left it running,
    and billing, on Meshy's servers after a Blender-side Esc). Swallows
    failures -- this is a courtesy call made from a fire-and-forget thread
    after the UI has already cancelled, so there's no one left to report an
    error to and nothing further the caller can do about it."""
    try:
        headers = _meshy_headers()
        base_url = (
            "https://api.meshy.ai/v2/text-to-3d"
            if label in ("preview", "refine")
            else "https://api.meshy.ai/openapi/v1/image-to-3d"
        )
        _delete_request(f"{base_url}/{task_id}", headers)
    except Exception:
        pass


class MeshyTimeout(ValueError):
    """Meshy task didn't finish inside our wall-clock deadline. Meshy's own
    server-side queue can genuinely sit at e.g. 99% for a long time under
    load -- the task is usually still running there, not dead -- so this
    carries enough (task_id/label) for a caller to resume polling the same
    task later instead of discarding it and re-submitting (and re-billing)
    a whole new generation."""

    def __init__(self, base_url: str, task_id: str, label: str, last_status: str):
        super().__init__(f"Meshy {label} timed out for task '{task_id}' (last status: {last_status})")
        self.base_url = base_url
        self.task_id = task_id
        self.label = label


def _poll_meshy_task(
    base_url: str, task_id: str, headers: dict, status_cb, label: str, cancel_event=None
) -> dict:
    """Poll a Meshy task (preview or refine share the same GET .../{id} +
    status contract) until SUCCEEDED, bounded by its own wall-clock deadline.

    cancel_event, if given, is checked once per tick (the same 3s cadence as
    the poll itself) so a user-triggered cancel stops this loop within one
    tick instead of running out its full multi-minute deadline for nothing
    once the caller has already moved on."""
    task_url = f"{base_url}/{task_id}"
    last_status = "UNKNOWN"
    deadline = time.monotonic() + _AI_GEN_DEADLINE_S
    while time.monotonic() < deadline:
        if cancel_event is not None and cancel_event.is_set():
            raise MeshyCancelled(f"Meshy {label} polling cancelled for task '{task_id}'")
        try:
            data = _get_json(task_url, headers)
        except Exception as exc:
            raise ValueError(f"Meshy {label} task lookup failed: {exc}") from exc
        last_status = data.get("status", last_status)
        progress = data.get("progress")
        if status_cb:
            status_cb(f"Meshy ({label}): {last_status}" + (f" ({progress}%)" if progress is not None else ""))
        if last_status == "SUCCEEDED":
            return data
        if last_status in ("FAILED", "CANCELED", "EXPIRED"):
            err = (data.get("task_error") or {}).get("message") or "Unknown error"
            raise ValueError(f"Meshy {label} {last_status}: {err}")
        time.sleep(_AI_GEN_POLL_INTERVAL_S)
    raise MeshyTimeout(base_url, task_id, label, last_status)


def _meshy_headers() -> dict:
    from ..config import load_env_vars
    load_env_vars()
    token = os.environ.get("MESHY_API_KEY")
    if not token:
        raise ValueError(
            "Meshy AI generation requires a free MESHY_API_KEY. "
            "Get one at https://www.meshy.ai/api and add it to your .env file."
        )
    return {"Authorization": f"Bearer {token}"}


def _download_meshy_result(data: dict, task_id: str, dest_dir: Path, status_cb) -> Path:
    model_url = data.get("model_urls", {}).get("glb") or data.get("model_url")
    if not model_url:
        raise ValueError(f"Meshy task '{task_id}' succeeded but returned no downloadable model URL")
    if status_cb:
        status_cb("Meshy: downloading generated model...")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "model.glb"
    _download_url(model_url, dest_file)
    return dest_file


def _generate_meshy_model(
    prompt: str, dest_dir: Path, status_cb=None, texture: bool = True, on_task=None, cancel_event=None
) -> tuple[Path, str]:
    """Text-to-3D via Meshy AI: create a preview (untextured geometry) task,
    poll it, then -- since texture=True by default -- submit and poll a
    'refine' task against it to bake PBR textures (Meshy has no single-call
    textured mode) before downloading the final GLB. Pure network/file I/O,
    no bpy calls -- safe to run on a background thread; status_cb(str), if
    given, is called on every poll tick so a caller polling from Blender's
    main thread can show live progress without blocking on this.

    on_task(task_id, label), if given, fires as soon as each task_id is known
    -- before the caller has a "SUCCEEDED" result -- so it can be cancelled
    (see cancel_meshy_task) while still in flight. cancel_event, if given, is
    checked by the underlying poll and raises MeshyCancelled promptly instead
    of running out the full poll deadline.

    If a poll hits its wall-clock deadline (MeshyTimeout), the task is often
    still running server-side -- resume_meshy_model_job can pick the same
    task_id back up later instead of burning a fresh generation."""
    headers = _meshy_headers()
    base_url = "https://api.meshy.ai/v2/text-to-3d"
    if status_cb:
        status_cb(f"Meshy: submitting prompt '{prompt}'...")
    try:
        created = _post_json(base_url, headers, {"mode": "preview", "prompt": prompt, "art_style": "realistic"})
    except Exception as exc:
        raise ValueError(f"Meshy task creation failed: {exc}") from exc
    task_id = created.get("result")
    if not task_id:
        raise ValueError(f"No task ID returned by Meshy: {created}")
    if on_task:
        on_task(task_id, "preview")

    data = _poll_meshy_task(base_url, task_id, headers, status_cb, "preview", cancel_event=cancel_event)

    if texture:
        try:
            refined = _post_json(base_url, headers, {"mode": "refine", "preview_task_id": task_id})
        except Exception as exc:
            raise ValueError(f"Meshy refine (texturing) task creation failed: {exc}") from exc
        refine_task_id = refined.get("result")
        if not refine_task_id:
            raise ValueError(f"No refine task ID returned by Meshy: {refined}")
        task_id = refine_task_id
        if on_task:
            on_task(task_id, "refine")
        data = _poll_meshy_task(base_url, refine_task_id, headers, status_cb, "refine", cancel_event=cancel_event)

    dest_file = _download_meshy_result(data, task_id, dest_dir, status_cb)
    return dest_file, f"Meshy AI ('{prompt}')"


def resume_meshy_model_job(
    task_id: str, label: str, dest_dir: Path, status_cb=None, texture: bool = True, on_task=None, cancel_event=None
) -> tuple[Path, str]:
    """Pick a Meshy job back up after a MeshyTimeout instead of re-submitting
    (and re-billing) a whole new generation: re-poll the same task_id from
    where it left off, then continue the pipeline (preview -> refine ->
    download) exactly as a fresh run would."""
    headers = _meshy_headers()
    base_url = "https://api.meshy.ai/v2/text-to-3d"
    if on_task:
        on_task(task_id, label)

    data = _poll_meshy_task(base_url, task_id, headers, status_cb, label, cancel_event=cancel_event)

    if label == "preview" and texture:
        try:
            refined = _post_json(base_url, headers, {"mode": "refine", "preview_task_id": task_id})
        except Exception as exc:
            raise ValueError(f"Meshy refine (texturing) task creation failed: {exc}") from exc
        refine_task_id = refined.get("result")
        if not refine_task_id:
            raise ValueError(f"No refine task ID returned by Meshy: {refined}")
        task_id = refine_task_id
        if on_task:
            on_task(task_id, "refine")
        data = _poll_meshy_task(base_url, refine_task_id, headers, status_cb, "refine", cancel_event=cancel_event)

    dest_file = _download_meshy_result(data, task_id, dest_dir, status_cb)
    return dest_file, "Meshy AI (resumed)"


def _generate_tripo_model(prompt: str, dest_dir: Path, status_cb=None) -> tuple[Path, str]:
    """Text-to-3D via Tripo3D: create a task, poll until it succeeds, then
    download the resulting GLB. Same threading contract as
    _generate_meshy_model above."""
    from ..config import load_env_vars
    load_env_vars()
    token = os.environ.get("TRIPO_API_KEY")
    if not token:
        raise ValueError(
            "Tripo3D generation requires a free TRIPO_API_KEY. "
            "Get one at https://platform.tripo3d.ai and add it to your .env file."
        )

    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.tripo3d.ai/v2/openapi"
    if status_cb:
        status_cb(f"Tripo3D: submitting prompt '{prompt}'...")
    try:
        created = _post_json(f"{base_url}/task", headers, {"type": "text_to_model", "prompt": prompt})
    except Exception as exc:
        raise ValueError(f"Tripo3D task creation failed: {exc}") from exc
    task_id = (created.get("data") or {}).get("task_id")
    if not task_id:
        raise ValueError(f"No task_id returned by Tripo3D: {created}")

    model_url = _poll_tripo_task(base_url, task_id, headers, status_cb, "text-to-3d")

    if status_cb:
        status_cb("Tripo3D: downloading generated model...")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "model.glb"
    _download_url(model_url, dest_file)
    return dest_file, f"Tripo3D ('{prompt}')"


def generate_ai_model_job(provider: str, prompt: str, status_cb=None, on_task=None, cancel_event=None) -> tuple[Path, str]:
    """Shared entry point for MESHY/TRIPO text-to-3D generation. Pure network
    I/O -- no bpy calls -- so callers that care about not freezing Blender's
    UI (e.g. the viewport panel's AI Generate button) can run this on a
    background thread and poll status_cb's output from a bpy.app.timers/modal
    tick instead of blocking the main thread for the whole generation.

    on_task/cancel_event are Meshy-only (see _generate_meshy_model) -- Tripo3D
    has no cancel endpoint wired up here, so they're accepted but ignored for
    that provider rather than making callers branch on it."""
    provider = provider.upper()
    cache_key = f"{provider.lower()}_prompt_{prompt.replace(' ', '_')[:40]}"
    cache_dir = Path(tempfile.gettempdir()) / "mcp_blender_assets" / provider.lower() / cache_key
    if provider == "MESHY":
        return _generate_meshy_model(prompt, cache_dir, status_cb=status_cb, on_task=on_task, cancel_event=cancel_event)
    if provider == "TRIPO":
        return _generate_tripo_model(prompt, cache_dir, status_cb=status_cb)
    raise ValueError(f"Unknown AI provider '{provider}' (expected MESHY or TRIPO)")


def resume_ai_model_job(task_id: str, label: str, prompt: str, status_cb=None, on_task=None, cancel_event=None) -> tuple[Path, str]:
    """Companion to generate_ai_model_job for the MeshyTimeout case: re-poll
    the task Meshy was still chewing on instead of starting over. Uses the
    same cache_dir derivation as generate_ai_model_job so a resumed job lands
    (and caches) exactly where the original run would have."""
    cache_key = f"meshy_prompt_{prompt.replace(' ', '_')[:40]}"
    cache_dir = Path(tempfile.gettempdir()) / "mcp_blender_assets" / "meshy" / cache_key
    return resume_meshy_model_job(task_id, label, cache_dir, status_cb=status_cb, on_task=on_task, cancel_event=cancel_event)


# Image-to-3D: same threading contract as the text path above. The source
# image rides along as a base64 data URI -- every supported provider accepts
# that encoding for uploads, and it means no public hosting is ever needed.
_AI_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
_AI_IMAGE_MAX_BYTES = 20 * 1024 * 1024

# Both image-to-3D providers can remesh to a polygon budget server-side, and
# doing it there is strictly better than downloading the raw generation and
# reducing it here: Meshy's default output runs to ~2M triangles (78 MB for a
# single cat), which costs a long download, a long import, and then minutes of
# local form-preserving reduction on a mesh two orders of magnitude above the
# budget. Asking for a budget up front makes every one of those steps small.
#
# The request is deliberately looser than the final vertex budget -- roughly
# four triangles per target vertex, against the ~2 a triangulated mesh
# actually needs -- so the local simplify pass still has real headroom to
# spend on shape rather than merely hitting the count.
_AI_POLYCOUNT_PER_VERTEX = 4
_AI_POLYCOUNT_MIN = 1_000
_AI_POLYCOUNT_MAX = 300_000


def _target_polycount(target_vertices) -> int | None:
    """Provider-side triangle budget for a local target vertex count, or None
    to leave the provider's own default alone (what 'keep original' wants)."""
    if not target_vertices or int(target_vertices) <= 0:
        return None
    wanted = int(target_vertices) * _AI_POLYCOUNT_PER_VERTEX
    return max(_AI_POLYCOUNT_MIN, min(_AI_POLYCOUNT_MAX, wanted))


def _encode_image_data_uri(image_path: str | Path) -> str:
    import mimetypes

    path = Path(image_path)
    if not path.is_file():
        raise ValueError(f"Image file not found: '{path}'")
    if path.suffix.lower() not in _AI_IMAGE_EXTENSIONS:
        raise ValueError(
            f"Unsupported image type '{path.suffix}'. Supported: "
            f"{', '.join(_AI_IMAGE_EXTENSIONS)}."
        )
    data = path.read_bytes()
    if not data:
        raise ValueError(f"Image file '{path}' is empty.")
    if len(data) > _AI_IMAGE_MAX_BYTES:
        raise ValueError(f"Image '{path.name}' exceeds the {_AI_IMAGE_MAX_BYTES // (1024 * 1024)} MB upload cap.")
    mime = mimetypes.guess_type(str(path))[0] or "image/png"
    return f"data:{mime};base64,{base64.b64encode(data).decode('ascii')}"


def _image_job_cache_dir(provider: str, image_path_str: str, polycount=None) -> Path:
    """Content-addressed cache dir, so regenerating from the same picture is a
    disk hit instead of a second paid generation.

    The polygon budget is part of the key: the same picture asked for at a
    different budget is a different model, and reusing the old one would
    silently ignore the new budget."""
    digest = hashlib.sha256(Path(image_path_str).read_bytes()).hexdigest()[:12]
    suffix = f"_p{polycount}" if polycount else ""
    return Path(tempfile.gettempdir()) / "mcp_blender_assets" / provider.lower() / f"img_{digest}{suffix}"


def generate_ai_model_image_job(
    provider: str, image_path: str, status_cb=None, target_vertices=None, on_task=None, cancel_event=None
) -> tuple[Path, str]:
    """Shared entry point for MESHY/TRIPO image-to-3D generation. Same pure
    network-I/O contract as generate_ai_model_job above.

    target_vertices is the budget the caller intends to reduce to locally; it
    is converted to a provider-side polygon budget so the generation arrives
    near that size instead of at the provider's multi-million-triangle
    default. Pass None to get the provider's raw output untouched.

    on_task/cancel_event are Meshy-only, same as generate_ai_model_job.
    """
    provider = provider.upper()
    polycount = _target_polycount(target_vertices)
    cache_dir = _image_job_cache_dir(provider, image_path, polycount)
    if cache_dir.is_file() or (cache_dir / "model.glb").is_file():
        model_file = cache_dir if cache_dir.is_file() else cache_dir / "model.glb"
        if status_cb:
            status_cb("Cache: previously generated from this exact image, reusing...")
        return model_file, f"{provider.capitalize()} AI (image-to-3d, cached)"
    if provider == "MESHY":
        return _generate_meshy_image_model(
            image_path, cache_dir, status_cb=status_cb, target_polycount=polycount,
            on_task=on_task, cancel_event=cancel_event,
        )
    if provider == "TRIPO":
        return _generate_tripo_image_model(image_path, cache_dir, status_cb=status_cb, target_polycount=polycount)
    raise ValueError(f"Unknown AI provider '{provider}' (expected MESHY or TRIPO)")


def _generate_meshy_image_model(
    image_path: str, dest_dir: Path, status_cb=None, target_polycount=None, on_task=None, cancel_event=None
) -> tuple[Path, str]:
    """Image-to-3D via Meshy AI (/v2/image-to-3d): single-stage, always
    textured -- unlike text mode there is no preview/refine split.

    target_polycount enables Meshy's own remesher, which returns a model
    already near the budget instead of the ~2M-triangle raw generation."""
    headers = _meshy_headers()
    # NB: unlike text-to-3d (which lives at /v2/text-to-3d), the image
    # pipeline is documented under /openapi/v1 -- /v2/image-to-3d 404s.
    base_url = "https://api.meshy.ai/openapi/v1/image-to-3d"
    if status_cb:
        status_cb("Meshy: uploading image...")
    payload = {"image_url": _encode_image_data_uri(image_path)}
    if target_polycount:
        payload["should_remesh"] = True
        payload["target_polycount"] = int(target_polycount)
    try:
        created = _post_json(base_url, headers, payload)
    except Exception as exc:
        raise ValueError(f"Meshy task creation failed: {exc}") from exc
    task_id = created.get("result")
    if not task_id:
        raise ValueError(f"No task ID returned by Meshy: {created}")
    if on_task:
        on_task(task_id, "image-to-3d")

    data = _poll_meshy_task(base_url, task_id, headers, status_cb, "image-to-3d", cancel_event=cancel_event)

    model_url = data.get("model_urls", {}).get("glb") or data.get("model_url")
    if not model_url:
        raise ValueError(f"Meshy task '{task_id}' succeeded but returned no downloadable model URL")

    if status_cb:
        status_cb("Meshy: downloading generated model...")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "model.glb"
    _download_url(model_url, dest_file)
    budget = f", remeshed to ~{int(target_polycount):,} tris" if target_polycount else ""
    return dest_file, f"Meshy AI (image-to-3d{budget})"


def _poll_tripo_task(base_url: str, task_id: str, headers: dict, status_cb, label: str) -> str:
    """Poll a Tripo task to terminal status and return its model download URL.
    Shared by text_to_model and image_to_model (same task lifecycle)."""
    task_url = f"{base_url}/task/{task_id}"
    model_url = None
    last_status = "unknown"
    deadline = time.monotonic() + _AI_GEN_DEADLINE_S
    while time.monotonic() < deadline:
        try:
            data = _get_json(task_url, headers)
        except Exception as exc:
            raise ValueError(f"Tripo3D {label} task lookup failed: {exc}") from exc
        payload = data.get("data") or {}
        last_status = payload.get("status", last_status)
        progress = payload.get("progress")
        if status_cb:
            status_cb(f"Tripo3D ({label}): {last_status}" + (f" ({progress}%)" if progress is not None else ""))
        if last_status == "success":
            model_url = (payload.get("output") or {}).get("model")
            break
        if last_status in ("failed", "cancelled", "canceled", "banned", "expired"):
            raise ValueError(f"Tripo3D {label} generation {last_status}")
        time.sleep(_AI_GEN_POLL_INTERVAL_S)

    if not model_url:
        raise ValueError(f"Tripo3D {label} generation timed out (last status: {last_status})")
    return model_url


def _generate_tripo_image_model(image_path: str, dest_dir: Path, status_cb=None, target_polycount=None) -> tuple[Path, str]:
    """Image-to-3D via Tripo3D: submit the local image as a base64 data URI,
    poll until success, download the GLB.

    Tripo spells the same server-side budget `face_limit`."""
    from ..config import load_env_vars
    load_env_vars()
    token = os.environ.get("TRIPO_API_KEY")
    if not token:
        raise ValueError(
            "Tripo3D generation requires a free TRIPO_API_KEY. "
            "Get one at https://platform.tripo3d.ai and add it to your .env file."
        )

    headers = {"Authorization": f"Bearer {token}"}
    base_url = "https://api.tripo3d.ai/v2/openapi"
    if status_cb:
        status_cb("Tripo3D: uploading image...")
    payload = {"type": "image_to_model", "file": _encode_image_data_uri(image_path)}
    if target_polycount:
        payload["face_limit"] = int(target_polycount)
    try:
        created = _post_json(f"{base_url}/task", headers, payload)
    except Exception as exc:
        raise ValueError(f"Tripo3D task creation failed: {exc}") from exc
    task_id = (created.get("data") or {}).get("task_id")
    if not task_id:
        raise ValueError(f"No task_id returned by Tripo3D: {created}")

    model_url = _poll_tripo_task(base_url, task_id, headers, status_cb, "image-to-3d")

    if status_cb:
        status_cb("Tripo3D: downloading generated model...")
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_file = dest_dir / "model.glb"
    _download_url(model_url, dest_file)
    budget = f", limited to ~{int(target_polycount):,} faces" if target_polycount else ""
    return dest_file, f"Tripo3D (image-to-3d{budget})"


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
        "Sketchfab), AI text-to-3D generation (Meshy AI, Tripo3D -- requires MESHY_API_KEY/"
        "TRIPO_API_KEY), local files, or direct URLs, with integrated automatic mesh simplification "
        "(form-preserving simplify_geometry, ratio decimate, voxel remesh) to hit a target vertex budget, "
        "and automatic scale/ground normalization."
    )

    def execute(self, params: dict) -> dict:
        from . import TOOL_REGISTRY
        from .progress_hud_ops import push_hud_update

        action = params.get("action", "import")
        if action == "search":
            query = params.get("query") or params.get("search_query", "")
            provider = params.get("provider", "ALL")
            limit = int(params.get("limit", 20))
            sort_by = params.get("sort_by", "RELEVANCE")
            hits = search_all_online_models(
                query, provider=provider, limit=limit, sort_by=sort_by,
                file_format=params.get("file_format", "ANY"),
                license_filter=params.get("license_filter", "ANY"),
                vert_band=params.get("vert_band", "ANY"),
                since_year=params.get("since_year", 0),
                author=params.get("author", ""),
                min_faces=params.get("min_faces", 0),
                max_faces=params.get("max_faces", 0),
            )
            return {
                "success": True,
                "message": f"Found {len(hits)} asset(s) matching '{query}' across {provider}",
                "hits": hits,
            }

        source_type = (params.get("source_type") or "SEARCH").upper()
        provider = (params.get("provider") or "ALL").upper()
        simplifier_tool = (params.get("simplifier_tool") or "SIMPLIFY").upper()
        target_vertices = params.get("target_vertices", 50000)
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
        raw_prompt = params.get("prompt", "")

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

        # force_redraw=True throughout: Super Import runs entirely inside one
        # blocking Operator.execute()/tool-dispatch call (download + import +
        # simplify), so a plain tag_redraw() would never actually paint until
        # the whole pass is done -- see push_hud_update's docstring.
        push_hud_update(
            title="Super Import",
            status=f"Resolving asset from {provider}...",
            progress_percent=5.0,
            force_redraw=True,
        )

        try:
            # AI text-to-3D generation (Meshy AI / Tripo3D) -- checked first so an
            # explicit provider/source_type never gets misrouted by the loose
            # heuristics (e.g. length-32 id) the other branches use to guess.
            if source_type == "AI_GEN" or provider in ("MESHY", "TRIPO"):
                prompt_text = raw_prompt.strip() or raw_query.strip()
                if not prompt_text and "_prompt_" in raw_asset_id:
                    prompt_text = raw_asset_id.split("_prompt_", 1)[-1].replace("_", " ").strip()
                if not prompt_text:
                    return {"success": False, "message": "'prompt' is required for AI generation"}

                resolved_path, credits_info = generate_ai_model_job(provider, prompt_text)

            # Sketchfab
            elif provider == "SKETCHFAB" or len(raw_asset_id) == 32:
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
            elif source_type == "URL" or (raw_url or raw_filepath.startswith("http") or raw_asset_id.startswith("http")):
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

            push_hud_update(
                title="Super Import",
                status=f"Importing '{resolved_path.name}'...",
                progress_percent=45.0,
                force_redraw=True,
            )

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

            # A model that arrives with a baked baseColor texture still renders
            # flat grey in Solid shading -- the default 3D viewport mode -- which
            # is what made a correctly-generated, fully textured AI asset look
            # like a broken one. Report it either way so a caller isn't left
            # guessing, and switch to Material Preview when it would otherwise
            # be invisible.
            textured = _has_baked_texture(mesh_objs)
            switched_viewport = False
            if textured and not bpy.app.background:
                switched_viewport = _switch_viewport_shading("MATERIAL") > 0

            simplification_log = []

            # Step 1: Mesh Simplification
            if simplifier_tool != "NONE" and target_vertices and int(target_vertices) > 0:
                budget = int(target_vertices)
                total_mesh_objs = len(mesh_objs)
                for idx, obj in enumerate(mesh_objs, 1):
                    current_verts = len(obj.data.vertices)
                    if current_verts <= budget:
                        continue

                    push_hud_update(
                        title="Super Import",
                        status=f"Simplifying '{obj.name}' ({idx}/{total_mesh_objs})...",
                        progress_percent=50.0 + (idx - 1) / total_mesh_objs * 35.0,
                        step_current=idx,
                        step_total=total_mesh_objs,
                        force_redraw=True,
                    )

                    if simplifier_tool == "SIMPLIFY":
                        simplify_tool = TOOL_REGISTRY.get("simplify_geometry")
                        if simplify_tool:
                            res = simplify_tool.execute({
                                "object_name": obj.name,
                                "target": budget,
                                "target_unit": "VERTICES",
                                # simplify_geometry is the only step here that
                                # can run for minutes, so it drives the HUD
                                # itself for the duration -- inside this
                                # object's slice of the 50-85% band, so the bar
                                # keeps moving instead of freezing on the
                                # "Simplifying..." frame pushed just above.
                                "_hud": {
                                    "base": 50.0 + (idx - 1) / total_mesh_objs * 35.0,
                                    "span": 35.0 / total_mesh_objs,
                                },
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
                                    if dec_res.get("success"):
                                        simplification_log.append(
                                            f"Decimated '{obj.name}' (ratio {ratio:.2f}) due to gate rollback"
                                        )
                                    else:
                                        simplification_log.append(
                                            f"'{obj.name}' left unreduced: {res.get('message')} | "
                                            f"decimate fallback also failed: {dec_res.get('message')}"
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
                push_hud_update(
                    title="Super Import",
                    status="Normalizing scale & placement...",
                    progress_percent=90.0,
                    force_redraw=True,
                )
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
            summary_msg += " | textured: yes" if textured else " | textured: no"
            if switched_viewport:
                summary_msg += " (viewport switched to Material Preview)"
            if norm_log:
                summary_msg += f" | {norm_log}"
            if simplification_log:
                summary_msg += f" | {'; '.join(simplification_log)}"

            push_hud_update(
                title="Super Import",
                status="Done",
                progress_percent=100.0,
                completed_summary=summary_msg[:80],
                auto_hide_seconds=6.0,
                force_redraw=True,
            )

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
                "textured": textured,
                "viewport_switched_to_material_preview": switched_viewport,
            }

        except Exception as exc:
            return {"success": False, "message": f"Super import failed: {exc}"}
