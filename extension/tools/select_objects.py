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

        original_mode = bpy.context.mode

        # bpy.ops.object.select_all() requires OBJECT mode context, but
        # per-name SELECT/DESELECT use obj.select_set() directly which
        # works in any mode -- only force a (temporary) OBJECT-mode detour
        # for the actions that actually need it, and restore whatever mode
        # the caller was in afterward rather than stranding them in OBJECT
        # mode as a side effect of a plain selection call.
        needs_object_mode = action in ("SELECT_ALL", "DESELECT_ALL", "INVERT", "SET")
        forced_object_mode = False
        if needs_object_mode and bpy.context.mode != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
                forced_object_mode = True
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
        elif forced_object_mode and original_mode != "OBJECT":
            # No mode was explicitly requested -- undo the temporary OBJECT
            # mode detour so this call doesn't leave the user's editor mode
            # changed as an unrequested side effect.
            restore_mode = "EDIT" if original_mode.startswith("EDIT") else original_mode
            try:
                bpy.ops.object.mode_set(mode=restore_mode)
            except Exception:
                pass

        selected = [obj.name for obj in bpy.context.selected_objects]
        active = bpy.context.active_object.name if bpy.context.active_object else None

        return {
            "success": True,
            "message": f"Selection updated. {len(selected)} object(s) selected.",
            "selected_objects": selected,
            "active_object": active,
            "current_mode": bpy.context.mode,
        }
