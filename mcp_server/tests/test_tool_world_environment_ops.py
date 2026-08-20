from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.world_environment_ops import register_world_environment_tools


@pytest.mark.asyncio
async def test_configure_world_environment_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "world_name": "World",
        "background_strength": 1.5,
    }
    cfg_world, cfg_physics, switch_ws = register_world_environment_tools(FakeMCP(), bridge)

    result = await cfg_world(color=[0.1, 0.1, 0.2, 1.0], strength=1.5)
    bridge.send_request.assert_awaited_once_with(
        "configure_world_environment",
        {
            "color": [0.1, 0.1, 0.2, 1.0],
            "strength": 1.5,
            "hdri_path": None,
            "hdri_rotation_z": 0.0,
        },
    )
    assert result["background_strength"] == 1.5


@pytest.mark.asyncio
async def test_configure_scene_physics_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "settings": {"gravity": [0.0, 0.0, -9.81]},
    }
    cfg_world, cfg_physics, switch_ws = register_world_environment_tools(FakeMCP(), bridge)

    result = await cfg_physics(gravity=[0.0, 0.0, -9.81], unit_system="METRIC")
    bridge.send_request.assert_awaited_once_with(
        "configure_scene_physics",
        {
            "gravity": [0.0, 0.0, -9.81],
            "unit_system": "METRIC",
            "unit_scale": None,
            "color_space_view_transform": None,
            "color_space_look": None,
            "color_space_exposure": None,
            "color_space_gamma": None,
        },
    )
    assert result["settings"]["gravity"] == [0.0, 0.0, -9.81]


@pytest.mark.asyncio
async def test_switch_workspace_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "active_workspace": "Sculpting",
    }
    cfg_world, cfg_physics, switch_ws = register_world_environment_tools(FakeMCP(), bridge)

    result = await switch_ws(workspace_name="Sculpting")
    bridge.send_request.assert_awaited_once_with(
        "switch_workspace",
        {"workspace_name": "Sculpting"},
    )
    assert result["active_workspace"] == "Sculpting"
