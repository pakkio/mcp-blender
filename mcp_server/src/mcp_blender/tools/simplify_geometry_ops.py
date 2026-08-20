from typing import Literal, Optional

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import HEAVY_REQUEST_TIMEOUT_S, BlenderBridge
from ..errors import BridgeError, ErrorType

TargetUnit = Literal["VERTICES", "TRIANGLES"]
Preset = Literal["BACKGROUND", "HERO", "MAX"]


class SimplifyGeometryParams(BaseModel):
    object_name: str
    target: Optional[int] = None
    target_unit: TargetUnit = "VERTICES"
    preset: Optional[Preset] = None
    repair: bool = True
    weld_factor: float = 0.0001
    preserve_uv: bool = True
    preserve_boundaries: bool = True
    sharp_angle: float = 3.0
    tolerance: float = 0.05
    use_symmetry: bool = False
    symmetry_axis: Literal["X", "Y", "Z"] = "X"
    max_deviation_pct: float = 2.0
    allow_new_holes: int = 0
    rollback_on_failure: bool = True
    dry_run: bool = False


def register_simplify_geometry_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="simplify_geometry",
        description=(
            "Reduce a mesh to a vertex budget (target or preset: BACKGROUND=10k, HERO=30k, MAX=100k) while "
            "preserving its form. Prefer this over decimate_mesh for imported/downloaded assets: it repairs the "
            "mesh first (welds coincident vertices, drops loose geometry, closes pinhole gaps -- imported meshes "
            "are usually not the welded manifold mesh decimate_mesh assumes, which is why decimate_mesh produces "
            "holes and torn topology on them), spends the vertex budget on flat/dense regions first via limited "
            "dissolve, then curvature-weighted collapse to protect thin features and boundaries. Measures the "
            "result (two-sided surface deviation, new-hole count) and rolls back to the original mesh rather than "
            "returning a broken result if the quality gate fails -- the response then includes a suggested_retry_target. "
            "Set dry_run=true to see the analysis and estimated ratio without changing anything."
        ),
    )
    async def simplify_geometry(
        object_name: str,
        target: Optional[int] = None,
        target_unit: TargetUnit = "VERTICES",
        preset: Optional[Preset] = None,
        repair: bool = True,
        weld_factor: float = 0.0001,
        preserve_uv: bool = True,
        preserve_boundaries: bool = True,
        sharp_angle: float = 3.0,
        tolerance: float = 0.05,
        use_symmetry: bool = False,
        symmetry_axis: Literal["X", "Y", "Z"] = "X",
        max_deviation_pct: float = 2.0,
        allow_new_holes: int = 0,
        rollback_on_failure: bool = True,
        dry_run: bool = False,
    ) -> dict:
        params = SimplifyGeometryParams(
            object_name=object_name,
            target=target,
            target_unit=target_unit,
            preset=preset,
            repair=repair,
            weld_factor=weld_factor,
            preserve_uv=preserve_uv,
            preserve_boundaries=preserve_boundaries,
            sharp_angle=sharp_angle,
            tolerance=tolerance,
            use_symmetry=use_symmetry,
            symmetry_axis=symmetry_axis,
            max_deviation_pct=max_deviation_pct,
            allow_new_holes=allow_new_holes,
            rollback_on_failure=rollback_on_failure,
            dry_run=dry_run,
        )
        result = await bridge.send_request("simplify_geometry", params.model_dump(), timeout=HEAVY_REQUEST_TIMEOUT_S)
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "simplify_geometry failed"))
        return result

    return (simplify_geometry,)
