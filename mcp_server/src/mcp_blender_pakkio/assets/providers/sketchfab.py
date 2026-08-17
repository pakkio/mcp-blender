"""Sketchfab: large model library, mixed licenses. Search is keyless;
downloading requires a SKETCHFAB_API_TOKEN (Sketchfab account, free tier
sufficient) -- https://sketchfab.com/settings/password ("API Token" tab).

The API sits behind a CloudFront AWS WAF that issues a JavaScript
bot-challenge (HTTP 202, `x-amzn-waf-action: challenge`) to non-browser
clients. httpx cannot pass it, and re-sending the resulting cookie is also
rejected (AWS WAF binds the token to the browser's TLS fingerprint). So when
a challenge is detected, API requests are re-issued *inside* a cached
headless Chrome (system-installed Chrome via Playwright -- no browser
download needed), which solves the challenge automatically.
"""

import asyncio
import json
import os
from pathlib import Path
from urllib.parse import urlencode

import httpx

from ..cache import find_cached_file
from .base import AssetHit, DownloadedAsset, ProviderError

BASE_URL = "https://api.sketchfab.com/v3"
TOKEN_ENV = "SKETCHFAB_API_TOKEN"

WAF_CHALLENGE_MSG = (
    "Sketchfab is blocked by AWS WAF (x-amzn-waf-action: challenge) and the "
    "headless-Chrome fallback is unavailable. Check that Chrome is installed "
    "and `playwright` is importable in the server environment, or download the "
    "model manually from sketchfab.com and import it via import_file."
)

# Cached Playwright page (kept alive across requests to amortise the ~5s launch).
_PAGE = None
# Guards the check-then-launch below so concurrent callers (e.g. a search
# racing a follow-up import) await the one launch instead of each seeing
# _PAGE as None and spawning their own extra, never-closed Chrome instance.
_PAGE_LOCK = asyncio.Lock()


async def _get_page():
    """Return a headless Chrome page with the Sketchfab WAF challenge solved."""
    global _PAGE
    if _PAGE is not None:
        return _PAGE
    async with _PAGE_LOCK:
        if _PAGE is not None:
            return _PAGE
        from playwright.async_api import async_playwright

        pw = await async_playwright().start()
        browser = await pw.chromium.launch(channel="chrome", headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await page.goto("https://www.sketchfab.com/", wait_until="domcontentloaded", timeout=60000)
        # Give the challenge a moment to clear (harmless if the token never appears).
        for _ in range(30):
            if any("aws-waf-token" in c.get("name", "") for c in await context.cookies()):
                break
            await asyncio.sleep(1)
        _PAGE = page
        return page


async def _browser_fetch_json(url: str, headers: dict | None = None) -> tuple[int, str] | None:
    """Fetch a URL from inside the (WAF-cleared) browser context. Returns
    (status_code, body) or None if Playwright/Chrome is unavailable."""
    try:
        page = await _get_page()
    except Exception:
        return None
    result = await page.evaluate(
        """async (args) => {
            const r = await fetch(args.url, { headers: args.headers || {}, credentials: 'include' });
            return { status: r.status, body: await r.text() };
        }""",
        {"url": url, "headers": headers or {}},
    )
    return int(result["status"]), str(result["body"])


class SketchfabProvider:
    name = "sketchfab"
    requires_token = True

    def is_available(self) -> bool:
        return True  # search works without a token; only download needs one

    def _token(self) -> str | None:
        return os.environ.get(TOKEN_ENV)

    async def _fetch(self, url: str, params: dict | None = None, headers: dict | None = None):
        """GET, transparently solving the AWS WAF challenge when it appears."""
        # Fast path: plain httpx -- works when no WAF challenge is active.
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code != 202 or resp.headers.get("x-amzn-waf-action") != "challenge":
                return resp.status_code, resp.text

        # WAF challenge: re-issue inside the browser context.
        full_url = url
        if params:
            qs = urlencode(params)
            full_url = f"{url}?{qs}" if "?" not in url else f"{url}&{qs}"
        result = await _browser_fetch_json(full_url, headers=headers)
        if result is None:
            raise ProviderError(WAF_CHALLENGE_MSG)
        status, body = result
        if status == 202:
            raise ProviderError(WAF_CHALLENGE_MSG)
        return status, body

    async def search(self, query: str, asset_type: str, limit: int) -> list[AssetHit]:
        if asset_type != "MODEL":
            return []

        status, body = await self._fetch(
            f"{BASE_URL}/search",
            {"type": "models", "q": query, "downloadable": "true", "count": limit},
        )
        if status != 200:
            raise ProviderError(f"Sketchfab search failed: HTTP {status}")

        data = json.loads(body)
        has_token = self._token() is not None
        hits = []
        for result in data.get("results", [])[:limit]:
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

        status, body = await self._fetch(
            f"{BASE_URL}/models/{asset_id}/download",
            headers={"Authorization": f"Token {token}"},
        )
        if status != 200:
            raise ProviderError(f"Sketchfab download request failed: HTTP {status}: {body[:300]}")

        data = json.loads(body)
        gltf = data.get("gltf") or data.get("source")
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