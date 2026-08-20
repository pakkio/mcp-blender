from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

LightType = Literal["POINT", "SUN", "SPOT", "AREA"]


class ConfigureLightParams(BaseModel):
    name: str
    light_type: Optional[LightType] = None
    energy: Optional[float] = None
    color: Optional[tuple[float, float, float]] = None
    spot_size: Optional[float] = None
    spot_blend: Optional[float] = None
    shadow_soft_size: Optional[float] = None
    size: Optional[float] = None
    size_y: Optional[float] = None


def register_light_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="configure_light",
        description="Configure properties of a light object (light type, power/energy in Watts, color, spot size/blend, area size, shadow soft size).",
    )
    async def configure_light(
        name: str,
        light_type: Optional[LightType] = None,
        energy: Optional[float] = None,
        color: Optional[tuple[float, float, float]] = None,
        spot_size: Optional[float] = None,
        spot_blend: Optional[float] = None,
        shadow_soft_size: Optional[float] = None,
        size: Optional[float] = None,
        size_y: Optional[float] = None,
    ) -> dict:
        params = ConfigureLightParams(
            name=name,
            light_type=light_type,
            energy=energy,
            color=color,
            spot_size=spot_size,
            spot_blend=spot_blend,
            shadow_soft_size=shadow_soft_size,
            size=size,
            size_y=size_y,
        )
        result = await bridge.send_request("configure_light", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_light failed"))
        return result

    return configure_light
