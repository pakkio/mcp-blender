import base64
import os
import tempfile
import time
import bpy
import numpy as np

from .base import ToolBase


# render_scene has no cancellation (bpy.ops.render.render blocks the main
# thread until it finishes, the same shape of hang simplify_geometry used to
# cause), so the only defense against an accidental multi-hour render is
# refusing to start one whose parameters -- taken from whatever the scene
# happens to carry when neither is passed explicitly -- are wildly past what
# a reasonable interactive/inspection render needs. Reasoned defaults, not
# measured; override with force=true for a deliberate final-quality render.
_MAX_RESOLUTION_PX = 8192
_MAX_SAMPLES = 4096

# sample_render_pixels' fallback when no image_path is given. Deliberately not
# the in-memory "Render Result" datablock: in background/headless Blender
# (the common way this bridge itself gets driven) Render Result's .size can
# read back as 0x0 even right after a successful render, since there's no
# display/window holding its pixel buffer live. render_scene always writes a
# file -- even to a throwaway temp path when output_path isn't given -- so
# tracking that path is a strictly more reliable "last render" reference.
_last_render_output_path = None


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

        force = bool(params.get("force", False))
        if not force:
            eff_res_x = scene.render.resolution_x * scene.render.resolution_percentage // 100
            eff_res_y = scene.render.resolution_y * scene.render.resolution_percentage // 100
            if eff_res_x > _MAX_RESOLUTION_PX or eff_res_y > _MAX_RESOLUTION_PX:
                return {
                    "success": False,
                    "message": (
                        f"Refusing to render at {eff_res_x}x{eff_res_y}px (cap {_MAX_RESOLUTION_PX}px/axis): "
                        "lower resolution_x/resolution_y/resolution_percentage, or pass force=true to render anyway."
                    ),
                }
            samples = None
            if scene.render.engine == "CYCLES":
                samples = scene.cycles.samples
            elif hasattr(scene, "eevee") and hasattr(scene.eevee, "taa_render_samples"):
                samples = scene.eevee.taa_render_samples
            if samples is not None and samples > _MAX_SAMPLES:
                return {
                    "success": False,
                    "message": (
                        f"Refusing to render at {samples} samples (cap {_MAX_SAMPLES}): pass a lower "
                        "'samples' param, or force=true to render anyway."
                    ),
                }

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

        if not is_animation and os.path.exists(actual_path):
            global _last_render_output_path
            _last_render_output_path = actual_path

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


class SampleRenderPixelsTool(ToolBase):
    name = "sample_render_pixels"
    description = (
        "Sample pixel colors from a rendered image over a region, to confirm what "
        "actually reached the render output (e.g. verify a material's color shows "
        "up, or that an object isn't occluded) without decoding a full base64 image."
    )

    def execute(self, params: dict) -> dict:
        x = int(params.get("x", 0))
        y = int(params.get("y", 0))
        width = max(1, int(params.get("width", 1)))
        height = max(1, int(params.get("height", 1)))
        image_path = params.get("image_path")

        if not image_path and _last_render_output_path and os.path.exists(_last_render_output_path):
            image_path = _last_render_output_path

        loaded_image = None
        if image_path:
            if not os.path.exists(image_path):
                return {"success": False, "message": f"Image not found: {image_path}"}
            # check_existing=False: always a fresh, disposable datablock read
            # straight off disk. check_existing=True would instead hand back
            # whatever bpy.data.images entry already has this filepath (stale
            # pixels if that path was rendered to more than once), and this
            # tool unconditionally removes what it loads once done -- doing
            # that to a datablock it didn't create would be a spooky-action
            # side effect on whatever else in the scene was using it.
            image = bpy.data.images.load(image_path, check_existing=False)
            loaded_image = image
        else:
            image = bpy.data.images.get("Render Result")
            if image is None or image.size[0] == 0 or image.size[1] == 0:
                return {
                    "success": False,
                    "message": "No renderable image available -- call render_scene first, or pass image_path.",
                }

        try:
            img_w, img_h = image.size
            if img_w == 0 or img_h == 0:
                return {"success": False, "message": "Image has no pixel data (0x0) -- render may not have completed."}
            if x < 0 or y < 0 or x + width > img_w or y + height > img_h:
                return {
                    "success": False,
                    "message": f"Region (x={x}, y={y}, {width}x{height}) is outside image bounds {img_w}x{img_h}.",
                }

            # foreach_get + numpy rather than list(image.pixels): the latter
            # copies the entire image (millions of floats for a normal render)
            # into a Python list just to read a small region.
            flat = np.empty(img_w * img_h * 4, dtype=np.float32)
            image.pixels.foreach_get(flat)
            pixels = flat.reshape(img_h, img_w, 4)
            region = pixels[y : y + height, x : x + width]

            avg = region.reshape(-1, 4).mean(axis=0)

            return {
                "success": True,
                "image_size": [img_w, img_h],
                "region": [x, y, width, height],
                "average_rgba": [round(float(c), 4) for c in avg],
                "note": "Origin (0,0) is bottom-left, matching Blender's own pixel/image convention.",
            }
        finally:
            if loaded_image is not None:
                bpy.data.images.remove(loaded_image)
