import bpy

from .base import ToolBase


class SetObjectPropertiesTool(ToolBase):
    name = "set_object_properties"
    description = "Set visibility, viewport color, rename, and custom properties on a Blender object."

    def execute(self, params: dict) -> dict:
        name = params.get("name")
        if not name:
            return {"success": False, "message": "'name' is required"}

        obj = bpy.data.objects.get(name)
        if not obj:
            return {"success": False, "message": f"Object '{name}' not found"}

        if params.get("new_name"):
            obj.name = params["new_name"]

        if params.get("hide_viewport") is not None:
            obj.hide_set(bool(params["hide_viewport"]))

        if params.get("hide_render") is not None:
            obj.hide_render = bool(params["hide_render"])

        if params.get("color") is not None:
            obj.color = tuple(params["color"])

        if params.get("custom_properties"):
            for k, v in params["custom_properties"].items():
                obj[k] = v

        return {
            "success": True,
            "message": f"Updated properties for '{obj.name}'",
            "name": obj.name,
            "hide_viewport": obj.hide_get(),
            "hide_render": obj.hide_render,
            "color": [round(c, 4) for c in obj.color],
        }
