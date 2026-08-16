"""ambientCG: CC0 PBR materials/textures, no API key required.
https://docs.ambientcg.com/
"""

from pathlib import Path

import httpx

from ..cache import find_cached_file
from .base import AssetHit, DownloadedAsset, ProviderError

BASE_URL = "https://ambientcg.com/api/v2/full_json"
DOWNLOAD_URL = "https://ambientcg.com/get"


class AmbientCGProvider:
    name = "ambientcg"
    requires_token = False

    def is_available(self) -> bool:
        return True

    async def search(self, query: str, asset_type: str, limit: int) -> list[AssetHit]:
        if asset_type != "TEXTURE":
            return []

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                BASE_URL, params={"q": query, "type": "Material", "limit": limit, "sort": "Popular"}
            )
        if resp.status_code != 200:
            raise ProviderError(f"ambientCG search failed: HTTP {resp.status_code}")

        body = resp.json()
        hits = []
        for asset in body.get("foundAssets", [])[:limit]:
            asset_id = asset.get("assetId")
            if not asset_id:
                continue
            hits.append(
                AssetHit(
                    id=asset_id,
                    provider=self.name,
                    name=asset.get("displayName", asset_id),
                    asset_type="TEXTURE",
                    license="CC0",
                    requires_token=False,
                    preview_url=asset.get("previewImage", {}).get("256-PNG") if isinstance(asset.get("previewImage"), dict) else None,
                )
            )
        return hits

    async def download(self, asset_id: str, dest_dir: str, resolution: str = "1K") -> DownloadedAsset:
        cached = find_cached_file(self.name, asset_id)
        if cached is not None:
            return DownloadedAsset(
                filepath=str(cached), provider=self.name, asset_id=asset_id,
                license="CC0", attribution=f"'{asset_id}' by ambientCG (CC0, ambientcg.com)", from_cache=True,
            )

        filename = f"{asset_id}_{resolution}-JPG.zip"
        dest_path = Path(dest_dir) / filename

        # DOWNLOAD_URL 302-redirects to the actual CDN file (confirmed live
        # against ambientcg.com/get) -- follow_redirects is required or every
        # download fails with a false "non-200" error.
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            async with client.stream("GET", DOWNLOAD_URL, params={"file": filename}) as stream:
                if stream.status_code != 200:
                    raise ProviderError(
                        f"ambientCG download failed for '{asset_id}' ({resolution}-JPG): HTTP {stream.status_code}"
                    )
                with open(dest_path, "wb") as f:
                    async for chunk in stream.aiter_bytes():
                        f.write(chunk)

        return DownloadedAsset(
            filepath=str(dest_path), provider=self.name, asset_id=asset_id,
            license="CC0", attribution=f"'{asset_id}' by ambientCG (CC0, ambientcg.com)", from_cache=False,
        )
