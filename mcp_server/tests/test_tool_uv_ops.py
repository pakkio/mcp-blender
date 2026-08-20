from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.uv_ops import register_uv_tools


@pytest.mark.asyncio
async def test_uv_unwrap_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Cube",
        "method": "SMART_PROJECT",
        "uv_layers": ["UVMap"],
    }
    uv_unwrap = register_uv_tools(FakeMCP(), bridge)

    result = await uv_unwrap(object_name="Cube", method="SMART_PROJECT", island_margin=0.05)
    bridge.send_request.assert_awaited_once_with(
        "uv_unwrap",
        {
            "object_name": "Cube",
            "method": "SMART_PROJECT",
            "angle_limit": 66.0,
            "island_margin": 0.05,
            "correct_aspect": True,
            "scale_to_bounds": False,
            "cube_size": 1.0,
            "pack_islands_margin": 0.02,
        },
    )
    assert result["success"] is True
