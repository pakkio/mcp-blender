from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class ExportUnityFBXParams(BaseModel):
    filepath: str
    selected_only: bool = False
    bake_anim: bool = True
    apply_modifiers: bool = True
    embed_textures: bool = False


class GenerateLODsParams(BaseModel):
    object_name: str
    ratios: list[float] = [1.0, 0.5, 0.25, 0.1]
    group_name: Optional[str] = None


def register_pipeline_export_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="export_unity_fbx",
        description="Export models/rigs/animations specifically tailored for Unity (fixes -90 degree axis rotation bug, strips leaf bones, bakes unit scales, embeds textures).",
    )
    async def export_unity_fbx(
        filepath: str,
        selected_only: bool = False,
        bake_anim: bool = True,
        apply_modifiers: bool = True,
        embed_textures: bool = False,
    ) -> dict:
        params = ExportUnityFBXParams(
            filepath=filepath,
            selected_only=selected_only,
            bake_anim=bake_anim,
            apply_modifiers=apply_modifiers,
            embed_textures=embed_textures,
        )
        result = await bridge.send_request("export_unity_fbx", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "export_unity_fbx failed"))
        return result

    @mcp.tool(
        name="generate_lods",
        description="Automatically generate a multi-level Level of Detail (LOD0..LODn) hierarchy with polygon reduction for game engines.",
    )
    async def generate_lods(
        object_name: str,
        ratios: list[float] = [1.0, 0.5, 0.25, 0.1],
        group_name: Optional[str] = None,
    ) -> dict:
        params = GenerateLODsParams(
            object_name=object_name,
            ratios=ratios,
            group_name=group_name,
        )
        result = await bridge.send_request("generate_lods", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "generate_lods failed"))
        return result

    return export_unity_fbx, generate_lods
