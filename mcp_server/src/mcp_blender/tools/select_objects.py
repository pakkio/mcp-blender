from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

SelectAction = Literal["SELECT", "DESELECT", "SET", "SELECT_ALL", "DESELECT_ALL", "INVERT"]
InteractionMode = Literal["OBJECT", "EDIT", "SCULPT", "POSE", "WEIGHT_PAINT", "VERTEX_PAINT", "TEXTURE_PAINT"]


class SelectObjectsParams(BaseModel):
    names: Optional[list[str]] = None
    action: SelectAction = "SET"
    active_object: Optional[str] = None
    mode: Optional[InteractionMode] = None


def register_select_objects_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="select_objects",
        description="Select or deselect objects in Blender, set the active object, and optionally switch interaction modes (OBJECT, EDIT, SCULPT, POSE, etc.).",
    )
    async def select_objects(
        names: Optional[list[str]] = None,
        action: SelectAction = "SET",
        active_object: Optional[str] = None,
        mode: Optional[InteractionMode] = None,
    ) -> dict:
        params = SelectObjectsParams(
            names=names,
            action=action,
            active_object=active_object,
            mode=mode,
        )
        result = await bridge.send_request("select_objects", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "select_objects failed"))
        return result

    return select_objects
