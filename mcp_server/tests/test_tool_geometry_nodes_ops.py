from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.bridge import HEAVY_REQUEST_TIMEOUT_S
from mcp_blender.tools.geometry_nodes_ops import register_geometry_nodes_tools


@pytest.mark.asyncio
async def test_create_geometry_nodes_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Terrain",
        "preset": "SCATTER_ON_SURFACE",
        "nodes_count": 6,
    }
    create_gn, edit_gn, bake_gn = register_geometry_nodes_tools(FakeMCP(), bridge)

    result = await create_gn(
        object_name="Terrain",
        preset="SCATTER_ON_SURFACE",
        preset_params={"density": 50.0},
    )
    bridge.send_request.assert_awaited_once_with(
        "create_geometry_nodes",
        {
            "object_name": "Terrain",
            "modifier_name": "GeometryNodes",
            "preset": "SCATTER_ON_SURFACE",
            "preset_params": {"density": 50.0},
        },
    )
    assert result["preset"] == "SCATTER_ON_SURFACE"


@pytest.mark.asyncio
async def test_edit_geometry_nodes_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "message": "Connected 'Distribute.Points' -> 'Instance.Points'",
    }
    create_gn, edit_gn, bake_gn = register_geometry_nodes_tools(FakeMCP(), bridge)

    result = await edit_gn(
        object_name="Terrain",
        action="CONNECT_NODES",
        from_node="Distribute",
        from_socket="Points",
        to_node="Instance",
        to_socket="Points",
    )
    bridge.send_request.assert_awaited_once_with(
        "edit_geometry_nodes",
        {
            "object_name": "Terrain",
            "modifier_name": "GeometryNodes",
            "action": "CONNECT_NODES",
            "node_type": None,
            "node_name": None,
            "node_location": [0.0, 0.0],
            "from_node": "Distribute",
            "from_socket": "Points",
            "to_node": "Instance",
            "to_socket": "Points",
            "input_name": None,
            "input_value": None,
        },
    )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_bake_geometry_nodes_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Terrain",
        "result_vertices": 1200,
    }
    create_gn, edit_gn, bake_gn = register_geometry_nodes_tools(FakeMCP(), bridge)

    result = await bake_gn(object_name="Terrain")
    bridge.send_request.assert_awaited_once_with(
        "bake_geometry_nodes",
        {
            "object_name": "Terrain",
            "modifier_name": "GeometryNodes",
        },
        timeout=HEAVY_REQUEST_TIMEOUT_S,
    )
    assert result["result_vertices"] == 1200
