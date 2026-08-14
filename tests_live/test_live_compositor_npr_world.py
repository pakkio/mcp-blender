"""Live tests for Compositor effects, NPR toon shaders, World environments, physics, and cleanup inside Blender."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveCompositorNPRWorld(LiveBpyTestCase):

    def test_compositor_effects(self):
        comp_res = self.execute_tool(
            "configure_compositor_effects",
            {
                "use_glare": True,
                "glare_threshold": 0.5,
                "use_lens_distortion": True,
                "distortion": 0.01,
            },
        )
        self.assertTrue(comp_res.get("success"), comp_res.get("message"))
        self.assertTrue(bpy.context.scene.use_nodes)

    def test_create_toon_shader(self):
        self.execute_tool("create_object", {"object_type": "MONKEY", "name": "ToonSuzanne"})

        toon_res = self.execute_tool(
            "create_toon_shader",
            {
                "material_name": "AnimeShadingMat",
                "object_name": "ToonSuzanne",
                "base_color": [0.9, 0.3, 0.3, 1.0],
                "shadow_color": [0.3, 0.1, 0.1, 1.0],
            },
        )
        self.assertTrue(toon_res.get("success"), toon_res.get("message"))
        self.assertIn("AnimeShadingMat", bpy.data.materials)

    def test_world_environment_and_physics(self):
        # Configure world background
        world_res = self.execute_tool(
            "configure_world_environment",
            {"color": [0.1, 0.1, 0.2, 1.0], "strength": 2.0},
        )
        self.assertTrue(world_res.get("success"), world_res.get("message"))

        # Configure scene physics & color management
        phys_res = self.execute_tool(
            "configure_scene_physics",
            {
                "gravity": [0.0, 0.0, -9.81],
                "unit_system": "METRIC",
                "color_space_exposure": 0.5,
            },
        )
        self.assertTrue(phys_res.get("success"), phys_res.get("message"))
        self.assertEqual(round(bpy.context.scene.gravity.z, 2), -9.81)

    def test_align_distribute_and_purge(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "Obj1", "location": [0, 0, 5]})
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "Obj2", "location": [0, 0, 10]})

        # Snap to ground
        snap_res = self.execute_tool(
            "align_distribute_objects",
            {"object_names": ["Obj1", "Obj2"], "action": "SNAP_TO_GROUND"},
        )
        self.assertTrue(snap_res.get("success"), snap_res.get("message"))

        # Purge orphans
        purge_res = self.execute_tool("purge_orphans_and_cleanup", {"action": "PURGE_ORPHANS"})
        self.assertTrue(purge_res.get("success"), purge_res.get("message"))
