from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class CreateArmatureParams(BaseModel):
    name: str = Field("Armature", description="Name for the armature object")
    location: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    bones: Optional[list[dict]] = Field(None, description="Detailed bone specifications")
    bone_names: Optional[list[str]] = Field(None, description="Simple sequential list of bone names")
    bind_mesh: Optional[str] = Field(None, description="Name of mesh to automatically bind and weight")
    bind_type: str = Field("AUTOMATIC_WEIGHTS", description="AUTOMATIC_WEIGHTS | ENVELOPE_WEIGHTS | EMPTY_GROUPS")


class PoseBoneParams(BaseModel):
    armature_name: str
    bone_name: str
    location: Optional[list[float]] = None
    rotation_euler: Optional[list[float]] = None
    rotation_quaternion: Optional[list[float]] = None
    scale: Optional[list[float]] = None
    frame: Optional[int] = None


class SetupIKConstraintParams(BaseModel):
    armature_name: str
    bone_name: str
    target_name: str
    target_bone: Optional[str] = None
    pole_target_name: Optional[str] = None
    pole_target_bone: Optional[str] = None
    pole_angle: float = 0.0
    chain_length: int = 2
    weight: float = 1.0


class SetupHumanoidRigPresetParams(BaseModel):
    name: str = "Humanoid_Rig"
    height: float = 1.8
    generate_ik: bool = True
    location: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])


class SetupSplineIKConstraintParams(BaseModel):
    armature_name: str
    bone_name: str
    curve_name: str
    chain_length: int = 4


def register_rigging_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_armature",
        description="Create an armature with one or more bones and optionally bind a mesh with automatic vertex weights.",
    )
    async def create_armature(
        name: str = "Armature",
        location: list[float] = [0.0, 0.0, 0.0],
        bones: Optional[list[dict]] = None,
        bone_names: Optional[list[str]] = None,
        bind_mesh: Optional[str] = None,
        bind_type: str = "AUTOMATIC_WEIGHTS",
    ) -> dict:
        params = CreateArmatureParams(
            name=name,
            location=location,
            bones=bones,
            bone_names=bone_names,
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

    @mcp.tool(
        name="setup_ik_constraint",
        description="Add an Inverse Kinematics (IK) constraint to a bone with target, pole target, pole angle, and chain length.",
    )
    async def setup_ik_constraint(
        armature_name: str,
        bone_name: str,
        target_name: str,
        target_bone: Optional[str] = None,
        pole_target_name: Optional[str] = None,
        pole_target_bone: Optional[str] = None,
        pole_angle: float = 0.0,
        chain_length: int = 2,
        weight: float = 1.0,
    ) -> dict:
        params = SetupIKConstraintParams(
            armature_name=armature_name,
            bone_name=bone_name,
            target_name=target_name,
            target_bone=target_bone,
            pole_target_name=pole_target_name,
            pole_target_bone=pole_target_bone,
            pole_angle=pole_angle,
            chain_length=chain_length,
            weight=weight,
        )
        result = await bridge.send_request("setup_ik_constraint", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_ik_constraint failed"))
        return result

    @mcp.tool(
        name="setup_humanoid_rig_preset",
        description="Generate a standard humanoid biped skeletal rig with anatomical bone proportions and optional automatic IK controls.",
    )
    async def setup_humanoid_rig_preset(
        name: str = "Humanoid_Rig",
        height: float = 1.8,
        generate_ik: bool = True,
        location: list[float] = [0.0, 0.0, 0.0],
    ) -> dict:
        params = SetupHumanoidRigPresetParams(
            name=name,
            height=height,
            generate_ik=generate_ik,
            location=location,
        )
        result = await bridge.send_request("setup_humanoid_rig_preset", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_humanoid_rig_preset failed"))
        return result

    @mcp.tool(
        name="setup_spline_ik_constraint",
        description="Add a Spline IK constraint to a bone chain to deform along a 3D curve object (ropes, tails, spines, tentacles).",
    )
    async def setup_spline_ik_constraint(
        armature_name: str,
        bone_name: str,
        curve_name: str,
        chain_length: int = 4,
    ) -> dict:
        params = SetupSplineIKConstraintParams(
            armature_name=armature_name,
            bone_name=bone_name,
            curve_name=curve_name,
            chain_length=chain_length,
        )
        result = await bridge.send_request("setup_spline_ik_constraint", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_spline_ik_constraint failed"))
        return result

    return (create_armature, pose_bone, setup_ik_constraint, setup_humanoid_rig_preset, setup_spline_ik_constraint)
