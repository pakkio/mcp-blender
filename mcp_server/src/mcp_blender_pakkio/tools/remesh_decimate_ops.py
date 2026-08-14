from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

DecimateMode = Literal["COLLAPSE", "UNSUBDIV", "PLANAR"]
RemeshMode = Literal["VOXEL", "SHARP", "SMOOTH", "BLOCKS"]


class DecimateMeshParams(BaseModel):
    object_name: str
    mode: DecimateMode = "COLLAPSE"
    ratio: float = 0.5
    iterations: int = 2
    angle_limit: float = 5.0
    use_symmetry: bool = False
    symmetry_axis: Literal["X", "Y", "Z"] = "X"
    apply_immediately: bool = True


class RemeshMeshParams(BaseModel):
    object_name: str
    mode: RemeshMode = "VOXEL"
    voxel_size: float = 0.05
    adaptivity: float = 0.0
    octree_depth: int = 4
    scale: float = 0.9
    smooth_shading: bool = True
    apply_immediately: bool = True


def register_remesh_decimate_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="decimate_mesh",
        description="Decimate/reduce polygon count of a mesh using COLLAPSE (ratio), UNSUBDIVIDE (iterations), or PLANAR (angle limit) algorithms.",
    )
    async def decimate_mesh(
        object_name: str,
        mode: DecimateMode = "COLLAPSE",
        ratio: float = 0.5,
        iterations: int = 2,
        angle_limit: float = 5.0,
        use_symmetry: bool = False,
        symmetry_axis: Literal["X", "Y", "Z"] = "X",
        apply_immediately: bool = True,
    ) -> dict:
        params = DecimateMeshParams(
            object_name=object_name,
            mode=mode,
            ratio=ratio,
            iterations=iterations,
            angle_limit=angle_limit,
            use_symmetry=use_symmetry,
            symmetry_axis=symmetry_axis,
            apply_immediately=apply_immediately,
        )
        result = await bridge.send_request("decimate_mesh", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "decimate_mesh failed"))
        return result

    @mcp.tool(
        name="remesh_mesh",
        description="Remesh geometry using modern VOXEL remesher or modifier-based remeshing (SHARP, SMOOTH, BLOCKS).",
    )
    async def remesh_mesh(
        object_name: str,
        mode: RemeshMode = "VOXEL",
        voxel_size: float = 0.05,
        adaptivity: float = 0.0,
        octree_depth: int = 4,
        scale: float = 0.9,
        smooth_shading: bool = True,
        apply_immediately: bool = True,
    ) -> dict:
        params = RemeshMeshParams(
            object_name=object_name,
            mode=mode,
            voxel_size=voxel_size,
            adaptivity=adaptivity,
            octree_depth=octree_depth,
            scale=scale,
            smooth_shading=smooth_shading,
            apply_immediately=apply_immediately,
        )
        result = await bridge.send_request("remesh_mesh", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "remesh_mesh failed"))
        return result

    return decimate_mesh, remesh_mesh
