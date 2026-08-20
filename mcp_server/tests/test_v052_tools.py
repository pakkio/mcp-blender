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
async def test_text_typography_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "name": "Title3D"}
    t_create = mcp_server._tool_manager.get_tool("create_3d_text")
    res = await t_create.run({"text": "Cyberpunk 2077", "extrude": 0.2})
    assert res["success"] is True

    t_deform = mcp_server._tool_manager.get_tool("deform_text_along_curve")
    res_def = await t_deform.run({"text_name": "Title3D", "create_circle_curve": True})
    assert res_def["success"] is True

    t_prop = mcp_server._tool_manager.get_tool("set_text_properties")
    res_prop = await t_prop.run({"text_name": "Title3D", "size": 2.0})
    assert res_prop["success"] is True


@pytest.mark.asyncio
async def test_curve_wire_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "name": "CableWire"}
    t_cable = mcp_server._tool_manager.get_tool("create_curve_cable")
    res = await t_cable.run({"start_point": [0, 0, 2], "end_point": [5, 0, 2], "sag": 1.0})
    assert res["success"] is True

    t_conv = mcp_server._tool_manager.get_tool("convert_mesh_to_curve")
    res_conv = await t_conv.run({"object_name": "Cube", "bevel_depth": 0.05})
    assert res_conv["success"] is True

    t_edit = mcp_server._tool_manager.get_tool("edit_curve_points")
    res_edit = await t_edit.run({"curve_name": "CableWire", "points": [{"co": [0, 0, 0]}]})
    assert res_edit["success"] is True


@pytest.mark.asyncio
async def test_asset_browser_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "target_name": "HeroProp"}
    t_asset = mcp_server._tool_manager.get_tool("manage_asset_browser")
    res = await t_asset.run({"action": "ASSET_MARK", "target_name": "HeroProp", "author": "Pakkio"})
    assert res["success"] is True

    t_prev = mcp_server._tool_manager.get_tool("generate_asset_preview")
    res_prev = await t_prev.run({"target_name": "HeroProp"})
    assert res_prev["success"] is True

    t_imp = mcp_server._tool_manager.get_tool("import_asset_library")
    res_imp = await t_imp.run({"filepath": "props.blend", "asset_name": "HeroProp"})
    assert res_imp["success"] is True


@pytest.mark.asyncio
async def test_lattice_deform_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "lattice_name": "Lattice_Hero"}
    t_lat = mcp_server._tool_manager.get_tool("create_lattice_deform")
    res = await t_lat.run({"target_object": "Hero", "u_resolution": 4})
    assert res["success"] is True

    t_def = mcp_server._tool_manager.get_tool("deform_lattice_points")
    res_def = await t_def.run({"lattice_name": "Lattice_Hero", "deformation": "SQUASH_AND_STRETCH"})
    assert res_def["success"] is True


@pytest.mark.asyncio
async def test_volumetric_vdb_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "name": "FogDomain"}
    t_vdb = mcp_server._tool_manager.get_tool("create_volume_vdb")
    res = await t_vdb.run({"name": "FogDomain", "density": 0.08})
    assert res["success"] is True

    t_vol = mcp_server._tool_manager.get_tool("configure_volume_shader")
    res_vol = await t_vol.run({"material_name": "M_Fog", "density": 0.1})
    assert res_vol["success"] is True

    t_bake = mcp_server._tool_manager.get_tool("bake_fluid_domain")
    res_bake = await t_bake.run({"domain_object": "FogDomain", "domain_type": "GAS"})
    assert res_bake["success"] is True


@pytest.mark.asyncio
async def test_sequencer_vse_tools(mock_bridge, mcp_server):
    mock_bridge.send_request.return_value = {"success": True, "strip_name": "Voiceover"}
    t_seq = mcp_server._tool_manager.get_tool("manage_sequencer_strips")
    res = await t_seq.run({"action": "ADD_COLOR", "length": 100})
    assert res["success"] is True

    t_audio = mcp_server._tool_manager.get_tool("configure_sequencer_audio")
    res_audio = await t_audio.run({"strip_name": "Voiceover", "volume": 0.8})
    assert res_audio["success"] is True
