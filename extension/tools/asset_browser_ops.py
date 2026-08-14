import os
import bpy

from .base import ToolBase


class ManageAssetBrowserTool(ToolBase):
    name = "manage_asset_browser"
    description = "Mark/unmark datablocks (objects, materials, node groups, worlds, actions) as Blender Assets, set catalog ID, description, author, and tags."

    def execute(self, params: dict) -> dict:
        action = params.get("action", "ASSET_MARK").upper()
        asset_type = (params.get("asset_type") or params.get("datablock_type") or "OBJECT").upper()
        target_name = params.get("target_name") or params.get("datablock_name") or params.get("name")
        description = params.get("description", "")
        author = params.get("author", "")
        tags = params.get("tags", [])

        if not target_name:
            return {"success": False, "message": "'target_name' or 'datablock_name' is required"}

        # Find target datablock
        db = None
        if asset_type == "OBJECT":
            db = bpy.data.objects.get(target_name)
        elif asset_type == "MATERIAL":
            db = bpy.data.materials.get(target_name)
        elif asset_type in ("NODE_GROUP", "GEOMETRY_NODES"):
            db = bpy.data.node_groups.get(target_name)
        elif asset_type == "WORLD":
            db = bpy.data.worlds.get(target_name)
        elif asset_type == "ACTION":
            db = bpy.data.actions.get(target_name)

        if not db:
            return {"success": False, "message": f"{asset_type} datablock '{target_name}' not found"}

        if action in ("ASSET_MARK", "MARK"):
            if not db.asset_data:
                db.asset_mark()

            ad = db.asset_data
            if description:
                ad.description = description
            if author:
                ad.author = author
            if tags:
                for tag in tags:
                    ad.tags.new(tag)

            return {
                "success": True,
                "message": f"Marked {asset_type} '{target_name}' as Blender Asset",
                "asset_type": asset_type,
                "target_name": target_name,
                "author": ad.author,
                "tags_count": len(ad.tags),
            }

        elif action in ("ASSET_CLEAR", "CLEAR"):
            if db.asset_data:
                db.asset_clear()
            return {
                "success": True,
                "message": f"Cleared asset status from {asset_type} '{target_name}'",
                "target_name": target_name,
            }

        return {"success": False, "message": f"Unknown action '{action}'. Supported: ASSET_MARK, ASSET_CLEAR"}


class GenerateAssetPreviewTool(ToolBase):
    name = "generate_asset_preview"
    description = "Generate or load a custom thumbnail preview for an asset datablock."

    def execute(self, params: dict) -> dict:
        target_name = params.get("target_name")
        asset_type = params.get("asset_type", "OBJECT").upper()
        custom_icon_path = params.get("custom_icon_path")

        if not target_name:
            return {"success": False, "message": "'target_name' is required"}

        db = bpy.data.objects.get(target_name) if asset_type == "OBJECT" else bpy.data.materials.get(target_name)
        if not db or not db.asset_data:
            return {"success": False, "message": f"Asset datablock '{target_name}' not found or not marked as asset"}

        if custom_icon_path and os.path.isfile(custom_icon_path):
            bpy.ops.ed.lib_id_load_custom_preview(
                {"id": db},
                filepath=os.path.abspath(custom_icon_path),
            )
            return {
                "success": True,
                "message": f"Loaded custom asset preview from '{custom_icon_path}' for '{target_name}'",
                "target_name": target_name,
            }

        # Trigger internal preview generation
        if hasattr(db.asset_data, "generate_preview"):
            db.asset_data.generate_preview()

        return {
            "success": True,
            "message": f"Generated preview for asset '{target_name}'",
            "target_name": target_name,
        }


class ImportAssetLibraryTool(ToolBase):
    name = "import_asset_library"
    description = "Append or link assets from an external .blend asset library file into the current scene."

    def execute(self, params: dict) -> dict:
        filepath = params.get("filepath")
        asset_name = params.get("asset_name")
        asset_type = params.get("asset_type", "OBJECT").upper()
        link = bool(params.get("link", False))

        if not filepath:
            return {"success": False, "message": "'filepath' is required"}
        filepath = os.path.abspath(os.path.expanduser(filepath))
        if not os.path.isfile(filepath):
            return {"success": False, "message": f"File '{filepath}' not found"}

        with bpy.data.libraries.load(filepath, link=link) as (data_from, data_to):
            if asset_type == "OBJECT":
                if asset_name in data_from.objects:
                    data_to.objects = [asset_name]
                else:
                    return {"success": False, "message": f"Object '{asset_name}' not found in '{filepath}'"}
            elif asset_type == "MATERIAL":
                if asset_name in data_from.materials:
                    data_to.materials = [asset_name]
                else:
                    return {"success": False, "message": f"Material '{asset_name}' not found in '{filepath}'"}
            elif asset_type in ("NODE_GROUP", "GEOMETRY_NODES"):
                if asset_name in data_from.node_groups:
                    data_to.node_groups = [asset_name]
                else:
                    return {"success": False, "message": f"NodeGroup '{asset_name}' not found in '{filepath}'"}

        # Link imported objects to active collection
        imported_names = []
        if data_to.objects:
            for obj in data_to.objects:
                if obj:
                    bpy.context.scene.collection.objects.link(obj)
                    imported_names.append(obj.name)

        return {
            "success": True,
            "message": f"Successfully {'linked' if link else 'appended'} {asset_type} '{asset_name}' from '{filepath}'",
            "asset_name": asset_name,
            "imported_objects": imported_names,
        }
