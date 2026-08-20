from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from conftest import FakeMCP
from mcp_blender.errors import BridgeError, ErrorType
from mcp_blender.tools.create_object import register_create_object_tool


@pytest.mark.asyncio
async def test_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "message": "Created object 'Cube'",
        "name": "Cube",
        "type": "MESH",
        "location": [0.0, 0.0, 0.0],
        "rotation_euler": [0.0, 0.0, 0.0],
        "scale": [1.0, 1.0, 1.0],
    }
    handler = register_create_object_tool(FakeMCP(), bridge)

    result = await handler(object_type="CUBE", name="Cube")

    bridge.send_request.assert_awaited_once()
    method, params = bridge.send_request.await_args.args
    assert method == "create_object"
    assert params["object_type"] == "CUBE"
    assert params["name"] == "Cube"
    assert result["name"] == "Cube"


@pytest.mark.asyncio
async def test_invalid_object_type_rejected_before_bridge_call():
    bridge = AsyncMock()
    handler = register_create_object_tool(FakeMCP(), bridge)

    with pytest.raises(ValidationError):
        await handler(object_type="NOT_A_REAL_TYPE")

    bridge.send_request.assert_not_called()


@pytest.mark.asyncio
async def test_domain_failure_raises_tool_execution_error():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "Unknown object_type 'FOO'"}
    handler = register_create_object_tool(FakeMCP(), bridge)

    with pytest.raises(BridgeError) as exc_info:
        await handler()

    assert exc_info.value.error_type is ErrorType.TOOL_EXECUTION
