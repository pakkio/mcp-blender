import bpy

from .base import ToolBase


class ApplyTransformTool(ToolBase):
    name = "apply_transform"
    description = "Apply location, rotation, and/or scale transforms to the object's mesh/curve data."

    def execute(self, params: dict) -> dict:
        name = params.get("name")
        if not name:
            return {"success": False, "message": "'name' is required"}

        obj = bpy.data.objects.get(name)
        if not obj:
            return {"success": False, "message": f"Object '{name}' not found"}

        apply_loc = params.get("location", False)
        apply_rot = params.get("rotation", False)
        apply_sca = params.get("scale", True)

        # In order to use bpy.ops.object.transform_apply, the object must be active and selected
        prev_active = bpy.context.active_object
        prev_selected = [o for o in bpy.context.selected_objects]

        try:
            if bpy.context.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")

            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            bpy.ops.object.transform_apply(location=apply_loc, rotation=apply_rot, scale=apply_sca)
        finally:
            # Restore selection
            bpy.ops.object.select_all(action="DESELECT")
            for o in prev_selected:
                if o.name in bpy.data.objects:
                    o.select_set(True)
            if prev_active and prev_active.name in bpy.data.objects:
                bpy.context.view_layer.objects.active = prev_active

        return {
            "success": True,
            "message": f"Applied transform to '{obj.name}' (location={apply_loc}, rotation={apply_rot}, scale={apply_sca})",
            "name": obj.name,
            "location": [round(v, 4) for v in obj.location],
            "rotation_euler": [round(v, 4) for v in obj.rotation_euler],
            "scale": [round(v, 4) for v in obj.scale],
        }
