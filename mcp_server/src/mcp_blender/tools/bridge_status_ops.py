from mcp.server.fastmcp import FastMCP

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


def register_bridge_status_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="get_bridge_status",
        description=(
            "Check whether Blender's main thread is still busy with a previous command, without "
            "waiting for that command to finish. Always answers immediately (short fixed timeout), "
            "even while a heavy operation like a checkpoint save, render, or bake is in progress. "
            "When busy, result.current gives a human-readable 'description' (method + params + "
            "elapsed seconds, e.g. \"create_scene_checkpoint({'name': 'before_boolean'}) — running "
            "for 12.3s\"), plus running_for_s and method separately, and result.queue_depth counts "
            "anything else waiting behind it -- poll this instead of guessing or re-sending the "
            "same slow request."
        ),
    )
    async def get_bridge_status() -> dict:
        result = await bridge.send_request("bridge_status", {}, timeout=5.0)
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "get_bridge_status failed"))
        return result

    return (get_bridge_status,)
