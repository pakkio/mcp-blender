import bpy
from .base import ToolBase


class SetupCameraTrackingTool(ToolBase):
    name = "setup_camera_tracking"
    description = "Configure camera and background movie clip tracking parameters for visual effects (VFX) matchmoving."

    def execute(self, params: dict) -> dict:
        camera_name = params.get("camera_name", "Camera")
        clip_path = params.get("clip_path")
        focal_length = float(params.get("focal_length", 35.0))
        sensor_width = float(params.get("sensor_width", 36.0))
        use_motion_blur = bool(params.get("use_motion_blur", True))

        cam_obj = bpy.data.objects.get(camera_name)
        if not cam_obj or cam_obj.type != "CAMERA":
            return {"success": False, "message": f"Camera '{camera_name}' not found"}

        cam_data = cam_obj.data
        cam_data.lens = focal_length
        cam_data.sensor_width = sensor_width

        if clip_path:
            try:
                clip = bpy.data.movieclips.load(clip_path)
                cam_data.show_background_images = True
                bg = cam_data.background_images.new()
                bg.source = "MOVIE_CLIP"
                bg.clip = clip
            except Exception as exc:
                return {"success": False, "message": f"Failed to load movie clip '{clip_path}': {exc}"}

        bpy.context.scene.render.use_motion_blur = use_motion_blur

        return {
            "success": True,
            "message": f"Configured camera '{camera_name}' for VFX tracking (focal={focal_length}mm, sensor={sensor_width}mm)",
            "camera_name": camera_name,
            "focal_length": focal_length,
            "sensor_width": sensor_width,
            "motion_blur": use_motion_blur,
        }


class SetupVFXShadowCatcherTool(ToolBase):
    name = "setup_vfx_shadow_catcher"
    description = "Create an invisible ground plane that catches 3D object shadows and reflections over live-action VFX plates."

    def execute(self, params: dict) -> dict:
        name = params.get("name", "VFX_Shadow_Catcher")
        size = float(params.get("size", 10.0))
        location = params.get("location", [0.0, 0.0, 0.0])
        transparent_film = bool(params.get("transparent_film", True))

        mesh = bpy.data.meshes.new(f"{name}_Mesh")
        plane_obj = bpy.data.objects.new(name, mesh)
        plane_obj.location = location
        bpy.context.scene.collection.objects.link(plane_obj)

        half = size / 2.0
        verts = [(-half, -half, 0), (half, -half, 0), (half, half, 0), (-half, half, 0)]
        faces = [(0, 1, 2, 3)]
        mesh.from_pydata(verts, [], faces)
        mesh.update()

        # Set shadow catcher property
        plane_obj.is_shadow_catcher = True

        if transparent_film:
            bpy.context.scene.render.film_transparent = True

        return {
            "success": True,
            "message": f"Created VFX shadow catcher plane '{plane_obj.name}' (size={size})",
            "object_name": plane_obj.name,
            "is_shadow_catcher": True,
            "film_transparent": bpy.context.scene.render.film_transparent,
        }
