from typing import Any, Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

BindType = Literal["AUTOMATIC_WEIGHTS", "ENVELOPE_WEIGHTS", "EMPTY_GROUPS"]


class CreateArmatureParams(BaseModel):
    name: str = "Armature"
    location: list[float] = [0.0, 0.0, 0.0]
    bones: Optional[list[dict[str, Any]]] = None
    bind_mesh: Optional[str] = None
    bind_type: BindType = "AUTOMATIC_WEIGHTS"


class PoseBoneParams(BaseModel):
    armature_name: str
    bone_name: str
    location: Optional[list[float]] = None
    rotation_euler: Optional[list[float]] = None
    rotation_quaternion: Optional[list[float]] = None
    scale: Optional[list[float]] = None
    frame: Optional[int] = None


def register_rigging_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_armature",
        description="Create an armature with one or more bones and optionally bind a mesh with automatic vertex weights.",
    )
    async def create_armature(
        name: str = "Armature",
        location: list[float] = [0.0, 0.0, 0.0],
        bones: Optional[list[dict[str, Any]]] = None,
        bind_mesh: Optional[str] = None,
        bind_type: BindType = "AUTOMATIC_WEIGHTS",
    ) -> dict:
        params = CreateArmatureParams(
            name=name,
            location=location,
            bones=bones,
            bind_mesh=bind_mesh,
            bind_type=bind_type,
        )
        result = await bridge.send_request("create_armature", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_armature failed"))
        return result

    @mcp.tool(
        name="pose_bone",
        description="Transform a bone in Pose Mode (location, rotation, scale) and optionally insert keyframes for skeletal animation.",
    )
    async def pose_bone(
        armature_name: str,
        bone_name: str,
        location: Optional[list[float]] = None,
        rotation_euler: Optional[list[float]] = None,
        rotation_quaternion: Optional[list[float]] = None,
        scale: Optional[list[float]] = None,
        frame: Optional[int] = None,
    ) -> dict:
        params = PoseBoneParams(
            armature_name=armature_name,
            bone_name=bone_name,
            location=location,
            rotation_euler=rotation_euler,
            rotation_quaternion=rotation_quaternion,
            scale=scale,
            frame=frame,
        )
        result = await bridge.send_request("pose_bone", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "pose_bone failed"))
        return result

    return create_armature, pose_bone
