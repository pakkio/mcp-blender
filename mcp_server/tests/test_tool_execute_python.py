from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from conftest import FakeMCP
from mcp_blender.errors import BridgeError, ErrorType
from mcp_blender.tools.execute_python import register_execute_blender_python_tool


@pytest.mark.asyncio
async def test_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "message": "Executed successfully",
        "stdout": "",
        "result": "42",
    }
    handler = register_execute_blender_python_tool(FakeMCP(), bridge)

    result = await handler(code="result = 42")

    bridge.send_request.assert_awaited_once_with("execute_blender_python", {"code": "result = 42"})
    assert result["result"] == "42"


@pytest.mark.asyncio
async def test_empty_code_rejected_before_bridge_call():
    bridge = AsyncMock()
    handler = register_execute_blender_python_tool(FakeMCP(), bridge)

    with pytest.raises(ValidationError):
        await handler(code="")

    bridge.send_request.assert_not_called()


@pytest.mark.asyncio
async def test_domain_failure_raises_tool_execution_error():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": False,
        "message": "NameError: name 'foo' is not defined",
        "traceback": "...",
        "stdout": "",
    }
    handler = register_execute_blender_python_tool(FakeMCP(), bridge)

    with pytest.raises(BridgeError) as exc_info:
        await handler(code="foo")

    assert exc_info.value.error_type is ErrorType.TOOL_EXECUTION
    assert "NameError" in exc_info.value.message
