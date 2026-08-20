from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class GetObjectInfoParams(BaseModel):
    name: str


def register_get_object_info_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="get_object_info",
        description="Get detailed inspection data for a specific Blender object (transform, bounding box, dimensions, parent/children, materials, modifiers, mesh/light/camera data, animation, custom properties).",
    )
    async def get_object_info(name: str) -> dict:
        params = GetObjectInfoParams(name=name)
        result = await bridge.send_request("get_object_info", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "get_object_info failed"))
        return result

    return get_object_info
