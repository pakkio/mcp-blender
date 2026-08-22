"""Image-to-3D generation: shared _image helper, per-provider pipelines,
and the ai_generate / import_online_asset plumbing that carries image_path.
"""

import base64
from unittest.mock import AsyncMock

import httpx
import pytest

from conftest import FakeMCP
from mcp_blender.assets.providers.base import ProviderError
from mcp_blender.assets.providers.meshy import MeshyProvider
from mcp_blender.assets.providers.tripo import TripoProvider
from mcp_blender.assets.providers.trellis import TrellisProvider
from mcp_blender.assets.providers._image import image_asset_id, to_data_uri
from mcp_blender.errors import BridgeError
from mcp_blender.tools.domain_facades import register_domain_facades


# 1x1 transparent PNG -- a real decodable image, not a fake extension.
_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk"
    "YPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
)


@pytest.fixture
def png_file(tmp_path):
    p = tmp_path / "source.png"
    p.write_bytes(_PNG_BYTES)
    return p


# --- _image helper ---


def test_image_asset_id_is_content_addressed(png_file):
    other = png_file.with_name("other.png")
    other.write_bytes(_PNG_BYTES + b"x")
    assert image_asset_id(png_file) == image_asset_id(png_file)
    assert image_asset_id(png_file) != image_asset_id(other)


def test_to_data_uri_encodes_mime_and_base64(png_file):
    uri = to_data_uri(png_file)
    assert uri.startswith("data:image/png;base64,")
    assert base64.b64decode(uri.split(",", 1)[1]) == _PNG_BYTES


def test_missing_image_raises_actionable(tmp_path):
    with pytest.raises(ProviderError, match="not found"):
        image_asset_id(tmp_path / "nope.png")


def test_unsupported_extension_raises(tmp_path):
    p = tmp_path / "logo.bmp"
    p.write_bytes(b"xx")
    with pytest.raises(ProviderError, match="Unsupported image type"):
        to_data_uri(p)


# --- Meshy ---


