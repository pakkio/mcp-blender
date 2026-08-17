from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class CreateCheckpointParams(BaseModel):
    name: Optional[str] = Field(None, description="Optional name for the checkpoint snapshot")


class RestoreCheckpointParams(BaseModel):
    name: str = Field(..., description="Name of the checkpoint to restore")


def register_checkpoint_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_scene_checkpoint",
        description="Create a snapshot checkpoint of the current Blender scene state to disk that can be reverted to anytime.",
    )
    async def create_scene_checkpoint(name: Optional[str] = None) -> dict:
        params = CreateCheckpointParams(name=name)
        result = await bridge.send_request("create_scene_checkpoint", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_scene_checkpoint failed"))
        return result

    @mcp.tool(
        name="restore_scene_checkpoint",
        description="Restore the scene to a previously saved checkpoint snapshot.",
    )
    async def restore_scene_checkpoint(name: str) -> dict:
        params = RestoreCheckpointParams(name=name)
        result = await bridge.send_request("restore_scene_checkpoint", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "restore_scene_checkpoint failed"))
        return result

    @mcp.tool(
        name="list_scene_checkpoints",
        description="List all available scene checkpoints saved during this session.",
    )
    async def list_scene_checkpoints() -> dict:
        result = await bridge.send_request("list_scene_checkpoints", {})
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "list_scene_checkpoints failed"))
        return result

    return (create_scene_checkpoint, restore_scene_checkpoint, list_scene_checkpoints)
