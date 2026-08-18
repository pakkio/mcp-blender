"""Budget-driven, form-preserving mesh reduction.

decimate_mesh / remesh_mesh (remesh_decimate_ops.py) are the wrong shape for
a messy imported asset: Collapse assumes a welded, manifold mesh, but glTF/
STL/FBX exporters split vertices at every UV seam and material boundary, so
what looks like one surface is really disconnected shells touching at their
edges. Collapse pulls those shells apart independently -- the "holes" a flat
decimate produces on real assets. And a flat ratio spends its budget evenly,
so a fork's thin tines get thinned at the same rate as its flat handle.

simplify_geometry repairs the mesh first (weld coincident verts, drop loose
geometry, close pinhole gaps), then reduces with the vertex budget spent
where the surface is flat and dense (limited dissolve, then curvature-
weighted Decimate), then measures what it produced (two-sided surface
deviation + new-hole count) and rolls back rather than handing back a
mesh that silently lost a feature.
"""

import math

import bmesh
import bpy
from mathutils.bvhtree import BVHTree

from . import simplify_geometry_planner as planner
from .base import ToolBase

_MAX_RATIO_ITERATIONS = 3
_DEVIATION_SAMPLE_LIMIT = 4000


class SimplifyGeometryTool(ToolBase):
    name = "simplify_geometry"
    description = (
        "Reduce a mesh to a vertex budget while preserving its form: repairs the mesh (welds seams, drops "
        "loose geometry, closes pinhole gaps), removes vertices from flat/dense regions first, protects thin "
        "features and boundaries via curvature-weighted decimation, then measures the result and rolls back "
        "rather than returning a mesh with new holes or a lost feature. Use this instead of decimate_mesh on "
        "imported/downloaded assets, which are usually not the welded manifold mesh decimate_mesh assumes."
    )

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        current_verts = len(obj.data.vertices)
        current_tris = sum(max(0, len(p.vertices) - 2) for p in obj.data.polygons)

        target_verts, error = planner.resolve_target_vertices(
            target=params.get("target"),
            target_unit=params.get("target_unit", "VERTICES"),
            preset=params.get("preset"),
            current_verts=current_verts,
            current_tris=current_tris,
        )
        if error:
            return {"success": False, "message": error}

        if target_verts >= current_verts:
            return {
                "success": True,
                "message": f"'{object_name}' already has {current_verts} vertices, at or under the {target_verts} target; nothing to do",
                "object_name": object_name,
                "original_vertices": current_verts,
                "result_vertices": current_verts,
                "target_vertices": target_verts,
                "gate": {"passed": True, "reason": "no reduction needed"},
            }

        dry_run = bool(params.get("dry_run", False))
        repair = bool(params.get("repair", True))
        weld_factor = float(params.get("weld_factor", 1e-4))
        preserve_uv = bool(params.get("preserve_uv", True))
        preserve_boundaries = bool(params.get("preserve_boundaries", True))
        sharp_angle = float(params.get("sharp_angle", 3.0))
        tolerance = float(params.get("tolerance", 0.05))
        use_symmetry = bool(params.get("use_symmetry", False))
        symmetry_axis = params.get("symmetry_axis", "X").upper()
        max_deviation_pct = float(params.get("max_deviation_pct", 2.0))
        allow_new_holes = int(params.get("allow_new_holes", 0))
        rollback_on_failure = bool(params.get("rollback_on_failure", True))

        analysis = _analyze(obj)

        if dry_run:
            estimated_ratio = planner.estimate_initial_ratio(current_verts, len(obj.data.polygons), target_verts)
            return {
                "success": True,
                "message": f"Dry run: '{object_name}' would be reduced from {current_verts} to ~{target_verts} vertices",
                "object_name": object_name,
                "original_vertices": current_verts,
                "target_vertices": target_verts,
                "analysis": analysis,
                "estimated_initial_ratio": round(estimated_ratio, 4),
                "dry_run": True,
            }

        original_mesh_copy = obj.data.copy()
        original_verts_count = current_verts

        bpy.context.view_layer.objects.active = obj
        if obj.data.shape_keys:
            obj.shape_key_clear()

        try:
            bm = bmesh.new()
            bm.from_mesh(obj.data)

            repair_stats = None
            if repair:
                repair_stats = _repair(bm, weld_factor=weld_factor)

            delimit = {"MATERIAL", "SHARP"}
            if preserve_uv:
                delimit |= {"UV", "SEAM"}
            dissolved = _dissolve_flat(bm, angle_limit_deg=sharp_angle, delimit=delimit)

            bm.to_mesh(obj.data)
            obj.data.update()
            bm.free()

            post_dissolve_verts = len(obj.data.vertices)

            if post_dissolve_verts > target_verts:
                collapse_stats = _weighted_collapse(
                    obj,
                    target_verts=target_verts,
                    preserve_boundaries=preserve_boundaries,
                    tolerance=tolerance,
                    use_symmetry=use_symmetry,
                    symmetry_axis=symmetry_axis,
                )
            else:
                collapse_stats = {"applied": False, "iterations": 0}

            result_verts = len(obj.data.vertices)

            deviation = _measure_deviation(original_mesh_copy, obj.data)
            new_boundary_edges = _count_boundary_edges(obj.data) - analysis["boundary_edges"]
            new_boundary_edges = max(0, new_boundary_edges)

            gate = planner.evaluate_quality_gate(
                deviation_max_pct=deviation["max_pct"],
                new_boundary_edges=new_boundary_edges,
                max_deviation_pct=max_deviation_pct,
                allow_new_holes=allow_new_holes,
            )

            if not gate["passed"] and rollback_on_failure:
                obj.data.clear_geometry()  # release derived data before swapping the mesh block
                obj.data = original_mesh_copy
                obj.data.update()
                suggested_target = planner.suggest_retry_target(target_verts, deviation["max_pct"], max_deviation_pct)
                return {
                    "success": False,
                    "message": (
                        f"Quality gate failed and '{object_name}' was rolled back to its original {original_verts_count} "
                        f"vertices: {gate['reason']}. Try target={suggested_target}, or repair=true / a coarser "
                        f"remesh_mesh pass first if the mesh has extensive non-manifold geometry."
                    ),
                    "object_name": object_name,
                    "original_vertices": original_verts_count,
                    "result_vertices": original_verts_count,
                    "target_vertices": target_verts,
                    "rolled_back": True,
                    "analysis": analysis,
                    "deviation": deviation,
                    "new_boundary_edges": new_boundary_edges,
                    "gate": gate,
                    "suggested_retry_target": suggested_target,
                }

            bpy.data.meshes.remove(original_mesh_copy)

            return {
                "success": True,
                "message": (
                    f"Simplified '{object_name}' from {original_verts_count} to {result_verts} vertices "
                    f"(target {target_verts}); {gate['reason']}"
                ),
                "object_name": object_name,
                "original_vertices": original_verts_count,
                "result_vertices": result_verts,
                "target_vertices": target_verts,
                "rolled_back": False,
                "analysis": analysis,
                "repair": repair_stats,
                "dissolved_vertices": dissolved,
                "collapse": collapse_stats,
                "deviation": deviation,
                "new_boundary_edges": new_boundary_edges,
                "gate": gate,
            }
        except Exception as exc:
            if rollback_on_failure:
                try:
                    obj.data.clear_geometry()
                    obj.data = original_mesh_copy
                    obj.data.update()
                except Exception:
                    pass
            return {"success": False, "message": f"simplify_geometry failed: {exc}"}


