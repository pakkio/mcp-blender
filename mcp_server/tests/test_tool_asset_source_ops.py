from unittest.mock import AsyncMock

import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.assets.providers.base import AssetHit, DownloadedAsset, ProviderError
from mcp_blender_pakkio.errors import BridgeError
from mcp_blender_pakkio.tools.asset_source_ops import register_asset_source_tools


class _FakeProvider:
    def __init__(self, name, hits=None, download_result=None, download_error=None):
        self.name = name
        self.requires_token = False
        self._hits = hits or []
        self._download_result = download_result
        self._download_error = download_error

    def is_available(self):
        return True

    async def search(self, query, asset_type, limit):
        return self._hits[:limit]

    async def download(self, asset_id, dest_dir):
        if self._download_error:
            raise self._download_error
        return self._download_result


@pytest.mark.asyncio
async def test_search_online_assets_merges_and_filters_token_required(monkeypatch):
    hit_free = AssetHit(id="chair1", provider="polyhaven", name="Chair", asset_type="MODEL", license="CC0", requires_token=False)
    hit_locked = AssetHit(id="chair2", provider="sketchfab", name="Chair 2", asset_type="MODEL", license="CC-BY", requires_token=True)

    providers = [_FakeProvider("polyhaven", hits=[hit_free]), _FakeProvider("sketchfab", hits=[hit_locked])]
    monkeypatch.setattr("mcp_blender_pakkio.tools.asset_source_ops.all_providers", lambda: providers)

    bridge = AsyncMock()
    search_fn, _import_fn = register_asset_source_tools(FakeMCP(), bridge)

    result = await search_fn(query="chair")

    assert result["success"] is True
    ids = [h["id"] for h in result["hits"]]
    assert ids == ["chair1"]
    assert result["provider_status"]["polyhaven"]["hit_count"] == 1


@pytest.mark.asyncio
async def test_search_online_assets_provider_error_is_isolated(monkeypatch):
    providers = [
        _FakeProvider("polyhaven", hits=[]),
    ]

    class _BrokenProvider(_FakeProvider):
        async def search(self, query, asset_type, limit):
            raise ProviderError("polyhaven is down")

    providers = [_BrokenProvider("polyhaven"), _FakeProvider("ambientcg", hits=[])]
    monkeypatch.setattr("mcp_blender_pakkio.tools.asset_source_ops.all_providers", lambda: providers)

    bridge = AsyncMock()
    search_fn, _import_fn = register_asset_source_tools(FakeMCP(), bridge)

    result = await search_fn(query="chair")

    assert result["success"] is True
    assert result["provider_status"]["polyhaven"]["error"] == "polyhaven is down"
    assert result["hits"] == []


@pytest.mark.asyncio
async def test_import_online_asset_happy_path(monkeypatch, tmp_path):
    downloaded = DownloadedAsset(
        filepath=str(tmp_path / "chair.glb"), provider="polyhaven", asset_id="chair1",
        license="CC0", attribution="'chair1' by Poly Haven (CC0)", from_cache=False,
    )
    (tmp_path / "chair.glb").write_bytes(b"glb-bytes")
    provider = _FakeProvider("polyhaven", download_result=downloaded)

    monkeypatch.setattr("mcp_blender_pakkio.tools.asset_source_ops.get_provider", lambda name: provider)
    monkeypatch.setattr("mcp_blender_pakkio.tools.asset_source_ops.cache_dir", lambda p, a: tmp_path)

    bridge = AsyncMock()

    async def send_request(method, params, timeout=None):
        if method == "import_file":
            return {"success": True, "imported_objects": ["Chair_Mesh"]}
        if method == "get_object_info":
            return {
                "success": True,
                "type": "MESH",
                "parent": None,
                "dimensions": [1.0, 1.0, 1.0],
                "mesh_data": {"polygons_count": 50000},
            }
        if method == "decimate_mesh":
            return {"success": True}
        return {"success": True}

    bridge.send_request.side_effect = send_request

    _search_fn, import_fn = register_asset_source_tools(FakeMCP(), bridge)

    result = await import_fn(asset_id="chair1", provider="polyhaven", target_poly_budget=10000)

    assert result["success"] is True
    assert result["imported_objects"] == ["Chair_Mesh"]
    assert result["decimation_applied"]["tri_count_before"] == 50000
    assert result["decimation_applied"]["ratio"] == pytest.approx(0.2, rel=1e-3)
    assert result["license"] == "CC0"


@pytest.mark.asyncio
async def test_import_online_asset_download_error_returns_failure(monkeypatch, tmp_path):
    provider = _FakeProvider("sketchfab", download_error=ProviderError("SKETCHFAB_API_TOKEN missing"))

    monkeypatch.setattr("mcp_blender_pakkio.tools.asset_source_ops.get_provider", lambda name: provider)
    monkeypatch.setattr("mcp_blender_pakkio.tools.asset_source_ops.cache_dir", lambda p, a: tmp_path)

    bridge = AsyncMock()
    _search_fn, import_fn = register_asset_source_tools(FakeMCP(), bridge)

    result = await import_fn(asset_id="chair2", provider="sketchfab")

    assert result["success"] is False
    assert "SKETCHFAB_API_TOKEN" in result["message"]
    bridge.send_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_import_online_asset_unknown_provider_raises(monkeypatch):
    bridge = AsyncMock()
    _search_fn, import_fn = register_asset_source_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError):
        await import_fn(asset_id="x", provider="nonexistent")
