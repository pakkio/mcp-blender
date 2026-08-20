from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

LatticeDeformType = Literal["SQUASH_AND_STRETCH", "TAPER", "BEND"]


class CreateLatticeDeformParams(BaseModel):
    target_object: str
    u_resolution: int = 3
    v_resolution: int = 3
    w_resolution: int = 3
    padding: float = 0.1


class DeformLatticePointsParams(BaseModel):
    lattice_name: str
    deformation: LatticeDeformType = "SQUASH_AND_STRETCH"
    factor: float = 0.3


def register_lattice_deform_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="create_lattice_deform",
        description="Create a 3D bounding Lattice cage around a target object with custom U/V/W resolution and automatically bind it with a Lattice Modifier.",
    )
    async def create_lattice_deform(
        target_object: str,
        u_resolution: int = 3,
        v_resolution: int = 3,
        w_resolution: int = 3,
        padding: float = 0.1,
    ) -> dict:
        params = CreateLatticeDeformParams(
            target_object=target_object,
            u_resolution=u_resolution,
            v_resolution=v_resolution,
            w_resolution=w_resolution,
            padding=padding,
        )
        result = await bridge.send_request("create_lattice_deform", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "create_lattice_deform failed"))
        return result

    @mcp.tool(
        name="deform_lattice_points",
        description="Apply procedural deformations (SQUASH_AND_STRETCH, BEND, TAPER, TWIST) or move specific control points on a Lattice object.",
    )
    async def deform_lattice_points(
        lattice_name: str,
        deformation: LatticeDeformType = "SQUASH_AND_STRETCH",
        factor: float = 0.3,
    ) -> dict:
        params = DeformLatticePointsParams(
            lattice_name=lattice_name,
            deformation=deformation,
            factor=factor,
        )
        result = await bridge.send_request("deform_lattice_points", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "deform_lattice_points failed"))
        return result

    return create_lattice_deform, deform_lattice_points
