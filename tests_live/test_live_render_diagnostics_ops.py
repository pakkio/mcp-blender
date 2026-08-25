"""Live tests for the render/occlusion diagnostic tools: sample_render_pixels
and raycast_from_camera. Added after a debugging session where confirming
"is this object occluded" or "did this material's color reach the render"
required manual hide/render/diff loops with no dedicated tool for either.
"""

import os
import tempfile

import bpy

from tests_live.base_case import LiveBpyTestCase


def _add_camera(location=(0, -4, 0), rotation=(1.5708, 0, 0)):
    bpy.ops.object.camera_add(location=location, rotation=rotation)
    cam = bpy.context.object
    bpy.context.scene.camera = cam
    return cam


def _add_topdown_camera(location=(0, 0, 4)):
    # Default camera rotation (0,0,0) looks straight down -Z: the plane
    # helpers below lie flat in the XY plane, so a side-on camera (as
    # _add_camera's default framing gives) would see them edge-on as a
    # sliver instead of face-on -- this framing is what the sample-pixel
    # tests actually need to hit a filled region of color.
    bpy.ops.object.camera_add(location=location, rotation=(0, 0, 0))
    cam = bpy.context.object
    bpy.context.scene.camera = cam
    return cam


def _add_flat_color_plane(color=(1.0, 0.0, 1.0, 1.0), location=(0, 0, 0)):
    bpy.ops.mesh.primitive_plane_add(size=4, location=location)
    plane = bpy.context.object
    mat = bpy.data.materials.new("FlatColor")
    mat.use_nodes = True
    emission = mat.node_tree.nodes.new("ShaderNodeEmission")
    emission.inputs["Color"].default_value = color
    output = mat.node_tree.nodes.get("Material Output")
    mat.node_tree.links.new(emission.outputs["Emission"], output.inputs["Surface"])
    plane.data.materials.append(mat)
    return plane


class TestLiveSampleRenderPixels(LiveBpyTestCase):
    def _render(self, engine="BLENDER_EEVEE_NEXT"):
        scene = bpy.context.scene
        scene.view_settings.view_transform = "Standard"
        render_tool = self.get_tool("render_scene")
        result = render_tool.execute(
            {
                "engine": engine,
                "resolution_x": 64,
                "resolution_y": 64,
                "resolution_percentage": 100,
                "samples": 4,
            }
        )
        self.assertTrue(result.get("success"), result.get("message"))
        return result

    def test_sample_render_pixels_reads_render_result(self):
        _add_flat_color_plane(color=(1.0, 0.0, 1.0, 1.0))
        _add_topdown_camera()
        self._render()

        tool = self.get_tool("sample_render_pixels")
        result = tool.execute({"x": 28, "y": 28, "width": 8, "height": 8})

        self.assertTrue(result.get("success"), result.get("message"))
        r, g, b, a = result["average_rgba"]
        self.assertGreater(r, 0.9)
        self.assertLess(g, 0.1)
        self.assertGreater(b, 0.9)

    def test_sample_render_pixels_reads_saved_file(self):
        _add_flat_color_plane(color=(0.0, 1.0, 0.0, 1.0))
        _add_topdown_camera()
        out_path = os.path.join(tempfile.gettempdir(), "mcp_sample_pixels_test.png")
        render_tool = self.get_tool("render_scene")
        bpy.context.scene.view_settings.view_transform = "Standard"
        render_result = render_tool.execute(
            {
                "output_path": out_path,
                "engine": "BLENDER_EEVEE_NEXT",
                "resolution_x": 64,
                "resolution_y": 64,
                "samples": 4,
            }
        )
        self.assertTrue(render_result.get("success"), render_result.get("message"))

        tool = self.get_tool("sample_render_pixels")
        result = tool.execute({"x": 28, "y": 28, "width": 8, "height": 8, "image_path": render_result["output_path"]})

        self.assertTrue(result.get("success"), result.get("message"))
        r, g, b, a = result["average_rgba"]
        self.assertLess(r, 0.1)
        self.assertGreater(g, 0.9)

    def test_sample_render_pixels_rejects_out_of_bounds_region(self):
        _add_flat_color_plane()
        _add_topdown_camera()
        self._render()

        tool = self.get_tool("sample_render_pixels")
        result = tool.execute({"x": 60, "y": 60, "width": 16, "height": 16})

        self.assertFalse(result.get("success"))
        self.assertIn("outside image bounds", result.get("message", ""))

    def test_sample_render_pixels_rejects_missing_image_path(self):
        tool = self.get_tool("sample_render_pixels")
        result = tool.execute(
            {"x": 0, "y": 0, "width": 1, "height": 1, "image_path": "C:/nope/does_not_exist.png"}
        )
        self.assertFalse(result.get("success"))
        self.assertIn("not found", result.get("message", "").lower())


class TestLiveRaycastFromCamera(LiveBpyTestCase):
    def test_raycast_finds_occluder_between_camera_and_target(self):
        cam = _add_camera(location=(0, -10, 0), rotation=(1.5708, 0, 0))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, -3, 0))
        sphere = bpy.context.object
        sphere.name = "ControlSphere"
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 5, 0))
        cube = bpy.context.object
        cube.name = "Bear"

        tool = self.get_tool("raycast_from_camera")
        result = tool.execute({"camera_name": cam.name, "target_object": "Bear"})

        self.assertTrue(result.get("success"), result.get("message"))
        hit_names = [h["name"] for h in result["hits"]]
        self.assertEqual(hit_names[0], "ControlSphere")
        self.assertIn("Bear", hit_names)
        self.assertLess(result["hits"][0]["distance"], result["hits"][1]["distance"])

    def test_raycast_with_clear_path_finds_only_target(self):
        cam = _add_camera(location=(0, -10, 0), rotation=(1.5708, 0, 0))
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
        cube = bpy.context.object
        cube.name = "Bear"

        tool = self.get_tool("raycast_from_camera")
        result = tool.execute({"camera_name": cam.name, "target_object": "Bear"})

        self.assertTrue(result.get("success"), result.get("message"))
        self.assertEqual([h["name"] for h in result["hits"]], ["Bear"])

    def test_raycast_with_no_target_uses_camera_forward_direction(self):
        cam = _add_camera(location=(0, -10, 0), rotation=(1.5708, 0, 0))
        bpy.ops.mesh.primitive_cube_add(size=1.0, location=(0, 0, 0))
        cube = bpy.context.object
        cube.name = "InFront"

        tool = self.get_tool("raycast_from_camera")
        result = tool.execute({"camera_name": cam.name, "max_distance": 20.0})

        self.assertTrue(result.get("success"), result.get("message"))
        self.assertIn("InFront", [h["name"] for h in result["hits"]])

    def test_raycast_missing_camera_errors(self):
        tool = self.get_tool("raycast_from_camera")
        result = tool.execute({"camera_name": "NoSuchCamera"})
        self.assertFalse(result.get("success"))
