import base64
from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp.server.fastmcp import Image
from mcp_blender_pakkio.bridge import HEAVY_REQUEST_TIMEOUT_S
from mcp_blender_pakkio.tools.render_ops import register_render_tools


@pytest.mark.asyncio
async def test_render_scene_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "output_path": "C:/tmp/render.png",
        "render_time_seconds": 1.2,
    }
    render_sc, get_ss, set_rs = register_render_tools(FakeMCP(), bridge)

    result = await render_sc(output_path="C:/tmp/render.png", engine="CYCLES", samples=64)

    bridge.send_request.assert_awaited_once_with(
        "render_scene",
        {
            "output_path": "C:/tmp/render.png",
            "engine": "CYCLES",
            "resolution_x": None,
            "resolution_y": None,
            "resolution_percentage": None,
            "samples": 64,
            "transparent_background": None,
            "animation": False,
            "return_image_base64": False,
        },
        timeout=HEAVY_REQUEST_TIMEOUT_S,
    )
    assert result["output_path"] == "C:/tmp/render.png"


@pytest.mark.asyncio
async def test_get_viewport_screenshot_happy_path():
    raw_bytes = b"fake-png-bytes"
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "output_path": "C:/tmp/viewport.png",
        "image_base64": base64.b64encode(raw_bytes).decode("utf-8"),
    }
    render_sc, get_ss, set_rs = register_render_tools(FakeMCP(), bridge)

    result = await get_ss(output_path="C:/tmp/viewport.png", return_image_base64=True)

    bridge.send_request.assert_awaited_once_with(
        "get_viewport_screenshot",
        {
            "output_path": "C:/tmp/viewport.png",
            "return_image_base64": True,
        },
    )
    assert isinstance(result, list)
    assert isinstance(result[0], Image)
    assert result[0].data == raw_bytes
    assert result[1]["output_path"] == "C:/tmp/viewport.png"
    assert "image_base64" not in result[1]


@pytest.mark.asyncio
async def test_get_viewport_screenshot_without_base64_returns_dict():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "output_path": "C:/tmp/viewport.png",
    }
    render_sc, get_ss, set_rs = register_render_tools(FakeMCP(), bridge)

    result = await get_ss(output_path="C:/tmp/viewport.png", return_image_base64=False)

    assert result == {"success": True, "output_path": "C:/tmp/viewport.png"}
