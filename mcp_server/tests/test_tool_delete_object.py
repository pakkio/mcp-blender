from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from conftest import FakeMCP
from mcp_blender.errors import BridgeError, ErrorType
from mcp_blender.tools.delete_object import register_delete_object_tool


@pytest.mark.asyncio
async def test_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "message": "Deleted object 'Cube'"}
    handler = register_delete_object_tool(FakeMCP(), bridge)

    result = await handler(name="Cube")

    bridge.send_request.assert_awaited_once_with(
        "delete_object", {"name": "Cube", "delete_hierarchy": False}
    )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_missing_required_name_rejected_before_bridge_call():
    bridge = AsyncMock()
    handler = register_delete_object_tool(FakeMCP(), bridge)

    with pytest.raises(ValidationError):
        await handler(name=None, names=None)

    bridge.send_request.assert_not_called()


@pytest.mark.asyncio
async def test_domain_failure_raises_tool_execution_error():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "Object 'Ghost' not found"}
    handler = register_delete_object_tool(FakeMCP(), bridge)

    with pytest.raises(BridgeError) as exc_info:
        await handler(name="Ghost")

    assert exc_info.value.error_type is ErrorType.TOOL_EXECUTION
