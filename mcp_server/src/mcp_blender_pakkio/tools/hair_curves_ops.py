from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class CreateHairCurvesParams(BaseModel):
    surface_object: str = Field(..., description="Name of the mesh surface object to attach hair curves to")
    name: str = Field("Hair_Curves", description="Name for the hair curves object")
    density: float = Field(100.0, description="Density factor for hair curves")
    length: float = Field(0.2, description="Strand length in scene units")
    points_per_curve: int = Field(5, description="Number of control points per curve strand")


class ApplyHairGroomModifierParams(BaseModel):
    curves_object: str = Field(..., description="Name of the Hair Curves object")
    effect_type: str = Field("FRIZZ", description="FRIZZ | CLUMP | NOISE | BRAID | PUFF")
    intensity: float = Field(0.5, description="Effect intensity multiplier")
    factor: float = Field(1.0, description="Scale or frequency factor")


class ConvertLegacyHairParams(BaseModel):
    object_name: str = Field(..., description="Name of the mesh object carrying legacy particle hair")


def register_hair_curves_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_hair_curves",
        description="Create modern Blender 4.2+ / 5.x Hair Curves (Geometry Nodes based) attached to a mesh surface with surface UV mapping.",
    )
    async def create_hair_curves(
        surface_object: str,
        name: str = "Hair_Curves",
        density: float = 100.0,
        length: float = 0.2,
        points_per_curve: int = 5,
    ) -> dict:
        params = CreateHairCurvesParams(
            surface_object=surface_object,
            name=name,
            density=density,
            length=length,
            points_per_curve=points_per_curve,
        )
        result = await bridge.send_request("create_hair_curves", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_hair_curves failed"))
        return result

    @mcp.tool(
        name="apply_hair_groom_modifier",
        description="Add procedural geometry nodes groom modifiers (FRIZZ, CLUMP, NOISE, BRAID, PUFF) to modern Hair Curves.",
    )
    async def apply_hair_groom_modifier(
        curves_object: str,
        effect_type: str = "FRIZZ",
        intensity: float = 0.5,
        factor: float = 1.0,
    ) -> dict:
        params = ApplyHairGroomModifierParams(
            curves_object=curves_object,
            effect_type=effect_type,
            intensity=intensity,
            factor=factor,
        )
        result = await bridge.send_request("apply_hair_groom_modifier", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "apply_hair_groom_modifier failed"))
        return result

    @mcp.tool(
        name="convert_legacy_hair_to_curves",
        description="Convert legacy particle hair systems on an object into modern Blender 4.2+ Hair Curves.",
    )
    async def convert_legacy_hair_to_curves(object_name: str) -> dict:
        params = ConvertLegacyHairParams(object_name=object_name)
        result = await bridge.send_request("convert_legacy_hair_to_curves", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "convert_legacy_hair_to_curves failed"))
        return result

    return (create_hair_curves, apply_hair_groom_modifier, convert_legacy_hair_to_curves)
