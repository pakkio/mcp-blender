from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class BakeAnimationParams(BaseModel):
    object_name: str
    frame_start: Optional[int] = None
    frame_end: Optional[int] = None
    visual_keying: bool = True
    clear_constraints: bool = False


class RenderAnimationSequenceParams(BaseModel):
    output_filepath: Optional[str] = None
    format: str = "FFMPEG"
    frame_start: Optional[int] = None
    frame_end: Optional[int] = None
    resolution_x: int = 1280
    resolution_y: int = 720


def register_animation_render_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="bake_object_animation",
        description="Bake object constraints, follow-paths, or physics simulations into permanent transform keyframes across a frame range for game engine export (Unity/Unreal).",
    )
    async def bake_object_animation(
        object_name: str,
        frame_start: Optional[int] = None,
        frame_end: Optional[int] = None,
        visual_keying: bool = True,
        clear_constraints: bool = False,
    ) -> dict:
        params = BakeAnimationParams(
            object_name=object_name,
            frame_start=frame_start,
            frame_end=frame_end,
            visual_keying=visual_keying,
            clear_constraints=clear_constraints,
        )
        result = await bridge.send_request("bake_object_animation", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "bake_object_animation failed"))
        return result

    @mcp.tool(
        name="render_animation_sequence",
        description="Render an entire animation frame sequence or video (MP4/H.264 or PNG sequence) to disk with timeline range and resolution controls.",
    )
    async def render_animation_sequence(
        output_filepath: Optional[str] = None,
        format: str = "FFMPEG",
        frame_start: Optional[int] = None,
        frame_end: Optional[int] = None,
        resolution_x: int = 1280,
        resolution_y: int = 720,
    ) -> dict:
        params = RenderAnimationSequenceParams(
            output_filepath=output_filepath,
            format=format,
            frame_start=frame_start,
            frame_end=frame_end,
            resolution_x=resolution_x,
            resolution_y=resolution_y,
        )
        result = await bridge.send_request("render_animation_sequence", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "render_animation_sequence failed"))
        return result

    return bake_object_animation, render_animation_sequence
