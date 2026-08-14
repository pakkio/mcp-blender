from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class ApplyTransformParams(BaseModel):
    name: str
    location: bool = False
    rotation: bool = False
    scale: bool = True


def register_apply_transform_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="apply_transform",
        description="Apply location, rotation, and/or scale transforms permanently into the object's geometry/mesh data.",
    )
    async def apply_transform(
        name: str,
        location: bool = False,
        rotation: bool = False,
        scale: bool = True,
    ) -> dict:
        params = ApplyTransformParams(
            name=name,
            location=location,
            rotation=rotation,
            scale=scale,
        )
        result = await bridge.send_request("apply_transform", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "apply_transform failed"))
        return result

    return apply_transform
