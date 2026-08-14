"""Live tests for animation, physics, and constraint tools inside Blender."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveAnimationPhysicsOps(LiveBpyTestCase):

    def test_timeline_and_keyframes(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "AnimCube"})

        # Set timeline range
        range_res = self.execute_tool("set_timeline_range", {"frame_start": 1, "frame_end": 120, "fps": 30})
        self.assertTrue(range_res.get("success"), range_res.get("message"))
        self.assertEqual(bpy.context.scene.frame_start, 1)
        self.assertEqual(bpy.context.scene.frame_end, 120)

        # Set keyframe
        key_res = self.execute_tool(
            "set_keyframe",
            {"object_name": "AnimCube", "data_path": "location", "frame": 1, "value": [0, 0, 0]},
        )
        self.assertTrue(key_res.get("success"), key_res.get("message"))

        # Set second keyframe
        key_res2 = self.execute_tool(
            "set_keyframe",
            {"object_name": "AnimCube", "data_path": "location", "frame": 60, "value": [5, 0, 2]},
        )
        self.assertTrue(key_res2.get("success"), key_res2.get("message"))

        # Delete keyframe
        del_key = self.execute_tool(
            "delete_keyframe",
            {"object_name": "AnimCube", "data_path": "location", "frame": 60},
        )
        self.assertTrue(del_key.get("success"), del_key.get("message"))

    def test_constraints_and_turntable(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "TargetBox"})
        self.execute_tool("create_object", {"object_type": "CAMERA", "name": "TurntableCam"})

        # Add constraint
        con_res = self.execute_tool(
            "add_constraint",
            {
                "object_name": "TurntableCam",
                "constraint_type": "TRACK_TO",
                "target_object": "TargetBox",
            },
        )
        self.assertTrue(con_res.get("success"), con_res.get("message"))
        cam = bpy.data.objects["TurntableCam"]
        self.assertGreaterEqual(len(cam.constraints), 1)

    def test_rigid_body_and_force_field(self):
        self.execute_tool("create_object", {"object_type": "PLANE", "name": "FloorPlane", "size": 10})
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "FallingCube", "location": [0, 0, 5]})

        # Setup passive rigid body
        rb_floor = self.execute_tool(
            "setup_rigid_body_simulation",
            {"object_name": "FloorPlane", "body_type": "PASSIVE"},
        )
        self.assertTrue(rb_floor.get("success"), rb_floor.get("message"))

        # Setup active rigid body
        rb_cube = self.execute_tool(
            "setup_rigid_body_simulation",
            {"object_name": "FallingCube", "body_type": "ACTIVE", "mass": 2.5},
        )
        self.assertTrue(rb_cube.get("success"), rb_cube.get("message"))

        # Add force field
        ff_res = self.execute_tool(
            "add_force_field",
            {"field_type": "WIND", "strength": 5.0, "location": [0, -2, 2]},
        )
        self.assertTrue(ff_res.get("success"), ff_res.get("message"))
