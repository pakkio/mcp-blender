import bpy

from .base import ToolBase


class ParentObjectsTool(ToolBase):
    name = "parent_objects"
    description = "Set parent-child relationship between Blender objects."

    def execute(self, params: dict) -> dict:
        parent_name = params.get("parent_name")
        child_names = params.get("child_names") or []
        keep_transform = params.get("keep_transform", True)
        parent_type = (params.get("parent_type") or "OBJECT").upper()

        if not parent_name:
            return {"success": False, "message": "'parent_name' is required"}
        if not child_names:
            return {"success": False, "message": "'child_names' list cannot be empty"}

        parent_obj = bpy.data.objects.get(parent_name)
        if not parent_obj:
            return {"success": False, "message": f"Parent object '{parent_name}' not found"}

        parented = []
        for c_name in child_names:
            child_obj = bpy.data.objects.get(c_name)
            if not child_obj:
                continue
            if child_obj == parent_obj:
                continue

            if keep_transform:
                child_matrix = child_obj.matrix_world.copy()
                child_obj.parent = parent_obj
                child_obj.parent_type = parent_type
                child_obj.matrix_world = child_matrix
            else:
                child_obj.parent = parent_obj
                child_obj.parent_type = parent_type

            parented.append(c_name)

        return {
            "success": True,
            "message": f"Parented {len(parented)} object(s) to '{parent_name}'",
            "parent_name": parent_name,
            "children": parented,
        }


class UnparentObjectsTool(ToolBase):
    name = "unparent_objects"
    description = "Clear parent relationship for specified objects."

    def execute(self, params: dict) -> dict:
        names = params.get("names") or []
        if params.get("name"):
            names.append(params["name"])

        if not names:
            return {"success": False, "message": "At least one object name is required"}

        keep_transform = params.get("keep_transform", True)
        unparented = []

        for name in names:
            obj = bpy.data.objects.get(name)
            if not obj or not obj.parent:
                continue

            if keep_transform:
                world_matrix = obj.matrix_world.copy()
                obj.parent = None
                obj.matrix_world = world_matrix
            else:
                obj.parent = None

            unparented.append(name)

        return {
            "success": True,
            "message": f"Unparented {len(unparented)} object(s)",
            "unparented": unparented,
        }
