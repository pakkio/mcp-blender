import pytest
from unittest.mock import AsyncMock, MagicMock
from mcp.server.fastmcp import FastMCP

from mcp_blender_pakkio.bridge import BlenderBridge
from mcp_blender_pakkio.tools import register_legacy_tools


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
async def test_batch_execution_tool(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {
        "success": True,
        "total_commands": 3,
        "total_executed": 3,
        "duration_seconds": 0.045,
        "results": [
            {"index": 0, "tool": "create_object", "success": True},
            {"index": 1, "tool": "create_material", "success": True},
            {"index": 2, "tool": "assign_material", "success": True},
        ],
    }

    t_batch = mcp_server._tool_manager.get_tool("execute_batch")
    res = await t_batch.run({
        "title": "Procedural Room Generation",
        "commands": [
            {"tool": "create_object", "params": {"object_type": "CUBE"}},
            {"tool": "create_material", "params": {"material_name": "M_Wall"}},
            {"tool": "assign_material", "params": {"object_name": "Cube", "material_name": "M_Wall"}},
        ],
        "update_hud": True,
    })
    assert res["success"] is True
    assert res["total_commands"] == 3


@pytest.mark.asyncio
async def test_progress_hud_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "progress_percent": 75.0}

    t_hud = mcp_server._tool_manager.get_tool("update_progress_hud")
    res = await t_hud.run({
        "title": "Baking Lightmaps",
        "status": "Denoising samples...",
        "progress_percent": 75.0,
        "step_current": 3,
        "step_total": 4,
        "details": ["Setup nodes", "Render bake", "Denoise"],
    })
    assert res["success"] is True

    t_clear = mcp_server._tool_manager.get_tool("clear_progress_hud")
    mock_bridge.send_request.return_value = {"success": True}
    res_clear = await t_clear.run({})
    assert res_clear["success"] is True
