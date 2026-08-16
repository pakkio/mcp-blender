from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

CollectionAction = Literal["CREATE", "DELETE", "RENAME", "LINK_OBJECT", "UNLINK_OBJECT", "SET_VISIBILITY"]


class ManageCollectionParams(BaseModel):
    action: CollectionAction = "CREATE"
    name: str
    new_name: Optional[str] = None
    object_name: Optional[str] = None
    parent_collection: Optional[str] = None
    hide_viewport: Optional[bool] = None
    hide_render: Optional[bool] = None


def register_collection_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="manage_collection",
        description="Create, delete, rename collections, link/unlink objects, nest collections, or toggle viewport/render visibility. "
        "Links one object per call -- for grouping many parts into a multi-level collection + parent hierarchy in one call, use organize_scene_hierarchy instead.",
    )
    async def manage_collection(
        action: CollectionAction = "CREATE",
        name: str = "",
        new_name: Optional[str] = None,
        object_name: Optional[str] = None,
        parent_collection: Optional[str] = None,
        hide_viewport: Optional[bool] = None,
        hide_render: Optional[bool] = None,
    ) -> dict:
        params = ManageCollectionParams(
            action=action,
            name=name,
            new_name=new_name,
            object_name=object_name,
            parent_collection=parent_collection,
            hide_viewport=hide_viewport,
            hide_render=hide_render,
        )
        result = await bridge.send_request("manage_collection", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "manage_collection failed"))
        return result

    return manage_collection
