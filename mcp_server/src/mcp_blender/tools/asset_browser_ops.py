from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

AssetAction = Literal["ASSET_MARK", "ASSET_CLEAR", "MARK", "CLEAR"]
AssetType = Literal["OBJECT", "MATERIAL", "NODE_GROUP", "GEOMETRY_NODES", "WORLD", "ACTION"]


class ManageAssetBrowserParams(BaseModel):
    action: AssetAction = "ASSET_MARK"
    asset_type: AssetType = "OBJECT"
    target_name: str
    description: str = ""
    author: str = ""
    tags: list[str] = []


class GenerateAssetPreviewParams(BaseModel):
    target_name: str
    asset_type: AssetType = "OBJECT"
    custom_icon_path: Optional[str] = None


class ImportAssetLibraryParams(BaseModel):
    filepath: str
    asset_name: str
    asset_type: AssetType = "OBJECT"
    link: bool = False


def register_asset_browser_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="manage_asset_browser",
        description="Mark/unmark datablocks (objects, materials, node groups, worlds, actions) as Blender Assets, set catalog ID, description, author, and tags.",
    )
    async def manage_asset_browser(
        target_name: str,
        action: AssetAction = "ASSET_MARK",
        asset_type: AssetType = "OBJECT",
        description: str = "",
        author: str = "",
        tags: list[str] = [],
    ) -> dict:
        params = ManageAssetBrowserParams(
            action=action,
            asset_type=asset_type,
            target_name=target_name,
            description=description,
            author=author,
            tags=tags,
        )
        result = await bridge.send_request("manage_asset_browser", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "manage_asset_browser failed"))
        return result

    @mcp.tool(
        name="generate_asset_preview",
        description="Generate or load a custom thumbnail preview for an asset datablock.",
    )
    async def generate_asset_preview(
        target_name: str,
        asset_type: AssetType = "OBJECT",
        custom_icon_path: Optional[str] = None,
    ) -> dict:
        params = GenerateAssetPreviewParams(
            target_name=target_name,
            asset_type=asset_type,
            custom_icon_path=custom_icon_path,
        )
        result = await bridge.send_request("generate_asset_preview", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "generate_asset_preview failed"))
        return result

    @mcp.tool(
        name="import_asset_library",
        description="Append or link assets from an external .blend asset library file into the current scene.",
    )
    async def import_asset_library(
        filepath: str,
        asset_name: str,
        asset_type: AssetType = "OBJECT",
        link: bool = False,
    ) -> dict:
        params = ImportAssetLibraryParams(
            filepath=filepath,
            asset_name=asset_name,
            asset_type=asset_type,
            link=link,
        )
        result = await bridge.send_request("import_asset_library", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "import_asset_library failed"))
        return result

    return manage_asset_browser, generate_asset_preview, import_asset_library
