from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.render_effects_ops import register_render_effects_tools


@pytest.mark.asyncio
async def test_configure_render_effects_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "effects": {"ambient_occlusion": True, "film_transparent": True},
    }
    cfg_fx, cfg_transp = register_render_effects_tools(FakeMCP(), bridge)

    result = await cfg_fx(
        ambient_occlusion=True,
        ao_distance=3.0,
        reflections=True,
        film_transparent=True,
    )
    bridge.send_request.assert_awaited_once_with(
        "configure_render_effects",
        {
            "ambient_occlusion": True,
            "ao_distance": 3.0,
            "ao_factor": None,
            "reflections": True,
            "refraction": None,
            "motion_blur": None,
            "motion_blur_shutter": None,
            "depth_of_field": None,
            "film_transparent": True,
            "volumetric_start": None,
            "volumetric_end": None,
        },
    )
    assert result["effects"]["ambient_occlusion"] is True


@pytest.mark.asyncio
async def test_configure_material_transparency_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "material_name": "Glass",
        "transmission": 0.95,
        "ior": 1.5,
    }
    cfg_fx, cfg_transp = register_render_effects_tools(FakeMCP(), bridge)

    result = await cfg_transp(
        material_name="Glass",
        transmission_weight=0.95,
        ior=1.5,
        blend_mode="BLEND",
    )
    bridge.send_request.assert_awaited_once_with(
        "configure_material_transparency",
        {
            "material_name": "Glass",
            "transmission_weight": 0.95,
            "ior": 1.5,
            "roughness": None,
            "alpha": None,
            "blend_mode": "BLEND",
            "shadow_mode": "HASHED",
            "use_screen_refraction": None,
            "backface_culling": None,
        },
    )
    assert result["transmission"] == 0.95