def _analyze(obj):
    """bmesh diagnosis of the input mesh: what a caller (and the quality
    gate) need to know before touching anything."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)

    boundary_edges = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    non_manifold_edges = sum(1 for e in bm.edges if len(e.link_faces) not in (1, 2))
    loose_verts = sum(1 for v in bm.verts if not v.link_edges)

    coincident = 0
    if len(bm.verts) < 60000:  # KDTree build cost; large meshes skip the exact count
        from mathutils.kdtree import KDTree

        kd = KDTree(len(bm.verts))
        for i, v in enumerate(bm.verts):
            kd.insert(v.co, i)
        kd.balance()
        seen = set()
        for i, v in enumerate(bm.verts):
            if i in seen:
                continue
            for _, j, dist in kd.find_range(v.co, 1e-5):
                if j != i:
                    coincident += 1
                    seen.add(j)

    shells = _count_shells(bm)

    diag = _bbox_diagonal(bm)

    bm.free()

    return {
        "vertices": len(obj.data.vertices),
        "faces": len(obj.data.polygons),
        "bbox_diagonal": round(diag, 6),
        "boundary_edges": boundary_edges,
        "non_manifold_edges": non_manifold_edges,
        "loose_vertices": loose_verts,
        "coincident_vertices": coincident,
        "shells": shells,
    }


def _bbox_diagonal(bm):
    if not bm.verts:
        return 0.0
    xs = [v.co.x for v in bm.verts]
    ys = [v.co.y for v in bm.verts]
    zs = [v.co.z for v in bm.verts]
    dx, dy, dz = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
    return math.sqrt(dx * dx + dy * dy + dz * dz)


def _count_shells(bm):
    """Number of connected components, via flood fill over vertex links."""
    unvisited = set(bm.verts)
    shells = 0
    while unvisited:
        shells += 1
        stack = [next(iter(unvisited))]
        while stack:
            v = stack.pop()
            if v not in unvisited:
                continue
            unvisited.discard(v)
            for e in v.link_edges:
                other = e.other_vert(v)
                if other in unvisited:
                    stack.append(other)
    return shells


def _repair(bm, weld_factor):
    """Weld coincident verts, drop loose geometry, close pinhole gaps,
    recalc normals. Order matters: welding first is what turns split-at-seam
    shells back into one manifold surface, which is the actual fix for the
    "decimate produces holes" failure mode.
    """
    diag = _bbox_diagonal(bm)
    dist = max(1e-6, weld_factor * diag) if diag > 0 else weld_factor

    before_verts = len(bm.verts)
    weld_result = bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    welded = before_verts - len(bm.verts)

    loose_verts = [v for v in bm.verts if not v.link_edges]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")

    loose_edges = [e for e in bm.edges if not e.link_faces]
    if loose_edges:
        bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")

    bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges)

    boundary_edges = [e for e in bm.edges if len(e.link_faces) == 1]
    filled = 0
    if boundary_edges:
        fill_result = bmesh.ops.holes_fill(bm, edges=boundary_edges, sides=4)
        filled = len(fill_result.get("faces", []))

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    return {
        "welded_vertices": welded,
        "loose_vertices_removed": len(loose_verts),
        "loose_edges_removed": len(loose_edges),
        "pinhole_faces_filled": filled,
    }


def _dissolve_flat(bm, angle_limit_deg, delimit):
    """Limited dissolve: removes vertices that carry no shape information
    (flat, dense regions) for free, before any lossy collapse happens."""
    before = len(bm.verts)
    bmesh.ops.dissolve_limit(
        bm,
        angle_limit=math.radians(angle_limit_deg),
        use_dissolve_boundaries=False,
        verts=bm.verts,
        edges=bm.edges,
        delimit=delimit,
    )
    return before - len(bm.verts)


def _curvature_weights(obj):
    """Per-vertex protection weight in [0, 1] from local curvature: the max
    angle between a vertex's incident face normals. Flat surfaces score near
    0 (safe to collapse), edges/corners/thin features score near 1.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.normal_update()

    weights = [0.0] * len(bm.verts)
    for v in bm.verts:
        if len(v.link_faces) < 2:
            weights[v.index] = 1.0  # boundary / non-manifold vertex: always protect
            continue
        normals = [f.normal for f in v.link_faces]
        max_angle = 0.0
        for i in range(len(normals)):
            for j in range(i + 1, len(normals)):
                try:
                    angle = normals[i].angle(normals[j])
                except ValueError:
                    angle = 0.0
                max_angle = max(max_angle, angle)
        weights[v.index] = min(1.0, max_angle / math.pi)

    bm.free()
    return weights


