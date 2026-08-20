from typing import Any, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class SetObjectPropertiesParams(BaseModel):
    name: str
    new_name: Optional[str] = None
    hide_viewport: Optional[bool] = None
    hide_render: Optional[bool] = None
    color: Optional[tuple[float, float, float, float]] = None
    custom_properties: Optional[dict[str, Any]] = None


def register_set_object_properties_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="set_object_properties",
        description="Set object viewport/render visibility, rename object, display color, and custom properties.",
    )
    async def set_object_properties(
        name: str,
        new_name: Optional[str] = None,
        hide_viewport: Optional[bool] = None,
        hide_render: Optional[bool] = None,
        color: Optional[tuple[float, float, float, float]] = None,
        custom_properties: Optional[dict[str, Any]] = None,
    ) -> dict:
        params = SetObjectPropertiesParams(
            name=name,
            new_name=new_name,
            hide_viewport=hide_viewport,
            hide_render=hide_render,
            color=color,
            custom_properties=custom_properties,
        )
        result = await bridge.send_request("set_object_properties", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "set_object_properties failed"))
        return result

    return set_object_properties
