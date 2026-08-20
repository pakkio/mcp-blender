from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.camera_ops import register_camera_tools


@pytest.mark.asyncio
async def test_configure_camera_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "name": "Camera", "lens": 85.0}
    config_cam, look_at, frame_obs = register_camera_tools(FakeMCP(), bridge)

    result = await config_cam(name="Camera", lens=85.0, set_as_active_camera=True)

    bridge.send_request.assert_awaited_once_with(
        "configure_camera",
        {
            "name": "Camera",
            "lens": 85.0,
            "camera_type": None,
            "ortho_scale": None,
            "clip_start": None,
            "clip_end": None,
            "sensor_width": None,
            "dof_focus_object": None,
            "dof_fstop": None,
            "set_as_active_camera": True,
        },
    )
    assert result["lens"] == 85.0


@pytest.mark.asyncio
async def test_camera_look_at_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "camera_name": "Camera"}
    config_cam, look_at, frame_obs = register_camera_tools(FakeMCP(), bridge)

    result = await look_at(camera_name="Camera", target_location=(0.0, 0.0, 1.0))

    bridge.send_request.assert_awaited_once_with(
        "camera_look_at",
        {
            "camera_name": "Camera",
            "target_location": (0.0, 0.0, 1.0),
            "target_object": None,
            "add_constraint": False,
        },
    )
    assert result["success"] is True
