from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class ConfigureCompositorEffectsParams(BaseModel):
    use_glare: bool = True
    glare_threshold: float = 0.8
    glare_size: int = 8
    use_lens_distortion: bool = False
    distortion: float = 0.02
    dispersion: float = 0.03
    use_viewport_compositing: bool = True


class CreateToonShaderParams(BaseModel):
    material_name: str = "M_AnimeToon"
    object_name: Optional[str] = None
    base_color: list[float] = [0.9, 0.4, 0.4, 1.0]
    shadow_color: list[float] = [0.4, 0.1, 0.2, 1.0]
    rim_color: list[float] = [1.0, 0.9, 0.6, 1.0]
    rim_power: float = 3.0


def register_compositor_effects_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="configure_compositor_effects",
        description="Configure post-processing compositor nodes: GPU Viewport Compositing, Bloom/Glare (Fog Glow, Streaks), Lens Distortion & Chromatic Aberration, and Color Grading.",
    )
    async def configure_compositor_effects(
        use_glare: bool = True,
        glare_threshold: float = 0.8,
        glare_size: int = 8,
        use_lens_distortion: bool = False,
        distortion: float = 0.02,
        dispersion: float = 0.03,
        use_viewport_compositing: bool = True,
    ) -> dict:
        params = ConfigureCompositorEffectsParams(
            use_glare=use_glare,
            glare_threshold=glare_threshold,
            glare_size=glare_size,
            use_lens_distortion=use_lens_distortion,
            distortion=distortion,
            dispersion=dispersion,
            use_viewport_compositing=use_viewport_compositing,
        )
        result = await bridge.send_request("configure_compositor_effects", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_compositor_effects failed"))
        return result

    @mcp.tool(
        name="create_toon_shader",
        description="Create an anime / cel-shaded Non-Photorealistic Material (NPR) with stepped shadow color ramps, highlight bands, and rim lighting.",
    )
    async def create_toon_shader(
        material_name: str = "M_AnimeToon",
        object_name: Optional[str] = None,
        base_color: list[float] = [0.9, 0.4, 0.4, 1.0],
        shadow_color: list[float] = [0.4, 0.1, 0.2, 1.0],
        rim_color: list[float] = [1.0, 0.9, 0.6, 1.0],
        rim_power: float = 3.0,
    ) -> dict:
        params = CreateToonShaderParams(
            material_name=material_name,
            object_name=object_name,
            base_color=base_color,
            shadow_color=shadow_color,
            rim_color=rim_color,
            rim_power=rim_power,
        )
        result = await bridge.send_request("create_toon_shader", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_toon_shader failed"))
        return result

    return configure_compositor_effects, create_toon_shader
