import base64
import os
import tempfile
import time
import bpy

from .base import ToolBase


def _set_render_engine(scene, engine: str):
    engine_upper = engine.upper()
    if engine_upper in ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT", "EEVEE"):
        try:
            scene.render.engine = "BLENDER_EEVEE_NEXT"
        except Exception:
            scene.render.engine = "BLENDER_EEVEE"
    elif engine_upper in ("CYCLES", "WORKBENCH", "BLENDER_WORKBENCH"):
        if engine_upper == "CYCLES":
            scene.render.engine = "CYCLES"
        else:
            scene.render.engine = "BLENDER_WORKBENCH"


class RenderSceneTool(ToolBase):
    name = "render_scene"
    description = "Render the active scene to an image file or base64 string, with customizable engine, resolution, and samples."

    def execute(self, params: dict) -> dict:
        scene = bpy.context.scene

        output_path = params.get("output_path")
        if not output_path:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"blender_render_{int(time.time())}.png")

        # Normalize directory path
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        engine = params.get("engine")
        if engine:
            _set_render_engine(scene, engine)

        if params.get("resolution_x") is not None:
            scene.render.resolution_x = int(params["resolution_x"])

        if params.get("resolution_y") is not None:
            scene.render.resolution_y = int(params["resolution_y"])

        if params.get("resolution_percentage") is not None:
            scene.render.resolution_percentage = int(params["resolution_percentage"])

        if params.get("samples") is not None:
            if scene.render.engine == "CYCLES":
                scene.cycles.samples = int(params["samples"])
            elif hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = int(params["samples"])

        if params.get("transparent_background") is not None:
            scene.render.film_transparent = bool(params["transparent_background"])

        scene.render.filepath = output_path
        scene.render.image_settings.file_format = "PNG"

        is_animation = params.get("animation", False)

        start_time = time.time()
        try:
            if is_animation:
                bpy.ops.render.render(animation=True, write_still=True)
            else:
                bpy.ops.render.render(write_still=True)
        except Exception as exc:
            return {"success": False, "message": f"Render failed: {exc}"}

        elapsed = round(time.time() - start_time, 2)

        # Actual saved path might have frame number if animation or extension
        actual_path = output_path
        if not os.path.exists(actual_path) and os.path.exists(output_path + ".png"):
            actual_path = output_path + ".png"

        image_base64 = None
        if params.get("return_image_base64", False) and os.path.exists(actual_path):
            with open(actual_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

        result = {
            "success": True,
            "message": f"Render completed in {elapsed}s",
            "output_path": actual_path,
            "render_time_seconds": elapsed,
            "engine": scene.render.engine,
            "resolution": [
                scene.render.resolution_x * scene.render.resolution_percentage // 100,
                scene.render.resolution_y * scene.render.resolution_percentage // 100,
            ],
        }

        if image_base64:
            result["image_base64"] = image_base64

        return result


class GetViewportScreenshotTool(ToolBase):
    name = "get_viewport_screenshot"
    description = "Quickly capture an OpenGL viewport screenshot to preview the scene."

    def execute(self, params: dict) -> dict:
        scene = bpy.context.scene
        output_path = params.get("output_path")
        if not output_path:
            temp_dir = tempfile.gettempdir()
            output_path = os.path.join(temp_dir, f"blender_viewport_{int(time.time())}.png")

        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        scene.render.filepath = output_path
        scene.render.image_settings.file_format = "PNG"

        try:
            bpy.ops.render.opengl(write_still=True)
        except Exception as exc:
            return {"success": False, "message": f"Viewport render failed: {exc}"}

        actual_path = output_path
        if not os.path.exists(actual_path) and os.path.exists(output_path + ".png"):
            actual_path = output_path + ".png"

        image_base64 = None
        if params.get("return_image_base64", True) and os.path.exists(actual_path):
            with open(actual_path, "rb") as f:
                image_base64 = base64.b64encode(f.read()).decode("utf-8")

        res = {
            "success": True,
            "message": f"Captured viewport screenshot to '{actual_path}'",
            "output_path": actual_path,
        }
        if image_base64:
            res["image_base64"] = image_base64
        return res


class SetRenderSettingsTool(ToolBase):
    name = "set_render_settings"
    description = "Set render settings including engine, device (GPU/CPU), resolution, color management, and samples."

    def execute(self, params: dict) -> dict:
        scene = bpy.context.scene

        if params.get("engine"):
            _set_render_engine(scene, params["engine"])

        if params.get("resolution_x") is not None:
            scene.render.resolution_x = int(params["resolution_x"])

        if params.get("resolution_y") is not None:
            scene.render.resolution_y = int(params["resolution_y"])

        if params.get("resolution_percentage") is not None:
            scene.render.resolution_percentage = int(params["resolution_percentage"])

        if params.get("device"):
            device_upper = params["device"].upper()
            if hasattr(scene, "cycles"):
                scene.cycles.device = device_upper

        if params.get("samples") is not None:
            if scene.render.engine == "CYCLES":
                scene.cycles.samples = int(params["samples"])
            elif hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
                scene.eevee.taa_render_samples = int(params["samples"])

        if params.get("transparent_background") is not None:
            scene.render.film_transparent = bool(params["transparent_background"])

        if params.get("color_management_view_transform"):
            scene.view_settings.view_transform = params["color_management_view_transform"]

        return {
            "success": True,
            "message": "Updated render settings",
            "engine": scene.render.engine,
            "resolution": [scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage],
            "film_transparent": scene.render.film_transparent,
            "view_transform": scene.view_settings.view_transform,
        }
