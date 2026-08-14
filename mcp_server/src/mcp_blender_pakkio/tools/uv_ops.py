from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

UVUnwrapMethod = Literal[
    "SMART_PROJECT",
    "LIGHTMAP_PACK",
    "CUBE_PROJECT",
    "CYLINDER_PROJECT",
    "SPHERE_PROJECT",
    "PROJECT_FROM_VIEW",
    "UNWRAP",
    "FOLLOW_ACTIVE_QUADS",
    "PACK_ISLANDS",
]


class UVUnwrapParams(BaseModel):
    object_name: str
    method: UVUnwrapMethod = "SMART_PROJECT"
    angle_limit: float = 66.0
    island_margin: float = 0.02
    correct_aspect: bool = True
    scale_to_bounds: bool = False
    cube_size: float = 1.0
    pack_islands_margin: float = 0.02


def register_uv_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="uv_unwrap",
        description="Unwrap UV coordinates on an object using SMART_PROJECT, LIGHTMAP_PACK, CUBE_PROJECT, SPHERE_PROJECT, CYLINDER_PROJECT, PROJECT_FROM_VIEW, UNWRAP (Angle/Conformal), or PACK_ISLANDS.",
    )
    async def uv_unwrap(
        object_name: str,
        method: UVUnwrapMethod = "SMART_PROJECT",
        angle_limit: float = 66.0,
        island_margin: float = 0.02,
        correct_aspect: bool = True,
        scale_to_bounds: bool = False,
        cube_size: float = 1.0,
        pack_islands_margin: float = 0.02,
    ) -> dict:
        params = UVUnwrapParams(
            object_name=object_name,
            method=method,
            angle_limit=angle_limit,
            island_margin=island_margin,
            correct_aspect=correct_aspect,
            scale_to_bounds=scale_to_bounds,
            cube_size=cube_size,
            pack_islands_margin=pack_islands_margin,
        )
        result = await bridge.send_request("uv_unwrap", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "uv_unwrap failed"))
        return result

    return uv_unwrap
