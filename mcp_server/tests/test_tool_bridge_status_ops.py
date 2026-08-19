from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.errors import BridgeError
from mcp_blender_pakkio.tools.bridge_status_ops import register_bridge_status_tools


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
