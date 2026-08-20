from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class UpdateProgressHUDParams(BaseModel):
    title: str = "MCP Agent Task"
    status: str = "Working..."
    progress_percent: float = 0.0
    step_current: int = 0
    step_total: int = 0
    details: list[str] = []
    show_hud: bool = True
    auto_hide_seconds: float = 0.0


class ClearProgressHUDParams(BaseModel):
    pass


def register_progress_hud_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="update_progress_hud",
        description="Display or update a non-modal floating progress HUD card in Blender with progress percentage (0-100%), task title, status, and detailed step explanations without blocking user interaction.",
    )
    async def update_progress_hud(
        title: str = "MCP Agent Task",
        status: str = "Working...",
        progress_percent: float = 0.0,
        step_current: int = 0,
        step_total: int = 0,
        details: list[str] = [],
        show_hud: bool = True,
        auto_hide_seconds: float = 0.0,
    ) -> dict:
        params = UpdateProgressHUDParams(
            title=title,
            status=status,
            progress_percent=progress_percent,
            step_current=step_current,
            step_total=step_total,
            details=details,
            show_hud=show_hud,
            auto_hide_seconds=auto_hide_seconds,
        )
        result = await bridge.send_request("update_progress_hud", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "update_progress_hud failed"))
        return result

    @mcp.tool(
        name="clear_progress_hud",
        description="Hide and clear the floating non-modal progress HUD window in Blender.",
    )
    async def clear_progress_hud() -> dict:
        result = await bridge.send_request("clear_progress_hud", {})
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "clear_progress_hud failed"))
        return result

    return update_progress_hud, clear_progress_hud
