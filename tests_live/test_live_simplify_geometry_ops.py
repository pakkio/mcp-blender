"""Live tests for simplify_geometry, run inside real Blender via bpy.

The acceptance criterion for this tool is test_fork_survives_where_plain_decimate_breaks:
decimate_mesh on a mesh with every edge split (the shape imported glTF/FBX/STL
geometry actually has -- split at every UV seam/material boundary) tears the
mesh apart into disconnected shells; simplify_geometry's weld-first repair
should not.
"""

import math

import bmesh
import bpy
from mathutils import Vector

from extension.tools.simplify_geometry_ops import _PREPASS_FACTOR
from tests_live.base_case import LiveBpyTestCase


def _boundary_edge_count(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    count = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    bm.free()
    return count


def _shell_count(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
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
    bm.free()
    return shells


def _build_fork(tine_count=4):
    """Handle + tines welded via boolean union: a dense flat region (handle)
    next to thin protruding features (tines), the exact shape a flat-ratio
    decimate handles badly.
    """
    bpy.ops.mesh.primitive_cube_add(size=1)
    handle = bpy.context.object
    handle.name = "ForkHandle"
    handle.scale = (0.15, 1.0, 0.05)
    bpy.context.view_layer.objects.active = handle
    bpy.ops.object.transform_apply(scale=True)

    bm = bmesh.new()
    bm.from_mesh(handle.data)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=6, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=bm.faces)
    bm.to_mesh(handle.data)
    handle.data.update()
    bm.free()

    tine_objs = []
    for i in range(tine_count):
        x = (i - (tine_count - 1) / 2) * 0.08
        bpy.ops.mesh.primitive_cylinder_add(radius=0.02, depth=0.9, location=(x, 0.9, 0), vertices=10)
        tine = bpy.context.object
        tine.name = f"Tine{i}"
        bm = bmesh.new()
        bm.from_mesh(tine.data)
        bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=4, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        bm.to_mesh(tine.data)
        tine.data.update()
        bm.free()
        tine_objs.append(tine)

    bpy.context.view_layer.objects.active = handle
    for tine in tine_objs:
        mod = handle.modifiers.new("union", "BOOLEAN")
        mod.operation = "UNION"
        mod.object = tine
        bpy.ops.object.modifier_apply(modifier=mod.name)
        bpy.data.objects.remove(tine, do_unlink=True)

    return handle


def _shatter_at_every_edge(obj):
    """Reproduce what glTF/FBX/STL exporters actually hand Blender: every
    edge becomes a shell boundary, since exporters split verts at every UV
    seam/material/smoothing-group boundary. bmesh.ops.split_edges on every
    edge is the extreme (but representative) case: every face an island that
    only happens to sit at the same coordinates as its neighbours.
    """
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bmesh.ops.split_edges(bm, edges=list(bm.edges))
    bm.to_mesh(obj.data)
    obj.data.update()
    bm.free()


class TestLiveSimplifyGeometry(LiveBpyTestCase):
    def test_vertex_group_weighting_direction_calibration(self):
        """Regression test for the calibrated invert_vertex_group=True
        assumption baked into simplify_geometry_ops._weighted_collapse: a
        vertex-group weight of 1.0 must survive Collapse at a HIGHER rate
        than weight 0.0, using the exact modifier settings the tool sets.
        """
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=40, y_subdivisions=40, size=2)
        obj = bpy.context.object
        mesh = obj.data

        vg = obj.vertex_groups.new(name="protect")
        left_idx = [v.index for v in mesh.vertices if v.co.x < 0]
        right_idx = [v.index for v in mesh.vertices if v.co.x >= 0]
        vg.add(left_idx, 1.0, "REPLACE")
        vg.add(right_idx, 0.0, "REPLACE")
        orig_left, orig_right = len(left_idx), len(right_idx)

        mod = obj.modifiers.new("d", "DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = 0.3
        mod.vertex_group = vg.name
        mod.vertex_group_factor = 1.0
        mod.invert_vertex_group = True
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)

        mesh = obj.data
        left_after = sum(1 for v in mesh.vertices if v.co.x < 0)
        right_after = sum(1 for v in mesh.vertices if v.co.x >= 0)

        self.assertGreater(
            left_after / orig_left, right_after / orig_right,
            f"weight=1.0 side kept {left_after}/{orig_left}, weight=0.0 side kept {right_after}/{orig_right} "
            "-- invert_vertex_group=True should make high-weight vertices survive more, not less",
        )

    def test_dense_sphere_reduces_within_tolerance_no_new_holes(self):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=7, radius=1.0)  # 40962 vertices
        sphere = bpy.context.object
        sphere.name = "DenseSphere"
        original_verts = len(sphere.data.vertices)
        self.assertGreater(original_verts, 30000)

        tool = self.get_tool("simplify_geometry")
        result = tool.execute({"object_name": "DenseSphere", "target": 5000, "tolerance": 0.1})

        self.assertTrue(result.get("success"), result.get("message"))
        self.assertFalse(result.get("rolled_back", False))
        self.assertAlmostEqual(result["result_vertices"], 5000, delta=500)
        self.assertLess(result["deviation"]["max_pct"], 1.0, result["deviation"])
        self.assertEqual(result["new_boundary_edges"], 0)

    def test_fork_survives_where_plain_decimate_breaks(self):
        fork = _build_fork(tine_count=4)
        _shatter_at_every_edge(fork)

        original_verts = len(fork.data.vertices)
        original_bbox_y = max(v.co.y for v in fork.data.vertices) - min(v.co.y for v in fork.data.vertices)
        original_shells = _shell_count(fork)
        self.assertGreater(original_shells, 100, "shatter step should have produced many disconnected islands")

        # Baseline: plain decimate_mesh on the shattered mesh, proving the
        # documented failure mode this tool exists to fix.
        bare_copy_data = fork.data.copy()
        bare_copy = bpy.data.objects.new("ForkBareDecimate", bare_copy_data)
        bpy.context.collection.objects.link(bare_copy)
        decimate_tool = self.get_tool("decimate_mesh")
        target_ratio = 5000 / original_verts if original_verts else 0.25
        decimate_result = decimate_tool.execute(
            {"object_name": "ForkBareDecimate", "mode": "COLLAPSE", "ratio": min(1.0, max(0.02, target_ratio))}
        )
        self.assertTrue(decimate_result.get("success"), decimate_result.get("message"))
        bare_boundary = _boundary_edge_count(bare_copy)
        self.assertGreater(
            bare_boundary, 500,
            "expected plain decimate_mesh on shattered geometry to leave large boundary/hole edges (the bug this "
            f"tool exists to fix); got only {bare_boundary}",
        )

        # simplify_geometry on the same shattered mesh must repair and reduce cleanly.
        tool = self.get_tool("simplify_geometry")
        result = tool.execute({"object_name": "ForkHandle", "target": 5000, "tolerance": 0.25})

        self.assertTrue(result.get("success"), result.get("message"))
        self.assertFalse(result.get("rolled_back", False), result.get("message"))
        self.assertGreater(result["repair"]["welded_vertices"], 0, "weld should have merged the shattered duplicate verts")
        self.assertEqual(result["new_boundary_edges"], 0, "repaired+simplified mesh should not have gained holes")

        fork.data.update()
        result_shells = _shell_count(fork)
        self.assertLessEqual(
            result_shells, 5,
            f"expected the weld to reunite the shattered mesh into a handful of shells (tines may separate from "
            f"the handle at their base), got {result_shells}",
        )

        result_bbox_y = max(v.co.y for v in fork.data.vertices) - min(v.co.y for v in fork.data.vertices)
        self.assertGreater(
            result_bbox_y, original_bbox_y * 0.9,
            f"tines should still extend to roughly their original length: {result_bbox_y} vs original {original_bbox_y}",
        )

    def test_impossible_target_rolls_back(self):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0)
        sphere = bpy.context.object
        sphere.name = "SmallSphere"
        original_verts = len(sphere.data.vertices)

        tool = self.get_tool("simplify_geometry")
        result = tool.execute(
            {
                "object_name": "SmallSphere",
                "target": 4,
                "max_deviation_pct": 0.001,
                "rollback_on_failure": True,
            }
        )

        self.assertFalse(result.get("success"))
        self.assertTrue(result.get("rolled_back"))
        self.assertEqual(result["result_vertices"], original_verts)
        self.assertEqual(len(sphere.data.vertices), original_verts)
        self.assertIn("suggested_retry_target", result)

    def test_prepass_engages_and_gate_still_measures_true_original(self):
        """A mesh far enough above budget to trigger _fast_prepass must still
        report/measure against its real starting point, not the intermediate
        pre-passed mesh -- a caller reading original_vertices or deviation
        should never see the cheap prepass leak into either.
        """
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=7, radius=1.0)  # 40962 vertices
        sphere = bpy.context.object
        sphere.name = "PrepassSphere"
        original_verts = len(sphere.data.vertices)
        target = 1000  # 40962 / 1000 ~= 41x, comfortably above the 8x prepass threshold

        tool = self.get_tool("simplify_geometry")
        result = tool.execute({"object_name": "PrepassSphere", "target": target, "tolerance": 0.15})

        self.assertIsNotNone(result.get("prepass"), "expected the pre-pass to engage on a 41x-over-budget mesh")
        self.assertGreater(result["prepass"]["vertices_before"], target * _PREPASS_FACTOR)
        self.assertGreater(result["prepass"]["vertices_before"], result["prepass"]["vertices_after"])

        # Reporting must reflect the true original, unaffected by the prepass.
        self.assertEqual(result["original_vertices"], original_verts)
        self.assertTrue(result["deviation"]["two_sided"], "sphere is well under the two-sided face limit")
        self.assertLess(result["deviation"]["max_pct"], 5.0, result["deviation"])

    def test_preserve_boundaries_protects_hole_rim(self):
        """A hole cut into a dense grid (too many sides for holes_fill's
        pinhole repair to silently close back up) must survive aggressive
        reduction far better with preserve_boundaries=True than False.
        """

        def _build_grid_with_hole(name):
            bpy.ops.mesh.primitive_grid_add(x_subdivisions=60, y_subdivisions=60, size=2)
            obj = bpy.context.object
            obj.name = name
            bm = bmesh.new()
            bm.from_mesh(obj.data)
            # A gentle height field keeps the surface non-planar: a perfectly
            # flat grid gets almost entirely eaten by the angle-limited
            # dissolve pass that runs before collapse, which would finish the
            # whole reduction on its own and leave preserve_boundaries (a
            # collapse-only setting) nothing to actually affect.
            for v in bm.verts:
                v.co.z = 0.08 * math.sin(v.co.x * 4.0) * math.cos(v.co.y * 4.0)
            bmesh.ops.triangulate(bm, faces=bm.faces)
            hole_faces = [
                f for f in bm.faces
                if abs(f.calc_center_median().x) < 0.3 and abs(f.calc_center_median().y) < 0.3
            ]
            bmesh.ops.delete(bm, geom=hole_faces, context="FACES")
            bm.to_mesh(obj.data)
            obj.data.update()
            bm.free()
            return obj

        preserved = _build_grid_with_hole("GridHolePreserved")
        unprotected = _build_grid_with_hole("GridHoleUnprotected")
        original_boundary_edges = _boundary_edge_count(preserved)
        self.assertGreater(original_boundary_edges, 20, "hole should be large enough to have a real rim")

        tool = self.get_tool("simplify_geometry")
        common = {
            "target": 300,
            "tolerance": 0.3,
            "max_deviation_pct": 50.0,
            "rollback_on_failure": False,
        }
        res_preserved = tool.execute({**common, "object_name": "GridHolePreserved", "preserve_boundaries": True})
        res_unprotected = tool.execute({**common, "object_name": "GridHoleUnprotected", "preserve_boundaries": False})
        self.assertTrue(res_preserved["collapse"]["applied"], "collapse must actually engage for this test to mean anything")
        self.assertTrue(res_unprotected["collapse"]["applied"], "collapse must actually engage for this test to mean anything")

        preserved_boundary_after = _boundary_edge_count(preserved)
        unprotected_boundary_after = _boundary_edge_count(unprotected)
        self.assertGreater(
            preserved_boundary_after, unprotected_boundary_after,
            f"preserve_boundaries=True kept {preserved_boundary_after} rim edges vs "
            f"{unprotected_boundary_after} without it -- expected the protected rim to survive better",
        )

    def test_collapse_solver_applies_best_sample_not_last(self):
        """Regression guard for _weighted_collapse's best-of-samples pick: the
        applied ratio must be the sample closest to target, which is only
        provably different from 'whatever the last iteration guessed' when
        the solve does not cleanly converge.
        """
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=6, radius=1.0)
        sphere = bpy.context.object
        sphere.name = "SolverSphere"

        tool = self.get_tool("simplify_geometry")
        # An unreasonably tight tolerance all but guarantees the solve runs
        # every iteration without ever hitting "within tolerance".
        result = tool.execute({"object_name": "SolverSphere", "target": 2000, "tolerance": 0.0001})

        self.assertTrue(result.get("success"), result.get("message"))
        samples = result["collapse"]["solver_samples"]
        self.assertGreaterEqual(len(samples), 2)
        best_ratio, best_verts = min(samples, key=lambda s: abs(s[1] - 2000))
        self.assertEqual(result["collapse"]["predicted_vertices"], best_verts)
        self.assertAlmostEqual(result["collapse"]["final_ratio"], best_ratio, places=4)

    def test_repair_restores_uvs_on_filled_pinholes(self):
        """holes_fill closes pinhole gaps in _repair; regression guard that the
        new faces it creates get real UVs copied from their surviving
        neighbours instead of the bmesh default (0, 0), which on a textured
        mesh renders as a flat wrong-coloured patch.
        """
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=14, y_subdivisions=14, size=2)
        obj = bpy.context.object
        obj.name = "UVPinholeGrid"

        bm = bmesh.new()
        bm.from_mesh(obj.data)
        # A gentle height field keeps the surface non-planar so the dissolve
        # pass right after repair (angle-limited) doesn't flatten the whole
        # thing away and wash out what this test is checking.
        for v in bm.verts:
            v.co.z = 0.08 * math.sin(v.co.x * 3.0) * math.cos(v.co.y * 3.0)
        bmesh.ops.triangulate(bm, faces=bm.faces)
        uv_layer = bm.loops.layers.uv.verify()
        for face in bm.faces:
            for loop in face.loops:
                co = loop.vert.co
                loop[uv_layer].uv = ((co.x + 1.0) / 2.0, (co.y + 1.0) / 2.0)

        # Poke a single-face pinhole away from the true UV(0, 0) corner.
        hole_face = min(
            bm.faces, key=lambda f: (f.calc_center_median() - Vector((0.3, 0.3, 0.0))).length
        )
        bmesh.ops.delete(bm, geom=[hole_face], context="FACES")
        bm.to_mesh(obj.data)
        obj.data.update()
        bm.free()

        tool = self.get_tool("simplify_geometry")
        current_verts = len(obj.data.vertices)
        result = tool.execute(
            {"object_name": "UVPinholeGrid", "target": current_verts - 1, "tolerance": 0.9}
        )

        self.assertTrue(result.get("success"), result.get("message"))
        self.assertGreater(result["repair"]["pinhole_faces_filled"], 0, "expected the pinhole to be filled")
        self.assertGreater(result["repair"]["uv_loops_patched"], 0, "expected the new face's UVs to be patched")

    def test_dry_run_changes_nothing(self):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1.0)
        sphere = bpy.context.object
        sphere.name = "DryRunSphere"
        original_verts = len(sphere.data.vertices)

        tool = self.get_tool("simplify_geometry")
        result = tool.execute({"object_name": "DryRunSphere", "target": 100, "dry_run": True})

        self.assertTrue(result.get("success"), result.get("message"))
        self.assertEqual(len(sphere.data.vertices), original_verts)
        self.assertIn("analysis", result)
        self.assertIn("estimated_initial_ratio", result)
