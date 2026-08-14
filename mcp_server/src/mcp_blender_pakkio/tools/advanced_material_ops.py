from typing import Any, Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

MaterialNodeAction = Literal[
    "GET_NODE_TREE",
    "ADD_NODE",
    "CONNECT_NODES",
    "DISCONNECT_NODES",
    "SET_NODE_INPUT",
    "REMOVE_NODE",
]
ColorAttrAction = Literal["CREATE", "SET_COLOR", "DELETE", "GET_ATTRIBUTES"]
ColorAttrDomain = Literal["CORNER", "POINT"]
ColorAttrDataType = Literal["FLOAT_COLOR", "BYTE_COLOR"]
ColorAttrFillMode = Literal["SOLID", "HEIGHT_GRADIENT"]


class EditMaterialNodesParams(BaseModel):
    material_name: str
    action: MaterialNodeAction = "GET_NODE_TREE"
    node_type: Optional[str] = None
    node_name: Optional[str] = None
    node_location: list[float] = [0.0, 0.0]
    from_node: Optional[str] = None
    from_socket: str = "Color"
    to_node: Optional[str] = None
    to_socket: str = "Base Color"
    input_socket: Optional[str] = None
    input_value: Optional[Any] = None


class ManageColorAttributesParams(BaseModel):
    object_name: str
    action: ColorAttrAction = "CREATE"
    attribute_name: str = "Color"
    domain: ColorAttrDomain = "CORNER"
    data_type: ColorAttrDataType = "FLOAT_COLOR"
    color: list[float] = [1.0, 0.0, 0.0, 1.0]
    fill_mode: ColorAttrFillMode = "SOLID"


def register_advanced_material_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="edit_material_nodes",
        description="Full low-level control over shader node trees: add shader nodes, connect/disconnect sockets, set socket parameter values, remove nodes, and inspect full material node graphs.",
    )
    async def edit_material_nodes(
        material_name: str,
        action: MaterialNodeAction = "GET_NODE_TREE",
        node_type: Optional[str] = None,
        node_name: Optional[str] = None,
        node_location: list[float] = [0.0, 0.0],
        from_node: Optional[str] = None,
        from_socket: str = "Color",
        to_node: Optional[str] = None,
        to_socket: str = "Base Color",
        input_socket: Optional[str] = None,
        input_value: Optional[Any] = None,
    ) -> dict:
        params = EditMaterialNodesParams(
            material_name=material_name,
            action=action,
            node_type=node_type,
            node_name=node_name,
            node_location=node_location,
            from_node=from_node,
            from_socket=from_socket,
            to_node=to_node,
            to_socket=to_socket,
            input_socket=input_socket,
            input_value=input_value,
        )
        result = await bridge.send_request("edit_material_nodes", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "edit_material_nodes failed"))
        return result

    @mcp.tool(
        name="manage_color_attributes",
        description="Manage vertex color attributes: create color layers, fill solid colors, generate height gradients, or random face island colors.",
    )
    async def manage_color_attributes(
        object_name: str,
        action: ColorAttrAction = "CREATE",
        attribute_name: str = "Color",
        domain: ColorAttrDomain = "CORNER",
        data_type: ColorAttrDataType = "FLOAT_COLOR",
        color: list[float] = [1.0, 0.0, 0.0, 1.0],
        fill_mode: ColorAttrFillMode = "SOLID",
    ) -> dict:
        params = ManageColorAttributesParams(
            object_name=object_name,
            action=action,
            attribute_name=attribute_name,
            domain=domain,
            data_type=data_type,
            color=color,
            fill_mode=fill_mode,
        )
        result = await bridge.send_request("manage_color_attributes", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "manage_color_attributes failed"))
        return result

    return edit_material_nodes, manage_color_attributes
