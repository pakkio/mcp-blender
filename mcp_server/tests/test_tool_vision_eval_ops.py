import base64
from unittest.mock import AsyncMock

import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.errors import BridgeError
from mcp_blender_pakkio.tools.vision_eval_ops import register_vision_eval_tools


@pytest.mark.asyncio
async def test_returns_guidance_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    bridge = AsyncMock()
    handler = register_vision_eval_tools(FakeMCP(), bridge)

    result = await handler(question="is this good?")

    assert result["success"] is False
    assert "OPENROUTER_API_KEY" in result["message"]
    bridge.send_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_multiview_happy_path(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    raw = b"fake-png"
    uri = "data:image/png;base64," + base64.b64encode(raw).decode()

    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "base64_data_uri": uri}
    handler = register_vision_eval_tools(FakeMCP(), bridge)

    async def fake_critique(question, png_bytes, model=None):
        assert png_bytes == raw
        return {"critique": "looks fine", "model": "m", "prompt_tokens": 1, "completion_tokens": 2}

    monkeypatch.setattr("mcp_blender_pakkio.tools.vision_eval_ops.critique_image", fake_critique)

    result = await handler(question="is this good?")

    bridge.send_request.assert_awaited_once_with(
        "capture_multiview_audit", {"target_object": None, "include_base64": True}, timeout=600.0
    )
    assert result["success"] is True
    assert result["critique"] == "looks fine"


@pytest.mark.asyncio
async def test_focus_requires_target_object(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    bridge = AsyncMock()
    handler = register_vision_eval_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError):
        await handler(question="is this good?", view="FOCUS")


@pytest.mark.asyncio
async def test_capture_failure_raises(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "no camera"}
    handler = register_vision_eval_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError, match="no camera"):
        await handler(question="is this good?")
