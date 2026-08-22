"""Live tests for regen_element_names: localized structural renaming,
empty-node scaffolding, and alphabetical re-linking."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveLocalizationOps(LiveBpyTestCase):

    def _make_category(self, name, parent_collection, object_names=()):
        col = bpy.data.collections.new(name)
        parent_collection.children.link(col)
        for obj_name in object_names:
            obj = bpy.data.objects.new(obj_name, bpy.data.meshes.new(obj_name + "Mesh"))
            col.objects.link(obj)
        return col

    def test_regen_translates_known_categories_to_italian(self):
        root = bpy.context.scene.collection
        self._make_category("Furniture", root, ["Chair_Mesh"])
        self._make_category("Characters", root, ["Hero_Mesh"])

        res = self.execute_tool("regen_element_names", {"lang": "it"})

        self.assertTrue(res["success"], res.get("message"))
        names = {c["new_name"] for c in res["root"]["children"]}
        self.assertIn("Arredamento", names)
        self.assertIn("Personaggi", names)
        # The scene's own master collection is read-only and must be left alone.
        self.assertEqual(res["root"]["renamed"], False)

    def test_regen_keeps_and_reports_empty_nodes_rather_than_skipping(self):
        root = bpy.context.scene.collection
        self._make_category("Props", root, [])  # scaffolded, nothing in it yet

        res = self.execute_tool("regen_element_names", {"lang": "it"})

        self.assertTrue(res["success"], res.get("message"))
        props_node = next(c for c in res["root"]["children"] if c["old_name"] == "Props")
        self.assertEqual(props_node["new_name"], "Oggetti")
        self.assertEqual(props_node["objects_count"], 0)
        # It must still exist in the scene, not have been pruned.
        self.assertIsNotNone(bpy.data.collections.get("Oggetti"))

    def test_regen_relinks_children_alphabetically(self):
        root = bpy.context.scene.collection
        self._make_category("Zebra", root, [])
        self._make_category("Alpha", root, [])
        self._make_category("Mid", root, [])

        res = self.execute_tool("regen_element_names", {"lang": "it"})

        self.assertTrue(res["success"], res.get("message"))
        live_order = [c.name for c in root.children]
        self.assertEqual(live_order, sorted(live_order, key=str.lower))

    def test_regen_scoped_to_specific_element_leaves_rest_untouched(self):
        root = bpy.context.scene.collection
        target = self._make_category("Furniture", root, [])
        self._make_category("Characters", root, [])  # outside the scope

        res = self.execute_tool("regen_element_names", {"lang": "it", "element": "Furniture"})

        self.assertTrue(res["success"], res.get("message"))
        self.assertEqual(res["root"]["new_name"], "Arredamento")
        # Untargeted sibling stays as-is.
        self.assertIsNotNone(bpy.data.collections.get("Characters"))
        self.assertIsNone(bpy.data.collections.get("Personaggi"))

    def test_regen_unsupported_lang_fails_cleanly(self):
        res = self.execute_tool("regen_element_names", {"lang": "xx"})
        self.assertFalse(res["success"])
        self.assertIn("Unsupported lang", res["message"])

    def test_regen_syncs_matching_root_empty_wrapper_name(self):
        root = bpy.context.scene.collection
        col = self._make_category("Furniture", root, [])
        wrapper = bpy.data.objects.new("Furniture", None)
        col.objects.link(wrapper)  # not required to be linked here, just needs to exist by name

        res = self.execute_tool("regen_element_names", {"lang": "it"})

        self.assertTrue(res["success"], res.get("message"))
        self.assertIsNone(bpy.data.objects.get("Furniture"))
        self.assertIsNotNone(bpy.data.objects.get("Arredamento"))

    def test_regen_reports_leaf_objects_with_parent_info(self):
        root = bpy.context.scene.collection
        self._make_category("Furniture", root, ["Chair_Mesh"])

        res = self.execute_tool("regen_element_names", {"lang": "it"})

        furniture_node = next(c for c in res["root"]["children"] if c["new_name"] == "Arredamento")
        self.assertEqual(len(furniture_node["objects"]), 1)
        self.assertEqual(furniture_node["objects"][0]["new_name"], "Chair_Mesh")
        self.assertEqual(furniture_node["objects"][0]["type"], "MESH")
