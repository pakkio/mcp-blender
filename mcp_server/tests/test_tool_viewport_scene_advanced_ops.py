from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.viewport_scene_advanced_ops import register_viewport_scene_advanced_tools


@pytest.mark.asyncio
async def test_configure_viewport_display_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "updated_settings": {"shading_type": "SOLID", "show_cavity": True},
    }
    cfg_view, purge_clean, align_objs = register_viewport_scene_advanced_tools(FakeMCP(), bridge)

    result = await cfg_view(
        shading_type="SOLID",
        show_cavity=True,
        show_stats=True,
    )
    bridge.send_request.assert_awaited_once_with(
        "configure_viewport_display",
        {
            "shading_type": "SOLID",
            "color_type": None,
            "show_cavity": True,
            "show_shadows": None,
            "show_wireframe": None,
            "show_face_orientation": None,
            "show_stats": True,
            "matcap_name": None,
        },
    )
    assert result["updated_settings"]["show_cavity"] is True


@pytest.mark.asyncio
async def test_purge_orphans_and_cleanup_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "action": "PURGE_ORPHANS",
    }
    cfg_view, purge_clean, align_objs = register_viewport_scene_advanced_tools(FakeMCP(), bridge)

    result = await purge_clean(action="PURGE_ORPHANS", num_passes=2)
    bridge.send_request.assert_awaited_once_with(
        "purge_orphans_and_cleanup",
        {"action": "PURGE_ORPHANS", "num_passes": 2},
    )
    assert result["action"] == "PURGE_ORPHANS"


@pytest.mark.asyncio
async def test_align_distribute_objects_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "action": "DISTRIBUTE_GRID",
        "objects_count": 4,
    }
    cfg_view, purge_clean, align_objs = register_viewport_scene_advanced_tools(FakeMCP(), bridge)

    result = await align_objs(
        object_names=["Obj1", "Obj2", "Obj3", "Obj4"],
        action="DISTRIBUTE_GRID",
        spacing=3.0,
        grid_columns=2,
    )
    bridge.send_request.assert_awaited_once_with(
        "align_distribute_objects",
        {
            "object_names": ["Obj1", "Obj2", "Obj3", "Obj4"],
            "action": "DISTRIBUTE_GRID",
            "spacing": 3.0,
            "grid_columns": 2,
            "axis": "X",
        },
    )
    assert result["objects_count"] == 4
