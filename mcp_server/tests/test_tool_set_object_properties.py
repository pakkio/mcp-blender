from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.set_object_properties import register_set_object_properties_tool


@pytest.mark.asyncio
async def test_set_object_properties_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "name": "NewCube",
        "hide_viewport": True,
    }
    handler = register_set_object_properties_tool(FakeMCP(), bridge)

    result = await handler(name="Cube", new_name="NewCube", hide_viewport=True)

    bridge.send_request.assert_awaited_once_with(
        "set_object_properties",
        {
            "name": "Cube",
            "new_name": "NewCube",
            "hide_viewport": True,
            "hide_render": None,
            "color": None,
            "custom_properties": None,
        },
    )
    assert result["name"] == "NewCube"
