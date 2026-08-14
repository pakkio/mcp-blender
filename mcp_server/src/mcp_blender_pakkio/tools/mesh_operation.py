from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

MeshOpType = Literal[
    "SHADE_SMOOTH",
    "SHADE_FLAT",
    "AUTO_SMOOTH",
    "SUBDIVIDE",
    "TRIANGULATE",
    "FLIP_NORMALS",
    "RECALCULATE_NORMALS",
    "MERGE_BY_DISTANCE",
    "SET_ORIGIN_TO_GEOMETRY",
    "SET_ORIGIN_TO_CURSOR",
    "SET_ORIGIN_TO_MASS_CENTER",
    "JOIN_SELECTED",
    "SEPARATE_BY_LOOSE_PARTS",
    "CONVERT_TO_MESH",
]


class MeshOperationParams(BaseModel):
    object_name: str
    operation: MeshOpType
    join_with_objects: Optional[list[str]] = None
    merge_distance: Optional[float] = 0.0001
    subdivision_cuts: Optional[int] = 1


def register_mesh_operation_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="mesh_operation",
        description="Execute mesh-level operations: SHADE_SMOOTH, SHADE_FLAT, AUTO_SMOOTH, SUBDIVIDE, TRIANGULATE, FLIP_NORMALS, RECALCULATE_NORMALS, MERGE_BY_DISTANCE, SET_ORIGIN_*, JOIN_SELECTED, SEPARATE_BY_LOOSE_PARTS, CONVERT_TO_MESH.",
    )
    async def mesh_operation(
        object_name: str,
        operation: MeshOpType,
        join_with_objects: Optional[list[str]] = None,
        merge_distance: Optional[float] = 0.0001,
        subdivision_cuts: Optional[int] = 1,
    ) -> dict:
        params = MeshOperationParams(
            object_name=object_name,
            operation=operation,
            join_with_objects=join_with_objects,
            merge_distance=merge_distance,
            subdivision_cuts=subdivision_cuts,
        )
        result = await bridge.send_request("mesh_operation", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "mesh_operation failed"))
        return result

    return mesh_operation
