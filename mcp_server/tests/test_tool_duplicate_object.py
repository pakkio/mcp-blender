from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.errors import BridgeError, ErrorType
from mcp_blender_pakkio.tools.duplicate_object import register_duplicate_object_tool


@pytest.mark.asyncio
async def test_duplicate_object_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "name": "Cube_Copy",
        "original_name": "Cube",
        "location": [2.0, 0.0, 0.0],
    }
    handler = register_duplicate_object_tool(FakeMCP(), bridge)

    result = await handler(name="Cube", new_name="Cube_Copy", offset=(2.0, 0.0, 0.0))

    bridge.send_request.assert_awaited_once_with(
        "duplicate_object",
        {
            "name": "Cube",
            "new_name": "Cube_Copy",
            "linked": False,
            "offset": (2.0, 0.0, 0.0),
            "collection": None,
        },
    )
    assert result["name"] == "Cube_Copy"
