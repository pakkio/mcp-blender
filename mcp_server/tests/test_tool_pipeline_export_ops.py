from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.pipeline_export_ops import register_pipeline_export_tools


@pytest.mark.asyncio
async def test_export_unity_fbx_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "filepath": "model.fbx",
        "axis_conversion": "Forward: -Z, Up: Y (Unity Native)",
    }
    unity_fbx, gen_lods = register_pipeline_export_tools(FakeMCP(), bridge)

    result = await unity_fbx(
        filepath="model.fbx",
        bake_anim=True,
        apply_modifiers=True,
    )
    bridge.send_request.assert_awaited_once_with(
        "export_unity_fbx",
        {
            "filepath": "model.fbx",
            "selected_only": False,
            "bake_anim": True,
            "apply_modifiers": True,
            "embed_textures": False,
        },
    )
    assert "Unity Native" in result["axis_conversion"]


@pytest.mark.asyncio
async def test_generate_lods_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "lod_group": "Cube_LODGroup",
        "lods": [{"name": "Cube_LOD0"}, {"name": "Cube_LOD1"}],
    }
    unity_fbx, gen_lods = register_pipeline_export_tools(FakeMCP(), bridge)

    result = await gen_lods(
        object_name="Cube",
        ratios=[1.0, 0.5, 0.25],
    )
    bridge.send_request.assert_awaited_once_with(
        "generate_lods",
        {
            "object_name": "Cube",
            "ratios": [1.0, 0.5, 0.25],
            "group_name": None,
        },
    )
    assert result["lod_group"] == "Cube_LODGroup"
