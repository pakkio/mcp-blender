from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class ProximityInteractionParams(BaseModel):
    target_object: str
    source_object: str
    max_distance: float = 2.0
    effect_type: str = "SCALE_DOWN"


class CurveProfileMeshParams(BaseModel):
    curve_object: str
    profile_type: str = "CIRCLE"
    radius: float = 0.1
    fill_caps: bool = True


class VolumeMeshBooleansGNParams(BaseModel):
    target_object: str
    voxel_amount: float = 64.0
    threshold: float = 0.1
    adaptivity: float = 0.0


def register_advanced_geom_nodes_studio_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="setup_geometry_proximity_interaction",
        description="Setup a Geometry Nodes proximity network (GeometryNodeGeometryProximity / Raycast) where target geometry reacts, deforms, or scales based on distance to another object.",
    )
    async def setup_geometry_proximity_interaction(
        target_object: str,
        source_object: str,
        max_distance: float = 2.0,
        effect_type: str = "SCALE_DOWN",
    ) -> dict:
        params = ProximityInteractionParams(
            target_object=target_object,
            source_object=source_object,
            max_distance=max_distance,
            effect_type=effect_type,
        )
        result = await bridge.send_request("setup_geometry_proximity_interaction", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "setup_geometry_proximity_interaction failed"))
        return result

    @mcp.tool(
        name="curve_to_profile_mesh",
        description="Sweep a procedural curve profile (Circle, Rectangle, Star, Line) along a curve with automatic caps and UV unwrap in Geometry Nodes.",
    )
    async def curve_to_profile_mesh(
        curve_object: str,
        profile_type: str = "CIRCLE",
        radius: float = 0.1,
        fill_caps: bool = True,
    ) -> dict:
        params = CurveProfileMeshParams(
            curve_object=curve_object,
            profile_type=profile_type,
            radius=radius,
            fill_caps=fill_caps,
        )
        result = await bridge.send_request("curve_to_profile_mesh", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "curve_to_profile_mesh failed"))
        return result

    @mcp.tool(
        name="volume_mesh_booleans_gn",
        description="Procedural OpenVDB volume meshing and smooth organic blending inside Geometry Nodes (Mesh to Volume -> Volume to Mesh).",
    )
    async def volume_mesh_booleans_gn(
        target_object: str,
        voxel_amount: float = 64.0,
        threshold: float = 0.1,
        adaptivity: float = 0.0,
    ) -> dict:
        params = VolumeMeshBooleansGNParams(
            target_object=target_object,
            voxel_amount=voxel_amount,
            threshold=threshold,
            adaptivity=adaptivity,
        )
        result = await bridge.send_request("volume_mesh_booleans_gn", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "volume_mesh_booleans_gn failed"))
        return result

    return (
        setup_geometry_proximity_interaction,
        curve_to_profile_mesh,
        volume_mesh_booleans_gn,
    )
