from unittest.mock import AsyncMock, patch
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.bridge import HEAVY_REQUEST_TIMEOUT_S
from mcp_blender_pakkio.config import resolve_tool_mode
from mcp_blender_pakkio.docs.registry import get_recipe, list_domains_summary, search_docs
from mcp_blender_pakkio.tools import register_all_tools
from mcp_blender_pakkio.tools.domain_facades import register_domain_facades


def test_docs_registry_search_and_recipes():
    # Search for cloth recipe
    res = search_docs("cloth")
    assert len(res["matched_recipes"]) > 0
    assert "Cloth" in res["matched_recipes"][0]["title"]
    assert len(res["matched_recipes"][0]["steps"]) >= 4

    # Search for hair
    res_hair = search_docs("hair")
    assert len(res_hair["matched_recipes"]) > 0

    # Get specific recipe
    recipe = get_recipe("ai_asset_generation")
    assert recipe is not None
    assert "Text-to-3D" in recipe["title"]

    # Domain summary
    summary = list_domains_summary()
    assert "blender_mesh" in summary
    assert "blender_material" in summary
    assert "blender_assets" in summary


@pytest.mark.asyncio
async def test_domain_facades_registration_and_dispatch():
    mcp = FakeMCP()
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "message": "OK"}

    register_domain_facades(mcp, bridge)

    # Check registered tool names
    registered_names = set(mcp.tools.keys())
    assert "blender_docs" in registered_names
    assert "blender_mesh" in registered_names
    assert "blender_material" in registered_names
    assert "blender_assets" in registered_names
    assert "blender_scene" in registered_names
    assert "blender_rigging_anim" in registered_names
    assert "blender_camera_lighting" in registered_names
    assert "blender_physics_sim" in registered_names
    assert "blender_render_pipeline" in registered_names
    assert "execute_blender_python" in registered_names

    # Test blender_docs
    docs_tool = mcp.tools["blender_docs"]
    doc_res = await docs_tool(query="pbr")
    assert "matched_recipes" in doc_res

    # Test blender_mesh dispatch
    mesh_tool = mcp.tools["blender_mesh"]
    await mesh_tool(action="create", params={"type": "CUBE", "name": "Box"})
    bridge.send_request.assert_awaited_with("create_object", {"type": "CUBE", "name": "Box"}, timeout=None)

    # Test blender_material dispatch
    mat_tool = mcp.tools["blender_material"]
    await mat_tool(action="create", params={"name": "Gold"})
    bridge.send_request.assert_awaited_with("create_material", {"name": "Gold"}, timeout=None)

    # Test blender_scene dispatch
    scene_tool = mcp.tools["blender_scene"]
    await scene_tool(action="checkpoint_create", params={"name": "test_chk"})
    bridge.send_request.assert_awaited_with(
        "create_scene_checkpoint", {"name": "test_chk"}, timeout=HEAVY_REQUEST_TIMEOUT_S
    )

    # Test blender_scene "busy" dispatch never gets the heavy timeout -- it's
    # meant to answer instantly regardless of what else is running.
    await scene_tool(action="busy")
    bridge.send_request.assert_awaited_with("bridge_status", {}, timeout=None)

    # Test blender_physics_sim dispatch
    phys_tool = mcp.tools["blender_physics_sim"]
    await phys_tool(action="setup_cloth", params={"object_name": "Sheet"})
    bridge.send_request.assert_awaited_with("setup_cloth_simulation", {"object_name": "Sheet"}, timeout=None)


@pytest.mark.asyncio
async def test_blender_scene_regen_action_routes_to_localization_orchestration():
    # "regen" needs its own bridge mock (must return a "root" tree, unlike
    # the generic {"success": True, "message": "OK"} used above) since it's
    # handled by regen_names' own orchestration, not the generic dispatcher.
    mcp = FakeMCP()
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "message": "Regenerated names for 'Scene Collection' (lang=it)",
        "root": {"old_name": "x", "new_name": "x", "objects": [], "children": []},
    }
    register_domain_facades(mcp, bridge)

    scene_tool = mcp.tools["blender_scene"]
    result = await scene_tool(action="regen", params={"lang": "it", "element": "Furniture"})

    bridge.send_request.assert_awaited_once_with(
        "regen_element_names", {"lang": "it", "element": "Furniture"}, timeout=HEAVY_REQUEST_TIMEOUT_S
    )
    assert result["success"] is True
    assert result["lang"] == "it"

    # And reachable as its own top-level tool too, per the "regen('it')" ask.
    assert "regen_names" in mcp.tools


@pytest.mark.asyncio
async def test_tool_mode_switching():
    # Test AGGREGATED mode (default)
    with patch.dict("os.environ", {"MCP_BLENDER_TOOL_MODE": "AGGREGATED"}):
        assert resolve_tool_mode() == "AGGREGATED"
        mcp = FakeMCP()
        bridge = AsyncMock()
        register_all_tools(mcp, bridge)
        # Should only have ~14 tools (10 domain facades + standalone search/import/
        # eval/simplify subtools) -- nowhere near FULL mode's ~138.
        assert len(mcp.tools) < 20
        assert "blender_mesh" in mcp.tools
        assert "simplify_geometry" in mcp.tools
        assert "get_bridge_status" in mcp.tools

    # Test FULL mode
    with patch.dict("os.environ", {"MCP_BLENDER_TOOL_MODE": "FULL"}):
        assert resolve_tool_mode() == "FULL"
        mcp_full = FakeMCP()
        bridge_full = AsyncMock()
        register_all_tools(mcp_full, bridge_full)
        # Should have 100+ granular tools
        assert len(mcp_full.tools) > 100
        assert "create_object" in mcp_full.tools
