from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

ParentType = Literal["OBJECT", "ARMATURE", "BONE", "VERTEX"]


class ParentObjectsParams(BaseModel):
    parent_name: str
    child_names: list[str]
    keep_transform: bool = True
    parent_type: ParentType = "OBJECT"


class UnparentObjectsParams(BaseModel):
    names: list[str]
    keep_transform: bool = True


def register_parent_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="parent_objects",
        description="Set parent-child relationship between Blender objects with option to keep current world transforms.",
    )
    async def parent_objects(
        parent_name: str,
        child_names: list[str],
        keep_transform: bool = True,
        parent_type: ParentType = "OBJECT",
    ) -> dict:
        params = ParentObjectsParams(
            parent_name=parent_name,
            child_names=child_names,
            keep_transform=keep_transform,
            parent_type=parent_type,
        )
        result = await bridge.send_request("parent_objects", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "parent_objects failed"))
        return result

    @mcp.tool(
        name="unparent_objects",
        description="Clear parent relationship for specified objects with option to maintain world transform.",
    )
    async def unparent_objects(
        names: list[str],
        keep_transform: bool = True,
    ) -> dict:
        params = UnparentObjectsParams(names=names, keep_transform=keep_transform)
        result = await bridge.send_request("unparent_objects", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "unparent_objects failed"))
        return result

    return parent_objects, unparent_objects
