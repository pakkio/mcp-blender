from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class DuplicateObjectParams(BaseModel):
    name: str
    new_name: Optional[str] = None
    linked: bool = False
    offset: tuple[float, float, float] = (0.0, 0.0, 0.0)
    collection: Optional[str] = None


def register_duplicate_object_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="duplicate_object",
        description="Duplicate an existing object (linked data or full copy) with optional position offset, new name, and destination collection.",
    )
    async def duplicate_object(
        name: str,
        new_name: Optional[str] = None,
        linked: bool = False,
        offset: tuple[float, float, float] = (0.0, 0.0, 0.0),
        collection: Optional[str] = None,
    ) -> dict:
        params = DuplicateObjectParams(
            name=name,
            new_name=new_name,
            linked=linked,
            offset=offset,
            collection=collection,
        )
        result = await bridge.send_request("duplicate_object", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "duplicate_object failed"))
        return result

    return duplicate_object
