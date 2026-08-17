from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.grease_pencil_ops import register_grease_pencil_tools


@pytest.mark.asyncio
async def test_setup_line_art_contour_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "gp_object": "LineArt_Ink",
        "source_type": "SCENE",
    }
    setup_lineart, *_ = register_grease_pencil_tools(FakeMCP(), bridge)

    result = await setup_lineart(
        source_type="SCENE",
        thickness=4,
        use_crease=True,
    )
    bridge.send_request.assert_awaited_once_with(
        "setup_line_art_contour",
        {
            "source_type": "SCENE",
            "target_object": None,
            "thickness": 4,
            "use_crease": True,
        },
    )
    assert result["gp_object"] == "LineArt_Ink"
