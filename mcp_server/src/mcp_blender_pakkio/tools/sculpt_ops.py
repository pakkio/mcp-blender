from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

SculptAction = Literal["ENTER", "EXIT", "TOGGLE"]
SculptFilterType = Literal[
    "SMOOTH",
    "SCALE",
    "INFLATE",
    "SPHERE",
    "RANDOM",
    "RELAX",
    "RELAX_FACE_SETS",
    "SURFACE_SMOOTH",
    "SHARPEN",
    "ENHANCE_DETAILS",
    "ERASE_DISPLACEMENT",
]
MaskAction = Literal[
    "CLEAR_MASK",
    "INVERT_MASK",
    "SMOOTH_MASK",
    "INIT_FACE_SETS_BY_LOOSE_PARTS",
    "INIT_FACE_SETS_BY_MATERIALS",
    "CREATE_FACE_SET_FROM_MASK",
]


class ConfigureSculptModeParams(BaseModel):
    object_name: Optional[str] = None
    action: SculptAction = "ENTER"
    brush_type: Optional[str] = None
    brush_size: Optional[float] = None
    brush_strength: Optional[float] = None
    use_symmetry_x: Optional[bool] = None
    use_symmetry_y: Optional[bool] = None
    use_symmetry_z: Optional[bool] = None
    use_dyntopo: Optional[bool] = None
    dyntopo_detail: Optional[float] = None
    dyntopo_detail_type: Literal["RELATIVE", "CONSTANT", "BRUSH", "MANUAL"] = "RELATIVE"


class ApplySculptFilterParams(BaseModel):
    object_name: Optional[str] = None
    filter_type: SculptFilterType = "SMOOTH"
    strength: float = 0.5
    iterations: int = 1
    deform_axis: Literal["XYZ", "X", "Y", "Z"] = "XYZ"


class SculptMaskFaceSetsParams(BaseModel):
    object_name: Optional[str] = None
    action: MaskAction = "CLEAR_MASK"


def register_sculpt_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="configure_sculpt_mode",
        description="Enter/exit Sculpt Mode, select sculpting brushes (Draw, Clay, Clay Strips, Crease, Smooth, Flatten, Grab, Snake Hook, Elastic Deform, Pinch, Cloth, Scrape), configure brush radius/strength, symmetry, and dynamic topology (Dyntopo).",
    )
    async def configure_sculpt_mode(
        object_name: Optional[str] = None,
        action: SculptAction = "ENTER",
        brush_type: Optional[str] = None,
        brush_size: Optional[float] = None,
        brush_strength: Optional[float] = None,
        use_symmetry_x: Optional[bool] = None,
        use_symmetry_y: Optional[bool] = None,
        use_symmetry_z: Optional[bool] = None,
        use_dyntopo: Optional[bool] = None,
        dyntopo_detail: Optional[float] = None,
        dyntopo_detail_type: Literal["RELATIVE", "CONSTANT", "BRUSH", "MANUAL"] = "RELATIVE",
    ) -> dict:
        params = ConfigureSculptModeParams(
            object_name=object_name,
            action=action,
            brush_type=brush_type,
            brush_size=brush_size,
            brush_strength=brush_strength,
            use_symmetry_x=use_symmetry_x,
            use_symmetry_y=use_symmetry_y,
            use_symmetry_z=use_symmetry_z,
            use_dyntopo=use_dyntopo,
            dyntopo_detail=dyntopo_detail,
            dyntopo_detail_type=dyntopo_detail_type,
        )
        result = await bridge.send_request("configure_sculpt_mode", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_sculpt_mode failed"))
        return result

    @mcp.tool(
        name="apply_sculpt_filter",
        description="Apply full-mesh sculpt deformation filters (SMOOTH, SCALE, INFLATE, SPHERE, RANDOM, RELAX, RELAX_FACE_SETS, SURFACE_SMOOTH, SHARPEN, ENHANCE_DETAILS).",
    )
    async def apply_sculpt_filter(
        object_name: Optional[str] = None,
        filter_type: SculptFilterType = "SMOOTH",
        strength: float = 0.5,
        iterations: int = 1,
        deform_axis: Literal["XYZ", "X", "Y", "Z"] = "XYZ",
    ) -> dict:
        params = ApplySculptFilterParams(
            object_name=object_name,
            filter_type=filter_type,
            strength=strength,
            iterations=iterations,
            deform_axis=deform_axis,
        )
        result = await bridge.send_request("apply_sculpt_filter", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "apply_sculpt_filter failed"))
        return result

    @mcp.tool(
        name="sculpt_mask_facesets",
        description="Manage sculpt masks and Face Sets (CLEAR_MASK, INVERT_MASK, SMOOTH_MASK, MASK_BY_CAVITY, INIT_FACE_SETS_BY_LOOSE_PARTS, INIT_FACE_SETS_BY_MATERIALS, CREATE_FACE_SET_FROM_MASK).",
    )
    async def sculpt_mask_facesets(
        object_name: Optional[str] = None,
        action: MaskAction = "CLEAR_MASK",
    ) -> dict:
        params = SculptMaskFaceSetsParams(
            object_name=object_name,
            action=action,
        )
        result = await bridge.send_request("sculpt_mask_facesets", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "sculpt_mask_facesets failed"))
        return result

    return configure_sculpt_mode, apply_sculpt_filter, sculpt_mask_facesets
