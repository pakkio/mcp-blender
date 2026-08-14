"""Live tests for scene hierarchy, camera, and lighting setups inside Blender."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveSceneLightingCamera(LiveBpyTestCase):

    def test_scene_info_and_hierarchy(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "SceneCube"})
        self.execute_tool("create_object", {"object_type": "CAMERA", "name": "MainCamera"})

        # Get scene info
        res = self.execute_tool("get_scene_info", {})
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertGreaterEqual(res.get("objects_count", 0), 2)

        # Get object info
        obj_res = self.execute_tool("get_object_info", {"name": "SceneCube"})
        self.assertTrue(obj_res.get("success"), obj_res.get("message"))
        self.assertEqual(obj_res.get("name"), "SceneCube")
        self.assertEqual(obj_res.get("type"), "MESH")

        # Select objects
        sel_res = self.execute_tool("select_objects", {"names": ["SceneCube"]})
        self.assertTrue(sel_res.get("success"), sel_res.get("message"))

    def test_collections(self):
        # Create collection
        create_col = self.execute_tool("manage_collection", {"name": "Props", "action": "CREATE"})
        self.assertTrue(create_col.get("success"), create_col.get("message"))
        self.assertIn("Props", bpy.data.collections)

        # Create object in collection
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "PropCube", "collection": "Props"})
        cube = bpy.data.objects["PropCube"]
        self.assertIn("Props", [c.name for c in cube.users_collection])

    def test_camera_and_tracking(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "FocusTarget", "location": [0, 0, 1]})
        self.execute_tool("create_object", {"object_type": "CAMERA", "name": "CamRig", "location": [5, -5, 4]})

        # Configure camera
        config_cam = self.execute_tool(
            "configure_camera",
            {
                "name": "CamRig",
                "lens": 50.0,
                "clip_start": 0.1,
                "clip_end": 1000.0,
                "set_as_active_camera": True,
            },
        )
        self.assertTrue(config_cam.get("success"), config_cam.get("message"))
        cam = bpy.data.objects["CamRig"]
        self.assertEqual(cam.data.lens, 50.0)

        # Look at target
        look_res = self.execute_tool("camera_look_at", {"camera_name": "CamRig", "target_object": "FocusTarget"})
        self.assertTrue(look_res.get("success"), look_res.get("message"))

    def test_lighting_rigs_and_sky(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "Subject"})

        # Studio lighting rig
        rig_res = self.execute_tool(
            "create_lighting_rig",
            {"rig_type": "THREE_POINT_STUDIO", "target_object": "Subject", "energy_multiplier": 1.5},
        )
        self.assertTrue(rig_res.get("success"), rig_res.get("message"))
        self.assertIn("Key_Light", bpy.data.objects)

        # Sky and sun rig
        sky_res = self.execute_tool(
            "setup_sky_sun_rig",
            {"sun_elevation": 35.0, "sun_rotation": 60.0},
        )
        self.assertTrue(sky_res.get("success"), sky_res.get("message"))
        self.assertIn("Sun_Rig", bpy.data.objects)

    def test_scene_performance_diagnostics(self):
        self.execute_tool("create_object", {"object_type": "MONKEY", "name": "DiagSuzanne"})
        perf_res = self.execute_tool("inspect_scene_performance", {})
        self.assertTrue(perf_res.get("success"), perf_res.get("message"))
        self.assertGreater(perf_res.get("total_triangles", 0), 0)
        self.assertGreater(perf_res.get("total_vertices", 0), 0)
