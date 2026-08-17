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
async def test_shader_studio_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "material_name": "M_WeatheredMetal"}

    t_grunge = mcp_server._tool_manager.get_tool("create_procedural_grunge_mask")
    res = await t_grunge.run({"material_name": "M_WeatheredMetal", "edge_wear_amount": 0.6})
    assert res["success"] is True

    t_spec = mcp_server._tool_manager.get_tool("setup_specialty_shader")
    res_spec = await t_spec.run({"material_name": "M_CarPaint", "preset": "CAR_PAINT"})
    assert res_spec["success"] is True


@pytest.mark.asyncio
async def test_advanced_geom_nodes_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "target": "TargetMesh"}

    t_prox = mcp_server._tool_manager.get_tool("setup_geometry_proximity_interaction")
    res = await t_prox.run({"target_object": "TargetMesh", "source_object": "SourceEffector"})
    assert res["success"] is True

    t_curve = mcp_server._tool_manager.get_tool("curve_to_profile_mesh")
    res_curve = await t_curve.run({"curve_object": "BezierCurve", "profile_type": "STAR"})
    assert res_curve["success"] is True


@pytest.mark.asyncio
async def test_material_slot_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "assigned_faces": 48}

    t_slots = mcp_server._tool_manager.get_tool("manage_material_slots")
    res = await t_slots.run({"object_name": "Building", "action": "ASSIGN_FACES", "material_name": "M_Glass"})
    assert res["success"] is True

    t_decal = mcp_server._tool_manager.get_tool("project_decal_material")
    mock_bridge.send_request.return_value = {"success": True, "decal_object": "Decal_Graffiti"}
    res_decal = await t_decal.run({"target_object": "Building", "decal_name": "Decal_Graffiti"})
    assert res_decal["success"] is True
