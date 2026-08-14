from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class SetObjectTransformParams(BaseModel):
    name: str
    location: Optional[tuple[float, float, float]] = None
    rotation_euler: Optional[tuple[float, float, float]] = None
    scale: Optional[tuple[float, float, float]] = None
    delta_location: Optional[tuple[float, float, float]] = None
    delta_rotation_euler: Optional[tuple[float, float, float]] = None
    delta_scale: Optional[tuple[float, float, float]] = None


def register_set_object_transform_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="set_object_transform",
        description="Set location, rotation, and scale on an existing object (supports absolute or relative/delta updates).",
    )
    async def set_object_transform(
        name: str,
        location: Optional[tuple[float, float, float]] = None,
        rotation_euler: Optional[tuple[float, float, float]] = None,
        scale: Optional[tuple[float, float, float]] = None,
        delta_location: Optional[tuple[float, float, float]] = None,
        delta_rotation_euler: Optional[tuple[float, float, float]] = None,
        delta_scale: Optional[tuple[float, float, float]] = None,
    ) -> dict:
        params = SetObjectTransformParams(
            name=name,
            location=location,
            rotation_euler=rotation_euler,
            scale=scale,
            delta_location=delta_location,
            delta_rotation_euler=delta_rotation_euler,
            delta_scale=delta_scale,
        )
        result = await bridge.send_request("set_object_transform", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "set_object_transform failed"))
        return result

    return set_object_transform
