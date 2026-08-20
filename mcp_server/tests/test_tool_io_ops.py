from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.io_ops import register_io_tools


@pytest.mark.asyncio
async def test_export_scene_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "filepath": "C:/tmp/scene.glb",
        "file_format": "GLB",
        "file_size_bytes": 1024,
    }
    export_sc, import_fl = register_io_tools(FakeMCP(), bridge)

    result = await export_sc(filepath="C:/tmp/scene.glb", file_format="GLB")

    bridge.send_request.assert_awaited_once_with(
        "export_scene",
        {
            "filepath": "C:/tmp/scene.glb",
            "file_format": "GLB",
            "selected_only": False,
            "apply_modifiers": True,
            "export_materials": True,
            "export_animations": True,
        },
    )
    assert result["file_size_bytes"] == 1024


@pytest.mark.asyncio
async def test_import_file_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "imported_objects": ["ImportedMesh"],
        "filepath": "C:/tmp/scene.glb",
    }
    export_sc, import_fl = register_io_tools(FakeMCP(), bridge)

    result = await import_fl(filepath="C:/tmp/scene.glb")

    bridge.send_request.assert_awaited_once_with(
        "import_file",
        {
            "filepath": "C:/tmp/scene.glb",
            "file_format": None,
            "forward_axis": None,
            "up_axis": None,
            "check_orientation": True,
            "auto_orient": False,
        },
    )
    assert result["imported_objects"] == ["ImportedMesh"]


@pytest.mark.asyncio
async def test_import_file_forwards_axis_and_auto_orient():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "imported_objects": ["Mesh"]}
    _, import_fl = register_io_tools(FakeMCP(), bridge)

    await import_fl(filepath="C:/tmp/part.stl", up_axis="Y", auto_orient=True)

    payload = bridge.send_request.await_args.args[1]
    assert payload["up_axis"] == "Y"
    assert payload["forward_axis"] is None
    assert payload["auto_orient"] is True
