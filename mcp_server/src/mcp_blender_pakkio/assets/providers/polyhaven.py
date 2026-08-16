"""Poly Haven: CC0 models/textures/HDRIs, no API key required.
https://api.polyhaven.com/ -- no free-text search endpoint, so search()
fetches the type's asset index and filters client-side on name/tag/category.

The /files/<id> response for models returns a .gltf file whose "include"
map lists the .bin and texture files it references by path *relative to
the .gltf itself* -- confirmed live against api.polyhaven.com/files/ArmChair_01.
Those must be downloaded alongside the .gltf into the same relative layout,
or Blender's glTF importer fails to resolve them.
"""

from pathlib import Path

import httpx

from ..cache import find_cached_file
from .base import AssetHit, DownloadedAsset, ProviderError

BASE_URL = "https://api.polyhaven.com"
_TYPE_PARAM = {"MODEL": "models", "TEXTURE": "textures", "HDRI": "hdris"}


class PolyHavenProvider:
    name = "polyhaven"
    requires_token = False

    def is_available(self) -> bool:
        return True

    async def search(self, query: str, asset_type: str, limit: int) -> list[AssetHit]:
        type_param = _TYPE_PARAM.get(asset_type)
        if type_param is None:
            return []

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(f"{BASE_URL}/assets", params={"t": type_param})
        if resp.status_code != 200:
            raise ProviderError(f"Poly Haven search failed: HTTP {resp.status_code}")

        assets = resp.json()
        needle = query.lower().strip()
        hits: list[AssetHit] = []
        for asset_id, info in assets.items():
            name = info.get("name", asset_id)
            haystack = " ".join(
                [name.lower(), asset_id.lower(), " ".join(info.get("tags") or []), " ".join(info.get("categories") or [])]
            )
            if needle and needle not in haystack:
                continue
            hits.append(
                AssetHit(
                    id=asset_id,
                    provider=self.name,
                    name=name,
                    asset_type=asset_type,
                    license="CC0",
                    requires_token=False,
                    preview_url=f"https://cdn.polyhaven.com/asset_img/thumbs/{asset_id}.png?width=256",
                )
            )
            if len(hits) >= limit:
                break

        return hits

    async def download(self, asset_id: str, dest_dir: str) -> DownloadedAsset:
        cached = find_cached_file(self.name, asset_id)
        if cached is not None:
            return DownloadedAsset(
                filepath=str(cached), provider=self.name, asset_id=asset_id,
                license="CC0", attribution=f"'{asset_id}' by Poly Haven (CC0, polyhaven.com)", from_cache=True,
            )

        async with httpx.AsyncClient(timeout=60.0) as client:
            files_resp = await client.get(f"{BASE_URL}/files/{asset_id}")
        if files_resp.status_code != 200:
            raise ProviderError(f"Poly Haven asset '{asset_id}' not found (HTTP {files_resp.status_code})")

        files = files_resp.json()
        entry, ext = _pick_model_entry(files)
        if entry is None:
            raise ProviderError(f"Poly Haven asset '{asset_id}' has no downloadable glTF/GLB file")

        dest_path = Path(dest_dir) / f"{asset_id}{ext}"
        await _stream_download(entry["url"], dest_path)

        # The .gltf references its .bin and textures by path relative to
        # itself via "include" -- fetch those into the same relative layout.
        for relative_path, include_meta in (entry.get("include") or {}).items():
            include_dest = dest_path.parent / relative_path
            include_dest.parent.mkdir(parents=True, exist_ok=True)
            await _stream_download(include_meta["url"], include_dest)

        return DownloadedAsset(
            filepath=str(dest_path), provider=self.name, asset_id=asset_id,
            license="CC0", attribution=f"'{asset_id}' by Poly Haven (CC0, polyhaven.com)", from_cache=False,
        )


async def _stream_download(url: str, dest_path: Path) -> None:
    async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
        async with client.stream("GET", url) as stream:
            if stream.status_code != 200:
                raise ProviderError(f"Poly Haven download failed for '{url}': HTTP {stream.status_code}")
            with open(dest_path, "wb") as f:
                async for chunk in stream.aiter_bytes():
                    f.write(chunk)


def _pick_model_entry(files: dict) -> tuple[dict | None, str]:
    gltf = files.get("gltf") or {}
    for resolution in ("1k", "2k", "4k", "8k"):
        variant = gltf.get(resolution)
        if not variant:
            continue
        entry = variant.get("gltf") or next(iter(variant.values()), None)
        if entry and entry.get("url"):
            url = entry["url"]
            return entry, ".glb" if url.lower().endswith(".glb") else ".gltf"
    return None, ""
