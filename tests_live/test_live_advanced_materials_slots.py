"""Live tests for material slots, decal projection, and procedural materials inside Blender."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveAdvancedMaterialsSlots(LiveBpyTestCase):

    def test_manage_material_slots_and_face_assignment(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "MultiMatCube"})
        self.execute_tool("create_material", {"name": "SlotMatRed", "base_color": [1, 0, 0, 1]})
        self.execute_tool("create_material", {"name": "SlotMatBlue", "base_color": [0, 0, 1, 1]})

        # Add slot
        add_slot = self.execute_tool(
            "manage_material_slots",
            {"object_name": "MultiMatCube", "action": "ADD_SLOT", "material_name": "SlotMatRed"},
        )
        self.assertTrue(add_slot.get("success"), add_slot.get("message"))

        # Assign to faces
        assign_faces = self.execute_tool(
            "manage_material_slots",
            {
                "object_name": "MultiMatCube",
                "action": "ASSIGN_FACES",
                "material_name": "SlotMatBlue",
                "face_indices": [0, 1],
            },
        )
        self.assertTrue(assign_faces.get("success"), assign_faces.get("message"))
        self.assertEqual(assign_faces.get("assigned_faces"), 2)

    def test_project_decal_material(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "DecalTargetCube"})
        self.execute_tool("create_material", {"name": "LogoDecalMat"})

        decal_res = self.execute_tool(
            "project_decal_material",
            {
                "target_object": "DecalTargetCube",
                "decal_name": "FrontLogoDecal",
                "material_name": "LogoDecalMat",
                "size": 0.5,
                "surface_offset": 0.005,
            },
        )
        self.assertTrue(decal_res.get("success"), decal_res.get("message"))
        self.assertIn("FrontLogoDecal", bpy.data.objects)
        decal_obj = bpy.data.objects["FrontLogoDecal"]
        self.assertEqual(decal_obj.parent.name, "DecalTargetCube")
        self.assertIn("Decal_Shrinkwrap", decal_obj.modifiers)

    def test_create_procedural_material(self):
        proc_res = self.execute_tool(
            "create_procedural_material",
            {
                "material_name": "ProcBrushedMetal",
                "preset": "BRUSHED_METAL",
            },
        )
        self.assertTrue(proc_res.get("success"), proc_res.get("message"))
        self.assertIn("ProcBrushedMetal", bpy.data.materials)
