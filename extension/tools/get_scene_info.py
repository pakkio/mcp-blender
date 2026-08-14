import bpy

from .base import ToolBase


class GetSceneInfoTool(ToolBase):
    name = "get_scene_info"
    description = "Get comprehensive information about the active Blender scene."

    def execute(self, params: dict) -> dict:
        scene = bpy.context.scene
        include_objects = params.get("include_objects", True)
        include_collections = params.get("include_collections", True)
        include_materials = params.get("include_materials", True)
        include_lights = params.get("include_lights", True)
        include_cameras = params.get("include_cameras", True)

        active_obj = bpy.context.active_object
        active_obj_name = active_obj.name if active_obj else None
        selected_obj_names = [obj.name for obj in bpy.context.selected_objects]

        data = {
            "success": True,
            "scene_name": scene.name,
            "frame_current": scene.frame_current,
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "fps": scene.render.fps,
            "render_engine": scene.render.engine,
            "resolution": [
                scene.render.resolution_x,
                scene.render.resolution_y,
                scene.render.resolution_percentage,
            ],
            "unit_system": scene.unit_settings.system,
            "active_object": active_obj_name,
            "selected_objects": selected_obj_names,
            "objects_count": len(scene.objects),
        }

        if include_objects:
            data["objects"] = [
                {
                    "name": obj.name,
                    "type": obj.type,
                    "location": [round(v, 4) for v in obj.location],
                    "rotation_euler": [round(v, 4) for v in obj.rotation_euler],
                    "scale": [round(v, 4) for v in obj.scale],
                    "hide_viewport": obj.hide_get(),
                    "hide_render": obj.hide_render,
                }
                for obj in scene.objects
            ]

        if include_collections:
            data["collections"] = [
                {
                    "name": col.name,
                    "objects_count": len(col.objects),
                    "hide_viewport": col.hide_viewport,
                    "hide_render": col.hide_render,
                }
                for col in bpy.data.collections
            ]

        if include_materials:
            data["materials"] = [
                {
                    "name": mat.name,
                    "users": mat.users,
                    "use_nodes": mat.use_nodes,
                }
                for mat in bpy.data.materials
            ]

        if include_cameras:
            active_cam = scene.camera.name if scene.camera else None
            data["cameras"] = [
                {
                    "name": obj.name,
                    "lens": getattr(obj.data, "lens", None),
                    "is_active": (obj.name == active_cam),
                }
                for obj in scene.objects
                if obj.type == "CAMERA"
            ]

        if include_lights:
            data["lights"] = [
                {
                    "name": obj.name,
                    "type": getattr(obj.data, "type", None),
                    "energy": getattr(obj.data, "energy", None),
                    "color": [round(v, 4) for v in getattr(obj.data, "color", [1, 1, 1])],
                }
                for obj in scene.objects
                if obj.type == "LIGHT"
            ]

        data["message"] = f"Scene '{scene.name}' has {len(scene.objects)} object(s)"
        return data
