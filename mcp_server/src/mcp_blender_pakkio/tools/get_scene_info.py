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


def register_get_scene_info_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="get_scene_info",
        description="Get comprehensive information about the active Blender scene (objects, collections, materials, lights, cameras, timeline, render settings).",
    )
    async def get_scene_info(
        include_objects: bool = True,
        include_collections: bool = True,
        include_materials: bool = True,
        include_lights: bool = True,
        include_cameras: bool = True,
    ) -> dict:
        params = GetSceneInfoParams(
            include_objects=include_objects,
            include_collections=include_collections,
            include_materials=include_materials,
            include_lights=include_lights,
            include_cameras=include_cameras,
        )
        result = await bridge.send_request("get_scene_info", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "get_scene_info failed"))
        return result

    return get_scene_info