def _weighted_collapse(obj, target_verts, preserve_boundaries, tolerance, use_symmetry, symmetry_axis):
    """Reduce to target_verts with Decimate Collapse, weighted so flat
    regions give up vertices first and curved/boundary vertices survive.

    Collapse's `ratio` parameter is face-based, so hitting a vertex target
    needs a solve: apply, measure, correct via secant on a working copy, up
    to _MAX_RATIO_ITERATIONS times, then apply for real at the last ratio.
    """
    weights = _curvature_weights(obj)
    if preserve_boundaries:
        # Boundary verts are already weight 1.0 from _curvature_weights
        # (link_faces < 2), so nothing extra needed here.
        pass

    vg_name = "_SimplifyProtect"
    if vg_name in obj.vertex_groups:
        obj.vertex_groups.remove(obj.vertex_groups[vg_name])
    vg = obj.vertex_groups.new(name=vg_name)
    for index, weight in enumerate(weights):
        vg.add([index], weight, "REPLACE")

    current_verts = len(obj.data.vertices)
    current_faces = len(obj.data.polygons)

    ratio = planner.estimate_initial_ratio(current_verts, current_faces, target_verts)
    samples = []
    iterations = 0
    final_result_verts = current_verts

    for iterations in range(1, _MAX_RATIO_ITERATIONS + 1):
        result_verts = _trial_collapse(obj, vg_name, ratio)
        samples.append((ratio, result_verts))
        final_result_verts = result_verts

        if planner.within_tolerance(result_verts, target_verts, tolerance):
            break

        if len(samples) >= 2:
            (r1, v1), (r2, v2) = samples[-2], samples[-1]
            ratio = planner.secant_next_ratio(r1, v1, r2, v2, target_verts)
        else:
            ratio = max(0.0001, min(1.0, ratio * (target_verts / max(1, result_verts))))

    # Apply for real at the last (best) ratio tried.
    mod = obj.modifiers.new(name="Simplify_Collapse", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = samples[-1][0]
    mod.vertex_group = vg_name
    mod.vertex_group_factor = 1.0
    mod.invert_vertex_group = True  # calibrated: weight=1.0 otherwise gets MORE decimated, not less
    if use_symmetry:
        mod.use_symmetry = True
        if hasattr(mod, "symmetry_axis"):
            mod.symmetry_axis = symmetry_axis
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)

    if vg_name in obj.vertex_groups:
        obj.vertex_groups.remove(obj.vertex_groups[vg_name])

    return {
        "applied": True,
        "iterations": iterations,
        "final_ratio": round(samples[-1][0], 4),
        "result_vertices": len(obj.data.vertices),
    }


