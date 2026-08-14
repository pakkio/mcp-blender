from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
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
    )
    assert result["output_path"] == "C:/tmp/render.png"


@pytest.mark.asyncio
async def test_get_viewport_screenshot_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "output_path": "C:/tmp/viewport.png",
        "image_base64": "iVBORw0KGgo...",
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
    assert result["image_base64"] == "iVBORw0KGgo..."
