"""bpy-free arithmetic for simplify_geometry: target resolution, budget
distribution, the ratio solver, and the quality gate. Kept separate from
simplify_geometry_ops.py (which does the actual bmesh/bpy work) so this half
is unit-testable outside Blender, the same split used by axis_utils.py.
"""

PRESETS = {
    "BACKGROUND": 10_000,
    "HERO": 30_000,
    "MAX": 100_000,
}


def resolve_target_vertices(target=None, target_unit="VERTICES", preset=None, current_verts=0, current_tris=0):
    """Resolve target/target_unit/preset into a single target vertex count.

    Returns (target_vertices, error). TRIANGLES targets are converted using
    the mesh's current tris-per-vertex ratio, since Decimate's own ratio
    parameter is face-based but the budget callers care about is vertices.
    """
    if preset is not None:
        key = str(preset).upper()
        if key not in PRESETS:
            return None, f"Unknown preset '{preset}'; expected one of {list(PRESETS)}"
        return PRESETS[key], None

    if target is None:
        return None, "One of 'target' or 'preset' is required"

    target = int(target)
    if target <= 0:
        return None, f"'target' must be positive, got {target}"

    unit = str(target_unit).upper()
    if unit == "VERTICES":
        return target, None
    if unit == "TRIANGLES":
        if current_tris <= 0 or current_verts <= 0:
            return None, "Cannot convert a TRIANGLES target without a positive current triangle/vertex count"
        verts_per_tri = current_verts / current_tris
        return max(4, round(target * verts_per_tri)), None
    return None, f"Unknown target_unit '{target_unit}'; expected VERTICES or TRIANGLES"


def distribute_vertex_budget(object_vertex_counts, total_target_vertices):
    """Split a total vertex budget across objects proportional to their
    current vertex count, so a 10-vert prop doesn't get the same target as
    the 50k-vert hero mesh sitting next to it in a multi-part import.

    Every object gets at least 4 vertices (the minimum for a mesh to exist).
    Rounding remainder goes to the largest object so the total matches exactly.
    """
    total_current = sum(object_vertex_counts.values())
    if total_current <= 0 or total_target_vertices <= 0:
        return {name: 0 for name in object_vertex_counts}

    result = {}
    for name, count in object_vertex_counts.items():
        share = round(total_target_vertices * count / total_current)
        result[name] = max(4, share)

    drift = total_target_vertices - sum(result.values())
    if drift and result:
        largest = max(result, key=lambda name: object_vertex_counts[name])
        result[largest] = max(4, result[largest] + drift)

    return result


def estimate_initial_ratio(current_verts, current_faces, target_verts):
    """First guess at Decimate's face ratio for a vertex target.

    Ratio is face-based but vertex and face counts track closely on a
    triangulated mesh, so vertices/current_verts is a good starting point;
    the secant step below corrects for the mesh-specific relationship.
    """
    if current_verts <= 0 or current_faces <= 0:
        return 1.0
    ratio = target_verts / current_verts
    return max(0.0001, min(1.0, ratio))


def secant_next_ratio(r1, v1, r2, v2, target_verts):
    """Next ratio guess from two (ratio -> resulting vertex count) samples.

    Falls back to a bisection-style nudge when the two samples produced the
    same vertex count (a flat region, e.g. both ratios already hit the
    modifier's minimum), since secant's division would be undefined there.
    """
    if v1 == v2:
        nudge = 0.1 if target_verts > v1 else -0.1
        return max(0.0001, min(1.0, r2 + nudge))
    slope = (r2 - r1) / (v2 - v1)
    next_ratio = r2 + slope * (target_verts - v2)
    return max(0.0001, min(1.0, next_ratio))


def within_tolerance(result_verts, target_verts, tolerance=0.05):
    if target_verts <= 0:
        return False
    return abs(result_verts - target_verts) / target_verts <= tolerance


def evaluate_quality_gate(deviation_max_pct, new_boundary_edges, max_deviation_pct=2.0, allow_new_holes=0):
    """Pass/fail verdict for a simplification result, plus why.

    Both signals are checked independently: either one alone is enough to
    fail, since a mesh that stayed close in surface deviation but tore a hole
    (or vice versa, a dense hole-free result that still drifted too far from
    the source silhouette) is equally not what a caller wants back.
    """
    reasons = []
    if deviation_max_pct > max_deviation_pct:
        reasons.append(
            f"max surface deviation {deviation_max_pct:.2f}% exceeds the {max_deviation_pct:.2f}% limit"
        )
    if new_boundary_edges > allow_new_holes:
        reasons.append(f"{new_boundary_edges} new boundary edge(s) appeared (limit {allow_new_holes})")

    if reasons:
        return {"passed": False, "reason": "; ".join(reasons)}
    return {"passed": True, "reason": "within tolerance"}


def suggest_retry_target(current_target, deviation_max_pct, max_deviation_pct):
    """A looser target to retry with after a failed quality gate.

    Deviation roughly scales with how aggressively the mesh was thinned, so
    scaling the target up by the same factor the deviation overshot by is a
    reasonable next guess -- not exact, but far better than leaving the
    caller to guess blind after a rollback.
    """
    if max_deviation_pct <= 0 or deviation_max_pct <= max_deviation_pct:
        return int(current_target * 1.5)
    factor = min(4.0, deviation_max_pct / max_deviation_pct)
    return int(round(current_target * factor))
