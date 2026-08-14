from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class ExecuteBatchParams(BaseModel):
    commands: list[dict]
    title: str = "Batch Execution"
    stop_on_error: bool = True
    update_hud: bool = True


def register_batch_execution_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="execute_batch",
        description="Execute a sequence of multiple MCP tool operations in a single optimized batch roundtrip with real-time HUD progress updates, error rollback, and comprehensive per-step reporting.",
    )
    async def execute_batch(
        commands: list[dict],
        title: str = "Batch Execution",
        stop_on_error: bool = True,
        update_hud: bool = True,
    ) -> dict:
        params = ExecuteBatchParams(
            commands=commands,
            title=title,
            stop_on_error=stop_on_error,
            update_hud=update_hud,
        )
        result = await bridge.send_request("execute_batch", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "execute_batch failed"))
        return result

    return (execute_batch,)
