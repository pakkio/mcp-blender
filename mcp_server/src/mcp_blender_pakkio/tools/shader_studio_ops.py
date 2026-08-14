from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class ProceduralGrungeParams(BaseModel):
    material_name: str
    edge_wear_amount: float = 0.5
    dirt_amount: float = 0.3
    noise_scale: float = 15.0


class TriplanarParams(BaseModel):
    material_name: str
    texture_scale: float = 2.0
    blend: float = 0.2


class SpecialtyShaderParams(BaseModel):
    material_name: str = "M_SpecialtyShader"
    preset: str = "CAR_PAINT"
    base_color: list[float] = [0.8, 0.05, 0.05, 1.0]


class ShaderNodeGroupParams(BaseModel):
    group_name: str = "CustomShaderGroup"
    action: str = "CREATE"


def register_shader_studio_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_procedural_grunge_mask",
        description="Generate an advanced procedural edge-wear, dirt, and cavity grunge mask node group (Pointiness, Curvature, AO, Noise) for weathered metal and worn surfaces.",
    )
    async def create_procedural_grunge_mask(
        material_name: str,
        edge_wear_amount: float = 0.5,
        dirt_amount: float = 0.3,
        noise_scale: float = 15.0,
    ) -> dict:
        params = ProceduralGrungeParams(
            material_name=material_name,
            edge_wear_amount=edge_wear_amount,
            dirt_amount=dirt_amount,
            noise_scale=noise_scale,
        )
        result = await bridge.send_request("create_procedural_grunge_mask", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_procedural_grunge_mask failed"))
        return result

    @mcp.tool(
        name="setup_triplanar_mapping",
        description="Setup seamless UV-free box / triplanar texture projection for seamless textures across complex organic rock, terrain, or architecture meshes.",
    )
    async def setup_triplanar_mapping(
        material_name: str,
        texture_scale: float = 2.0,
        blend: float = 0.2,
    ) -> dict:
        params = TriplanarParams(
            material_name=material_name,
            texture_scale=texture_scale,
            blend=blend,
        )
        result = await bridge.send_request("setup_triplanar_mapping", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_triplanar_mapping failed"))
        return result

    @mcp.tool(
        name="setup_specialty_shader",
        description="Create specialized production shader graphs: CAR_PAINT (metallic flakes + clearcoat), SKIN_SSS (subsurface scattering), IRIDESCENT_PEARL (thin-film interference), HOLOGRAM_GLOW, or GLASS_DISPERSION.",
    )
    async def setup_specialty_shader(
        material_name: str = "M_SpecialtyShader",
        preset: str = "CAR_PAINT",
        base_color: list[float] = [0.8, 0.05, 0.05, 1.0],
    ) -> dict:
        params = SpecialtyShaderParams(
            material_name=material_name,
            preset=preset,
            base_color=base_color,
        )
        result = await bridge.send_request("setup_specialty_shader", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_specialty_shader failed"))
        return result

    @mcp.tool(
        name="manage_shader_node_group",
        description="Create reusable Shader Node Groups with custom inputs, outputs, and internal sub-networks.",
    )
    async def manage_shader_node_group(
        group_name: str = "CustomShaderGroup",
        action: str = "CREATE",
    ) -> dict:
        params = ShaderNodeGroupParams(group_name=group_name, action=action)
        result = await bridge.send_request("manage_shader_node_group", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "manage_shader_node_group failed"))
        return result

    return (
        create_procedural_grunge_mask,
        setup_triplanar_mapping,
        setup_specialty_shader,
        manage_shader_node_group,
    )
