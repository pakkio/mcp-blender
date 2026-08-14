from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import HEAVY_REQUEST_TIMEOUT_S, BlenderBridge
from ..errors import BridgeError, ErrorType

AdvancedBakeType = Literal[
    "COMBINED",
    "DIFFUSE",
    "NORMAL",
    "ROUGHNESS",
    "AO",
    "SHADOW",
    "EMISSION",
    "ENVIRONMENT",
    "POSITION",
    "UV",
]
LightProbeType = Literal["GRID", "SPHERE", "PLANE"]


class BakeAdvancedParams(BaseModel):
    target_object: str
    source_objects: Optional[list[str]] = None
    bake_type: AdvancedBakeType = "NORMAL"
    selected_to_active: bool = False
    cage_object: Optional[str] = None
    cage_extrusion: float = 0.05
    bake_to_vertex_colors: bool = False
    vertex_color_layer: str = "BakedColor"
    output_filepath: Optional[str] = None
    width: int = 2048
    height: int = 2048
    margin: int = 16
    samples: int = 32
    denoise: bool = False


class ConfigureLightProbeParams(BaseModel):
    probe_type: LightProbeType = "GRID"
    name: Optional[str] = None
    location: list[float] = [0.0, 0.0, 0.0]
    resolution: list[int] = [4, 4, 4]
    influence_distance: float = 5.0
    bake_cache: bool = False


def register_advanced_bake_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="bake_advanced",
        description="Advanced high-to-low poly baking, multi-pass baking (NORMAL, COMBINED, DIFFUSE, ROUGHNESS, AO, SHADOW, EMISSION), cage/extrusion ray distance, and baking to vertex color attributes.",
    )
    async def bake_advanced(
        target_object: str,
        source_objects: Optional[list[str]] = None,
        bake_type: AdvancedBakeType = "NORMAL",
        selected_to_active: bool = False,
        cage_object: Optional[str] = None,
        cage_extrusion: float = 0.05,
        bake_to_vertex_colors: bool = False,
        vertex_color_layer: str = "BakedColor",
        output_filepath: Optional[str] = None,
        width: int = 2048,
        height: int = 2048,
        margin: int = 16,
        samples: int = 32,
        denoise: bool = False,
    ) -> dict:
        params = BakeAdvancedParams(
            target_object=target_object,
            source_objects=source_objects,
            bake_type=bake_type,
            selected_to_active=selected_to_active,
            cage_object=cage_object,
            cage_extrusion=cage_extrusion,
            bake_to_vertex_colors=bake_to_vertex_colors,
            vertex_color_layer=vertex_color_layer,
            output_filepath=output_filepath,
            width=width,
            height=height,
            margin=margin,
            samples=samples,
            denoise=denoise,
        )
        result = await bridge.send_request(
            "bake_advanced", params.model_dump(), timeout=HEAVY_REQUEST_TIMEOUT_S
        )
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "bake_advanced failed"))
        return result

    @mcp.tool(
        name="configure_light_probe",
        description="Create and configure EEVEE Light Probes (GRID Irradiance Volume, SPHERE Reflection Probe, PLANE Reflection Plane) and trigger lighting cache bake.",
    )
    async def configure_light_probe(
        probe_type: LightProbeType = "GRID",
        name: Optional[str] = None,
        location: list[float] = [0.0, 0.0, 0.0],
        resolution: list[int] = [4, 4, 4],
        influence_distance: float = 5.0,
        bake_cache: bool = False,
    ) -> dict:
        params = ConfigureLightProbeParams(
            probe_type=probe_type,
            name=name,
            location=location,
            resolution=resolution,
            influence_distance=influence_distance,
            bake_cache=bake_cache,
        )
        result = await bridge.send_request(
            "configure_light_probe", params.model_dump(), timeout=HEAVY_REQUEST_TIMEOUT_S
        )
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_light_probe failed"))
        return result

    return bake_advanced, configure_light_probe
