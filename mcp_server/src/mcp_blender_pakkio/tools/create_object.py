from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

ObjectType = Literal[
    "CUBE",
    "UV_SPHERE",
    "ICO_SPHERE",
    "CYLINDER",
    "CONE",
    "PLANE",
    "TORUS",
    "GRID",
    "MONKEY",
    "CIRCLE",
    "EMPTY",
    "CAMERA",
    "LIGHT",
    "TEXT",
    "CURVE_BEZIER",
    "CURVE_CIRCLE",
]
LightType = Literal["POINT", "SUN", "SPOT", "AREA"]


class CreateObjectParams(BaseModel):
    object_type: ObjectType = "CUBE"
    name: Optional[str] = None
    location: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_euler: Optional[tuple[float, float, float]] = None
    scale: Optional[tuple[float, float, float]] = None
    collection: Optional[str] = None
    radius: Optional[float] = None
    size: Optional[float] = None
    light_type: Optional[LightType] = "POINT"
    light_energy: Optional[float] = 1000.0
    light_color: Optional[tuple[float, float, float]] = None
    text_body: Optional[str] = None
    text_extrude: Optional[float] = 0.0


def register_create_object_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_object",
        description="Create mesh primitives (CUBE, UV_SPHERE, ICO_SPHERE, CYLINDER, CONE, PLANE, TORUS, GRID, MONKEY, CIRCLE), EMPTY, CAMERA, LIGHT, TEXT, or CURVE objects in the scene.",
    )
    async def create_object(
        object_type: ObjectType = "CUBE",
        name: Optional[str] = None,
        location: tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation_euler: Optional[tuple[float, float, float]] = None,
        scale: Optional[tuple[float, float, float]] = None,
        collection: Optional[str] = None,
        radius: Optional[float] = None,
        size: Optional[float] = None,
        light_type: Optional[LightType] = "POINT",
        light_energy: Optional[float] = 1000.0,
        light_color: Optional[tuple[float, float, float]] = None,
        text_body: Optional[str] = None,
        text_extrude: Optional[float] = 0.0,
    ) -> dict:
        params = CreateObjectParams(
            object_type=object_type,
            name=name,
            location=location,
            rotation_euler=rotation_euler,
            scale=scale,
            collection=collection,
            radius=radius,
            size=size,
            light_type=light_type,
            light_energy=light_energy,
            light_color=light_color,
            text_body=text_body,
            text_extrude=text_extrude,
        )
        result = await bridge.send_request("create_object", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_object failed"))
        return result

    return create_object
