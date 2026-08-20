from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

LightingRigType = Literal[
    "THREE_POINT_STUDIO",
    "PRODUCT_SOFTBOX",
    "CYBERPUNK_NEON",
    "FILM_NOIR",
    "WARM_GOLDEN_HOUR",
]


class CreateLightingRigParams(BaseModel):
    rig_type: LightingRigType = "THREE_POINT_STUDIO"
    target_object: Optional[str] = None
    energy_multiplier: float = 1.0


class ConfigureLightLinkingParams(BaseModel):
    light_name: str
    collection_name: Optional[str] = None


def register_studio_lighting_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_lighting_rig",
        description="Instantly build production lighting setups (THREE_POINT_STUDIO, PRODUCT_SOFTBOX, CYBERPUNK_NEON, FILM_NOIR, WARM_GOLDEN_HOUR) with automatic target tracking.",
    )
    async def create_lighting_rig(
        rig_type: LightingRigType = "THREE_POINT_STUDIO",
        target_object: Optional[str] = None,
        energy_multiplier: float = 1.0,
    ) -> dict:
        params = CreateLightingRigParams(
            rig_type=rig_type,
            target_object=target_object,
            energy_multiplier=energy_multiplier,
        )
        result = await bridge.send_request("create_lighting_rig", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_lighting_rig failed"))
        return result

    @mcp.tool(
        name="configure_light_linking",
        description="Configure per-object light linking and shadow linking (link lights to illuminate specific objects or exclude shadows).",
    )
    async def configure_light_linking(
        light_name: str,
        collection_name: Optional[str] = None,
    ) -> dict:
        params = ConfigureLightLinkingParams(
            light_name=light_name,
            collection_name=collection_name,
        )
        result = await bridge.send_request("configure_light_linking", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_light_linking failed"))
        return result

    return create_lighting_rig, configure_light_linking
