from typing import Any, Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

AddonAction = Literal["LIST", "ENABLE", "DISABLE", "SET_PREFERENCES"]
AddonFilter = Literal["ALL", "ENABLED_ONLY", "DISABLED_ONLY"]


class ManageAddonsParams(BaseModel):
    action: AddonAction = "LIST"
    addon_name: Optional[str] = None
    filter: AddonFilter = "ALL"
    preferences: Optional[dict[str, Any]] = None


class InspectAddonParams(BaseModel):
    addon_name: str


def register_addon_management_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="manage_addons",
        description="List, discover, enable, disable, and configure settings for any Blender add-on or extension (including Rigify, Node Wrangler, LoopTools, Archimesh, glTF, FBX, and custom extensions).",
    )
    async def manage_addons(
        action: AddonAction = "LIST",
        addon_name: Optional[str] = None,
        filter: AddonFilter = "ALL",
        preferences: Optional[dict[str, Any]] = None,
    ) -> dict:
        params = ManageAddonsParams(
            action=action,
            addon_name=addon_name,
            filter=filter,
            preferences=preferences,
        )
        result = await bridge.send_request("manage_addons", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "manage_addons failed"))
        return result

    @mcp.tool(
        name="inspect_addon",
        description="Inspect full metadata, configuration settings, enabled status, documentation links, and preference properties for a specific Blender add-on.",
    )
    async def inspect_addon(
        addon_name: str,
    ) -> dict:
        params = InspectAddonParams(addon_name=addon_name)
        result = await bridge.send_request("inspect_addon", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "inspect_addon failed"))
        return result

    return manage_addons, inspect_addon
