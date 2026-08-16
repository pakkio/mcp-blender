from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class GroupSpec(BaseModel):
    name: str
    objects: list[str] = []
    collection_path: Optional[str] = None
    root_empty: bool = True
    children: list["GroupSpec"] = []


class OrganizeSceneHierarchyParams(BaseModel):
    groups: list[GroupSpec]
    keep_transform: bool = True
    rename_members: bool = False


def register_hierarchy_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="organize_scene_hierarchy",
        description=(
            "Build a multi-level semantic grouping in one call: nested collections (via collection_path, "
            "e.g. 'Furniture/Chairs') plus an empty-parent hierarchy over a set of objects, with optional "
            "nested child groups. Call this after any multi-part build -- never leave loose objects at scene root."
        ),
    )
    async def organize_scene_hierarchy(
        groups: list[dict],
        keep_transform: bool = True,
        rename_members: bool = False,
    ) -> dict:
        params = OrganizeSceneHierarchyParams(
            groups=groups,
            keep_transform=keep_transform,
            rename_members=rename_members,
        )
        result = await bridge.send_request("organize_scene_hierarchy", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "organize_scene_hierarchy failed"))
        return result

    return organize_scene_hierarchy
