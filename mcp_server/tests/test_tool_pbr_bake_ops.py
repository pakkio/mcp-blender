from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.pbr_bake_ops import register_pbr_bake_tools


@pytest.mark.asyncio
async def test_setup_pbr_materials_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "material_name": "PBR_Wood",
        "connected_maps": ["albedo", "normal", "roughness"],
    }
    setup_pbr, proc_mat, bake_tex = register_pbr_bake_tools(FakeMCP(), bridge)

    result = await setup_pbr(
        material_name="PBR_Wood",
        albedo_path="wood_albedo.png",
        normal_path="wood_normal.png",
        roughness_path="wood_rough.png",
    )
    bridge.send_request.assert_awaited_once_with(
        "setup_pbr_materials",
        {
            "material_name": "PBR_Wood",
            "object_name": None,
            "albedo_path": "wood_albedo.png",
            "normal_path": "wood_normal.png",
            "roughness_path": "wood_rough.png",
            "metallic_path": None,
            "height_path": None,
            "emission_path": None,
            "ao_path": None,
            "uv_scale": [1.0, 1.0, 1.0],
        },
    )
    assert len(result["connected_maps"]) == 3


@pytest.mark.asyncio
async def test_create_procedural_material_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "material_name": "ProceduralMarble",
        "pattern": "VORONOI",
    }
    setup_pbr, proc_mat, bake_tex = register_pbr_bake_tools(FakeMCP(), bridge)

    result = await proc_mat(
        material_name="ProceduralMarble",
        pattern="VORONOI",
        scale=10.0,
    )
    bridge.send_request.assert_awaited_once_with(
        "create_procedural_material",
        {
            "material_name": "ProceduralMarble",
            "pattern": "VORONOI",
            "scale": 10.0,
            "detail": 4.0,
            "roughness": 0.5,
            "color1": [0.8, 0.2, 0.2, 1.0],
            "color2": [0.1, 0.1, 0.3, 1.0],
            "bump_strength": 0.1,
            "metallic": 0.0,
            "object_name": None,
        },
    )
    assert result["pattern"] == "VORONOI"


@pytest.mark.asyncio
async def test_bake_textures_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Cube",
        "bake_type": "NORMAL",
    }
    setup_pbr, proc_mat, bake_tex = register_pbr_bake_tools(FakeMCP(), bridge)

    result = await bake_tex(
        object_name="Cube",
        output_filepath="normal_baked.png",
        bake_type="NORMAL",
    )
    bridge.send_request.assert_awaited_once_with(
        "bake_textures",
        {
            "object_name": "Cube",
            "bake_type": "NORMAL",
            "output_filepath": "normal_baked.png",
            "width": 1024,
            "height": 1024,
            "samples": 16,
        },
    )
    assert result["bake_type"] == "NORMAL"
