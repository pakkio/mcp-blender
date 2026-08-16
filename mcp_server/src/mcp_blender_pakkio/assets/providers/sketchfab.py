"""Sketchfab: large model library, mixed licenses. Search is keyless;
downloading requires a SKETCHFAB_API_TOKEN (Sketchfab account, free tier
sufficient) -- https://sketchfab.com/settings/password ("API Token" tab).
"""

import os
from pathlib import Path

import httpx

from ..cache import find_cached_file
from .base import AssetHit, DownloadedAsset, ProviderError

BASE_URL = "https://api.sketchfab.com/v3"
TOKEN_ENV = "SKETCHFAB_API_TOKEN"


class SketchfabProvider:
    name = "sketchfab"
    requires_token = True

    def is_available(self) -> bool:
        return True  # search works without a token; only download needs one

    def _token(self) -> str | None:
        return os.environ.get(TOKEN_ENV)

    async def search(self, query: str, asset_type: str, limit: int) -> list[AssetHit]:
        if asset_type != "MODEL":
            return []

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BASE_URL}/search",
                params={"type": "models", "q": query, "downloadable": "true", "count": limit},
            )
        if resp.status_code != 200:
            raise ProviderError(f"Sketchfab search failed: HTTP {resp.status_code}")

        body = resp.json()
        has_token = self._token() is not None
        hits = []
        for result in body.get("results", [])[:limit]:
            uid = result.get("uid")
            if not uid:
                continue
            license_info = result.get("license") or {}
            hits.append(
                AssetHit(
                    id=uid,
                    provider=self.name,
                    name=result.get("name", uid),
                    asset_type="MODEL",
                    license=license_info.get("label", "unknown"),
                    requires_token=not has_token,
                    preview_url=(result.get("thumbnails", {}).get("images") or [{}])[0].get("url"),
                    tri_count_hint=result.get("faceCount"),
                    extra={"license_url": license_info.get("url")},
                )
            )
        return hits

    async def download(self, asset_id: str, dest_dir: str) -> DownloadedAsset:
        token = self._token()
        if not token:
            raise ProviderError(
                f"Downloading Sketchfab model '{asset_id}' requires {TOKEN_ENV} in .env. "
                "Get a free token at https://sketchfab.com/settings/password (API Token tab). "
                "Search still works without it -- try Poly Haven or ambientCG instead if you don't have one."
            )

        cached = find_cached_file(self.name, asset_id)
        if cached is not None:
            return DownloadedAsset(
                filepath=str(cached), provider=self.name, asset_id=asset_id,
                license="see Sketchfab model page", attribution=f"Sketchfab model '{asset_id}' -- check license/attribution requirement on the model page",
                from_cache=True,
            )

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{BASE_URL}/models/{asset_id}/download",
                headers={"Authorization": f"Token {token}"},
            )
        if resp.status_code != 200:
            raise ProviderError(f"Sketchfab download request failed: HTTP {resp.status_code}: {resp.text[:300]}")

        body = resp.json()
        gltf = body.get("gltf") or body.get("source")
        if not gltf or not gltf.get("url"):
            raise ProviderError(f"Sketchfab model '{asset_id}' has no downloadable glTF package")

        dest_path = Path(dest_dir) / f"{asset_id}.zip"
        async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
            async with client.stream("GET", gltf["url"]) as stream:
                if stream.status_code != 200:
                    raise ProviderError(f"Sketchfab file download failed: HTTP {stream.status_code}")
                with open(dest_path, "wb") as f:
                    async for chunk in stream.aiter_bytes():
                        f.write(chunk)

        return DownloadedAsset(
            filepath=str(dest_path), provider=self.name, asset_id=asset_id,
            license="see Sketchfab model page", attribution=f"Sketchfab model '{asset_id}' -- check license/attribution requirement on the model page",
            from_cache=False,
        )
