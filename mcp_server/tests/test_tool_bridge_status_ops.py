from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.errors import BridgeError
from mcp_blender.tools.bridge_status_ops import register_bridge_status_tools


@pytest.mark.asyncio
async def test_get_bridge_status_idle():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "busy": False, "current": None, "queue_depth": 0}
    (status_fn,) = register_bridge_status_tools(FakeMCP(), bridge)

    result = await status_fn()

    assert result["busy"] is False
    bridge.send_request.assert_awaited_with("bridge_status", {}, timeout=5.0)


@pytest.mark.asyncio
async def test_get_bridge_status_busy():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "busy": True,
        "current": {"method": "create_scene_checkpoint", "request_id": "abc", "running_for_s": 12.3},
        "queue_depth": 1,
    }
    (status_fn,) = register_bridge_status_tools(FakeMCP(), bridge)

    result = await status_fn()

    assert result["busy"] is True
    assert result["current"]["method"] == "create_scene_checkpoint"
    assert result["queue_depth"] == 1


@pytest.mark.asyncio
async def test_get_bridge_status_raises_on_failure():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "boom"}
    (status_fn,) = register_bridge_status_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError):
        await status_fn()


@pytest.mark.asyncio
async def test_get_bridge_status_carries_phased_progress():
    """Long tools publish viewport-HUD progress (title/status/percent/steps);
    get_bridge_status must pass that block through untouched so MCP clients
    can poll the % bar while the heavy call is still in flight."""
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "busy": True,
        "current": {"method": "simplify_geometry", "request_id": "abc", "running_for_s": 42.1},
        "client_status": None,
        "progress": {
            "visible": True,
            "title": "Simplify 'Cat' (1,033,549 -> ~50,000 verts)",
            "status": "Shrinking flat zones, keeping the details  [42s]",
            "progress": 72.5,
            "step_current": 0,
            "step_total": 0,
            "details": ["Solving collapse ratio (3/4, try 0.0521)..."],
            "completed_summary": "",
            "next_steps": [],
            "updated_at": 1234567890.0,
            "age_s": 0.3,
        },
        "queue_depth": 0,
    }
    (status_fn,) = register_bridge_status_tools(FakeMCP(), bridge)

    result = await status_fn()

    assert result["busy"] is True
    assert result["progress"]["progress"] == 72.5
    assert "Shrinking flat zones" in result["progress"]["status"]
    assert result["progress"]["age_s"] == 0.3
