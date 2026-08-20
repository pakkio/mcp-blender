from typing import Any, Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import HEAVY_REQUEST_TIMEOUT_S, BlenderBridge
from ..errors import BridgeError, ErrorType

GeometryNodesPreset = Literal[
    "EMPTY",
    "SCATTER_ON_SURFACE",
    "EXTRUDE_FACES",
    "SUBDIVIDE_AND_NOISE",
    "CURVE_TO_TUBE",
    "WIREFRAME_LATTICE",
    "PROCEDURAL_GRID_ARRAY",
]
GNAction = Literal[
    "GET_GRAPH_INFO",
    "ADD_NODE",
    "CONNECT_NODES",
    "REMOVE_NODE",
    "SET_INPUT_VALUE",
]


class CreateGeometryNodesParams(BaseModel):
    object_name: str
    modifier_name: str = "GeometryNodes"
    preset: GeometryNodesPreset = "EMPTY"
    preset_params: Optional[dict[str, Any]] = None


class EditGeometryNodesParams(BaseModel):
    object_name: str
    modifier_name: str = "GeometryNodes"
    action: GNAction = "GET_GRAPH_INFO"
    node_type: Optional[str] = None
    node_name: Optional[str] = None
    node_location: list[float] = [0.0, 0.0]
    from_node: Optional[str] = None
    from_socket: str = "Geometry"
    to_node: Optional[str] = None
    to_socket: str = "Geometry"
    input_name: Optional[str] = None
    input_value: Optional[Any] = None


class BakeGeometryNodesParams(BaseModel):
    object_name: str
    modifier_name: str = "GeometryNodes"


def register_geometry_nodes_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_geometry_nodes",
        description="Create and configure a Geometry Nodes modifier on an object with built-in presets (EMPTY, SCATTER_ON_SURFACE, EXTRUDE_FACES, SUBDIVIDE_AND_NOISE, CURVE_TO_TUBE, WIREFRAME_LATTICE, PROCEDURAL_GRID_ARRAY).",
    )
    async def create_geometry_nodes(
        object_name: str,
        modifier_name: str = "GeometryNodes",
        preset: GeometryNodesPreset = "EMPTY",
        preset_params: Optional[dict[str, Any]] = None,
    ) -> dict:
        params = CreateGeometryNodesParams(
            object_name=object_name,
            modifier_name=modifier_name,
            preset=preset,
            preset_params=preset_params,
        )
        result = await bridge.send_request("create_geometry_nodes", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_geometry_nodes failed"))
        return result

    @mcp.tool(
        name="edit_geometry_nodes",
        description="Inspect and edit Geometry Nodes graphs: add/remove nodes, connect sockets, set exposed modifier input values, or query full node graph structure.",
    )
    async def edit_geometry_nodes(
        object_name: str,
        modifier_name: str = "GeometryNodes",
        action: GNAction = "GET_GRAPH_INFO",
        node_type: Optional[str] = None,
        node_name: Optional[str] = None,
        node_location: list[float] = [0.0, 0.0],
        from_node: Optional[str] = None,
        from_socket: str = "Geometry",
        to_node: Optional[str] = None,
        to_socket: str = "Geometry",
        input_name: Optional[str] = None,
        input_value: Optional[Any] = None,
    ) -> dict:
        params = EditGeometryNodesParams(
            object_name=object_name,
            modifier_name=modifier_name,
            action=action,
            node_type=node_type,
            node_name=node_name,
            node_location=node_location,
            from_node=from_node,
            from_socket=from_socket,
            to_node=to_node,
            to_socket=to_socket,
            input_name=input_name,
            input_value=input_value,
        )
        result = await bridge.send_request("edit_geometry_nodes", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "edit_geometry_nodes failed"))
        return result

    @mcp.tool(
        name="bake_geometry_nodes",
        description="Permanently bake Geometry Nodes modifiers to real mesh geometry, with automatic realization of instanced meshes.",
    )
    async def bake_geometry_nodes(
        object_name: str,
        modifier_name: str = "GeometryNodes",
    ) -> dict:
        params = BakeGeometryNodesParams(
            object_name=object_name,
            modifier_name=modifier_name,
        )
        result = await bridge.send_request(
            "bake_geometry_nodes", params.model_dump(), timeout=HEAVY_REQUEST_TIMEOUT_S
        )
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "bake_geometry_nodes failed"))
        return result

    return create_geometry_nodes, edit_geometry_nodes, bake_geometry_nodes
