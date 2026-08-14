import bpy

from .base import ToolBase


class DeleteObjectTool(ToolBase):
    name = "delete_object"
    description = "Delete one or more objects from the scene by name, with optional hierarchy deletion."

    def execute(self, params: dict) -> dict:
        names = []
        if params.get("name"):
            names.append(params["name"])
        if params.get("names"):
            names.extend(params["names"])

        if not names:
            return {"success": False, "message": "Either 'name' or 'names' must be provided"}

        delete_hierarchy = params.get("delete_hierarchy", False)

        def _collect_descendants(obj, collected: set):
            for child in obj.children:
                if child not in collected:
                    collected.add(child)
                    _collect_descendants(child, collected)

        objects_to_delete = set()
        for name in names:
            obj = bpy.data.objects.get(name)
            if obj:
                objects_to_delete.add(obj)
                if delete_hierarchy:
                    _collect_descendants(obj, objects_to_delete)

        if not objects_to_delete:
            return {"success": False, "message": f"None of the specified objects were found: {names}"}

        deleted_names = []
        for obj in list(objects_to_delete):
            deleted_names.append(obj.name)
            bpy.data.objects.remove(obj, do_unlink=True)

        return {
            "success": True,
            "message": f"Deleted {len(deleted_names)} object(s)",
            "deleted_count": len(deleted_names),
            "deleted_names": deleted_names,
        }
