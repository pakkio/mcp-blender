from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.vision_feedback_ops import register_vision_feedback_tools


@pytest.mark.asyncio
async def test_capture_multiview_audit_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "output_filepath": "/tmp/audit.png",
        "views": ["Perspective", "Front", "Right", "Top"],
    }
    audit_func, focus_func = register_vision_feedback_tools(FakeMCP(), bridge)

    result = await audit_func(
        target_object="Character",
        resolution=1024,
        shading_mode="SOLID",
    )
    bridge.send_request.assert_awaited_once_with(
        "capture_multiview_audit",
        {
            "target_object": "Character",
            "output_filepath": None,
            "include_base64": False,
            "resolution": 1024,
            "shading_mode": "SOLID",
        },
    )
    assert result["output_filepath"] == "/tmp/audit.png"


@pytest.mark.asyncio
async def test_inspect_focus_shot_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "target_object": "Character",
        "output_filepath": "/tmp/focus.png",
    }
    audit_func, focus_func = register_vision_feedback_tools(FakeMCP(), bridge)

    result = await focus_func(
        target_object="Character",
        focal_length=85.0,
    )
    bridge.send_request.assert_awaited_once_with(
        "inspect_focus_shot",
        {
            "target_object": "Character",
            "focal_length": 85.0,
            "angle_elevation": 20.0,
            "angle_azimuth": 45.0,
            "output_filepath": None,
            "include_base64": False,
        },
    )
    assert result["target_object"] == "Character"
