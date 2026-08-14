import bpy

from .base import ToolBase


def _apply_modifier_properties(modifier, properties: dict):
    for prop_name, prop_val in properties.items():
        if not hasattr(modifier, prop_name):
            continue
        # Handle object references
        if prop_name in ("object", "target", "mirror_object") and isinstance(prop_val, str):
            target_obj = bpy.data.objects.get(prop_val)
            if target_obj:
                setattr(modifier, prop_name, target_obj)
        elif isinstance(prop_val, list):
            setattr(modifier, prop_name, tuple(prop_val))
        else:
            setattr(modifier, prop_name, prop_val)


class AddModifierTool(ToolBase):
    name = "add_modifier"
    description = "Add a modifier (Subsurf, Bevel, Boolean, Mirror, Array, Solidify, etc.) to an object."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        modifier_type = (params.get("modifier_type") or "").upper()
        modifier_name = params.get("name") or modifier_type.capitalize()
        properties = params.get("properties") or {}

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}
        if not modifier_type:
            return {"success": False, "message": "'modifier_type' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        try:
            mod = obj.modifiers.new(name=modifier_name, type=modifier_type)
        except Exception as exc:
            return {"success": False, "message": f"Failed to add modifier '{modifier_type}': {exc}"}

        _apply_modifier_properties(mod, properties)

        return {
            "success": True,
            "message": f"Added modifier '{mod.name}' ({mod.type}) to '{obj.name}'",
            "object_name": obj.name,
            "modifier_name": mod.name,
            "modifier_type": mod.type,
        }


class ApplyModifierTool(ToolBase):
    name = "apply_modifier"
    description = "Apply a modifier permanently to an object's geometry."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        modifier_name = params.get("modifier_name")

        if not object_name or not modifier_name:
            return {"success": False, "message": "'object_name' and 'modifier_name' are required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        mod = obj.modifiers.get(modifier_name)
        if not mod:
            return {"success": False, "message": f"Modifier '{modifier_name}' not found on '{object_name}'"}

        prev_active = bpy.context.active_object
        prev_selected = [o for o in bpy.context.selected_objects]

        try:
            if bpy.context.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")

            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            bpy.ops.object.modifier_apply(modifier=modifier_name)
        except Exception as exc:
            return {"success": False, "message": f"Failed to apply modifier '{modifier_name}': {exc}"}
        finally:
            bpy.ops.object.select_all(action="DESELECT")
            for o in prev_selected:
                if o.name in bpy.data.objects:
                    o.select_set(True)
            if prev_active and prev_active.name in bpy.data.objects:
                bpy.context.view_layer.objects.active = prev_active

        return {
            "success": True,
            "message": f"Applied modifier '{modifier_name}' on '{obj.name}'",
            "object_name": obj.name,
            "modifier_name": modifier_name,
        }


class RemoveModifierTool(ToolBase):
    name = "remove_modifier"
    description = "Remove a modifier from an object."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        modifier_name = params.get("modifier_name")

        if not object_name or not modifier_name:
            return {"success": False, "message": "'object_name' and 'modifier_name' are required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        mod = obj.modifiers.get(modifier_name)
        if not mod:
            return {"success": False, "message": f"Modifier '{modifier_name}' not found on '{object_name}'"}

        obj.modifiers.remove(mod)

        return {
            "success": True,
            "message": f"Removed modifier '{modifier_name}' from '{obj.name}'",
            "object_name": obj.name,
            "modifier_name": modifier_name,
        }


class SetModifierPropertiesTool(ToolBase):
    name = "set_modifier_properties"
    description = "Update properties on an existing modifier."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        modifier_name = params.get("modifier_name")
        properties = params.get("properties") or {}

        if not object_name or not modifier_name:
            return {"success": False, "message": "'object_name' and 'modifier_name' are required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        mod = obj.modifiers.get(modifier_name)
        if not mod:
            return {"success": False, "message": f"Modifier '{modifier_name}' not found on '{object_name}'"}

        _apply_modifier_properties(mod, properties)

        return {
            "success": True,
            "message": f"Updated properties for modifier '{modifier_name}' on '{obj.name}'",
            "object_name": obj.name,
            "modifier_name": modifier_name,
        }
