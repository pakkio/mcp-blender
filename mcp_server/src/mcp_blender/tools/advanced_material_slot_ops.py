from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class AutoLoadPBRParams(BaseModel):
    folder_path: str
    material_name: str = "M_AutoPBR"


class ManageMaterialSlotsParams(BaseModel):
    object_name: str
    action: str = "ASSIGN_SLOT"
    material_name: Optional[str] = None
    slot_index: int = 0
    face_indices: list[int] = []


class ProjectDecalParams(BaseModel):
    target_object: str
    decal_name: str = "Decal_Graphic"
    material_name: Optional[str] = None
    location: list[float] = [0.0, 0.0, 1.0]
    size: float = 1.0
    surface_offset: float = 0.002


def register_advanced_material_slot_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="auto_load_pbr_texture_set",
        description="Automatically inspect a texture folder, detect PBR maps (Albedo/BaseColor, Roughness, Metallic, Normal, Height/Displacement, AO), and wire a complete Principled BSDF PBR material graph.",
    )
    async def auto_load_pbr_texture_set(
        folder_path: str,
        material_name: str = "M_AutoPBR",
    ) -> dict:
        params = AutoLoadPBRParams(folder_path=folder_path, material_name=material_name)
        result = await bridge.send_request("auto_load_pbr_texture_set", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "auto_load_pbr_texture_set failed"))
        return result

    @mcp.tool(
        name="manage_material_slots",
        description="Add, remove, or assign multi-material slots on an object, or assign specific materials to face selections or polygon indices.",
    )
    async def manage_material_slots(
        object_name: str,
        action: str = "ASSIGN_SLOT",
        material_name: Optional[str] = None,
        slot_index: int = 0,
        face_indices: list[int] = [],
    ) -> dict:
        params = ManageMaterialSlotsParams(
            object_name=object_name,
            action=action,
            material_name=material_name,
            slot_index=slot_index,
            face_indices=face_indices,
        )
        result = await bridge.send_request("manage_material_slots", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "manage_material_slots failed"))
        return result

    @mcp.tool(
        name="project_decal_material",
        description="Create a floating alpha decal projection plane parented and shrinkwrapped to a target mesh surface.",
    )
    async def project_decal_material(
        target_object: str,
        decal_name: str = "Decal_Graphic",
        material_name: Optional[str] = None,
        location: list[float] = [0.0, 0.0, 1.0],
        size: float = 1.0,
        surface_offset: float = 0.002,
    ) -> dict:
        params = ProjectDecalParams(
            target_object=target_object,
            decal_name=decal_name,
            material_name=material_name,
            location=location,
            size=size,
            surface_offset=surface_offset,
        )
        result = await bridge.send_request("project_decal_material", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "project_decal_material failed"))
        return result

    return (
        auto_load_pbr_texture_set,
        manage_material_slots,
        project_decal_material,
    )
