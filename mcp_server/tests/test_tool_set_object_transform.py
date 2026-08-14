from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from conftest import FakeMCP
from mcp_blender_pakkio.errors import BridgeError, ErrorType
from mcp_blender_pakkio.tools.set_object_transform import register_set_object_transform_tool


@pytest.mark.asyncio
async def test_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "message": "Updated transform for 'Cube'",
        "name": "Cube",
        "location": [1.0, 2.0, 3.0],
        "rotation_euler": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
    }
    handler = register_set_object_transform_tool(FakeMCP(), bridge)

    result = await handler(name="Cube", location=(1.0, 2.0, 3.0))

    bridge.send_request.assert_awaited_once()
    method, params = bridge.send_request.await_args.args
    assert method == "set_object_transform"
    assert params["name"] == "Cube"
    assert result["location"] == [1.0, 2.0, 3.0]


@pytest.mark.asyncio
async def test_missing_required_name_rejected_before_bridge_call():
    bridge = AsyncMock()
    handler = register_set_object_transform_tool(FakeMCP(), bridge)

    with pytest.raises(ValidationError):
        await handler(name=None)

    bridge.send_request.assert_not_called()


@pytest.mark.asyncio
async def test_domain_failure_raises_tool_execution_error():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "Object 'Ghost' not found"}
    handler = register_set_object_transform_tool(FakeMCP(), bridge)

    with pytest.raises(BridgeError) as exc_info:
        await handler(name="Ghost")

    assert exc_info.value.error_type is ErrorType.TOOL_EXECUTION
    assert "Ghost" in exc_info.value.message
