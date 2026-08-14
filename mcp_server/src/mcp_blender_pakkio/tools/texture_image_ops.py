from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

AlphaMode = Literal["OPAQUE", "CLIP", "BLEND"]
ProjectionType = Literal["CAMERA", "DECAL_EMPTY", "UV_PROJECT"]


class ImportImageAsPlaneParams(BaseModel):
    image_path: str
    name: Optional[str] = None
    location: list[float] = [0.0, 0.0, 0.0]
    rotation_euler: list[float] = [0.0, 0.0, 0.0]
    height: float = 2.0
    emit_strength: float = 0.0
    alpha_mode: AlphaMode = "BLEND"


class ProjectImageTextureParams(BaseModel):
    target_object: str
    image_path: str
    projection_type: ProjectionType = "CAMERA"
    camera_name: Optional[str] = None
    empty_name: Optional[str] = None
    material_name: Optional[str] = None


def register_texture_image_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="import_image_as_plane",
        description="Import an image file as a textured 3D plane mesh with correct aspect ratio, material node graph, and alpha transparency.",
    )
    async def import_image_as_plane(
        image_path: str,
        name: Optional[str] = None,
        location: list[float] = [0.0, 0.0, 0.0],
        rotation_euler: list[float] = [0.0, 0.0, 0.0],
        height: float = 2.0,
        emit_strength: float = 0.0,
        alpha_mode: AlphaMode = "BLEND",
    ) -> dict:
        params = ImportImageAsPlaneParams(
            image_path=image_path,
            name=name,
            location=location,
            rotation_euler=rotation_euler,
            height=height,
            emit_strength=emit_strength,
            alpha_mode=alpha_mode,
        )
        result = await bridge.send_request("import_image_as_plane", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "import_image_as_plane failed"))
        return result

    @mcp.tool(
        name="project_image_texture",
        description="Project an image texture onto an object using camera projection or empty-driven decal projection mapping.",
    )
    async def project_image_texture(
        target_object: str,
        image_path: str,
        projection_type: ProjectionType = "CAMERA",
        camera_name: Optional[str] = None,
        empty_name: Optional[str] = None,
        material_name: Optional[str] = None,
    ) -> dict:
        params = ProjectImageTextureParams(
            target_object=target_object,
            image_path=image_path,
            projection_type=projection_type,
            camera_name=camera_name,
            empty_name=empty_name,
            material_name=material_name,
        )
        result = await bridge.send_request("project_image_texture", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "project_image_texture failed"))
        return result

    return import_image_as_plane, project_image_texture
