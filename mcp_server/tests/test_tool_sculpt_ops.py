from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.sculpt_ops import register_sculpt_tools


@pytest.mark.asyncio
async def test_configure_sculpt_mode_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "SculptSphere",
        "current_mode": "SCULPT",
        "active_brush": "Draw",
    }
    cfg_sculpt, apply_filter, mask_ops = register_sculpt_tools(FakeMCP(), bridge)

    result = await cfg_sculpt(
        object_name="SculptSphere",
        action="ENTER",
        brush_type="DRAW",
        brush_size=50,
        brush_strength=0.8,
        use_symmetry_x=True,
    )
    bridge.send_request.assert_awaited_once_with(
        "configure_sculpt_mode",
        {
            "object_name": "SculptSphere",
            "action": "ENTER",
            "brush_type": "DRAW",
            "brush_size": 50.0,
            "brush_strength": 0.8,
            "use_symmetry_x": True,
            "use_symmetry_y": None,
            "use_symmetry_z": None,
            "use_dyntopo": None,
            "dyntopo_detail": None,
            "dyntopo_detail_type": "RELATIVE",
        },
    )
    assert result["current_mode"] == "SCULPT"


@pytest.mark.asyncio
async def test_apply_sculpt_filter_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "SculptSphere",
        "filter_type": "INFLATE",
    }
    cfg_sculpt, apply_filter, mask_ops = register_sculpt_tools(FakeMCP(), bridge)

    result = await apply_filter(
        object_name="SculptSphere",
        filter_type="INFLATE",
        strength=0.4,
    )
    bridge.send_request.assert_awaited_once_with(
        "apply_sculpt_filter",
        {
            "object_name": "SculptSphere",
            "filter_type": "INFLATE",
            "strength": 0.4,
            "iterations": 1,
            "deform_axis": "XYZ",
        },
    )
    assert result["filter_type"] == "INFLATE"


@pytest.mark.asyncio
async def test_sculpt_mask_facesets_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "SculptSphere",
        "action": "CLEAR_MASK",
    }
    cfg_sculpt, apply_filter, mask_ops = register_sculpt_tools(FakeMCP(), bridge)

    result = await mask_ops(
        object_name="SculptSphere",
        action="CLEAR_MASK",
    )
    bridge.send_request.assert_awaited_once_with(
        "sculpt_mask_facesets",
        {
            "object_name": "SculptSphere",
            "action": "CLEAR_MASK",
        },
    )
    assert result["action"] == "CLEAR_MASK"
