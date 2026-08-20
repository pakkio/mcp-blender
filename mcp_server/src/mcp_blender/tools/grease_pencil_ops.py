from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class SetupLineArtContourParams(BaseModel):
    source_type: str = Field("SCENE", description="SCENE | OBJECT | COLLECTION")
    target_object: Optional[str] = Field(None, description="Name of object if source_type is OBJECT")
    thickness: int = Field(3, description="Line thickness in pixels")
    use_crease: bool = Field(True, description="Detect sharp crease edges")


class CreateGreasePencilLayerParams(BaseModel):
    gp_object: Optional[str] = Field(None, description="Grease pencil object name")
    layer_name: str = Field("Lines", description="Name for the layer")
    color: list[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])
    use_lights: bool = Field(False, description="Whether layer responds to scene lights")


class DrawGreasePencilStrokesParams(BaseModel):
    gp_object: str = Field(..., description="Grease pencil object name")
    layer_name: str = Field("Lines", description="Layer name to draw into")
    strokes: list[dict] = Field(..., description="List of stroke dicts with points [[x,y,z], ...]")
    frame: int = Field(1, description="Frame number to insert the drawing")


def register_grease_pencil_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="setup_line_art_contour",
        description="Add cartoon / anime Line Art contour ink outlines around 3D objects or scene collections using Grease Pencil Line Art.",
    )
    async def setup_line_art_contour(
        source_type: str = "SCENE",
        target_object: Optional[str] = None,
        thickness: int = 3,
        use_crease: bool = True,
    ) -> dict:
        params = SetupLineArtContourParams(
            source_type=source_type,
            target_object=target_object,
            thickness=thickness,
            use_crease=use_crease,
        )
        result = await bridge.send_request("setup_line_art_contour", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_line_art_contour failed"))
        return result

    @mcp.tool(
        name="create_grease_pencil_layer",
        description="Create or configure a Grease Pencil / GPv3 drawing layer with color, line thickness, and blending properties.",
    )
    async def create_grease_pencil_layer(
        gp_object: Optional[str] = None,
        layer_name: str = "Lines",
        color: list[float] = [0.0, 0.0, 0.0, 1.0],
        use_lights: bool = False,
    ) -> dict:
        params = CreateGreasePencilLayerParams(
            gp_object=gp_object,
            layer_name=layer_name,
            color=color,
            use_lights=use_lights,
        )
        result = await bridge.send_request("create_grease_pencil_layer", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_grease_pencil_layer failed"))
        return result

    @mcp.tool(
        name="draw_grease_pencil_strokes",
        description="Draw procedural 2D/3D strokes into a Grease Pencil frame with point coordinates, pressure, and strength.",
    )
    async def draw_grease_pencil_strokes(
        gp_object: str,
        layer_name: str,
        strokes: list[dict],
        frame: int = 1,
    ) -> dict:
        params = DrawGreasePencilStrokesParams(
            gp_object=gp_object,
            layer_name=layer_name,
            strokes=strokes,
            frame=frame,
        )
        result = await bridge.send_request("draw_grease_pencil_strokes", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "draw_grease_pencil_strokes failed"))
        return result

    return (setup_line_art_contour, create_grease_pencil_layer, draw_grease_pencil_strokes)
