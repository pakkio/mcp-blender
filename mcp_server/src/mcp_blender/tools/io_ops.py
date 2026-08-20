from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

ExportFormat = Literal["GLTF", "GLB", "FBX", "OBJ", "STL", "USD"]
ImportFormat = Literal["GLTF", "GLB", "FBX", "OBJ", "STL", "USD", "BLEND"]
Axis = Literal["X", "Y", "Z", "-X", "-Y", "-Z"]

AXIS_HELP = (
    "Axis convention OF THE SOURCE FILE (Blender itself is -Y forward / Z up). Leave unset to use "
    "the importer default. Set up_axis='Y' when a model imports lying on its side — the usual cause "
    "is a Y-up file (Maya, Unity, 3ds Max exports, most STL) that carries no axis metadata. "
    "Supplying only one axis fills in the conventional partner. glTF/GLB and USD self-describe their "
    "orientation and normally need nothing here."
)


class ExportSceneParams(BaseModel):
    filepath: str
    file_format: ExportFormat = "GLB"
    selected_only: bool = False
    apply_modifiers: bool = True
    export_materials: bool = True
    export_animations: bool = True


class ImportFileParams(BaseModel):
    filepath: str
    file_format: Optional[ImportFormat] = None
    forward_axis: Optional[Axis] = None
    up_axis: Optional[Axis] = None
    check_orientation: bool = True
    auto_orient: bool = False


def register_io_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="export_scene",
        description="Export the active Blender scene or selected objects to 3D file formats (GLTF, GLB, FBX, OBJ, STL, USD).",
    )
    async def export_scene(
        filepath: str,
        file_format: ExportFormat = "GLB",
        selected_only: bool = False,
        apply_modifiers: bool = True,
        export_materials: bool = True,
        export_animations: bool = True,
    ) -> dict:
        params = ExportSceneParams(
            filepath=filepath,
            file_format=file_format,
            selected_only=selected_only,
            apply_modifiers=apply_modifiers,
            export_materials=export_materials,
            export_animations=export_animations,
        )
        result = await bridge.send_request("export_scene", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "export_scene failed"))
        return result

    @mcp.tool(
        name="import_file",
        description=(
            "Import 3D model files (GLTF, GLB, FBX, OBJ, STL, USD, BLEND) into the current Blender scene. "
            + AXIS_HELP
            + " The result always includes an 'orientation' report measured from the imported geometry "
            "(mass distribution and base-vs-top footprint); pass auto_orient=true to rotate a model that "
            "lands upside down or on its side back upright."
        ),
    )
    async def import_file(
        filepath: str,
        file_format: Optional[ImportFormat] = None,
        forward_axis: Optional[Axis] = None,
        up_axis: Optional[Axis] = None,
        check_orientation: bool = True,
        auto_orient: bool = False,
    ) -> dict:
        params = ImportFileParams(
            filepath=filepath,
            file_format=file_format,
            forward_axis=forward_axis,
            up_axis=up_axis,
            check_orientation=check_orientation,
            auto_orient=auto_orient,
        )
        result = await bridge.send_request("import_file", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "import_file failed"))
        return result

    return export_scene, import_file
