from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class GetSceneInfoParams(BaseModel):
    include_objects: bool = True
    include_collections: bool = True
    include_materials: bool = True
    include_lights: bool = True
    include_cameras: bool = True
    include_hierarchy: bool = False


def register_get_scene_info_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="get_scene_info",
        description="Get comprehensive information about the active Blender scene (objects, collections, materials, lights, cameras, timeline, render settings). "
        "Pass include_hierarchy=True to also get parent/child and collection-membership data -- call this before organize_scene_hierarchy or after a multi-part build to check nothing is left ungrouped.",
    )
    async def get_scene_info(
        include_objects: bool = True,
        include_collections: bool = True,
        include_materials: bool = True,
        include_lights: bool = True,
        include_cameras: bool = True,
        include_hierarchy: bool = False,
    ) -> dict:
        params = GetSceneInfoParams(
            include_objects=include_objects,
            include_collections=include_collections,
            include_materials=include_materials,
            include_lights=include_lights,
            include_cameras=include_cameras,
            include_hierarchy=include_hierarchy,
        )
        result = await bridge.send_request("get_scene_info", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "get_scene_info failed"))
        return result

    return get_scene_info
