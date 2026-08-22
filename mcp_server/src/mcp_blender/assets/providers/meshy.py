import asyncio
import os
from pathlib import Path
import httpx

from ..cache import find_cached_file
from . import _image as image_util
from .base import AssetHit, DownloadedAsset, ProviderError

BASE_URL = "https://api.meshy.ai/v2/text-to-3d"
# Unlike text-to-3d (/v2), the image pipeline is documented under /openapi/v1.
IMAGE_BASE_URL = "https://api.meshy.ai/openapi/v1/image-to-3d"


class MeshyProvider:
    name = "meshy"
    requires_token = True

    def _get_token(self) -> str | None:
        return os.environ.get("MESHY_API_KEY")

    def is_available(self) -> bool:
        return bool(self._get_token())

    async def search(self, query: str, asset_type: str, limit: int) -> list[AssetHit]:
        if asset_type != "MODEL":
            return []

        token = self._get_token()
        default_gen_hit = AssetHit(
            id=f"meshy_prompt_{query.replace(' ', '_')[:30]}",
            provider=self.name,
            name=f"Meshy AI Generate: '{query}'",
            asset_type="MODEL",
            license="Proprietary / User Generated",
            requires_token=True,
            tri_count_hint=30000,
            extra={"prompt": query, "note": "Requires MESHY_API_KEY"},
        )
        if not token:
            return [default_gen_hit]

        headers = {"Authorization": f"Bearer {token}"}
        hits = [default_gen_hit]
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(BASE_URL, headers=headers, params={"pageSize": limit})
            if resp.status_code == 200:
                body = resp.json()
                task_list = body if isinstance(body, list) else body.get("result", [])
                if isinstance(task_list, list):
                    for task in task_list[:limit]:
                        tid = task.get("id")
                        if not tid:
                            continue
                        p = task.get("prompt", f"Meshy Task {tid}")
                        if query.lower() in p.lower() or not query:
                            hits.append(
                                AssetHit(
                                    id=tid,
                                    provider=self.name,
                                    name=p,
                                    asset_type="MODEL",
                                    license="Proprietary / User Generated",
                                    requires_token=True,
                                    preview_url=task.get("thumbnail_url"),
                                    tri_count_hint=task.get("polycount", 30000),
                                )
                            )
        except Exception:
            pass
        return hits

    async def _poll_task(self, client: httpx.AsyncClient, headers: dict, task_id: str) -> dict:
        """Poll a Meshy task (preview or refine) until it reaches a terminal
        status. Both stages use the same GET /{task_id} + status contract."""
        task_url = f"{BASE_URL}/{task_id}"
        last_status = "UNKNOWN"
        for _ in range(120):
            resp = await client.get(task_url, headers=headers)
            if resp.status_code != 200:
                raise ProviderError(f"Meshy API task lookup failed: HTTP {resp.status_code}")
            data = resp.json()
            last_status = data.get("status", last_status)
            if last_status == "SUCCEEDED":
                return data
            if last_status in ("FAILED", "CANCELED", "EXPIRED"):
                err = data.get("task_error", {}).get("message") or "Unknown error"
                raise ProviderError(f"Meshy generation {last_status}: {err}")
            await asyncio.sleep(3.0)
        raise ProviderError(f"Meshy generation timed out for task '{task_id}'. Status: {last_status}")

    async def download(
        self, asset_id: str, dest_dir: str, texture: bool = True, image_path: str | None = None
    ) -> DownloadedAsset:
        """texture=True (default) runs Meshy's two-stage pipeline: a fast
        untextured 'preview' geometry pass, then a slower 'refine' pass that
        bakes PBR textures onto it -- 'preview' alone is always plain grey
        geometry, Meshy has no single-call textured mode. texture=False skips
        the refine stage for a faster, untextured result.

        Image-to-3D ids ('<provider>_img_<sha8>') take the /v2/image-to-3d
        pipeline instead, which is single-stage and always textured -- there
        is no preview/refine split on that endpoint. image_path must be the
        local file the id was derived from (the hash alone can't recover it).
        """
        if asset_id.startswith("meshy_img_"):
            if not image_path:
                raise ProviderError(
                    f"Meshy image task '{asset_id}' needs its source image; "
                    "pass image_path again."
                )
            return await self._download_image(asset_id, dest_dir, image_path)

        cache_id = asset_id if texture else f"{asset_id}_untextured"
        cached = find_cached_file(self.name, cache_id)
        if cached is not None:
            return DownloadedAsset(
                filepath=str(cached),
                provider=self.name,
                asset_id=asset_id,
                license="User Generated",
                attribution=f"'{asset_id}' generated by Meshy AI",
                from_cache=True,
            )

        token = self._get_token()
        if not token:
            raise ProviderError("Meshy AI requires MESHY_API_KEY environment variable.")

        headers = {"Authorization": f"Bearer {token}"}

        async with httpx.AsyncClient(timeout=60.0) as client:
            task_id = asset_id
            if asset_id.startswith("meshy_prompt_"):
                prompt = asset_id[len("meshy_prompt_"):].replace("_", " ")
                create_resp = await client.post(
                    BASE_URL,
                    headers=headers,
                    json={"mode": "preview", "prompt": prompt, "art_style": "realistic"},
                )
                if create_resp.status_code not in (200, 202):
                    raise ProviderError(f"Meshy task creation failed: HTTP {create_resp.status_code} - {create_resp.text}")
                task_id = create_resp.json().get("result")
                if not task_id:
                    raise ProviderError(f"No task ID returned by Meshy: {create_resp.text}")

            data = await self._poll_task(client, headers, task_id)

            if texture:
                refine_resp = await client.post(
                    BASE_URL,
                    headers=headers,
                    json={"mode": "refine", "preview_task_id": task_id},
                )
                if refine_resp.status_code not in (200, 202):
                    raise ProviderError(
                        f"Meshy refine (texturing) task creation failed: HTTP {refine_resp.status_code} - {refine_resp.text}"
                    )
                refine_task_id = refine_resp.json().get("result")
                if not refine_task_id:
                    raise ProviderError(f"No refine task ID returned by Meshy: {refine_resp.text}")
                data = await self._poll_task(client, headers, refine_task_id)

            model_url = data.get("model_urls", {}).get("glb") or data.get("model_url")
            if not model_url:
                raise ProviderError(f"Meshy task '{task_id}' succeeded but returned no downloadable model URL")

            glb_resp = await client.get(model_url)
            if glb_resp.status_code != 200:
                raise ProviderError(f"Failed to download GLB from Meshy: HTTP {glb_resp.status_code}")

        out_file = Path(dest_dir) / f"{cache_id}.glb"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(glb_resp.content)

        return DownloadedAsset(
            filepath=str(out_file),
            provider=self.name,
            asset_id=asset_id,
            license="User Generated",
            attribution=f"'{asset_id}' generated by Meshy AI" + ("" if texture else " (untextured preview)"),
            from_cache=False,
        )

    async def _download_image(self, asset_id: str, dest_dir: str, image_path: str) -> DownloadedAsset:
        """Single-stage image-to-3D: upload the local image as a base64 data
        URI, poll, download the GLB. Unlike text-to-3d there is no separate
        refine pass -- the result is textured out of the box."""
        cached = find_cached_file(self.name, asset_id)
        if cached is not None:
            return DownloadedAsset(
                filepath=str(cached),
                provider=self.name,
                asset_id=asset_id,
                license="User Generated",
                attribution=f"'{asset_id}' generated by Meshy AI (image-to-3d)",
                from_cache=True,
            )

        token = self._get_token()
        if not token:
            raise ProviderError("Meshy AI requires MESHY_API_KEY environment variable.")

        headers = {"Authorization": f"Bearer {token}"}
        payload = {"image_url": image_util.to_data_uri(image_path)}

        async with httpx.AsyncClient(timeout=60.0) as client:
            create_resp = await client.post(IMAGE_BASE_URL, headers=headers, json=payload)
            if create_resp.status_code not in (200, 202):
                raise ProviderError(
                    f"Meshy image-to-3d task creation failed: HTTP {create_resp.status_code} - {create_resp.text}"
                )
            task_id = create_resp.json().get("result")
            if not task_id:
                raise ProviderError(f"No task ID returned by Meshy: {create_resp.text}")

            task_url = f"{IMAGE_BASE_URL}/{task_id}"
            last_status = "UNKNOWN"
            for _ in range(120):
                resp = await client.get(task_url, headers=headers)
                if resp.status_code != 200:
                    raise ProviderError(f"Meshy API task lookup failed: HTTP {resp.status_code}")
                data = resp.json()
                last_status = data.get("status", last_status)
                if last_status == "SUCCEEDED":
                    break
                if last_status in ("FAILED", "CANCELED", "EXPIRED"):
                    err = data.get("task_error", {}).get("message") or "Unknown error"
                    raise ProviderError(f"Meshy generation {last_status}: {err}")
                await asyncio.sleep(3.0)
            else:
                raise ProviderError(
                    f"Meshy generation timed out for task '{task_id}'. Status: {last_status}"
                )

            model_url = data.get("model_urls", {}).get("glb") or data.get("model_url")
            if not model_url:
                raise ProviderError(f"Meshy task '{task_id}' succeeded but returned no downloadable model URL")

            glb_resp = await client.get(model_url)
            if glb_resp.status_code != 200:
                raise ProviderError(f"Failed to download GLB from Meshy: HTTP {glb_resp.status_code}")

        out_file = Path(dest_dir) / f"{asset_id}.glb"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_bytes(glb_resp.content)

        return DownloadedAsset(
            filepath=str(out_file),
            provider=self.name,
            asset_id=asset_id,
            license="User Generated",
            attribution=f"'{asset_id}' generated by Meshy AI (image-to-3d)",
            from_cache=False,
        )
