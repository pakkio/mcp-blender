from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, model_validator

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class DeleteObjectParams(BaseModel):
    name: Optional[str] = None
    names: Optional[list[str]] = None
    delete_hierarchy: bool = False

    @model_validator(mode="after")
    def check_name_or_names(self):
        if not self.name and not self.names:
            raise ValueError("Either 'name' or 'names' must be provided")
        return self


def register_delete_object_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="delete_object",
        description="Delete one or more objects from the scene by name, with optional hierarchy deletion.",
    )
    async def delete_object(
        name: Optional[str] = None,
        names: Optional[list[str]] = None,
        delete_hierarchy: bool = False,
    ) -> dict:
        params = DeleteObjectParams(name=name, names=names, delete_hierarchy=delete_hierarchy)
        result = await bridge.send_request("delete_object", params.model_dump(exclude_none=True))
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "delete_object failed"))
        return result

    return delete_object
