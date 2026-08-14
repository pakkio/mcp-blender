from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class ScenePerformanceParams(BaseModel):
    pass


class SkySunRigParams(BaseModel):
    sun_elevation: float = 25.0
    sun_rotation: float = 45.0
    turbidity: float = 2.2
    ozone: float = 1.0
    sun_intensity: float = 1.0


def register_scene_diagnostics_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="inspect_scene_performance",
        description="Audit scene complexity, polygon budgets, triangle counts per object, non-manifold mesh errors, and memory usage for game engine / rendering optimization.",
    )
    async def inspect_scene_performance() -> dict:
        result = await bridge.send_request("inspect_scene_performance", {})
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "inspect_scene_performance failed"))
        return result

    @mcp.tool(
        name="setup_sky_sun_rig",
        description="Setup a physical Nishita Sky atmosphere with a synchronized directional Sun light, realistic sun elevation/rotation, and ozone/turbidity settings.",
    )
    async def setup_sky_sun_rig(
        sun_elevation: float = 25.0,
        sun_rotation: float = 45.0,
        turbidity: float = 2.2,
        ozone: float = 1.0,
        sun_intensity: float = 1.0,
    ) -> dict:
        params = SkySunRigParams(
            sun_elevation=sun_elevation,
            sun_rotation=sun_rotation,
            turbidity=turbidity,
            ozone=ozone,
            sun_intensity=sun_intensity,
        )
        result = await bridge.send_request("setup_sky_sun_rig", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_sky_sun_rig failed"))
        return result

    return inspect_scene_performance, setup_sky_sun_rig
