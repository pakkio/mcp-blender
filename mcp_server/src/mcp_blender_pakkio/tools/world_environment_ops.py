from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

UnitSystem = Literal["METRIC", "IMPERIAL", "NONE"]
ViewTransform = Literal["AgX", "Filmic", "Standard", "Raw"]


class ConfigureWorldEnvironmentParams(BaseModel):
    color: Optional[list[float]] = None
    strength: Optional[float] = None
    hdri_path: Optional[str] = None
    hdri_rotation_z: float = 0.0


class ConfigureScenePhysicsParams(BaseModel):
    gravity: Optional[list[float]] = None
    unit_system: Optional[UnitSystem] = None
    unit_scale: Optional[float] = None
    color_space_view_transform: Optional[ViewTransform] = None
    color_space_look: Optional[str] = None
    color_space_exposure: Optional[float] = None
    color_space_gamma: Optional[float] = None


class SwitchWorkspaceParams(BaseModel):
    workspace_name: str


def register_world_environment_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="configure_world_environment",
        description="Configure the 3D World background (solid color, lighting strength, or 360 HDRI environment map texture with Z-axis rotation).",
    )
    async def configure_world_environment(
        color: Optional[list[float]] = None,
        strength: Optional[float] = None,
        hdri_path: Optional[str] = None,
        hdri_rotation_z: float = 0.0,
    ) -> dict:
        params = ConfigureWorldEnvironmentParams(
            color=color,
            strength=strength,
            hdri_path=hdri_path,
            hdri_rotation_z=hdri_rotation_z,
        )
        result = await bridge.send_request("configure_world_environment", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_world_environment failed"))
        return result

    @mcp.tool(
        name="configure_scene_physics",
        description="Configure global scene gravity, metric/imperial unit scales, and Color Management transforms (AgX, Filmic, Exposure, Gamma, Look).",
    )
    async def configure_scene_physics(
        gravity: Optional[list[float]] = None,
        unit_system: Optional[UnitSystem] = None,
        unit_scale: Optional[float] = None,
        color_space_view_transform: Optional[ViewTransform] = None,
        color_space_look: Optional[str] = None,
        color_space_exposure: Optional[float] = None,
        color_space_gamma: Optional[float] = None,
    ) -> dict:
        params = ConfigureScenePhysicsParams(
            gravity=gravity,
            unit_system=unit_system,
            unit_scale=unit_scale,
            color_space_view_transform=color_space_view_transform,
            color_space_look=color_space_look,
            color_space_exposure=color_space_exposure,
            color_space_gamma=color_space_gamma,
        )
        result = await bridge.send_request("configure_scene_physics", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_scene_physics failed"))
        return result

    @mcp.tool(
        name="switch_workspace",
        description="Switch the active Blender workspace layout (Layout, Modeling, Sculpting, UV Editing, Texture Paint, Shading, Animation, Rendering, Compositing, Geometry Nodes, Scripting).",
    )
    async def switch_workspace(
        workspace_name: str,
    ) -> dict:
        params = SwitchWorkspaceParams(workspace_name=workspace_name)
        result = await bridge.send_request("switch_workspace", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "switch_workspace failed"))
        return result

    return configure_world_environment, configure_scene_physics, switch_workspace
