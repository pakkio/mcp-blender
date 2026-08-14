from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.rigging_ops import register_rigging_tools


@pytest.mark.asyncio
async def test_create_armature_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "armature_name": "HeroRig",
        "bones": ["Root", "Spine", "Head"],
    }
    create_arm, pose_b = register_rigging_tools(FakeMCP(), bridge)

    result = await create_arm(
        name="HeroRig",
        bones=[
            {"name": "Root", "head": [0, 0, 0], "tail": [0, 0, 1]},
            {"name": "Spine", "head": [0, 0, 1], "tail": [0, 0, 2], "parent": "Root"},
        ],
    )
    bridge.send_request.assert_awaited_once_with(
        "create_armature",
        {
            "name": "HeroRig",
            "location": [0.0, 0.0, 0.0],
            "bones": [
                {"name": "Root", "head": [0, 0, 0], "tail": [0, 0, 1]},
                {"name": "Spine", "head": [0, 0, 1], "tail": [0, 0, 2], "parent": "Root"},
            ],
            "bind_mesh": None,
            "bind_type": "AUTOMATIC_WEIGHTS",
        },
    )
    assert result["armature_name"] == "HeroRig"


@pytest.mark.asyncio
async def test_pose_bone_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "armature_name": "HeroRig",
        "bone_name": "Spine",
        "frame": 10,
    }
    create_arm, pose_b = register_rigging_tools(FakeMCP(), bridge)

    result = await pose_b(
        armature_name="HeroRig",
        bone_name="Spine",
        rotation_euler=[0.2, 0.0, 0.0],
        frame=10,
    )
    bridge.send_request.assert_awaited_once_with(
        "pose_bone",
        {
            "armature_name": "HeroRig",
            "bone_name": "Spine",
            "location": None,
            "rotation_euler": [0.2, 0.0, 0.0],
            "rotation_quaternion": None,
            "scale": None,
            "frame": 10,
        },
    )
    assert result["frame"] == 10
