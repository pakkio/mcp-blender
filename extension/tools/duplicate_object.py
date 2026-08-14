import bpy
import mathutils

from .base import ToolBase


class DuplicateObjectTool(ToolBase):
    name = "duplicate_object"
    description = "Duplicate an object (linked or unlinked) with optional offset, name, and collection."

    def execute(self, params: dict) -> dict:
        name = params.get("name")
        if not name:
            return {"success": False, "message": "'name' parameter is required"}

        obj = bpy.data.objects.get(name)
        if obj is None:
            return {"success": False, "message": f"Object '{name}' not found"}

        linked = params.get("linked", False)
        new_name = params.get("new_name")
        offset = params.get("offset") or [0.0, 0.0, 0.0]
        collection_name = params.get("collection")

        # Create copy of object
        new_obj = obj.copy()
        if not linked and obj.data:
            new_obj.data = obj.data.copy()

        if new_name:
            new_obj.name = new_name

        # Apply offset
        new_obj.location = (
            obj.location.x + offset[0],
            obj.location.y + offset[1],
            obj.location.z + offset[2],
        )

        # Link to collection
        target_collection = bpy.data.collections.get(collection_name) if collection_name else None
        if target_collection:
            target_collection.objects.link(new_obj)
        elif obj.users_collection:
            obj.users_collection[0].objects.link(new_obj)
        else:
            bpy.context.scene.collection.objects.link(new_obj)

        return {
            "success": True,
            "message": f"Duplicated '{obj.name}' to '{new_obj.name}'",
            "name": new_obj.name,
            "original_name": obj.name,
            "type": new_obj.type,
            "location": [round(v, 4) for v in new_obj.location],
            "linked": linked,
        }
