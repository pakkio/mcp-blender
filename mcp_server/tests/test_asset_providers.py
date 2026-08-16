import httpx
import pytest

from mcp_blender_pakkio.assets.providers.ambientcg import AmbientCGProvider
from mcp_blender_pakkio.assets.providers.base import ProviderError
from mcp_blender_pakkio.assets.providers.polyhaven import PolyHavenProvider
from mcp_blender_pakkio.assets.providers.sketchfab import SketchfabProvider


def _mock_transport(handler):
    return httpx.MockTransport(handler)


@pytest.mark.asyncio
async def test_polyhaven_search_filters_by_query(monkeypatch):
    def handler(request):
        assert request.url.params["t"] == "models"
        return httpx.Response(
            200,
            json={
                "victorian_chair": {"name": "Victorian Chair", "tags": ["furniture", "chair"], "categories": []},
                "modern_lamp": {"name": "Modern Lamp", "tags": ["light"], "categories": []},
            },
        )

    async def fake_get(self, url, params=None, **kwargs):
        request = httpx.Request("GET", url, params=params)
        return handler(request)

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    provider = PolyHavenProvider()
    hits = await provider.search("chair", "MODEL", 10)

    assert len(hits) == 1
    assert hits[0].id == "victorian_chair"
    assert hits[0].license == "CC0"
    assert hits[0].requires_token is False


@pytest.mark.asyncio
async def test_polyhaven_search_http_error_raises(monkeypatch):
    async def fake_get(self, url, params=None, **kwargs):
        return httpx.Response(500, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    provider = PolyHavenProvider()
    with pytest.raises(ProviderError):
        await provider.search("chair", "MODEL", 10)


class _FakeStream:
    """Minimal stand-in for httpx.AsyncClient.stream()'s async context manager."""

    def __init__(self, status_code=200, body=b"file-bytes"):
        self.status_code = status_code
        self._body = body

    async def aiter_bytes(self):
        yield self._body

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


@pytest.mark.asyncio
async def test_polyhaven_download_fetches_include_files(monkeypatch, tmp_path):
    """Regression test: Poly Haven's .gltf references .bin/textures via an
    "include" map with paths relative to the .gltf itself (confirmed live
    against api.polyhaven.com/files/ArmChair_01) -- download() must fetch
    those too, or Blender's importer can't resolve the mesh's dependencies.
    """
    monkeypatch.setattr(
        "mcp_blender_pakkio.assets.providers.polyhaven.find_cached_file", lambda *a, **k: None
    )

    files_payload = {
        "gltf": {
            "1k": {
                "gltf": {
                    "url": "https://dl.polyhaven.org/file/ph-assets/Models/gltf/1k/Chair/Chair_1k.gltf",
                    "include": {
                        "Chair.bin": {"url": "https://dl.polyhaven.org/file/.../Chair.bin"},
                        "textures/Chair_diff_1k.jpg": {"url": "https://dl.polyhaven.org/file/.../Chair_diff_1k.jpg"},
                    },
                }
            }
        }
    }

    async def fake_get(self, url, params=None, **kwargs):
        return httpx.Response(200, json=files_payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)
    monkeypatch.setattr(httpx.AsyncClient, "stream", lambda self, method, url, **kwargs: _FakeStream())

    provider = PolyHavenProvider()
    result = await provider.download("Chair", str(tmp_path))

    assert result.filepath.endswith("Chair.gltf")
    assert (tmp_path / "Chair.bin").exists()
    assert (tmp_path / "textures" / "Chair_diff_1k.jpg").exists()


@pytest.mark.asyncio
async def test_ambientcg_search_only_supports_textures():
    provider = AmbientCGProvider()
    hits = await provider.search("brick", "MODEL", 10)
    assert hits == []


@pytest.mark.asyncio
async def test_ambientcg_search_happy_path(monkeypatch):
    async def fake_get(self, url, params=None, **kwargs):
        assert params["type"] == "Material"
        return httpx.Response(
            200,
            json={"foundAssets": [{"assetId": "Bricks076", "displayName": "Bricks 076"}]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    provider = AmbientCGProvider()
    hits = await provider.search("brick", "TEXTURE", 10)

    assert hits[0].id == "Bricks076"
    assert hits[0].license == "CC0"


@pytest.mark.asyncio
async def test_ambientcg_download_follows_redirects(monkeypatch, tmp_path):
    """Regression test: ambientcg.com/get 302-redirects to the actual CDN
    file (confirmed live) -- download()'s AsyncClient must be constructed
    with follow_redirects=True or every download fails as a false non-200.
    """
    monkeypatch.setattr(
        "mcp_blender_pakkio.assets.providers.ambientcg.find_cached_file", lambda *a, **k: None
    )

    captured_kwargs = {}
    original_init = httpx.AsyncClient.__init__

    def capturing_init(self, *args, **kwargs):
        captured_kwargs.update(kwargs)
        return original_init(self, *args, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "__init__", capturing_init)
    monkeypatch.setattr(httpx.AsyncClient, "stream", lambda self, method, url, **kwargs: _FakeStream())

    provider = AmbientCGProvider()
    result = await provider.download("Bricks076", str(tmp_path))

    assert captured_kwargs.get("follow_redirects") is True
    assert result.filepath.endswith(".zip")


@pytest.mark.asyncio
async def test_sketchfab_search_marks_requires_token_without_env(monkeypatch):
    monkeypatch.delenv("SKETCHFAB_API_TOKEN", raising=False)

    async def fake_get(self, url, params=None, **kwargs):
        return httpx.Response(
            200,
            json={"results": [{"uid": "abc123", "name": "Chair", "license": {"label": "CC-BY"}}]},
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    provider = SketchfabProvider()
    hits = await provider.search("chair", "MODEL", 10)

    assert hits[0].requires_token is True
    assert hits[0].license == "CC-BY"


@pytest.mark.asyncio
async def test_sketchfab_download_without_token_raises_actionable_error(monkeypatch, tmp_path):
    monkeypatch.delenv("SKETCHFAB_API_TOKEN", raising=False)

    provider = SketchfabProvider()
    with pytest.raises(ProviderError, match="SKETCHFAB_API_TOKEN"):
        await provider.download("abc123", str(tmp_path))
