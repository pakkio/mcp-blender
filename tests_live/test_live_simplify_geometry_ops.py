"""Live tests for simplify_geometry, run inside real Blender via bpy.

The acceptance criterion for this tool is test_fork_survives_where_plain_decimate_breaks:
decimate_mesh on a mesh with every edge split (the shape imported glTF/FBX/STL
geometry actually has -- split at every UV seam/material boundary) tears the
mesh apart into disconnected shells; simplify_geometry's weld-first repair
should not.
"""

import bmesh
import bpy

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
