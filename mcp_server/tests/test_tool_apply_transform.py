from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.apply_transform import register_apply_transform_tool


@pytest.mark.asyncio
async def test_apply_transform_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "name": "Cube",
        "scale": [1.0, 1.0, 1.0],
    }
    handler = register_apply_transform_tool(FakeMCP(), bridge)

    result = await handler(name="Cube", scale=True, rotation=True)

    bridge.send_request.assert_awaited_once_with(
        "apply_transform",
        {
            "name": "Cube",
            "location": False,
            "rotation": True,
            "scale": True,
        },
    )
    assert result["scale"] == [1.0, 1.0, 1.0]