def _trial_collapse(obj, vg_name, ratio):
    """Apply Collapse to a scratch copy of the mesh to measure the vertex
    count a given ratio would produce, without touching the real object."""
    trial_mesh = obj.data.copy()
    trial_obj = bpy.data.objects.new("_SimplifyTrial", trial_mesh)
    bpy.context.collection.objects.link(trial_obj)
    try:
        mod = trial_obj.modifiers.new(name="Trial", type="DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        mod.vertex_group = vg_name if vg_name in trial_obj.vertex_groups else ""
        if vg_name in trial_obj.vertex_groups:
            mod.vertex_group_factor = 1.0
            mod.invert_vertex_group = True
        bpy.context.view_layer.objects.active = trial_obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
        return len(trial_obj.data.vertices)
    finally:
        bpy.data.objects.remove(trial_obj, do_unlink=True)
        if trial_mesh.users == 0:
            bpy.data.meshes.remove(trial_mesh)


def _count_boundary_edges(mesh):
    bm = bmesh.new()
    bm.from_mesh(mesh)
    count = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    bm.free()
    return count


def _measure_deviation(original_mesh, result_mesh):
    """Two-sided surface deviation between the original and simplified mesh,
    as a percentage of the original's bbox diagonal.

    Both directions matter: original->result alone reports 0 for a mesh that
    lost a whole feature (nothing on the result is "far" from a point on a
    thin part removed entirely), and only shows up when measured the other
    way, result->original, i.e. how far the original's surface now is from
    its nearest point on the simplified result.
    """
    bm_orig = bmesh.new()
    bm_orig.from_mesh(original_mesh)
    bm_result = bmesh.new()
    bm_result.from_mesh(result_mesh)

    if not bm_orig.verts or not bm_result.verts:
        bm_orig.free()
        bm_result.free()
        return {"mean_pct": 0.0, "max_pct": 0.0, "sampled_points": 0}

    diag = _bbox_diagonal(bm_orig)
    if diag <= 1e-9:
        bm_orig.free()
        bm_result.free()
        return {"mean_pct": 0.0, "max_pct": 0.0, "sampled_points": 0}

    bvh_orig = BVHTree.FromBMesh(bm_orig)
    bvh_result = BVHTree.FromBMesh(bm_result)

    def _sample(bm, limit):
        verts = list(bm.verts)
        stride = max(1, len(verts) // limit)
        return verts[::stride]

    distances = []
    for v in _sample(bm_result, _DEVIATION_SAMPLE_LIMIT):
        _, _, _, dist = bvh_orig.find_nearest(v.co)
        if dist is not None:
            distances.append(dist)
    for v in _sample(bm_orig, _DEVIATION_SAMPLE_LIMIT):
        _, _, _, dist = bvh_result.find_nearest(v.co)
        if dist is not None:
            distances.append(dist)

    bm_orig.free()
    bm_result.free()

    if not distances:
        return {"mean_pct": 0.0, "max_pct": 0.0, "sampled_points": 0}

    mean_pct = (sum(distances) / len(distances)) / diag * 100.0
    max_pct = max(distances) / diag * 100.0
    return {"mean_pct": round(mean_pct, 4), "max_pct": round(max_pct, 4), "sampled_points": len(distances)}
