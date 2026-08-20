from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

ShadingType = Literal["WIREFRAME", "SOLID", "MATERIAL", "RENDERED"]
ColorType = Literal["MATERIAL", "SINGLE", "OBJECT", "RANDOM", "VERTEX", "TEXTURE"]
CleanupAction = Literal["PURGE_ORPHANS", "PACK_ALL_LIBRARIES", "UNPACK_ALL_LIBRARIES"]
AlignAction = Literal[
    "ALIGN_X",
    "ALIGN_Y",
    "ALIGN_Z",
    "ALIGN_CENTERS",
    "DISTRIBUTE_GRID",
    "DISTRIBUTE_LINEAR",
    "SNAP_TO_GROUND",
]


class ConfigureViewportDisplayParams(BaseModel):
    shading_type: Optional[ShadingType] = None
    color_type: Optional[ColorType] = None
    show_cavity: Optional[bool] = None
    show_shadows: Optional[bool] = None
    show_wireframe: Optional[bool] = None
    show_face_orientation: Optional[bool] = None
    show_stats: Optional[bool] = None
    matcap_name: Optional[str] = None


class PurgeOrphansAndCleanupParams(BaseModel):
    action: CleanupAction = "PURGE_ORPHANS"
    num_passes: int = 3


class AlignDistributeObjectsParams(BaseModel):
    object_names: Optional[list[str]] = None
    action: AlignAction = "ALIGN_X"
    spacing: float = 2.0
    grid_columns: int = 3
    axis: Literal["X", "Y", "Z"] = "X"


def register_viewport_scene_advanced_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="configure_viewport_display",
        description="Control 3D Viewport shading mode (SOLID, MATERIAL, RENDERED, WIREFRAME), studio lighting/matcaps, cavity/shadows, and overlays (face orientation normal check, wireframe, scene statistics).",
    )
    async def configure_viewport_display(
        shading_type: Optional[ShadingType] = None,
        color_type: Optional[ColorType] = None,
        show_cavity: Optional[bool] = None,
        show_shadows: Optional[bool] = None,
        show_wireframe: Optional[bool] = None,
        show_face_orientation: Optional[bool] = None,
        show_stats: Optional[bool] = None,
        matcap_name: Optional[str] = None,
    ) -> dict:
        params = ConfigureViewportDisplayParams(
            shading_type=shading_type,
            color_type=color_type,
            show_cavity=show_cavity,
            show_shadows=show_shadows,
            show_wireframe=show_wireframe,
            show_face_orientation=show_face_orientation,
            show_stats=show_stats,
            matcap_name=matcap_name,
        )
        result = await bridge.send_request("configure_viewport_display", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_viewport_display failed"))
        return result

    @mcp.tool(
        name="purge_orphans_and_cleanup",
        description="Purge unused orphan datablocks (materials, meshes, textures, node groups, actions) and manage packed file resources.",
    )
    async def purge_orphans_and_cleanup(
        action: CleanupAction = "PURGE_ORPHANS",
        num_passes: int = 3,
    ) -> dict:
        params = PurgeOrphansAndCleanupParams(
            action=action,
            num_passes=num_passes,
        )
        result = await bridge.send_request("purge_orphans_and_cleanup", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "purge_orphans_and_cleanup failed"))
        return result

    @mcp.tool(
        name="align_distribute_objects",
        description="Align, distribute in 3D grid/linear patterns, or snap objects down to ground level (Z=0).",
    )
    async def align_distribute_objects(
        object_names: Optional[list[str]] = None,
        action: AlignAction = "ALIGN_X",
        spacing: float = 2.0,
        grid_columns: int = 3,
        axis: Literal["X", "Y", "Z"] = "X",
    ) -> dict:
        params = AlignDistributeObjectsParams(
            object_names=object_names,
            action=action,
            spacing=spacing,
            grid_columns=grid_columns,
            axis=axis,
        )
        result = await bridge.send_request("align_distribute_objects", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "align_distribute_objects failed"))
        return result

    return configure_viewport_display, purge_orphans_and_cleanup, align_distribute_objects
