from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

BlendMode = Literal["OPAQUE", "CLIP", "HASHED", "BLEND"]
ShadowMode = Literal["NONE", "OPAQUE", "CLIP", "HASHED"]


class ConfigureRenderEffectsParams(BaseModel):
    ambient_occlusion: Optional[bool] = None
    ao_distance: Optional[float] = None
    ao_factor: Optional[float] = None
    reflections: Optional[bool] = None
    refraction: Optional[bool] = None
    motion_blur: Optional[bool] = None
    motion_blur_shutter: Optional[float] = None
    depth_of_field: Optional[bool] = None
    film_transparent: Optional[bool] = None
    volumetric_start: Optional[float] = None
    volumetric_end: Optional[float] = None


class ConfigureMaterialTransparencyParams(BaseModel):
    material_name: str
    transmission_weight: Optional[float] = None
    ior: Optional[float] = None
    roughness: Optional[float] = None
    alpha: Optional[float] = None
    blend_mode: BlendMode = "BLEND"
    shadow_mode: ShadowMode = "HASHED"
    use_screen_refraction: Optional[bool] = None
    backface_culling: Optional[bool] = None


def register_render_effects_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="configure_render_effects",
        description="Configure high-end rendering effects: Ambient Occlusion (distance/factor), EEVEE Next Raytracing & Screen Space Reflections, Refractions, Motion Blur, Depth of Field, Volumetrics, and Film Transparency (Alpha channel rendering).",
    )
    async def configure_render_effects(
        ambient_occlusion: Optional[bool] = None,
        ao_distance: Optional[float] = None,
        ao_factor: Optional[float] = None,
        reflections: Optional[bool] = None,
        refraction: Optional[bool] = None,
        motion_blur: Optional[bool] = None,
        motion_blur_shutter: Optional[float] = None,
        depth_of_field: Optional[bool] = None,
        film_transparent: Optional[bool] = None,
        volumetric_start: Optional[float] = None,
        volumetric_end: Optional[float] = None,
    ) -> dict:
        params = ConfigureRenderEffectsParams(
            ambient_occlusion=ambient_occlusion,
            ao_distance=ao_distance,
            ao_factor=ao_factor,
            reflections=reflections,
            refraction=refraction,
            motion_blur=motion_blur,
            motion_blur_shutter=motion_blur_shutter,
            depth_of_field=depth_of_field,
            film_transparent=film_transparent,
            volumetric_start=volumetric_start,
            volumetric_end=volumetric_end,
        )
        result = await bridge.send_request("configure_render_effects", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_render_effects failed"))
        return result

    @mcp.tool(
        name="configure_material_transparency",
        description="Configure advanced glass, liquid, acrylic, and transparent shader properties: Transmission weight, Index of Refraction (IOR), Alpha blend modes, screen refraction, backface culling, and roughness.",
    )
    async def configure_material_transparency(
        material_name: str,
        transmission_weight: Optional[float] = None,
        ior: Optional[float] = None,
        roughness: Optional[float] = None,
        alpha: Optional[float] = None,
        blend_mode: BlendMode = "BLEND",
        shadow_mode: ShadowMode = "HASHED",
        use_screen_refraction: Optional[bool] = None,
        backface_culling: Optional[bool] = None,
    ) -> dict:
        params = ConfigureMaterialTransparencyParams(
            material_name=material_name,
            transmission_weight=transmission_weight,
            ior=ior,
            roughness=roughness,
            alpha=alpha,
            blend_mode=blend_mode,
            shadow_mode=shadow_mode,
            use_screen_refraction=use_screen_refraction,
            backface_culling=backface_culling,
        )
        result = await bridge.send_request("configure_material_transparency", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_material_transparency failed"))
        return result

    return configure_render_effects, configure_material_transparency
