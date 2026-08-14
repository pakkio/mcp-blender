"""Live tests for advanced modeling, mesh surgery, UV unwrap, and export tools inside Blender."""

import os
import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveAdvancedModelingPipeline(LiveBpyTestCase):

    def test_uv_unwrap(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "UVCube"})
        res = self.execute_tool("uv_unwrap", {"object_name": "UVCube", "method": "SMART_PROJECT", "island_margin": 0.05})
        self.assertTrue(res.get("success"), res.get("message"))
        cube = bpy.data.objects["UVCube"]
        self.assertGreater(len(cube.data.uv_layers), 0)

    def test_advanced_mesh_edit_bisect_and_extrude(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "BisectCube"})

        # Bisect cut with cap fill
        bisect_res = self.execute_tool(
            "advanced_mesh_edit",
            {
                "object_name": "BisectCube",
                "operation": "BISECT",
                "plane_co": [0, 0, 0],
                "plane_no": [0, 0, 1],
                "clear_inner": True,
                "use_fill": True,
            },
        )
        self.assertTrue(bisect_res.get("success"), bisect_res.get("message"))

        # Extrude along normals
        extrude_res = self.execute_tool(
            "advanced_mesh_edit",
            {
                "object_name": "BisectCube",
                "operation": "EXTRUDE_ALONG_NORMALS",
                "offset": 0.3,
            },
        )
        self.assertTrue(extrude_res.get("success"), extrude_res.get("message"))

    def test_manipulate_origin_cursor(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "OriginCube", "location": [2, 2, 2]})

        # Set origin to bottom (for floor placement)
        res = self.execute_tool(
            "manipulate_origin_cursor",
            {"object_name": "OriginCube", "action": "ORIGIN_TO_BOTTOM"},
        )
        self.assertTrue(res.get("success"), res.get("message"))

        # Reset 3D cursor
        res_cursor = self.execute_tool(
            "manipulate_origin_cursor",
            {"action": "CURSOR_TO_ORIGIN"},
        )
        self.assertTrue(res_cursor.get("success"), res_cursor.get("message"))

    def test_generate_lods(self):
        self.execute_tool("create_object", {"object_type": "MONKEY", "name": "LODMonkey"})

        lod_res = self.execute_tool(
            "generate_lods",
            {
                "object_name": "LODMonkey",
                "ratios": [1.0, 0.5, 0.25],
            },
        )
        self.assertTrue(lod_res.get("success"), lod_res.get("message"))
        self.assertEqual(len(lod_res.get("lods", [])), 3)
        self.assertIn("LODMonkey_LODGroup", bpy.data.objects)

    def test_export_unity_fbx(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "ExportCube"})
        temp_fbx = os.path.join(bpy.app.tempdir, "live_test_unity.fbx")

        export_res = self.execute_tool(
            "export_unity_fbx",
            {
                "filepath": temp_fbx,
                "selected_only": False,
                "bake_anim": False,
            },
        )
        self.assertTrue(export_res.get("success"), export_res.get("message"))
        self.assertTrue(os.path.isfile(export_res.get("filepath", temp_fbx)))
        if os.path.isfile(temp_fbx):
            os.remove(temp_fbx)
