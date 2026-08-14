"""Live tests for object and mesh operations inside Blender."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveObjectMeshOps(LiveBpyTestCase):

    def test_create_and_delete_objects(self):
        # Create cube
        res = self.execute_tool("create_object", {"object_type": "CUBE", "name": "LiveTestCube", "location": [1.0, 2.0, 3.0]})
        self.assertTrue(res.get("success"), res.get("message"))
        self.assertIn("LiveTestCube", bpy.data.objects)
        cube = bpy.data.objects["LiveTestCube"]
        self.assertEqual(round(cube.location.x, 2), 1.0)
        self.assertEqual(round(cube.location.y, 2), 2.0)
        self.assertEqual(round(cube.location.z, 2), 3.0)

        # Create sphere
        res_sphere = self.execute_tool("create_object", {"object_type": "UV_SPHERE", "name": "LiveTestSphere", "radius": 1.5})
        self.assertTrue(res_sphere.get("success"), res_sphere.get("message"))
        self.assertIn("LiveTestSphere", bpy.data.objects)

        # Delete object
        del_res = self.execute_tool("delete_object", {"names": ["LiveTestCube"]})
        self.assertTrue(del_res.get("success"), del_res.get("message"))
        self.assertNotIn("LiveTestCube", bpy.data.objects)

    def test_transform_and_apply(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "TransformCube"})
        res = self.execute_tool(
            "set_object_transform",
            {
                "name": "TransformCube",
                "location": [5.0, -2.0, 1.0],
                "rotation_euler": [0.0, 0.0, 0.785],
                "scale": [2.0, 2.0, 2.0],
            },
        )
        self.assertTrue(res.get("success"), res.get("message"))
        obj = bpy.data.objects["TransformCube"]
        self.assertEqual(round(obj.location.x, 1), 5.0)
        self.assertEqual(round(obj.scale.x, 1), 2.0)

        # Apply transform
        apply_res = self.execute_tool(
            "apply_transform",
            {"name": "TransformCube", "location": False, "rotation": True, "scale": True},
        )
        self.assertTrue(apply_res.get("success"), apply_res.get("message"))
        self.assertEqual(round(obj.scale.x, 1), 1.0)

    def test_parent_unparent_and_duplicate(self):
        self.execute_tool("create_object", {"object_type": "EMPTY", "name": "ParentObj"})
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "ChildObj"})

        parent_res = self.execute_tool("parent_objects", {"parent_name": "ParentObj", "child_names": ["ChildObj"]})
        self.assertTrue(parent_res.get("success"), parent_res.get("message"))
        child = bpy.data.objects["ChildObj"]
        self.assertEqual(child.parent.name, "ParentObj")

        # Duplicate child
        dup_res = self.execute_tool("duplicate_object", {"name": "ChildObj", "new_name": "ChildObjDup"})
        self.assertTrue(dup_res.get("success"), dup_res.get("message"))
        self.assertIn("ChildObjDup", bpy.data.objects)

        # Unparent
        unparent_res = self.execute_tool("unparent_objects", {"names": ["ChildObj"]})
        self.assertTrue(unparent_res.get("success"), unparent_res.get("message"))
        self.assertIsNone(child.parent)

    def test_mesh_operations_and_modifiers(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "ModCube"})
        
        # Add modifier
        mod_res = self.execute_tool(
            "add_modifier",
            {"object_name": "ModCube", "modifier_type": "SUBSURF", "modifier_name": "SubsurfMod"},
        )
        self.assertTrue(mod_res.get("success"), mod_res.get("message"))
        obj = bpy.data.objects["ModCube"]
        self.assertIn("SubsurfMod", obj.modifiers)

        # Set modifier properties
        set_mod = self.execute_tool(
            "set_modifier_properties",
            {"object_name": "ModCube", "modifier_name": "SubsurfMod", "properties": {"levels": 2}},
        )
        self.assertTrue(set_mod.get("success"), set_mod.get("message"))
        self.assertEqual(obj.modifiers["SubsurfMod"].levels, 2)

        # Apply modifier
        apply_mod = self.execute_tool(
            "apply_modifier",
            {"object_name": "ModCube", "modifier_name": "SubsurfMod"},
        )
        self.assertTrue(apply_mod.get("success"), apply_mod.get("message"))
        self.assertNotIn("SubsurfMod", obj.modifiers)
        self.assertGreater(len(obj.data.vertices), 8)

    def test_boolean_and_decimate(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "TargetCube", "location": [0, 0, 0]})
        self.execute_tool("create_object", {"object_type": "UV_SPHERE", "name": "CutterSphere", "location": [0.5, 0, 0]})

        bool_res = self.execute_tool(
            "boolean_operation",
            {
                "target_object": "TargetCube",
                "operand_object": "CutterSphere",
                "operation": "DIFFERENCE",
                "apply_immediately": True,
            },
        )
        self.assertTrue(bool_res.get("success"), bool_res.get("message"))

        # Decimate
        dec_res = self.execute_tool(
            "decimate_mesh",
            {"object_name": "TargetCube", "ratio": 0.5, "apply_immediately": True},
        )
        self.assertTrue(dec_res.get("success"), dec_res.get("message"))
