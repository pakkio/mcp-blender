from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class CreateMaterialParams(BaseModel):
    name: str
    base_color: Optional[tuple[float, float, float, float]] = (0.8, 0.8, 0.8, 1.0)
    metallic: Optional[float] = 0.0
    roughness: Optional[float] = 0.5
    specular: Optional[float] = 0.5
    ior: Optional[float] = 1.45
    transmission: Optional[float] = 0.0
    emission_color: Optional[tuple[float, float, float, float]] = (0.0, 0.0, 0.0, 1.0)
    emission_strength: Optional[float] = 1.0
    alpha: Optional[float] = 1.0
    assign_to_object: Optional[str] = None


class AssignMaterialParams(BaseModel):
    object_name: str
    material_name: str
    slot_index: Optional[int] = None


class GetMaterialInfoParams(BaseModel):
    material_name: str


class SetMaterialPropertiesParams(BaseModel):
    material_name: str
    base_color: Optional[tuple[float, float, float, float]] = None
    metallic: Optional[float] = None
    roughness: Optional[float] = None
    specular: Optional[float] = None
    ior: Optional[float] = None
    transmission: Optional[float] = None
    emission_color: Optional[tuple[float, float, float, float]] = None
    emission_strength: Optional[float] = None
    alpha: Optional[float] = None


def register_material_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_material",
        description="Create a PBR material with Principled BSDF shader and optionally assign it to an object.",
    )
    async def create_material(
        name: str,
        base_color: Optional[tuple[float, float, float, float]] = (0.8, 0.8, 0.8, 1.0),
        metallic: Optional[float] = 0.0,
        roughness: Optional[float] = 0.5,
        specular: Optional[float] = 0.5,
        ior: Optional[float] = 1.45,
        transmission: Optional[float] = 0.0,
        emission_color: Optional[tuple[float, float, float, float]] = (0.0, 0.0, 0.0, 1.0),
        emission_strength: Optional[float] = 1.0,
        alpha: Optional[float] = 1.0,
        assign_to_object: Optional[str] = None,
    ) -> dict:
        params = CreateMaterialParams(
            name=name,
            base_color=base_color,
            metallic=metallic,
            roughness=roughness,
            specular=specular,
            ior=ior,
            transmission=transmission,
            emission_color=emission_color,
            emission_strength=emission_strength,
            alpha=alpha,
            assign_to_object=assign_to_object,
        )
        result = await bridge.send_request("create_material", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_material failed"))
        return result

    @mcp.tool(
        name="assign_material",
        description="Assign an existing material to an object or specific material slot.",
    )
    async def assign_material(
        object_name: str,
        material_name: str,
        slot_index: Optional[int] = None,
    ) -> dict:
        params = AssignMaterialParams(
            object_name=object_name,
            material_name=material_name,
            slot_index=slot_index,
        )
        result = await bridge.send_request("assign_material", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "assign_material failed"))
        return result

    @mcp.tool(
        name="get_material_info",
        description="Get detailed shader node and Principled BSDF information for a material.",
    )
    async def get_material_info(material_name: str) -> dict:
        params = GetMaterialInfoParams(material_name=material_name)
        result = await bridge.send_request("get_material_info", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "get_material_info failed"))
        return result

    @mcp.tool(
        name="set_material_properties",
        description="Update shader parameters on an existing material's Principled BSDF.",
    )
    async def set_material_properties(
        material_name: str,
        base_color: Optional[tuple[float, float, float, float]] = None,
        metallic: Optional[float] = None,
        roughness: Optional[float] = None,
        specular: Optional[float] = None,
        ior: Optional[float] = None,
        transmission: Optional[float] = None,
        emission_color: Optional[tuple[float, float, float, float]] = None,
        emission_strength: Optional[float] = None,
        alpha: Optional[float] = None,
    ) -> dict:
        params = SetMaterialPropertiesParams(
            material_name=material_name,
            base_color=base_color,
            metallic=metallic,
            roughness=roughness,
            specular=specular,
            ior=ior,
            transmission=transmission,
            emission_color=emission_color,
            emission_strength=emission_strength,
            alpha=alpha,
        )
        result = await bridge.send_request("set_material_properties", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "set_material_properties failed"))
        return result

    return create_material, assign_material, get_material_info, set_material_properties
