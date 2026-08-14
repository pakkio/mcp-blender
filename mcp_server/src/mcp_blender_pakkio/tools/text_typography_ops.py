from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

TextAlignX = Literal["LEFT", "CENTER", "RIGHT", "JUSTIFY", "FLUSH"]
TextAlignY = Literal["TOP_BASELINE", "TOP", "CENTER", "BOTTOM", "BOTTOM_BASELINE"]


class Create3DTextParams(BaseModel):
    text: str = "Hello 3D"
    name: str = "Text3D"
    location: list[float] = [0.0, 0.0, 0.0]
    rotation: list[float] = [0.0, 0.0, 0.0]
    scale: list[float] = [1.0, 1.0, 1.0]
    extrude: float = 0.1
    bevel_depth: float = 0.02
    bevel_resolution: int = 3
    align_x: TextAlignX = "CENTER"
    align_y: TextAlignY = "CENTER"
    character_spacing: float = 1.0
    convert_to_mesh: bool = False


class DeformTextAlongCurveParams(BaseModel):
    text_name: str
    curve_name: Optional[str] = None
    create_circle_curve: bool = False
    circle_radius: float = 3.0


class SetTextPropertiesParams(BaseModel):
    text_name: str
    text: Optional[str] = None
    extrude: Optional[float] = None
    bevel_depth: Optional[float] = None
    size: Optional[float] = None
    character_spacing: Optional[float] = None


def register_text_typography_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_3d_text",
        description="Create a 3D Text object with custom font size, extrude depth, bevel resolution, alignment (LEFT, CENTER, RIGHT, JUSTIFY), tracking, and optional mesh conversion.",
    )
    async def create_3d_text(
        text: str = "Hello 3D",
        name: str = "Text3D",
        location: list[float] = [0.0, 0.0, 0.0],
        rotation: list[float] = [0.0, 0.0, 0.0],
        scale: list[float] = [1.0, 1.0, 1.0],
        extrude: float = 0.1,
        bevel_depth: float = 0.02,
        bevel_resolution: int = 3,
        align_x: TextAlignX = "CENTER",
        align_y: TextAlignY = "CENTER",
        character_spacing: float = 1.0,
        convert_to_mesh: bool = False,
    ) -> dict:
        params = Create3DTextParams(
            text=text,
            name=name,
            location=location,
            rotation=rotation,
            scale=scale,
            extrude=extrude,
            bevel_depth=bevel_depth,
            bevel_resolution=bevel_resolution,
            align_x=align_x,
            align_y=align_y,
            character_spacing=character_spacing,
            convert_to_mesh=convert_to_mesh,
        )
        result = await bridge.send_request("create_3d_text", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_3d_text failed"))
        return result

    @mcp.tool(
        name="deform_text_along_curve",
        description="Deform and wrap 3D text along a Bezier curve or circular path for logos, circular signage, and ribbons.",
    )
    async def deform_text_along_curve(
        text_name: str,
        curve_name: Optional[str] = None,
        create_circle_curve: bool = False,
        circle_radius: float = 3.0,
    ) -> dict:
        params = DeformTextAlongCurveParams(
            text_name=text_name,
            curve_name=curve_name,
            create_circle_curve=create_circle_curve,
            circle_radius=circle_radius,
        )
        result = await bridge.send_request("deform_text_along_curve", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "deform_text_along_curve failed"))
        return result

    @mcp.tool(
        name="set_text_properties",
        description="Update body content, font size, extrude depth, bevel, and letter spacing on existing 3D text.",
    )
    async def set_text_properties(
        text_name: str,
        text: Optional[str] = None,
        extrude: Optional[float] = None,
        bevel_depth: Optional[float] = None,
        size: Optional[float] = None,
        character_spacing: Optional[float] = None,
    ) -> dict:
        params = SetTextPropertiesParams(
            text_name=text_name,
            text=text,
            extrude=extrude,
            bevel_depth=bevel_depth,
            size=size,
            character_spacing=character_spacing,
        )
        result = await bridge.send_request("set_text_properties", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "set_text_properties failed"))
        return result

    return create_3d_text, deform_text_along_curve, set_text_properties
