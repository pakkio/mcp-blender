"""Live tests for organize_scene_hierarchy and get_scene_info(include_hierarchy=True)."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveHierarchyOps(LiveBpyTestCase):

    def _create_cubes(self, names, locations):
        for name, loc in zip(names, locations):
            res = self.execute_tool("create_object", {"object_type": "CUBE", "name": name, "location": list(loc)})
            self.assertTrue(res.get("success"), res.get("message"))

    def test_organize_scene_hierarchy_single_group(self):
        names = ["ChairLeg1", "ChairLeg2", "ChairSeat"]
        self._create_cubes(names, [(0, 0, 0), (1, 0, 0), (0.5, 0, 1)])

        res = self.execute_tool(
            "organize_scene_hierarchy",
            {"groups": [{"name": "Chair_01", "collection_path": "Furniture/Chairs", "objects": names}]},
        )
        self.assertTrue(res.get("success"), res.get("message"))

        group = res["groups"][0]
        self.assertEqual(group["objects"], names)
        self.assertIsNotNone(group["root_empty"])
        self.assertEqual(group["collection"], "Chairs")

        root_empty = bpy.data.objects[group["root_empty"]]
        self.assertEqual(root_empty.type, "EMPTY")

        for name in names:
            obj = bpy.data.objects[name]
            self.assertEqual(obj.parent, root_empty)

        self.assertIn("Chairs", bpy.data.collections)
        self.assertIn("Furniture", bpy.data.collections)
        chairs_col = bpy.data.collections["Chairs"]
        furniture_col = bpy.data.collections["Furniture"]
        self.assertIn("Chairs", [c.name for c in furniture_col.children])
        for name in names:
            self.assertIn(name, [o.name for o in chairs_col.objects])

    def test_organize_scene_hierarchy_keeps_world_transform(self):
        self._create_cubes(["FarCube"], [(10.0, 5.0, -3.0)])

        res = self.execute_tool(
            "organize_scene_hierarchy",
            {"groups": [{"name": "Group_01", "objects": ["FarCube"]}], "keep_transform": True},
        )
        self.assertTrue(res.get("success"), res.get("message"))

        obj = bpy.data.objects["FarCube"]
        world_loc = obj.matrix_world.translation
        self.assertAlmostEqual(round(world_loc.x, 2), 10.0)
        self.assertAlmostEqual(round(world_loc.y, 2), 5.0)
        self.assertAlmostEqual(round(world_loc.z, 2), -3.0)

    def test_organize_scene_hierarchy_nested_children(self):
        self._create_cubes(["Leg1", "Leg2"], [(0, 0, 0), (1, 0, 0)])
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "Top", "location": [0, 0, 1]})

        res = self.execute_tool(
            "organize_scene_hierarchy",
            {
                "groups": [
                    {
                        "name": "Table_01",
                        "objects": ["Top"],
                        "children": [{"name": "Legs_01", "objects": ["Leg1", "Leg2"]}],
                    }
                ]
            },
        )
        self.assertTrue(res.get("success"), res.get("message"))

        top_group = res["groups"][0]
        legs_group = top_group["children"][0]
        self.assertTrue(legs_group["success"])

        table_root = bpy.data.objects[top_group["root_empty"]]
        legs_root = bpy.data.objects[legs_group["root_empty"]]
        self.assertEqual(legs_root.parent, table_root)

    def test_organize_scene_hierarchy_missing_object_fails(self):
        res = self.execute_tool(
            "organize_scene_hierarchy",
            {"groups": [{"name": "Bad", "objects": ["DoesNotExist"]}]},
        )
        self.assertFalse(res.get("success"))

    def test_get_scene_info_include_hierarchy(self):
        self._create_cubes(["A", "B"], [(0, 0, 0), (1, 0, 0)])
        self.execute_tool("parent_objects", {"parent_name": "A", "child_names": ["B"]})

        res = self.execute_tool("get_scene_info", {"include_hierarchy": True})
        self.assertTrue(res.get("success"))

        objects_by_name = {o["name"]: o for o in res["objects"]}
        self.assertEqual(objects_by_name["B"]["parent"], "A")
        self.assertIn("B", objects_by_name["A"]["children"])
        self.assertIn("collections", objects_by_name["A"])

    def test_get_scene_info_without_hierarchy_omits_fields(self):
        self._create_cubes(["OnlyCube"], [(0, 0, 0)])

        res = self.execute_tool("get_scene_info", {})
        obj = res["objects"][0]
        self.assertNotIn("parent", obj)
        self.assertNotIn("children", obj)
