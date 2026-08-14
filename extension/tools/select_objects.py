import bpy

from .base import ToolBase


class SelectObjectsTool(ToolBase):
    name = "select_objects"
    description = "Select/deselect objects in Blender, set the active object, and switch modes."

    def execute(self, params: dict) -> dict:
        names = params.get("names") or []
        action = (params.get("action") or "SET").upper()
        active_object_name = params.get("active_object")
        mode = params.get("mode")

        # Make sure we're in OBJECT mode before doing bulk selections if not specified
        if bpy.context.mode != "OBJECT" and mode != bpy.context.mode:
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except Exception:
                pass

        if action == "SELECT_ALL":
            bpy.ops.object.select_all(action="SELECT")
        elif action == "DESELECT_ALL":
            bpy.ops.object.select_all(action="DESELECT")
        elif action == "INVERT":
            bpy.ops.object.select_all(action="INVERT")
        elif action == "SET":
            bpy.ops.object.select_all(action="DESELECT")
            for name in names:
                obj = bpy.data.objects.get(name)
                if obj:
                    obj.select_set(True)
        elif action == "SELECT":
            for name in names:
                obj = bpy.data.objects.get(name)
                if obj:
                    obj.select_set(True)
        elif action == "DESELECT":
            for name in names:
                obj = bpy.data.objects.get(name)
                if obj:
                    obj.select_set(False)

        # Set active object
        if active_object_name:
            active_obj = bpy.data.objects.get(active_object_name)
            if active_obj:
                bpy.context.view_layer.objects.active = active_obj
                active_obj.select_set(True)

        # Switch mode if requested
        if mode:
            mode_upper = mode.upper()
            try:
                bpy.ops.object.mode_set(mode=mode_upper)
            except Exception as exc:
                return {
                    "success": False,
                    "message": f"Failed to switch to mode '{mode_upper}': {exc}",
                }

        selected = [obj.name for obj in bpy.context.selected_objects]
        active = bpy.context.active_object.name if bpy.context.active_object else None

        return {
            "success": True,
            "message": f"Selection updated. {len(selected)} object(s) selected.",
            "selected_objects": selected,
            "active_object": active,
            "current_mode": bpy.context.mode,
        }
