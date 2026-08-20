from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.light_ops import register_light_tools


@pytest.mark.asyncio
async def test_configure_light_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "name": "Light",
        "light_type": "SUN",
        "energy": 500.0,
    }
    handler = register_light_tools(FakeMCP(), bridge)

    result = await handler(name="Light", light_type="SUN", energy=500.0)

    bridge.send_request.assert_awaited_once_with(
        "configure_light",
        {
            "name": "Light",
            "light_type": "SUN",
            "energy": 500.0,
            "color": None,
            "spot_size": None,
            "spot_blend": None,
            "shadow_soft_size": None,
            "size": None,
            "size_y": None,
        },
    )
    assert result["energy"] == 500.0
