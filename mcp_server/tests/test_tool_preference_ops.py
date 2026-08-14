from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.preference_ops import register_preference_tools


@pytest.mark.asyncio
async def test_configure_preferences_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "updated_preferences": {"undo_steps": 64},
    }
    cfg_pref, sys_info = register_preference_tools(FakeMCP(), bridge)

    result = await cfg_pref(undo_steps=64, view_rotate_method="TURNTABLE")
    bridge.send_request.assert_awaited_once_with(
        "configure_preferences",
        {
            "compute_device_type": None,
            "use_cpu_with_gpu": None,
            "undo_steps": 64,
            "undo_memory_limit_mb": None,
            "autosave_interval_minutes": None,
            "view_rotate_method": "TURNTABLE",
            "save_user_preferences": False,
        },
    )
    assert result["updated_preferences"]["undo_steps"] == 64


@pytest.mark.asyncio
async def test_get_system_info_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "blender_version": "5.2.0 LTS",
        "os_platform": "Windows-11",
    }
    cfg_pref, sys_info = register_preference_tools(FakeMCP(), bridge)

    result = await sys_info()
    bridge.send_request.assert_awaited_once_with("get_system_info", {})
    assert "5.2" in result["blender_version"]
