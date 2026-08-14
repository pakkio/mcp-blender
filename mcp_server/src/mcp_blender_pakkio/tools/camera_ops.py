from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

CameraType = Literal["PERSP", "ORTHO", "PANO"]


class ConfigureCameraParams(BaseModel):
    name: str
    lens: Optional[float] = None
    camera_type: Optional[CameraType] = None
    ortho_scale: Optional[float] = None
    clip_start: Optional[float] = None
    clip_end: Optional[float] = None
    sensor_width: Optional[float] = None
    dof_focus_object: Optional[str] = None
    dof_fstop: Optional[float] = None
    set_as_active_camera: bool = False


class CameraLookAtParams(BaseModel):
    camera_name: str
    target_location: Optional[tuple[float, float, float]] = None
    target_object: Optional[str] = None
    add_constraint: bool = False


class FrameObjectsParams(BaseModel):
    camera_name: Optional[str] = None
    target_objects: Optional[list[str]] = None
    margin: float = 1.5


def register_camera_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="configure_camera",
        description="Configure camera focal length (lens), sensor width, clip start/end, depth of field, ortho scale, and active status.",
    )
    async def configure_camera(
        name: str,
        lens: Optional[float] = None,
        camera_type: Optional[CameraType] = None,
        ortho_scale: Optional[float] = None,
        clip_start: Optional[float] = None,
        clip_end: Optional[float] = None,
        sensor_width: Optional[float] = None,
        dof_focus_object: Optional[str] = None,
        dof_fstop: Optional[float] = None,
        set_as_active_camera: bool = False,
    ) -> dict:
        params = ConfigureCameraParams(
            name=name,
            lens=lens,
            camera_type=camera_type,
            ortho_scale=ortho_scale,
            clip_start=clip_start,
            clip_end=clip_end,
            sensor_width=sensor_width,
            dof_focus_object=dof_focus_object,
            dof_fstop=dof_fstop,
            set_as_active_camera=set_as_active_camera,
        )
        result = await bridge.send_request("configure_camera", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_camera failed"))
        return result

    @mcp.tool(
        name="camera_look_at",
        description="Point a camera or object directly at a target coordinate or target object (via direct rotation calculation or TRACK_TO constraint).",
    )
    async def camera_look_at(
        camera_name: str,
        target_location: Optional[tuple[float, float, float]] = None,
        target_object: Optional[str] = None,
        add_constraint: bool = False,
    ) -> dict:
        params = CameraLookAtParams(
            camera_name=camera_name,
            target_location=target_location,
            target_object=target_object,
            add_constraint=add_constraint,
        )
        result = await bridge.send_request("camera_look_at", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "camera_look_at failed"))
        return result

    @mcp.tool(
        name="frame_objects",
        description="Automatically reposition and point a camera to frame specified objects (or all visible objects) cleanly in view.",
    )
    async def frame_objects(
        camera_name: Optional[str] = None,
        target_objects: Optional[list[str]] = None,
        margin: float = 1.5,
    ) -> dict:
        params = FrameObjectsParams(
            camera_name=camera_name,
            target_objects=target_objects,
            margin=margin,
        )
        result = await bridge.send_request("frame_objects", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "frame_objects failed"))
        return result

    return configure_camera, camera_look_at, frame_objects
