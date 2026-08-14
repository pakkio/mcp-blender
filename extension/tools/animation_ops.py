import bpy

from .base import ToolBase


def _get_action_fcurves(action, obj=None):
    """Retrieve fcurves across Blender versions (legacy fcurves vs Blender 4.4+/5.x layered actions)."""
    if action is None:
        return []
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    curves = []
    if hasattr(action, "layers"):
        for layer in action.layers:
            for strip in layer.strips:
                if hasattr(strip, "channelbags"):
                    for cb in strip.channelbags:
                        if hasattr(cb, "fcurves"):
                            curves.extend(cb.fcurves)
                elif hasattr(strip, "channelbag"):
                    cb = strip.channelbag(obj.animation_data.action_slot) if (obj and hasattr(obj, "animation_data") and hasattr(obj.animation_data, "action_slot")) else None
                    if cb and hasattr(cb, "fcurves"):
                        curves.extend(cb.fcurves)
    return curves


class SetKeyframeTool(ToolBase):
    name = "set_keyframe"
    description = "Insert a keyframe for location, rotation, scale, or custom properties on an object at a specific frame."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        frame = params.get("frame")
        data_path = params.get("data_path", "location")
        value = params.get("value")
        interpolation = params.get("interpolation", "BEZIER")

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}
        if frame is None:
            return {"success": False, "message": "'frame' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        # If custom property
        if data_path == "custom":
            prop_name = params.get("custom_property_name")
            if not prop_name:
                return {"success": False, "message": "'custom_property_name' is required for custom data_path"}
            if value is not None:
                obj[prop_name] = value[0] if isinstance(value, list) and len(value) == 1 else value
            obj.keyframe_insert(data_path=f'["{prop_name}"]', frame=frame)
        else:
            # Set value if provided
            if value is not None:
                if data_path == "location":
                    obj.location = tuple(value)
                elif data_path == "rotation_euler":
                    obj.rotation_euler = tuple(value)
                elif data_path == "scale":
                    obj.scale = tuple(value)

            obj.keyframe_insert(data_path=data_path, frame=frame)

        # Set interpolation mode if action exists
        if obj.animation_data and obj.animation_data.action and interpolation:
            for fcurve in _get_action_fcurves(obj.animation_data.action, obj):
                if fcurve.data_path.startswith(data_path) or (data_path == "custom" and prop_name in fcurve.data_path):
                    for kf in fcurve.keyframe_points:
                        if int(kf.co[0]) == int(frame):
                            kf.interpolation = interpolation

        return {
            "success": True,
            "message": f"Inserted keyframe on '{obj.name}.{data_path}' at frame {frame}",
            "object_name": obj.name,
            "data_path": data_path,
            "frame": frame,
        }


class DeleteKeyframeTool(ToolBase):
    name = "delete_keyframe"
    description = "Delete keyframes on an object for a specific frame or frame range."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        frame = params.get("frame")
        data_path = params.get("data_path")
        frame_range = params.get("frame_range")

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or not obj.animation_data or not obj.animation_data.action:
            return {"success": False, "message": f"Object '{object_name}' has no animation data"}

        action = obj.animation_data.action
        deleted_points = 0

        for fcurve in _get_action_fcurves(action, obj):
            if data_path and not fcurve.data_path.startswith(data_path):
                continue

            points_to_remove = []
            for kf in fcurve.keyframe_points:
                kf_frame = int(kf.co[0])
                if frame is not None and kf_frame == frame:
                    points_to_remove.append(kf)
                elif frame_range and (frame_range[0] <= kf_frame <= frame_range[1]):
                    points_to_remove.append(kf)

            for pt in points_to_remove:
                fcurve.keyframe_points.remove(pt)
                deleted_points += 1

        return {
            "success": True,
            "message": f"Deleted {deleted_points} keyframe points on '{obj.name}'",
            "object_name": obj.name,
            "deleted_points": deleted_points,
        }


class SetTimelineRangeTool(ToolBase):
    name = "set_timeline_range"
    description = "Configure timeline start/end frame, current frame, and FPS."

    def execute(self, params: dict) -> dict:
        scene = bpy.context.scene

        if params.get("frame_start") is not None:
            scene.frame_start = int(params["frame_start"])

        if params.get("frame_end") is not None:
            scene.frame_end = int(params["frame_end"])

        if params.get("frame_current") is not None:
            scene.frame_set(int(params["frame_current"]))

        if params.get("fps") is not None:
            scene.render.fps = int(params["fps"])

        return {
            "success": True,
            "message": f"Timeline set to frames {scene.frame_start}-{scene.frame_end} (current: {scene.frame_current}, fps: {scene.render.fps})",
            "frame_start": scene.frame_start,
            "frame_end": scene.frame_end,
            "frame_current": scene.frame_current,
            "fps": scene.render.fps,
        }
