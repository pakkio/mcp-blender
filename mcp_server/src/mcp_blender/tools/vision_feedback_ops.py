from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType
from ..images import image_result

AuditShading = Literal["SOLID", "WIREFRAME", "MATERIAL", "RENDERED"]


class CaptureMultiviewAuditParams(BaseModel):
    target_object: Optional[str] = None
    output_filepath: Optional[str] = None
    include_base64: bool = False
    resolution: int = 1024
    shading_mode: AuditShading = "SOLID"


class InspectFocusShotParams(BaseModel):
    target_object: str
    focal_length: float = 50.0
    angle_elevation: float = 20.0
    angle_azimuth: float = 45.0
    output_filepath: Optional[str] = None
    include_base64: bool = False


def register_vision_feedback_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="capture_multiview_audit",
        description="Capture a 4-angle visual inspection contact sheet (Front, Right Side, Top, and 3/4 Perspective) of the scene or target object for multimodal AI vision analysis. "
        "With include_base64=True the contact sheet is returned as real image content -- use this to actually verify your work. "
        "If you cannot see the returned image yourself, call evaluate_scene_visually instead of guessing.",
        structured_output=False,
    )
    async def capture_multiview_audit(
        target_object: Optional[str] = None,
        output_filepath: Optional[str] = None,
        include_base64: bool = False,
        resolution: int = 1024,
        shading_mode: AuditShading = "SOLID",
    ) -> list | dict:
        params = CaptureMultiviewAuditParams(
            target_object=target_object,
            output_filepath=output_filepath,
            include_base64=include_base64,
            resolution=resolution,
            shading_mode=shading_mode,
        )
        result = await bridge.send_request("capture_multiview_audit", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "capture_multiview_audit failed"))
        return image_result(result, "base64_data_uri")

    @mcp.tool(
        name="inspect_focus_shot",
        description="Frame a cinematic close-up camera shot directly on a target object with custom focal length (e.g. 50mm, 85mm macro) and capture an inspection snapshot. "
        "With include_base64=True the snapshot is returned as real image content.",
        structured_output=False,
    )
    async def inspect_focus_shot(
        target_object: str,
        focal_length: float = 50.0,
        angle_elevation: float = 20.0,
        angle_azimuth: float = 45.0,
        output_filepath: Optional[str] = None,
        include_base64: bool = False,
    ) -> list | dict:
        params = InspectFocusShotParams(
            target_object=target_object,
            focal_length=focal_length,
            angle_elevation=angle_elevation,
            angle_azimuth=angle_azimuth,
            output_filepath=output_filepath,
            include_base64=include_base64,
        )
        result = await bridge.send_request("inspect_focus_shot", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "inspect_focus_shot failed"))
        return image_result(result)

    return capture_multiview_audit, inspect_focus_shot
