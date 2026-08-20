from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.physics_simulation_ops import register_physics_simulation_tools


@pytest.mark.asyncio
async def test_setup_rigid_body_simulation_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Box",
        "body_type": "ACTIVE",
    }
    setup_rb, setup_cloth, add_force = register_physics_simulation_tools(FakeMCP(), bridge)

    result = await setup_rb(
        object_name="Box",
        body_type="ACTIVE",
        mass=5.0,
        settle_simulation=True,
    )
    bridge.send_request.assert_awaited_once_with(
        "setup_rigid_body_simulation",
        {
            "object_name": "Box",
            "body_type": "ACTIVE",
            "mass": 5.0,
            "friction": 0.5,
            "bounciness": 0.1,
            "collision_shape": "CONVEX_HULL",
            "settle_simulation": True,
            "settle_frames": 40,
        },
    )
    assert result["body_type"] == "ACTIVE"


@pytest.mark.asyncio
async def test_setup_cloth_simulation_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "ClothSheet",
        "preset": "SILK",
    }
    setup_rb, setup_cloth, add_force = register_physics_simulation_tools(FakeMCP(), bridge)

    result = await setup_cloth(
        object_name="ClothSheet",
        preset="SILK",
    )
    bridge.send_request.assert_awaited_once_with(
        "setup_cloth_simulation",
        {
            "object_name": "ClothSheet",
            "preset": "SILK",
            "pin_vertex_group": None,
            "use_pressure": False,
            "pressure": 1.0,
        },
    )
    assert result["preset"] == "SILK"


@pytest.mark.asyncio
async def test_add_force_field_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "field_name": "Field_Wind",
    }
    setup_rb, setup_cloth, add_force = register_physics_simulation_tools(FakeMCP(), bridge)

    result = await add_force(
        field_type="WIND",
        strength=25.0,
    )
    bridge.send_request.assert_awaited_once_with(
        "add_force_field",
        {
            "field_type": "WIND",
            "strength": 25.0,
            "flow": 1.0,
            "location": [0.0, 0.0, 0.0],
            "rotation": [0.0, 0.0, 0.0],
        },
    )
    assert result["field_name"] == "Field_Wind"
