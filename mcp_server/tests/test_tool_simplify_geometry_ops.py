from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.bridge import HEAVY_REQUEST_TIMEOUT_S
from mcp_blender.tools.simplify_geometry_ops import register_simplify_geometry_tools


@pytest.mark.asyncio
async def test_simplify_geometry_happy_path_defaults():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Fork",
        "original_vertices": 40000,
        "result_vertices": 9950,
    }
    (simplify_geometry,) = register_simplify_geometry_tools(FakeMCP(), bridge)

    result = await simplify_geometry(object_name="Fork", preset="BACKGROUND")

    bridge.send_request.assert_awaited_once_with(
        "simplify_geometry",
        {
            "object_name": "Fork",
            "target": None,
            "target_unit": "VERTICES",
            "preset": "BACKGROUND",
            "repair": True,
            "weld_factor": 0.0001,
            "preserve_uv": True,
            "preserve_boundaries": True,
            "sharp_angle": 3.0,
            "tolerance": 0.05,
            "use_symmetry": False,
            "symmetry_axis": "X",
            "max_deviation_pct": 2.0,
            "allow_new_holes": 0,
            "rollback_on_failure": True,
            "dry_run": False,
        },
        timeout=HEAVY_REQUEST_TIMEOUT_S,
    )
    assert result["result_vertices"] == 9950


@pytest.mark.asyncio
async def test_simplify_geometry_failure_raises_bridge_error():
    from mcp_blender.errors import BridgeError

    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": False,
        "message": "Quality gate failed and 'Fork' was rolled back; try target=25000",
    }
    (simplify_geometry,) = register_simplify_geometry_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError) as exc_info:
        await simplify_geometry(object_name="Fork", target=10000)

    assert "rolled back" in str(exc_info.value)


@pytest.mark.asyncio
async def test_simplify_geometry_dry_run_forwards_flag():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "dry_run": True}
    (simplify_geometry,) = register_simplify_geometry_tools(FakeMCP(), bridge)

    await simplify_geometry(object_name="Fork", target=5000, dry_run=True)

    payload = bridge.send_request.await_args.args[1]
    assert payload["dry_run"] is True
    assert payload["target"] == 5000
