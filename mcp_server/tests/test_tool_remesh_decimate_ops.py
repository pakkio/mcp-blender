from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.bridge import HEAVY_REQUEST_TIMEOUT_S
from mcp_blender_pakkio.tools.remesh_decimate_ops import register_remesh_decimate_tools


@pytest.mark.asyncio
async def test_decimate_mesh_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Cube",
        "mode": "COLLAPSE",
        "result_vertices": 50,
    }
    decimate, remesh = register_remesh_decimate_tools(FakeMCP(), bridge)

    result = await decimate(object_name="Cube", ratio=0.25)
    bridge.send_request.assert_awaited_once_with(
        "decimate_mesh",
        {
            "object_name": "Cube",
            "mode": "COLLAPSE",
            "ratio": 0.25,
            "iterations": 2,
            "angle_limit": 5.0,
            "use_symmetry": False,
            "symmetry_axis": "X",
            "apply_immediately": True,
        },
        timeout=HEAVY_REQUEST_TIMEOUT_S,
    )
    assert result["result_vertices"] == 50


@pytest.mark.asyncio
async def test_remesh_mesh_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Cube",
        "mode": "VOXEL",
        "result_vertices": 1200,
    }
    decimate, remesh = register_remesh_decimate_tools(FakeMCP(), bridge)

    result = await remesh(object_name="Cube", mode="VOXEL", voxel_size=0.02)
    bridge.send_request.assert_awaited_once_with(
        "remesh_mesh",
        {
            "object_name": "Cube",
            "mode": "VOXEL",
            "voxel_size": 0.02,
            "adaptivity": 0.0,
            "octree_depth": 4,
            "scale": 0.9,
            "smooth_shading": True,
            "apply_immediately": True,
        },
    )
    assert result["mode"] == "VOXEL"
