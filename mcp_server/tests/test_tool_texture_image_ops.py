from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.texture_image_ops import register_texture_image_tools


@pytest.mark.asyncio
async def test_import_image_as_plane_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "name": "MyTexturePlane",
        "dimensions": [4.0, 2.0],
    }
    import_plane, project_tex = register_texture_image_tools(FakeMCP(), bridge)

    result = await import_plane(image_path="test.png", height=2.0, alpha_mode="CLIP")
    bridge.send_request.assert_awaited_once_with(
        "import_image_as_plane",
        {
            "image_path": "test.png",
            "name": None,
            "location": [0.0, 0.0, 0.0],
            "rotation_euler": [0.0, 0.0, 0.0],
            "height": 2.0,
            "emit_strength": 0.0,
            "alpha_mode": "CLIP",
        },
    )
    assert result["name"] == "MyTexturePlane"


@pytest.mark.asyncio
async def test_project_image_texture_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "target_object": "Cube",
        "projection_type": "CAMERA",
    }
    import_plane, project_tex = register_texture_image_tools(FakeMCP(), bridge)

    result = await project_tex(target_object="Cube", image_path="decal.png", projection_type="CAMERA")
    bridge.send_request.assert_awaited_once_with(
        "project_image_texture",
        {
            "target_object": "Cube",
            "image_path": "decal.png",
            "projection_type": "CAMERA",
            "camera_name": None,
            "empty_name": None,
            "material_name": None,
        },
    )
    assert result["target_object"] == "Cube"
