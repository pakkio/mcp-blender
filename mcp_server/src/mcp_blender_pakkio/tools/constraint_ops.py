from typing import Any, Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

ConstraintType = Literal[
    "TRACK_TO",
    "DAMPED_TRACK",
    "FOLLOW_PATH",
    "COPY_TRANSFORMS",
    "COPY_LOCATION",
    "COPY_ROTATION",
    "LIMIT_DISTANCE",
    "LIMIT_LOCATION",
    "CHILD_OF",
    "IK",
]


class AddConstraintParams(BaseModel):
    object_name: str
    constraint_type: ConstraintType = "TRACK_TO"
    target_object: Optional[str] = None
    subtarget: Optional[str] = None
    name: Optional[str] = None
    properties: Optional[dict[str, Any]] = None


class AnimateCameraTurntableParams(BaseModel):
    camera_name: str = "Camera"
    target_object: Optional[str] = None
    target_location: list[float] = [0.0, 0.0, 0.0]
    radius: float = 10.0
    height: float = 5.0
    duration_frames: int = 120
    start_frame: int = 1


def register_constraint_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="add_constraint",
        description="Add constraints to an object or bone (TRACK_TO, DAMPED_TRACK, FOLLOW_PATH, COPY_TRANSFORMS, COPY_LOCATION, COPY_ROTATION, LIMIT_DISTANCE, CHILD_OF, IK).",
    )
    async def add_constraint(
        object_name: str,
        constraint_type: ConstraintType = "TRACK_TO",
        target_object: Optional[str] = None,
        subtarget: Optional[str] = None,
        name: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
    ) -> dict:
        params = AddConstraintParams(
            object_name=object_name,
            constraint_type=constraint_type,
            target_object=target_object,
            subtarget=subtarget,
            name=name,
            properties=properties,
        )
        result = await bridge.send_request("add_constraint", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "add_constraint failed"))
        return result

    @mcp.tool(
        name="animate_camera_turntable",
        description="Create a smooth 360-degree turntable camera animation around a target object or location over a specified duration.",
    )
    async def animate_camera_turntable(
        camera_name: str = "Camera",
        target_object: Optional[str] = None,
        target_location: list[float] = [0.0, 0.0, 0.0],
        radius: float = 10.0,
        height: float = 5.0,
        duration_frames: int = 120,
        start_frame: int = 1,
    ) -> dict:
        params = AnimateCameraTurntableParams(
            camera_name=camera_name,
            target_object=target_object,
            target_location=target_location,
            radius=radius,
            height=height,
            duration_frames=duration_frames,
            start_frame=start_frame,
        )
        result = await bridge.send_request("animate_camera_turntable", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "animate_camera_turntable failed"))
        return result

    return add_constraint, animate_camera_turntable
