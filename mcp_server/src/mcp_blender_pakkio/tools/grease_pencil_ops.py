from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

LineArtSource = Literal["SCENE", "OBJECT", "COLLECTION"]


class SetupLineArtContourParams(BaseModel):
    source_type: LineArtSource = "SCENE"
    target_object: Optional[str] = None
    thickness: int = 3
    use_crease: bool = True


def register_grease_pencil_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="setup_line_art_contour",
        description="Add cartoon / anime Line Art contour ink outlines around 3D objects or scene collections using Grease Pencil Line Art.",
    )
    async def setup_line_art_contour(
        source_type: LineArtSource = "SCENE",
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

    return setup_line_art_contour
