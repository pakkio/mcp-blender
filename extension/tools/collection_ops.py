import bpy

from .base import ToolBase


class ManageCollectionTool(ToolBase):
    name = "manage_collection"
    description = "Create, delete, rename collections, link/unlink objects, and set collection visibility."

    def execute(self, params: dict) -> dict:
        action = (params.get("action") or "CREATE").upper()
        name = params.get("name")

        if not name:
            return {"success": False, "message": "'name' is required"}

        if action == "CREATE":
            col = bpy.data.collections.get(name)
            if not col:
                col = bpy.data.collections.new(name)
                parent_name = params.get("parent_collection")
                if parent_name:
                    parent_col = bpy.data.collections.get(parent_name)
                    if parent_col:
                        parent_col.children.link(col)
                    else:
                        bpy.context.scene.collection.children.link(col)
                else:
                    bpy.context.scene.collection.children.link(col)

            return {
                "success": True,
                "message": f"Created collection '{col.name}'",
                "collection_name": col.name,
            }

        elif action == "DELETE":
            col = bpy.data.collections.get(name)
            if not col:
                return {"success": False, "message": f"Collection '{name}' not found"}
            bpy.data.collections.remove(col)
            return {"success": True, "message": f"Deleted collection '{name}'"}

        elif action == "RENAME":
            col = bpy.data.collections.get(name)
            new_name = params.get("new_name")
            if not col:
                return {"success": False, "message": f"Collection '{name}' not found"}
            if not new_name:
                return {"success": False, "message": "'new_name' is required for RENAME"}
            col.name = new_name
            return {"success": True, "message": f"Renamed collection '{name}' to '{col.name}'"}

        elif action == "LINK_OBJECT":
            col = bpy.data.collections.get(name)
            obj_name = params.get("object_name")
            if not col:
                return {"success": False, "message": f"Collection '{name}' not found"}
            if not obj_name:
                return {"success": False, "message": "'object_name' is required"}
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                return {"success": False, "message": f"Object '{obj_name}' not found"}
            if obj.name not in col.objects:
                col.objects.link(obj)
            return {"success": True, "message": f"Linked '{obj_name}' to collection '{name}'"}

        elif action == "UNLINK_OBJECT":
            col = bpy.data.collections.get(name)
            obj_name = params.get("object_name")
            if not col:
                return {"success": False, "message": f"Collection '{name}' not found"}
            if not obj_name:
                return {"success": False, "message": "'object_name' is required"}
            obj = bpy.data.objects.get(obj_name)
            if not obj:
                return {"success": False, "message": f"Object '{obj_name}' not found"}
            if obj.name in col.objects:
                col.objects.unlink(obj)
            return {"success": True, "message": f"Unlinked '{obj_name}' from collection '{name}'"}

        elif action == "SET_VISIBILITY":
            col = bpy.data.collections.get(name)
            if not col:
                return {"success": False, "message": f"Collection '{name}' not found"}
            if params.get("hide_viewport") is not None:
                col.hide_viewport = bool(params["hide_viewport"])
            if params.get("hide_render") is not None:
                col.hide_render = bool(params["hide_render"])
            return {
                "success": True,
                "message": f"Updated visibility for collection '{name}'",
                "hide_viewport": col.hide_viewport,
                "hide_render": col.hide_render,
            }

        return {"success": False, "message": f"Unknown action '{action}'"}
