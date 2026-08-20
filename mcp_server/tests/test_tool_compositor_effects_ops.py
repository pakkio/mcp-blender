from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.compositor_effects_ops import register_compositor_effects_tools


@pytest.mark.asyncio
async def test_configure_compositor_effects_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "glare_enabled": True,
    }
    cfg_comp, toon_mat = register_compositor_effects_tools(FakeMCP(), bridge)

    result = await cfg_comp(
        use_glare=True,
        glare_threshold=0.7,
        use_lens_distortion=True,
    )
    bridge.send_request.assert_awaited_once_with(
        "configure_compositor_effects",
        {
            "use_glare": True,
            "glare_threshold": 0.7,
            "glare_size": 8,
            "use_lens_distortion": True,
            "distortion": 0.02,
            "dispersion": 0.03,
            "use_viewport_compositing": True,
        },
    )
    assert result["glare_enabled"] is True


@pytest.mark.asyncio
async def test_create_toon_shader_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "material_name": "M_AnimeToon",
    }
    cfg_comp, toon_mat = register_compositor_effects_tools(FakeMCP(), bridge)

    result = await toon_mat(
        material_name="M_AnimeToon",
        object_name="Suzanne",
        base_color=[0.2, 0.6, 0.8, 1.0],
    )
    bridge.send_request.assert_awaited_once_with(
        "create_toon_shader",
        {
            "material_name": "M_AnimeToon",
            "object_name": "Suzanne",
            "base_color": [0.2, 0.6, 0.8, 1.0],
            "shadow_color": [0.4, 0.1, 0.2, 1.0],
            "rim_color": [1.0, 0.9, 0.6, 1.0],
            "rim_power": 3.0,
        },
    )
    assert result["material_name"] == "M_AnimeToon"
