from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.advanced_mesh_edit_ops import register_advanced_mesh_edit_tools


@pytest.mark.asyncio
async def test_advanced_mesh_edit_bisect_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Sphere",
        "operation": "BISECT",
    }
    mesh_edit, origin_cursor = register_advanced_mesh_edit_tools(FakeMCP(), bridge)

    result = await mesh_edit(
        object_name="Sphere",
        operation="BISECT",
        plane_co=[0.0, 0.0, 1.0],
        plane_no=[0.0, 0.0, 1.0],
        clear_outer=True,
    )
    bridge.send_request.assert_awaited_once_with(
        "advanced_mesh_edit",
        {
            "object_name": "Sphere",
            "operation": "BISECT",
            "plane_co": [0.0, 0.0, 1.0],
            "plane_no": [0.0, 0.0, 1.0],
            "clear_inner": False,
            "clear_outer": True,
            "use_fill": True,
            "number_cuts": 0,
            "offset": 0.2,
            "crease_value": 1.0,
            "weight_value": 1.0,
            "other_objects": None,
        },
    )
    assert result["operation"] == "BISECT"


@pytest.mark.asyncio
async def test_manipulate_origin_cursor_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Sphere",
        "new_origin_location": [0.0, 0.0, 0.0],
    }
    mesh_edit, origin_cursor = register_advanced_mesh_edit_tools(FakeMCP(), bridge)

    result = await origin_cursor(
        object_name="Sphere",
        action="ORIGIN_TO_BOTTOM",
    )
    bridge.send_request.assert_awaited_once_with(
        "manipulate_origin_cursor",
        {
            "object_name": "Sphere",
            "action": "ORIGIN_TO_BOTTOM",
            "location": None,
        },
    )
    assert result["success"] is True
