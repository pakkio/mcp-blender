"""Live tests for materials, specialty shaders, and node graphs inside Blender."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveMaterialShaderOps(LiveBpyTestCase):

    def test_create_and_assign_material(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "MatCube"})
        
        # Create material
        create_res = self.execute_tool(
            "create_material",
            {
                "name": "LiveTestMat",
                "base_color": [0.2, 0.7, 0.9, 1.0],
                "metallic": 0.8,
                "roughness": 0.2,
                "assign_to_object": "MatCube",
            },
        )
        self.assertTrue(create_res.get("success"), create_res.get("message"))
        self.assertIn("LiveTestMat", bpy.data.materials)
        mat = bpy.data.materials["LiveTestMat"]
        self.assertTrue(mat.use_nodes)

        # Get material info
        info_res = self.execute_tool("get_material_info", {"material_name": "LiveTestMat"})
        self.assertTrue(info_res.get("success"), info_res.get("message"))
        self.assertIn("principled_bsdf", info_res)
        self.assertEqual(info_res["principled_bsdf"]["metallic"], 0.8)

        # Set material properties
        set_res = self.execute_tool(
            "set_material_properties",
            {"material_name": "LiveTestMat", "roughness": 0.05, "metallic": 1.0},
        )
        self.assertTrue(set_res.get("success"), set_res.get("message"))

    def test_specialty_shader_presets(self):
        # Car Paint
        res_car = self.execute_tool(
            "setup_specialty_shader",
            {"material_name": "CarPaintMat", "preset": "CAR_PAINT", "base_color": [0.8, 0.0, 0.0, 1.0]},
        )
        self.assertTrue(res_car.get("success"), res_car.get("message"))
        self.assertIn("CarPaintMat", bpy.data.materials)

        # Skin SSS
        res_skin = self.execute_tool(
            "setup_specialty_shader",
            {"material_name": "SkinMat", "preset": "SKIN_SSS"},
        )
        self.assertTrue(res_skin.get("success"), res_skin.get("message"))

        # Hologram
        res_holo = self.execute_tool(
            "setup_specialty_shader",
            {"material_name": "HoloMat", "preset": "HOLOGRAM_GLOW"},
        )
        self.assertTrue(res_holo.get("success"), res_holo.get("message"))

    def test_procedural_grunge_and_triplanar(self):
        self.execute_tool("create_material", {"name": "GrungeMat"})
        
        # Add procedural grunge mask
        grunge_res = self.execute_tool(
            "create_procedural_grunge_mask",
            {"material_name": "GrungeMat", "edge_wear_amount": 0.7, "dirt_amount": 0.4},
        )
        self.assertTrue(grunge_res.get("success"), grunge_res.get("message"))

        # Triplanar mapping
        self.execute_tool("create_material", {"name": "TriplanarMat"})
        tri_res = self.execute_tool(
            "setup_triplanar_mapping",
            {"material_name": "TriplanarMat", "texture_scale": 3.5},
        )
        self.assertTrue(tri_res.get("success"), tri_res.get("message"))

    def test_shader_node_group(self):
        group_res = self.execute_tool(
            "manage_shader_node_group",
            {"group_name": "LiveCustomNodeGroup", "action": "CREATE"},
        )
        self.assertTrue(group_res.get("success"), group_res.get("message"))
        self.assertIn("LiveCustomNodeGroup", bpy.data.node_groups)
