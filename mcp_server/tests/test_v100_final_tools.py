import pytest
from unittest.mock import AsyncMock, MagicMock
from mcp.server.fastmcp import FastMCP

from mcp_blender.bridge import BlenderBridge
from mcp_blender.tools import register_legacy_tools


@pytest.fixture
def mock_bridge():
    bridge = MagicMock(spec=BlenderBridge)
    bridge.send_request = AsyncMock()
    return bridge


@pytest.fixture
def mcp_server(mock_bridge):
    mcp = FastMCP("test-blender")
    register_legacy_tools(mcp, mock_bridge)
    return mcp


@pytest.mark.asyncio
async def test_scene_diagnostics_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {
        "success": True,
        "total_triangles": 14200,
        "non_manifold_warnings": [],
    }

    t_diag = mcp_server._tool_manager.get_tool("inspect_scene_performance")
    res = await t_diag.run({})
    assert res["success"] is True
    assert res["total_triangles"] == 14200

    t_sky = mcp_server._tool_manager.get_tool("setup_sky_sun_rig")
    mock_bridge.send_request.return_value = {"success": True, "sun_object": "Sun_Rig"}
    res_sky = await t_sky.run({"sun_elevation": 30.0, "sun_rotation": 60.0})
    assert res_sky["success"] is True


@pytest.mark.asyncio
async def test_animation_render_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "frame_range": [1, 50]}

    t_bake = mcp_server._tool_manager.get_tool("bake_object_animation")
    res = await t_bake.run({"object_name": "AnimatedCharacter", "frame_start": 1, "frame_end": 50})
    assert res["success"] is True

    t_render = mcp_server._tool_manager.get_tool("render_animation_sequence")
    mock_bridge.send_request.return_value = {"success": True, "format": "FFMPEG"}
    res_render = await t_render.run({"format": "FFMPEG", "frame_start": 1, "frame_end": 20})
    assert res_render["success"] is True
