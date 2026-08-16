from unittest.mock import AsyncMock

import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.errors import BridgeError, ErrorType
from mcp_blender_pakkio.tools.get_scene_info import register_get_scene_info_tool


@pytest.mark.asyncio
async def test_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "message": "ok",
        "scene_name": "Scene",
        "objects": [],
        "collections": [],
    }
    handler = register_get_scene_info_tool(FakeMCP(), bridge)

    result = await handler()

    bridge.send_request.assert_awaited_once_with(
        "get_scene_info",
        {
            "include_objects": True,
            "include_collections": True,
            "include_materials": True,
            "include_lights": True,
            "include_cameras": True,
            "include_hierarchy": False,
        },
    )
    assert result["scene_name"] == "Scene"


@pytest.mark.asyncio
async def test_domain_failure_raises_tool_execution_error():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "Scene unavailable"}
    handler = register_get_scene_info_tool(FakeMCP(), bridge)

    with pytest.raises(BridgeError) as exc_info:
        await handler()

    assert exc_info.value.error_type is ErrorType.TOOL_EXECUTION
    assert "Scene unavailable" in exc_info.value.message
