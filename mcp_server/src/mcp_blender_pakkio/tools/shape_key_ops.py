from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

ShapeKeyAction = Literal["CREATE_BASIS", "ADD_KEY", "SET_VALUE", "REMOVE_KEY"]


class ManageShapeKeysParams(BaseModel):
    object_name: str
    action: ShapeKeyAction = "ADD_KEY"
    key_name: Optional[str] = None
    value: Optional[float] = None
    frame: Optional[int] = None


def register_shape_key_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="manage_shape_keys",
        description="Manage shape keys (morph targets) on a mesh: create Basis, add shape keys, set weights (0.0 to 1.0), and keyframe shape key animation.",
    )
    async def manage_shape_keys(
        object_name: str,
        action: ShapeKeyAction = "ADD_KEY",
        key_name: Optional[str] = None,
        value: Optional[float] = None,
        frame: Optional[int] = None,
    ) -> dict:
        params = ManageShapeKeysParams(
            object_name=object_name,
            action=action,
            key_name=key_name,
            value=value,
            frame=frame,
        )
        result = await bridge.send_request("manage_shape_keys", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "manage_shape_keys failed"))
        return result

    return manage_shape_keys
