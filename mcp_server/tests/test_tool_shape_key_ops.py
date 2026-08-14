from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.shape_key_ops import register_shape_key_tools


@pytest.mark.asyncio
async def test_manage_shape_keys_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Cube",
        "key_name": "Blink",
        "value": 1.0,
    }
    manage_sk = register_shape_key_tools(FakeMCP(), bridge)

    result = await manage_sk(
        object_name="Cube",
        action="ADD_KEY",
        key_name="Blink",
        value=1.0,
    )
    bridge.send_request.assert_awaited_once_with(
        "manage_shape_keys",
        {
            "object_name": "Cube",
            "action": "ADD_KEY",
            "key_name": "Blink",
            "value": 1.0,
            "frame": None,
        },
    )
    assert result["key_name"] == "Blink"
