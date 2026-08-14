from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import HEAVY_REQUEST_TIMEOUT_S, BlenderBridge
from ..errors import BridgeError, ErrorType

RenderEngineType = Literal["BLENDER_EEVEE_NEXT", "CYCLES", "BLENDER_WORKBENCH", "BLENDER_EEVEE"]
ColorTransformType = Literal["AgX", "Filmic", "Standard", "Raw"]


class RenderSceneParams(BaseModel):
    output_path: Optional[str] = None
    engine: Optional[RenderEngineType] = None
    resolution_x: Optional[int] = None
    resolution_y: Optional[int] = None
    resolution_percentage: Optional[int] = None
    samples: Optional[int] = None
    transparent_background: Optional[bool] = None
    animation: bool = False
    return_image_base64: bool = False


class GetViewportScreenshotParams(BaseModel):
    output_path: Optional[str] = None
    return_image_base64: bool = True


class SetRenderSettingsParams(BaseModel):
    engine: Optional[RenderEngineType] = None
    resolution_x: Optional[int] = None
    resolution_y: Optional[int] = None
    resolution_percentage: Optional[int] = None
    samples: Optional[int] = None
    device: Optional[Literal["CPU", "GPU"]] = None
    transparent_background: Optional[bool] = None
    color_management_view_transform: Optional[ColorTransformType] = None


def register_render_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="render_scene",
        description="Render the active scene to an image file or base64 string, with customizable engine, resolution, samples, and transparency.",
    )
    async def render_scene(
        output_path: Optional[str] = None,
        engine: Optional[RenderEngineType] = None,
        resolution_x: Optional[int] = None,
        resolution_y: Optional[int] = None,
        resolution_percentage: Optional[int] = None,
        samples: Optional[int] = None,
        transparent_background: Optional[bool] = None,
        animation: bool = False,
        return_image_base64: bool = False,
    ) -> dict:
        params = RenderSceneParams(
            output_path=output_path,
            engine=engine,
            resolution_x=resolution_x,
            resolution_y=resolution_y,
            resolution_percentage=resolution_percentage,
            samples=samples,
            transparent_background=transparent_background,
            animation=animation,
            return_image_base64=return_image_base64,
        )
        result = await bridge.send_request(
            "render_scene", params.model_dump(), timeout=HEAVY_REQUEST_TIMEOUT_S
        )
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "render_scene failed"))
        return result

    @mcp.tool(
        name="get_viewport_screenshot",
        description="Quickly capture an OpenGL viewport screenshot to preview the scene and return it as image path and/or base64 data.",
    )
    async def get_viewport_screenshot(
        output_path: Optional[str] = None,
        return_image_base64: bool = True,
    ) -> dict:
        params = GetViewportScreenshotParams(
            output_path=output_path,
            return_image_base64=return_image_base64,
        )
        result = await bridge.send_request("get_viewport_screenshot", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "get_viewport_screenshot failed"))
        return result

    @mcp.tool(
        name="set_render_settings",
        description="Configure render engine, GPU/CPU compute device, resolution, color transform, and sampling.",
    )
    async def set_render_settings(
        engine: Optional[RenderEngineType] = None,
        resolution_x: Optional[int] = None,
        resolution_y: Optional[int] = None,
        resolution_percentage: Optional[int] = None,
        samples: Optional[int] = None,
        device: Optional[Literal["CPU", "GPU"]] = None,
        transparent_background: Optional[bool] = None,
        color_management_view_transform: Optional[ColorTransformType] = None,
    ) -> dict:
        params = SetRenderSettingsParams(
            engine=engine,
            resolution_x=resolution_x,
            resolution_y=resolution_y,
            resolution_percentage=resolution_percentage,
            samples=samples,
            device=device,
            transparent_background=transparent_background,
            color_management_view_transform=color_management_view_transform,
        )
        result = await bridge.send_request("set_render_settings", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "set_render_settings failed"))
        return result

    return render_scene, get_viewport_screenshot, set_render_settings
