from typing import Any, Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

ModifierType = Literal[
    "SUBSURF",
    "BEVEL",
    "BOOLEAN",
    "MIRROR",
    "ARRAY",
    "SOLIDIFY",
    "REMESH",
    "DECIMATE",
    "CURVE",
    "DISPLACE",
    "SCREW",
    "SKIN",
    "NODES",
    "WEIGHTED_NORMAL",
    "TRIANGULATE",
    "WIREFRAME",
    "EDGE_SPLIT",
    "SMOOTH",
]


class AddModifierParams(BaseModel):
    object_name: str
    modifier_type: ModifierType
    name: Optional[str] = None
    properties: Optional[dict[str, Any]] = None


class ApplyModifierParams(BaseModel):
    object_name: str
    modifier_name: str


class RemoveModifierParams(BaseModel):
    object_name: str
    modifier_name: str


class SetModifierPropertiesParams(BaseModel):
    object_name: str
    modifier_name: str
    properties: dict[str, Any]


def register_modifier_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="add_modifier",
        description="Add a modifier to an object (SUBSURF, BEVEL, BOOLEAN, MIRROR, ARRAY, SOLIDIFY, REMESH, DECIMATE, etc.) with configurable initial properties.",
    )
    async def add_modifier(
        object_name: str,
        modifier_type: ModifierType,
        name: Optional[str] = None,
        properties: Optional[dict[str, Any]] = None,
    ) -> dict:
        params = AddModifierParams(
            object_name=object_name,
            modifier_type=modifier_type,
            name=name,
            properties=properties,
        )
        result = await bridge.send_request("add_modifier", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "add_modifier failed"))
        return result

    @mcp.tool(
        name="apply_modifier",
        description="Apply a modifier permanently to an object's geometry.",
    )
    async def apply_modifier(
        object_name: str,
        modifier_name: str,
    ) -> dict:
        params = ApplyModifierParams(object_name=object_name, modifier_name=modifier_name)
        result = await bridge.send_request("apply_modifier", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "apply_modifier failed"))
        return result

    @mcp.tool(
        name="remove_modifier",
        description="Remove a modifier from an object.",
    )
    async def remove_modifier(
        object_name: str,
        modifier_name: str,
    ) -> dict:
        params = RemoveModifierParams(object_name=object_name, modifier_name=modifier_name)
        result = await bridge.send_request("remove_modifier", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "remove_modifier failed"))
        return result

    @mcp.tool(
        name="set_modifier_properties",
        description="Update settings and parameters on an existing modifier.",
    )
    async def set_modifier_properties(
        object_name: str,
        modifier_name: str,
        properties: dict[str, Any],
    ) -> dict:
        params = SetModifierPropertiesParams(
            object_name=object_name,
            modifier_name=modifier_name,
            properties=properties,
        )
        result = await bridge.send_request("set_modifier_properties", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "set_modifier_properties failed"))
        return result

    return add_modifier, apply_modifier, remove_modifier, set_modifier_properties
