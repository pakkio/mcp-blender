"""Live tests for Lattice deformers, OpenVDB volumetrics, VSE audio/sequencer, and Asset Browser inside Blender."""

import bpy
from tests_live.base_case import LiveBpyTestCase


class TestLiveVSELatticeVolumetrics(LiveBpyTestCase):

    def test_lattice_deform_and_points(self):
        self.execute_tool("create_object", {"object_type": "CUBE", "name": "SquashCube"})

        # Create lattice
        lat_res = self.execute_tool(
            "create_lattice_deform",
            {"target_object": "SquashCube", "u_resolution": 3, "v_resolution": 3, "w_resolution": 3},
        )
        self.assertTrue(lat_res.get("success"), lat_res.get("message"))
        lat_name = lat_res.get("lattice_name")
        self.assertIn(lat_name, bpy.data.objects)

        # Deform lattice points
        deform_res = self.execute_tool(
            "deform_lattice_points",
            {"lattice_name": lat_name, "deformation": "SQUASH_AND_STRETCH", "factor": 0.4},
        )
        self.assertTrue(deform_res.get("success"), deform_res.get("message"))

    def test_volume_vdb_and_shader(self):
        # Create procedural volume fog box
        vol_res = self.execute_tool("create_volume_vdb", {"name": "ProceduralFogDomain", "density": 0.08})
        self.assertTrue(vol_res.get("success"), vol_res.get("message"))
        self.assertIn("ProceduralFogDomain", bpy.data.objects)

        # Configure volume shader
        shader_res = self.execute_tool(
            "configure_volume_shader",
            {"object_name": "ProceduralFogDomain", "density": 0.15, "emission_strength": 0.5},
        )
        self.assertTrue(shader_res.get("success"), shader_res.get("message"))

    def test_sequencer_strips_and_audio(self):
        # Add color strip
        strip_res = self.execute_tool(
            "manage_sequencer_strips",
            {"action": "ADD_COLOR", "name": "LiveColorStrip", "channel": 1, "frame_start": 1, "length": 60},
        )
        self.assertTrue(strip_res.get("success"), strip_res.get("message"))

        # Configure sequencer audio
        audio_res = self.execute_tool(
            "configure_sequencer_audio",
            {"strip_name": "LiveColorStrip", "volume": 0.8},
        )
        self.assertTrue(audio_res.get("success"), audio_res.get("message"))

        # Clear all
        clear_res = self.execute_tool("manage_sequencer_strips", {"action": "CLEAR_ALL"})
        self.assertTrue(clear_res.get("success"), clear_res.get("message"))

    def test_asset_browser_mark_and_clear(self):
        self.execute_tool("create_object", {"object_type": "MONKEY", "name": "AssetSuzanne"})

        # Mark as asset
        mark_res = self.execute_tool(
            "manage_asset_browser",
            {
                "action": "ASSET_MARK",
                "asset_type": "OBJECT",
                "target_name": "AssetSuzanne",
                "author": "Antigravity",
                "description": "Test asset model",
                "tags": ["character", "prop"],
            },
        )
        self.assertTrue(mark_res.get("success"), mark_res.get("message"))
        obj = bpy.data.objects["AssetSuzanne"]
        self.assertIsNotNone(obj.asset_data)

        # Clear asset
        clear_res = self.execute_tool(
            "manage_asset_browser",
            {"action": "ASSET_CLEAR", "asset_type": "OBJECT", "target_name": "AssetSuzanne"},
        )
        self.assertTrue(clear_res.get("success"), clear_res.get("message"))
