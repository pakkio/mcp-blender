from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

ProceduralPattern = Literal["NOISE", "VORONOI", "WAVE", "BRICK", "CHECKER", "GRADIENT"]
BakeType = Literal["COMBINED", "DIFFUSE", "NORMAL", "ROUGHNESS", "AO", "SHADOW", "EMIT"]


class SetupPBRMaterialsParams(BaseModel):
    material_name: str
    object_name: Optional[str] = None
    albedo_path: Optional[str] = None
    normal_path: Optional[str] = None
    roughness_path: Optional[str] = None
    metallic_path: Optional[str] = None
    height_path: Optional[str] = None
    emission_path: Optional[str] = None
    ao_path: Optional[str] = None
    uv_scale: list[float] = [1.0, 1.0, 1.0]


class CreateProceduralMaterialParams(BaseModel):
    material_name: str
    pattern: ProceduralPattern = "NOISE"
    scale: float = 5.0
    detail: float = 4.0
    roughness: float = 0.5
    color1: list[float] = [0.8, 0.2, 0.2, 1.0]
    color2: list[float] = [0.1, 0.1, 0.3, 1.0]
    bump_strength: float = 0.1
    metallic: float = 0.0
    object_name: Optional[str] = None


class BakeTexturesParams(BaseModel):
    object_name: str
    bake_type: BakeType = "DIFFUSE"
    output_filepath: str
    width: int = 1024
    height: int = 1024
    samples: int = 16


def register_pbr_bake_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="setup_pbr_materials",
        description="Automatically build and connect a full PBR material node tree (Albedo, Normal, Roughness, Metallic, Height/Displacement, Emission, AO) with appropriate color spaces.",
    )
    async def setup_pbr_materials(
        material_name: str,
        object_name: Optional[str] = None,
        albedo_path: Optional[str] = None,
        normal_path: Optional[str] = None,
        roughness_path: Optional[str] = None,
        metallic_path: Optional[str] = None,
        height_path: Optional[str] = None,
        emission_path: Optional[str] = None,
        ao_path: Optional[str] = None,
        uv_scale: list[float] = [1.0, 1.0, 1.0],
    ) -> dict:
        params = SetupPBRMaterialsParams(
            material_name=material_name,
            object_name=object_name,
            albedo_path=albedo_path,
            normal_path=normal_path,
            roughness_path=roughness_path,
            metallic_path=metallic_path,
            height_path=height_path,
            emission_path=emission_path,
            ao_path=ao_path,
            uv_scale=uv_scale,
        )
        result = await bridge.send_request("setup_pbr_materials", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_pbr_materials failed"))
        return result

    @mcp.tool(
        name="create_procedural_material",
        description="Generate a procedural material using NOISE, VORONOI, WAVE, BRICK, CHECKER, or GRADIENT texture networks.",
    )
    async def create_procedural_material(
        material_name: str,
        pattern: ProceduralPattern = "NOISE",
        scale: float = 5.0,
        detail: float = 4.0,
        roughness: float = 0.5,
        color1: list[float] = [0.8, 0.2, 0.2, 1.0],
        color2: list[float] = [0.1, 0.1, 0.3, 1.0],
        bump_strength: float = 0.1,
        metallic: float = 0.0,
        object_name: Optional[str] = None,
    ) -> dict:
        params = CreateProceduralMaterialParams(
            material_name=material_name,
            pattern=pattern,
            scale=scale,
            detail=detail,
            roughness=roughness,
            color1=color1,
            color2=color2,
            bump_strength=bump_strength,
            metallic=metallic,
            object_name=object_name,
        )
        result = await bridge.send_request("create_procedural_material", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_procedural_material failed"))
        return result

    @mcp.tool(
        name="bake_textures",
        description="Bake lighting, diffuse, normal maps, roughness, or ambient occlusion to an image texture using the Cycles render engine.",
    )
    async def bake_textures(
        object_name: str,
        output_filepath: str,
        bake_type: BakeType = "DIFFUSE",
        width: int = 1024,
        height: int = 1024,
        samples: int = 16,
    ) -> dict:
        params = BakeTexturesParams(
            object_name=object_name,
            output_filepath=output_filepath,
            bake_type=bake_type,
            width=width,
            height=height,
            samples=samples,
        )
        result = await bridge.send_request("bake_textures", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "bake_textures failed"))
        return result

    return setup_pbr_materials, create_procedural_material, bake_textures
