from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

FluidDomainType = Literal["GAS", "LIQUID"]


class CreateVolumeVDBParams(BaseModel):
    name: str = "VolumeDomain"
    vdb_filepath: Optional[str] = None
    location: list[float] = [0.0, 0.0, 1.0]
    scale: list[float] = [2.0, 2.0, 2.0]
    density: float = 0.05


class ConfigureVolumeShaderParams(BaseModel):
    material_name: Optional[str] = None
    object_name: Optional[str] = None
    density: float = 0.1
    color: list[float] = [1.0, 1.0, 1.0, 1.0]
    absorption_color: list[float] = [0.0, 0.0, 0.0, 1.0]
    emission_strength: float = 0.0
    blackbody_intensity: float = 0.0


class BakeFluidDomainParams(BaseModel):
    domain_object: str
    domain_type: FluidDomainType = "GAS"
    resolution_max: int = 64


def register_volumetric_vdb_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_volume_vdb",
        description="Create an OpenVDB volume object from file or create a procedural volumetric fog/cloud domain box.",
    )
    async def create_volume_vdb(
        name: str = "VolumeDomain",
        vdb_filepath: Optional[str] = None,
        location: list[float] = [0.0, 0.0, 1.0],
        scale: list[float] = [2.0, 2.0, 2.0],
        density: float = 0.05,
    ) -> dict:
        params = CreateVolumeVDBParams(
            name=name,
            vdb_filepath=vdb_filepath,
            location=location,
            scale=scale,
            density=density,
        )
        result = await bridge.send_request("create_volume_vdb", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_volume_vdb failed"))
        return result

    @mcp.tool(
        name="configure_volume_shader",
        description="Configure Principled Volume shader properties: density, color, absorption color, emission strength, and blackbody temperature.",
    )
    async def configure_volume_shader(
        material_name: Optional[str] = None,
        object_name: Optional[str] = None,
        density: float = 0.1,
        color: list[float] = [1.0, 1.0, 1.0, 1.0],
        absorption_color: list[float] = [0.0, 0.0, 0.0, 1.0],
        emission_strength: float = 0.0,
        blackbody_intensity: float = 0.0,
    ) -> dict:
        params = ConfigureVolumeShaderParams(
            material_name=material_name,
            object_name=object_name,
            density=density,
            color=color,
            absorption_color=absorption_color,
            emission_strength=emission_strength,
            blackbody_intensity=blackbody_intensity,
        )
        result = await bridge.send_request("configure_volume_shader", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_volume_shader failed"))
        return result

    @mcp.tool(
        name="bake_fluid_domain",
        description="Configure Mantaflow smoke, fire, or liquid simulation domains and start background simulation bake.",
    )
    async def bake_fluid_domain(
        domain_object: str,
        domain_type: FluidDomainType = "GAS",
        resolution_max: int = 64,
    ) -> dict:
        params = BakeFluidDomainParams(
            domain_object=domain_object,
            domain_type=domain_type,
            resolution_max=resolution_max,
        )
        result = await bridge.send_request("bake_fluid_domain", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "bake_fluid_domain failed"))
        return result

    return create_volume_vdb, configure_volume_shader, bake_fluid_domain
