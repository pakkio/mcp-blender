from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.animation_ops import register_animation_tools


@pytest.mark.asyncio
async def test_set_keyframe_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Cube",
        "data_path": "location",
        "frame": 10,
    }
    set_kf, del_kf, set_tl = register_animation_tools(FakeMCP(), bridge)

    result = await set_kf(
        object_name="Cube",
        frame=10,
        data_path="location",
        value=[0.0, 0.0, 5.0],
    )

    bridge.send_request.assert_awaited_once_with(
        "set_keyframe",
        {
            "object_name": "Cube",
            "frame": 10,
            "data_path": "location",
            "value": [0.0, 0.0, 5.0],
            "custom_property_name": None,
            "interpolation": "BEZIER",
        },
    )
    assert result["frame"] == 10


@pytest.mark.asyncio
async def test_set_timeline_range_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "frame_start": 1,
        "frame_end": 120,
        "fps": 30,
    }
    set_kf, del_kf, set_tl = register_animation_tools(FakeMCP(), bridge)

    result = await set_tl(frame_start=1, frame_end=120, fps=30)

    bridge.send_request.assert_awaited_once_with(
        "set_timeline_range",
        {
            "frame_start": 1,
            "frame_end": 120,
            "frame_current": None,
            "fps": 30,
        },
    )
    assert result["frame_end"] == 120
