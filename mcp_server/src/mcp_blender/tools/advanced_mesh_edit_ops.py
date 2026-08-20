from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

MeshOp = Literal[
    "BRIDGE_EDGE_LOOPS",
    "BISECT",
    "EXTRUDE_ALONG_NORMALS",
    "EXTRUDE_INDIVIDUAL_FACES",
    "SET_EDGE_CREASE",
    "SET_BEVEL_WEIGHT",
    "SEPARATE_BY_LOOSE_PARTS",
    "SEPARATE_BY_MATERIAL",
    "JOIN_OBJECTS",
]
OriginAction = Literal[
    "ORIGIN_TO_GEOMETRY",
    "ORIGIN_TO_CURSOR",
    "ORIGIN_TO_BOTTOM",
    "ORIGIN_TO_CENTER_OF_MASS",
    "CURSOR_TO_SELECTED",
    "CURSOR_TO_ORIGIN",
    "SET_CURSOR_LOCATION",
    "SET_ORIGIN_LOCATION",
]


class AdvancedMeshEditParams(BaseModel):
    object_name: str
    operation: MeshOp = "BRIDGE_EDGE_LOOPS"
    plane_co: list[float] = [0.0, 0.0, 0.0]
    plane_no: list[float] = [0.0, 0.0, 1.0]
    clear_inner: bool = False
    clear_outer: bool = False
    use_fill: bool = True
    number_cuts: int = 0
    offset: float = 0.2
    crease_value: float = 1.0
    weight_value: float = 1.0
    other_objects: Optional[list[str]] = None


class ManipulateOriginCursorParams(BaseModel):
    object_name: Optional[str] = None
    action: OriginAction = "ORIGIN_TO_GEOMETRY"
    location: Optional[list[float]] = None


def register_advanced_mesh_edit_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="advanced_mesh_edit",
        description="Advanced direct mesh editing: Bridge Edge Loops, Bisect plane cuts with cap fill, Extrude along normals / individual faces, Edge Crease, Bevel Weights, Separate by loose parts/materials, and Join meshes.",
    )
    async def advanced_mesh_edit(
        object_name: str,
        operation: MeshOp = "BRIDGE_EDGE_LOOPS",
        plane_co: list[float] = [0.0, 0.0, 0.0],
        plane_no: list[float] = [0.0, 0.0, 1.0],
        clear_inner: bool = False,
        clear_outer: bool = False,
        use_fill: bool = True,
        number_cuts: int = 0,
        offset: float = 0.2,
        crease_value: float = 1.0,
        weight_value: float = 1.0,
        other_objects: Optional[list[str]] = None,
    ) -> dict:
        params = AdvancedMeshEditParams(
            object_name=object_name,
            operation=operation,
            plane_co=plane_co,
            plane_no=plane_no,
            clear_inner=clear_inner,
            clear_outer=clear_outer,
            use_fill=use_fill,
            number_cuts=number_cuts,
            offset=offset,
            crease_value=crease_value,
            weight_value=weight_value,
            other_objects=other_objects,
        )
        result = await bridge.send_request("advanced_mesh_edit", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "advanced_mesh_edit failed"))
        return result

    @mcp.tool(
        name="manipulate_origin_cursor",
        description="Manipulate 3D Cursor and object origin points (Origin to Geometry, Origin to Cursor, Origin to Bottom bounding box for floor snapping, Origin to Center of Mass, Cursor to Selected, Set Cursor/Origin Location).",
    )
    async def manipulate_origin_cursor(
        object_name: Optional[str] = None,
        action: OriginAction = "ORIGIN_TO_GEOMETRY",
        location: Optional[list[float]] = None,
    ) -> dict:
        params = ManipulateOriginCursorParams(
            object_name=object_name,
            action=action,
            location=location,
        )
        result = await bridge.send_request("manipulate_origin_cursor", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "manipulate_origin_cursor failed"))
        return result

    return advanced_mesh_edit, manipulate_origin_cursor
