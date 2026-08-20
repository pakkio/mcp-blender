from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.studio_lighting_ops import register_studio_lighting_tools


@pytest.mark.asyncio
async def test_create_lighting_rig_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "rig_type": "THREE_POINT_STUDIO",
        "lights": ["Key_Light", "Fill_Light", "Rim_Light"],
    }
    create_rig, cfg_linking = register_studio_lighting_tools(FakeMCP(), bridge)

    result = await create_rig(
        rig_type="THREE_POINT_STUDIO",
        target_object="Character",
        energy_multiplier=1.5,
    )
    bridge.send_request.assert_awaited_once_with(
        "create_lighting_rig",
        {
            "rig_type": "THREE_POINT_STUDIO",
            "target_object": "Character",
            "energy_multiplier": 1.5,
        },
    )
    assert len(result["lights"]) == 3


@pytest.mark.asyncio
async def test_configure_light_linking_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "light_name": "Key_Light",
    }
    create_rig, cfg_linking = register_studio_lighting_tools(FakeMCP(), bridge)

    result = await cfg_linking(
        light_name="Key_Light",
        collection_name="HeroAssets",
    )
    bridge.send_request.assert_awaited_once_with(
        "configure_light_linking",
        {
            "light_name": "Key_Light",
            "collection_name": "HeroAssets",
        },
    )
    assert result["success"] is True
