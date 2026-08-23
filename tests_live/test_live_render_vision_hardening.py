"""Live tests for the item-9 main-thread-hang hardening: render_scene's
resolution/sample caps, capture_multiview_audit's RENDERED refusal above a
polygon budget, and super_import's textured-detection/viewport-switch helpers.
"""

import bpy

from extension.tools.render_ops import _MAX_RESOLUTION_PX, _MAX_SAMPLES
from extension.tools.super_import_ops import _has_baked_texture, _switch_viewport_shading
from extension.tools.vision_feedback_ops import _RENDERED_POLY_BUDGET
from tests_live.base_case import LiveBpyTestCase


class TestLiveRenderCaps(LiveBpyTestCase):
    def test_render_scene_refuses_above_resolution_cap(self):
        bpy.ops.mesh.primitive_cube_add()
        tool = self.get_tool("render_scene")
        result = tool.execute(
            {
                "engine": "BLENDER_WORKBENCH",
                "resolution_x": _MAX_RESOLUTION_PX + 100,
                "resolution_y": 100,
                "resolution_percentage": 100,
            }
        )
        self.assertFalse(result.get("success"))
        self.assertIn("cap", result.get("message", "").lower())

    def test_render_scene_refuses_above_samples_cap(self):
        bpy.ops.mesh.primitive_cube_add()
        tool = self.get_tool("render_scene")
        result = tool.execute(
            {
                "engine": "CYCLES",
                "resolution_x": 64,
                "resolution_y": 64,
                "samples": _MAX_SAMPLES + 1,
            }
        )
        self.assertFalse(result.get("success"))
        self.assertIn("cap", result.get("message", "").lower())

    def _add_camera(self):
        bpy.ops.object.camera_add(location=(0, -4, 0), rotation=(1.5708, 0, 0))
        bpy.context.scene.camera = bpy.context.object

    def test_render_scene_force_bypasses_caps(self):
        bpy.ops.mesh.primitive_cube_add()
        self._add_camera()
        tool = self.get_tool("render_scene")
        result = tool.execute(
            {
                "engine": "BLENDER_WORKBENCH",
                "resolution_x": 32,
                "resolution_y": 32,
                "samples": _MAX_SAMPLES + 1,
                "force": True,
            }
        )
        self.assertTrue(result.get("success"), result.get("message"))

    def test_render_scene_within_caps_succeeds(self):
        bpy.ops.mesh.primitive_cube_add()
        self._add_camera()
        tool = self.get_tool("render_scene")
        result = tool.execute({"engine": "BLENDER_WORKBENCH", "resolution_x": 32, "resolution_y": 32})
        self.assertTrue(result.get("success"), result.get("message"))


class TestLiveCaptureMultiviewAuditCaps(LiveBpyTestCase):
    def _add_dense_mesh(self, subdivisions=8):
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=subdivisions, radius=1.0)
        return bpy.context.object

    def test_refuses_rendered_above_poly_budget(self):
        obj = self._add_dense_mesh()
        self.assertGreater(len(obj.data.polygons), _RENDERED_POLY_BUDGET)

        tool = self.get_tool("capture_multiview_audit")
        result = tool.execute({"shading_mode": "RENDERED", "resolution": 64})

        self.assertFalse(result.get("success"))
        self.assertIn("RENDERED", result.get("message", ""))

    def test_force_rendered_bypasses_the_refusal(self):
        obj = self._add_dense_mesh()
        self.assertGreater(len(obj.data.polygons), _RENDERED_POLY_BUDGET)

        tool = self.get_tool("capture_multiview_audit")
        result = tool.execute(
            {"shading_mode": "RENDERED", "resolution": 64, "force_rendered": True}
        )
        self.assertTrue(result.get("success"), result.get("message"))

    def test_low_poly_composite_has_correct_resolution_and_view_count(self):
        # SOLID/WIREFRAME/MATERIAL shading go through bpy.ops.render.opengl,
        # which needs a viewport and so cannot run under -b (no OpenGL
        # context) -- this exercises the same numpy-vectorised pixel-copy
        # path via RENDERED (bpy.ops.render.render, which works headless)
        # forced past the poly-budget refusal on trivial geometry.
        bpy.ops.mesh.primitive_cube_add()
        tool = self.get_tool("capture_multiview_audit")
        result = tool.execute({"shading_mode": "RENDERED", "resolution": 64, "force_rendered": True})

        self.assertTrue(result.get("success"), result.get("message"))
        self.assertEqual(result["resolution"], [64, 64])
        self.assertEqual(len(result["views"]), 4)


class TestLiveSuperImportTextureHelpers(LiveBpyTestCase):
    def test_has_baked_texture_true_when_image_texture_present(self):
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.object
        mat = bpy.data.materials.new("TexturedMat")
        mat.use_nodes = True
        img = bpy.data.images.new("tiny", width=2, height=2)
        tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        obj.data.materials.append(mat)

        self.assertTrue(_has_baked_texture([obj]))

    def test_has_baked_texture_false_for_plain_color_material(self):
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.object
        mat = bpy.data.materials.new("PlainMat")
        mat.use_nodes = True
        obj.data.materials.append(mat)

        self.assertFalse(_has_baked_texture([obj]))

    def test_has_baked_texture_false_with_no_objects_or_materials(self):
        bpy.ops.mesh.primitive_cube_add()
        obj = bpy.context.object
        self.assertFalse(_has_baked_texture([obj]))
        self.assertFalse(_has_baked_texture([]))

    def test_switch_viewport_shading_never_raises_and_reports_accurately(self):
        # Whether `blender -b` carries any window/VIEW_3D area at all is
        # platform/version-dependent -- what matters is that this never
        # raises, and that its return value and any area it touches agree.
        switched = _switch_viewport_shading("MATERIAL")
        self.assertGreaterEqual(switched, 0)
        touched = 0
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type != "VIEW_3D":
                    continue
                for space in area.spaces:
                    if space.type == "VIEW_3D":
                        self.assertEqual(space.shading.type, "MATERIAL")
                        touched += 1
        self.assertEqual(touched, switched)
