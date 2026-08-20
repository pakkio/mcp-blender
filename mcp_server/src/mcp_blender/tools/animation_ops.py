from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

DataPathType = Literal["location", "rotation_euler", "scale", "custom"]
InterpolationType = Literal["BEZIER", "LINEAR", "CONSTANT"]


class SetKeyframeParams(BaseModel):
    object_name: str
    frame: int
    data_path: DataPathType = "location"
    value: Optional[list[float]] = None
    custom_property_name: Optional[str] = None
    interpolation: InterpolationType = "BEZIER"


class DeleteKeyframeParams(BaseModel):
    object_name: str
    frame: Optional[int] = None
    data_path: Optional[str] = None
    frame_range: Optional[tuple[int, int]] = None


class SetTimelineRangeParams(BaseModel):
    frame_start: Optional[int] = None
    frame_end: Optional[int] = None
    frame_current: Optional[int] = None
    fps: Optional[int] = None


def register_animation_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="set_keyframe",
        description="Insert keyframes on an object for location, rotation, scale, or custom properties at a specific frame.",
    )
    async def set_keyframe(
        object_name: str,
        frame: int,
        data_path: DataPathType = "location",
        value: Optional[list[float]] = None,
        custom_property_name: Optional[str] = None,
        interpolation: InterpolationType = "BEZIER",
    ) -> dict:
        params = SetKeyframeParams(
            object_name=object_name,
            frame=frame,
            data_path=data_path,
            value=value,
            custom_property_name=custom_property_name,
            interpolation=interpolation,
        )
        result = await bridge.send_request("set_keyframe", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "set_keyframe failed"))
        return result

    @mcp.tool(
        name="delete_keyframe",
        description="Delete keyframes on an object at a specific frame or frame range.",
    )
    async def delete_keyframe(
        object_name: str,
        frame: Optional[int] = None,
        data_path: Optional[str] = None,
        frame_range: Optional[tuple[int, int]] = None,
    ) -> dict:
        params = DeleteKeyframeParams(
            object_name=object_name,
            frame=frame,
            data_path=data_path,
            frame_range=frame_range,
        )
        result = await bridge.send_request("delete_keyframe", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "delete_keyframe failed"))
        return result

    @mcp.tool(
        name="set_timeline_range",
        description="Configure timeline start/end frame, current playback frame, and FPS.",
    )
    async def set_timeline_range(
        frame_start: Optional[int] = None,
        frame_end: Optional[int] = None,
        frame_current: Optional[int] = None,
        fps: Optional[int] = None,
    ) -> dict:
        params = SetTimelineRangeParams(
            frame_start=frame_start,
            frame_end=frame_end,
            frame_current=frame_current,
            fps=fps,
        )
        result = await bridge.send_request("set_timeline_range", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "set_timeline_range failed"))
        return result

    return set_keyframe, delete_keyframe, set_timeline_range