@pytest.mark.asyncio
async def test_meshy_image_download_posts_data_uri_and_saves_glb(monkeypatch, tmp_path, png_file):
    monkeypatch.setenv("MESHY_API_KEY", "tok")
    monkeypatch.setattr("mcp_blender.assets.providers.meshy.find_cached_file", lambda *a, **k: None)

    posted = {}

    async def fake_post(self, url, headers=None, json=None):
        posted["url"] = url
        posted["json"] = json
        return httpx.Response(200, json={"result": "task-img-1"}, request=httpx.Request("POST", url))

    async def fake_get(self, url, **kwargs):
        if url.endswith("/task-img-1"):
            return httpx.Response(
                200,
                json={"status": "SUCCEEDED", "model_urls": {"glb": "https://x/model.glb"}},
                request=httpx.Request("GET", url),
            )
        return httpx.Response(200, content=b"glTF-model-bytes", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = await MeshyProvider().download("meshy_img_abc12345", str(tmp_path), image_path=str(png_file))

    assert posted["url"] == "https://api.meshy.ai/v2/image-to-3d"
    assert posted["json"]["image_url"].startswith("data:image/png;base64,")
    assert result.filepath.endswith(".glb")
    assert result.from_cache is False
    assert "image-to-3d" in result.attribution


@pytest.mark.asyncio
async def test_meshy_image_without_token_raises_actionable(monkeypatch, tmp_path, png_file):
    monkeypatch.delenv("MESHY_API_KEY", raising=False)
    monkeypatch.setattr("mcp_blender.assets.providers.meshy.find_cached_file", lambda *a, **k: None)
    with pytest.raises(ProviderError, match="MESHY_API_KEY"):
        await MeshyProvider().download("meshy_img_abc12345", str(tmp_path), image_path=str(png_file))


@pytest.mark.asyncio
async def test_meshy_image_id_requires_image_path(tmp_path):
    with pytest.raises(ProviderError, match="pass image_path"):
        await MeshyProvider().download("meshy_img_abc12345", str(tmp_path))


# --- Tripo ---


@pytest.mark.asyncio
async def test_tripo_image_download_and_polling(monkeypatch, tmp_path, png_file):
    """Also covers the polling fix: first status poll returns 'running' with no
    model URL yet (which used to fail immediately), second returns success."""
    monkeypatch.setenv("TRIPO_API_KEY", "tok")
    monkeypatch.setattr("mcp_blender.assets.providers.tripo.find_cached_file", lambda *a, **k: None)

    sleeps = []
    monkeypatch.setattr("mcp_blender.assets.providers.tripo.asyncio.sleep", lambda s: sleeps.append(s) or _noop())
    posted = {}
    polls = {"count": 0}

    async def fake_post(self, url, headers=None, json=None):
        posted["json"] = json
        return httpx.Response(
            200, json={"data": {"task_id": "t9"}}, request=httpx.Request("POST", url)
        )

    async def fake_get(self, url, **kwargs):
        if str(url).endswith("/task/t9"):
            polls["count"] += 1
            if polls["count"] == 1:
                return httpx.Response(200, json={"data": {"status": "running"}}, request=httpx.Request("GET", url))
            return httpx.Response(
                200,
                json={"data": {"status": "success", "output": {"model": "https://x/m.glb"}}},
                request=httpx.Request("GET", url),
            )
        return httpx.Response(200, content=b"glTF-bytes", request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)
    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    result = await TripoProvider().download("tripo_img_abc12345", str(tmp_path), image_path=str(png_file))

    assert posted["json"]["type"] == "image_to_model"
    assert posted["json"]["file"].startswith("data:image/png;base64,")
    assert polls["count"] == 2  # 'running' then 'success'
    assert result.filepath.endswith(".glb")


async def _noop():
    return None


# --- Trellis ---


@pytest.mark.asyncio
async def test_trellis_image_without_endpoint_raises_actionable(monkeypatch, tmp_path, png_file):
    monkeypatch.delenv("TRELLIS_ENDPOINT_URL", raising=False)
    monkeypatch.setenv("HF_TOKEN", "tok")
    monkeypatch.setattr("mcp_blender.assets.providers.trellis.find_cached_file", lambda *a, **k: None)
    with pytest.raises(ProviderError, match="TRELLIS_ENDPOINT_URL"):
        await TrellisProvider().download("trellis_img_abc12345", str(tmp_path), image_path=str(png_file))


@pytest.mark.asyncio
async def test_trellis_text_only_still_rejected(tmp_path):
    with pytest.raises(ProviderError, match="only supports image-to-3d"):
        await TrellisProvider().download("trellis_prompt_chair", str(tmp_path))


@pytest.mark.asyncio
async def test_trellis_image_raw_glb_response(monkeypatch, tmp_path, png_file):
    monkeypatch.setenv("TRELLIS_ENDPOINT_URL", "https://abc.endpoints.huggingface.cloud")
    monkeypatch.setenv("HF_TOKEN", "tok")
    monkeypatch.setattr("mcp_blender.assets.providers.trellis.find_cached_file", lambda *a, **k: None)

    async def fake_post(self, url, headers=None, json=None):
        assert json["inputs"].startswith("data:image/png;base64,")
        return httpx.Response(200, content=b"glTF-trellis", request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await TrellisProvider().download("trellis_img_abc12345", str(tmp_path), image_path=str(png_file))
    assert result.filepath.endswith(".glb")


# --- Facade plumbing ---


@pytest.mark.asyncio
async def test_ai_generate_routes_image_path_through_import(monkeypatch, tmp_path, png_file):
    """ai_generate(image_path=...) must derive the hash id and carry the source
    file into provider download; missing both prompt and image must fail fast."""
    captured = {}

    class _FakeProvider:
        name = "meshy"

        async def download(self, asset_id, dest_dir, image_path=None):
            return await fake_download(self, asset_id, dest_dir, image_path)

        async def search(self, *a):
            return []

        def is_available(self):
            return True

    from mcp_blender.assets.providers.base import DownloadedAsset

    async def fake_download(self, asset_id, dest_dir, image_path=None):
        captured["asset_id"] = asset_id
        captured["image_path"] = image_path
        out = tmp_path / "fake.glb"
        out.write_bytes(b"glTF-fake")
        return DownloadedAsset(
            filepath=str(out),
            provider="meshy",
            asset_id=asset_id,
            license="User Generated",
            attribution="test",
            from_cache=False,
        )

    monkeypatch.setattr("mcp_blender.tools.asset_source_ops.get_provider", lambda name: _FakeProvider())
    monkeypatch.setattr("mcp_blender.tools.asset_source_ops.cache_dir", lambda p, a: tmp_path)

    # Bridge mock covering the import pipeline after download.
    bridge = AsyncMock()

    def send_request(method, params=None, timeout=None):
        if method == "import_file":
            return _res({"success": True, "imported_objects": ["Obj"], "orientation": None})
        if method == "get_object_info":
            return _res(
                {
                    "success": True,
                    "type": "MESH",
                    "parent": None,
                    "dimensions": [1, 1, 1],
                    "mesh_data": {"vertices_count": 8, "polygons_count": 12},
                }
            )
        return _res({"success": True})

    class _Res(dict):
        pass

    async def send_request_async(method, params=None, timeout=None):
        return send_request(method, params, timeout)

    bridge.send_request = send_request_async

    mcp = FakeMCP()
    register_domain_facades(mcp, bridge)

    assets_tool = mcp.tools["blender_assets"]

    # Neither prompt nor image -> actionable validation error.
    with pytest.raises(BridgeError, match="ai_generate needs"):
        await assets_tool(action="ai_generate", params={})

    # Nonexistent image -> actionable validation error, nothing generated.
    with pytest.raises(BridgeError, match="not found"):
        await assets_tool(action="ai_generate", params={"image_path": str(tmp_path / "gone.png")})

    # Happy path: hash-derived id + image_path carried through.
    res = await assets_tool(action="ai_generate", params={"image_path": str(png_file)})
    expected_id = f"meshy_img_{image_asset_id(png_file)}"
    assert captured["asset_id"] == expected_id
    assert captured["image_path"] == str(png_file)
    assert res.get("success") is True


def _res(payload):
    r = dict(payload)
    r.setdefault("success", True)
    return r
