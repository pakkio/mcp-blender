from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.addon_management_ops import register_addon_management_tools


@pytest.mark.asyncio
async def test_manage_addons_list_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "total_addons": 12,
        "addons": [{"name": "Node Wrangler", "enabled": True}],
    }
    manage_addons, inspect_addon = register_addon_management_tools(FakeMCP(), bridge)

    result = await manage_addons(action="LIST", filter="ENABLED_ONLY")
    bridge.send_request.assert_awaited_once_with(
        "manage_addons",
        {
            "action": "LIST",
            "addon_name": None,
            "filter": "ENABLED_ONLY",
            "preferences": None,
        },
    )
    assert result["total_addons"] == 12


@pytest.mark.asyncio
async def test_inspect_addon_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "name": "glTF 2.0 format",
        "is_enabled": True,
    }
    manage_addons, inspect_addon = register_addon_management_tools(FakeMCP(), bridge)

    result = await inspect_addon(addon_name="io_scene_gltf2")
    bridge.send_request.assert_awaited_once_with(
        "inspect_addon",
        {"addon_name": "io_scene_gltf2"},
    )
    assert result["name"] == "glTF 2.0 format"
