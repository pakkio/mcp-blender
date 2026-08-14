from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.constraint_ops import register_constraint_tools


@pytest.mark.asyncio
async def test_add_constraint_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Camera",
        "constraint_name": "Track_To_Auto",
        "constraint_type": "TRACK_TO",
    }
    add_con, turntable = register_constraint_tools(FakeMCP(), bridge)

    result = await add_con(
        object_name="Camera",
        constraint_type="TRACK_TO",
        target_object="Cube",
    )
    bridge.send_request.assert_awaited_once_with(
        "add_constraint",
        {
            "object_name": "Camera",
            "constraint_type": "TRACK_TO",
            "target_object": "Cube",
            "subtarget": None,
            "name": None,
            "properties": None,
        },
    )
    assert result["constraint_type"] == "TRACK_TO"


@pytest.mark.asyncio
async def test_animate_camera_turntable_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "camera_name": "Camera",
        "frame_range": [1, 121],
    }
    add_con, turntable = register_constraint_tools(FakeMCP(), bridge)

    result = await turntable(
        camera_name="Camera",
        target_object="Cube",
        radius=8.0,
        height=4.0,
        duration_frames=120,
    )
    bridge.send_request.assert_awaited_once_with(
        "animate_camera_turntable",
        {
            "camera_name": "Camera",
            "target_object": "Cube",
            "target_location": [0.0, 0.0, 0.0],
            "radius": 8.0,
            "height": 4.0,
            "duration_frames": 120,
            "start_frame": 1,
        },
    )
    assert result["frame_range"] == [1, 121]
