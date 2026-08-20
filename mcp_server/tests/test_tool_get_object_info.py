from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError

from conftest import FakeMCP
from mcp_blender.errors import BridgeError, ErrorType
from mcp_blender.tools.get_object_info import register_get_object_info_tool


@pytest.mark.asyncio
async def test_get_object_info_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "name": "Cube",
        "type": "MESH",
        "location": [0.0, 0.0, 0.0],
        "mesh_data": {"vertices_count": 8, "edges_count": 12, "polygons_count": 6},
    }
    handler = register_get_object_info_tool(FakeMCP(), bridge)

    result = await handler(name="Cube")

    bridge.send_request.assert_awaited_once_with("get_object_info", {"name": "Cube"})
    assert result["name"] == "Cube"
    assert result["mesh_data"]["vertices_count"] == 8


@pytest.mark.asyncio
async def test_get_object_info_not_found():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "Object 'NotReal' not found"}
    handler = register_get_object_info_tool(FakeMCP(), bridge)

    with pytest.raises(BridgeError) as exc_info:
        await handler(name="NotReal")

    assert exc_info.value.error_type is ErrorType.TOOL_EXECUTION
