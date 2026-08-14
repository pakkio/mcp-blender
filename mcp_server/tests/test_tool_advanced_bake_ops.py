from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.bridge import HEAVY_REQUEST_TIMEOUT_S
from mcp_blender_pakkio.tools.advanced_bake_ops import register_advanced_bake_tools


@pytest.mark.asyncio
async def test_bake_advanced_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "target_object": "LowPolyMesh",
        "bake_type": "NORMAL",
        "output_filepath": "/tmp/normal_map.png",
    }
    bake_adv, cfg_probe = register_advanced_bake_tools(FakeMCP(), bridge)

    result = await bake_adv(
        target_object="LowPolyMesh",
        source_objects=["HighPolyMesh"],
        bake_type="NORMAL",
        selected_to_active=True,
        cage_extrusion=0.05,
    )
    bridge.send_request.assert_awaited_once_with(
        "bake_advanced",
        {
            "target_object": "LowPolyMesh",
            "source_objects": ["HighPolyMesh"],
            "bake_type": "NORMAL",
            "selected_to_active": True,
            "cage_object": None,
            "cage_extrusion": 0.05,
            "bake_to_vertex_colors": False,
            "vertex_color_layer": "BakedColor",
            "output_filepath": None,
            "width": 2048,
            "height": 2048,
            "margin": 16,
            "samples": 32,
            "denoise": False,
        },
        timeout=HEAVY_REQUEST_TIMEOUT_S,
    )
    assert result["bake_type"] == "NORMAL"


@pytest.mark.asyncio
async def test_configure_light_probe_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "probe_name": "VolumeProbe",
        "probe_type": "GRID",
    }
    bake_adv, cfg_probe = register_advanced_bake_tools(FakeMCP(), bridge)

    result = await cfg_probe(
        probe_type="GRID",
        name="VolumeProbe",
        location=[0, 0, 2],
        resolution=[4, 4, 4],
    )
    bridge.send_request.assert_awaited_once_with(
        "configure_light_probe",
        {
            "probe_type": "GRID",
            "name": "VolumeProbe",
            "location": [0.0, 0.0, 2.0],
            "resolution": [4, 4, 4],
            "influence_distance": 5.0,
            "bake_cache": False,
        },
        timeout=HEAVY_REQUEST_TIMEOUT_S,
    )
    assert result["probe_name"] == "VolumeProbe"
