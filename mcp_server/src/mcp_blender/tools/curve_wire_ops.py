from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class CreateCurveCableParams(BaseModel):
    name: str = "CableWire"
    start_point: list[float] = [-2.0, 0.0, 3.0]
    end_point: list[float] = [2.0, 0.0, 3.0]
    sag: float = 0.8
    radius: float = 0.04
    resolution: int = 12


class ConvertMeshToCurveParams(BaseModel):
    object_name: str
    bevel_depth: float = 0.03
    extrude: float = 0.0


class EditCurvePointsParams(BaseModel):
    curve_name: str
    points: list[dict] = []
    bevel_depth: Optional[float] = None


def register_curve_wire_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_curve_cable",
        description="Procedurally create electrical cables, wires, pipes, or neon tubes between two points with gravity sag, bevel depth, and resolution.",
    )
    async def create_curve_cable(
        name: str = "CableWire",
        start_point: list[float] = [-2.0, 0.0, 3.0],
        end_point: list[float] = [2.0, 0.0, 3.0],
        sag: float = 0.8,
        radius: float = 0.04,
        resolution: int = 12,
    ) -> dict:
        params = CreateCurveCableParams(
            name=name,
            start_point=start_point,
            end_point=end_point,
            sag=sag,
            radius=radius,
            resolution=resolution,
        )
        result = await bridge.send_request("create_curve_cable", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_curve_cable failed"))
        return result

    @mcp.tool(
        name="convert_mesh_to_curve",
        description="Convert mesh edges into 3D curves with automatic bevel depth for neon tubing, railings, or wireframes.",
    )
    async def convert_mesh_to_curve(
        object_name: str,
        bevel_depth: float = 0.03,
        extrude: float = 0.0,
    ) -> dict:
        params = ConvertMeshToCurveParams(
            object_name=object_name,
            bevel_depth=bevel_depth,
            extrude=extrude,
        )
        result = await bridge.send_request("convert_mesh_to_curve", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "convert_mesh_to_curve failed"))
        return result

    @mcp.tool(
        name="edit_curve_points",
        description="Add or modify control points, handles, radius, and tilt on Bezier and Poly splines.",
    )
    async def edit_curve_points(
        curve_name: str,
        points: list[dict] = [],
        bevel_depth: Optional[float] = None,
    ) -> dict:
        params = EditCurvePointsParams(
            curve_name=curve_name,
            points=points,
            bevel_depth=bevel_depth,
        )
        result = await bridge.send_request("edit_curve_points", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "edit_curve_points failed"))
        return result

    return create_curve_cable, convert_mesh_to_curve, edit_curve_points
