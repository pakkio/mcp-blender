from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class SetupCameraTrackingParams(BaseModel):
    camera_name: str = Field("Camera", description="Name of the camera to configure")
    clip_path: Optional[str] = Field(None, description="Path to background video movie clip")
    focal_length: float = Field(35.0, description="Camera focal length in millimeters")
    sensor_width: float = Field(36.0, description="Camera sensor width in millimeters")
    use_motion_blur: bool = Field(True, description="Enable motion blur for matching live-action footage")


class SetupVFXShadowCatcherParams(BaseModel):
    name: str = Field("VFX_Shadow_Catcher", description="Name of the ground plane object")
    size: float = Field(10.0, description="Size of the shadow catcher plane in meters")
    location: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])
    transparent_film: bool = Field(True, description="Enable transparent film background rendering")


def register_vfx_tracking_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="setup_camera_tracking",
        description="Configure camera and background movie clip tracking parameters for visual effects (VFX) matchmoving.",
    )
    async def setup_camera_tracking(
        camera_name: str = "Camera",
        clip_path: Optional[str] = None,
        focal_length: float = 35.0,
        sensor_width: float = 36.0,
        use_motion_blur: bool = True,
    ) -> dict:
        params = SetupCameraTrackingParams(
            camera_name=camera_name,
            clip_path=clip_path,
            focal_length=focal_length,
            sensor_width=sensor_width,
            use_motion_blur=use_motion_blur,
        )
        result = await bridge.send_request("setup_camera_tracking", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_camera_tracking failed"))
        return result

    @mcp.tool(
        name="setup_vfx_shadow_catcher",
        description="Create an invisible ground plane that catches 3D object shadows and reflections over live-action VFX plates.",
    )
    async def setup_vfx_shadow_catcher(
        name: str = "VFX_Shadow_Catcher",
        size: float = 10.0,
        location: list[float] = [0.0, 0.0, 0.0],
        transparent_film: bool = True,
    ) -> dict:
        params = SetupVFXShadowCatcherParams(
            name=name,
            size=size,
            location=location,
            transparent_film=transparent_film,
        )
        result = await bridge.send_request("setup_vfx_shadow_catcher", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_vfx_shadow_catcher failed"))
        return result

    return (setup_camera_tracking, setup_vfx_shadow_catcher)
