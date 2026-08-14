"""Live tests for Geometry Nodes, curves, and 3D text tools inside Blender."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveGeometryNodesCurves(LiveBpyTestCase):

    def test_geometry_nodes_creation_and_edit(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "GNCube"})
        
        # Create GN modifier
        create_gn = self.execute_tool("create_geometry_nodes", {"object_name": "GNCube", "modifier_name": "GeometryNodes", "preset": "EMPTY"})
        self.assertTrue(create_gn.get("success"), create_gn.get("message"))
        tree_name = create_gn.get("tree_name")
        self.assertIn(tree_name, bpy.data.node_groups)

        # Edit GN (add subdivide node)
        edit_gn = self.execute_tool(
            "edit_geometry_nodes",
            {
                "object_name": "GNCube",
                "modifier_name": "GeometryNodes",
                "action": "ADD_NODE",
                "node_type": "GeometryNodeSubdivideMesh",
            },
        )
        self.assertTrue(edit_gn.get("success"), edit_gn.get("message"))

    def test_curve_to_profile_mesh(self):
        self.execute_tool("create_object", {"object_type": "CURVE_BEZIER", "name": "ProfilePath"})
        
        sweep_res = self.execute_tool(
            "curve_to_profile_mesh",
            {"curve_object": "ProfilePath", "profile_type": "CIRCLE", "radius": 0.25, "fill_caps": True},
        )
        self.assertTrue(sweep_res.get("success"), sweep_res.get("message"))
        curve_obj = bpy.data.objects["ProfilePath"]
        self.assertIn("CurveProfile_GN", curve_obj.modifiers)

    def test_geometry_proximity_interaction(self):
        self.execute_tool("create_object", {"object_type": "GRID", "name": "GroundGrid", "size": 10})
        self.execute_tool("create_object", {"object_type": "UV_SPHERE", "name": "EffectorBall", "location": [0, 0, 1]})

        prox_res = self.execute_tool(
            "setup_geometry_proximity_interaction",
            {"target_object": "GroundGrid", "source_object": "EffectorBall", "max_distance": 3.0},
        )
        self.assertTrue(prox_res.get("success"), prox_res.get("message"))
        grid = bpy.data.objects["GroundGrid"]
        self.assertIn("ProximityReaction_GN", grid.modifiers)

    def test_3d_text_and_properties(self):
        # Create 3D text
        text_res = self.execute_tool(
            "create_3d_text",
            {"text": "Hello Blender", "name": "Live3DTitle", "extrude": 0.2, "bevel_depth": 0.02},
        )
        self.assertTrue(text_res.get("success"), text_res.get("message"))
        self.assertIn("Live3DTitle", bpy.data.objects)
        text_obj = bpy.data.objects["Live3DTitle"]
        self.assertEqual(text_obj.data.body, "Hello Blender")

        # Set text properties
        set_text = self.execute_tool(
            "set_text_properties",
            {"text_name": "Live3DTitle", "text": "Updated 3D Title", "extrude": 0.4},
        )
        self.assertTrue(set_text.get("success"), set_text.get("message"))
        self.assertEqual(text_obj.data.body, "Updated 3D Title")

    def test_curve_cable_generation(self):
        cable_res = self.execute_tool(
            "create_curve_cable",
            {
                "name": "LivePowerCable",
                "start_point": [0.0, 0.0, 3.0],
                "end_point": [5.0, 0.0, 3.0],
                "sag_amount": 0.8,
                "bevel_radius": 0.05,
            },
        )
        self.assertTrue(cable_res.get("success"), cable_res.get("message"))
        self.assertIn("LivePowerCable", bpy.data.objects)
