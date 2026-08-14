import addon_utils
import sys
import bpy

from .base import ToolBase


class ManageAddonsTool(ToolBase):
    name = "manage_addons"
    description = "List, discover, enable, disable, and configure settings for any Blender add-on or extension (including Rigify, Node Wrangler, LoopTools, Archimesh, glTF, FBX, and custom extensions)."

    def execute(self, params: dict) -> dict:
        action = params.get("action", "LIST").upper()
        addon_name = params.get("addon_name")
        filter_mode = params.get("filter", "ALL").upper()
        prefs_data = params.get("preferences")

        # Refresh addons list
        addon_utils.modules_refresh()
        modules = list(addon_utils.modules())

        if action == "LIST":
            addons_list = []
            for mod in modules:
                name = mod.__name__
                is_enabled, is_loaded = addon_utils.check(name)

                if filter_mode == "ENABLED_ONLY" and not is_enabled:
                    continue
                if filter_mode == "DISABLED_ONLY" and is_enabled:
                    continue

                info = addon_utils.module_bl_info(mod)
                addons_list.append({
                    "module": name,
                    "name": info.get("name", name),
                    "version": info.get("version", ()),
                    "category": info.get("category", "General"),
                    "enabled": is_enabled,
                    "description": info.get("description", ""),
                })

            return {
                "success": True,
                "total_addons": len(addons_list),
                "filter": filter_mode,
                "addons": sorted(addons_list, key=lambda x: x["name"]),
            }

        elif action == "ENABLE":
            if not addon_name:
                return {"success": False, "message": "'addon_name' is required for ENABLE"}

            # Enable addon
            try:
                addon_utils.enable(addon_name, default_set=True)
                is_enabled, _ = addon_utils.check(addon_name)
                return {
                    "success": is_enabled,
                    "message": f"Addon '{addon_name}' is now {'enabled' if is_enabled else 'failed to enable'}",
                    "addon_name": addon_name,
                    "enabled": is_enabled,
                }
            except Exception as exc:
                return {"success": False, "message": f"Failed to enable addon '{addon_name}': {exc}"}

        elif action == "DISABLE":
            if not addon_name:
                return {"success": False, "message": "'addon_name' is required for DISABLE"}

            try:
                addon_utils.disable(addon_name, default_set=True)
                is_enabled, _ = addon_utils.check(addon_name)
                return {
                    "success": not is_enabled,
                    "message": f"Addon '{addon_name}' is now {'disabled' if not is_enabled else 'still enabled'}",
                    "addon_name": addon_name,
                    "enabled": is_enabled,
                }
            except Exception as exc:
                return {"success": False, "message": f"Failed to disable addon '{addon_name}': {exc}"}

        elif action == "SET_PREFERENCES":
            if not addon_name:
                return {"success": False, "message": "'addon_name' is required for SET_PREFERENCES"}
            if not prefs_data:
                return {"success": False, "message": "'preferences' dictionary is required"}

            addon_prefs = bpy.context.preferences.addons.get(addon_name)
            if not addon_prefs or not hasattr(addon_prefs, "preferences"):
                return {"success": False, "message": f"Addon '{addon_name}' is not enabled or has no preferences"}

            updated = []
            for k, v in prefs_data.items():
                if hasattr(addon_prefs.preferences, k):
                    setattr(addon_prefs.preferences, k, v)
                    updated.append(k)

            return {
                "success": True,
                "message": f"Updated preferences for '{addon_name}': {', '.join(updated)}",
                "addon_name": addon_name,
                "updated_keys": updated,
            }

        else:
            return {"success": False, "message": f"Unknown action '{action}'. Supported: LIST, ENABLE, DISABLE, SET_PREFERENCES"}


class InspectAddonTool(ToolBase):
    name = "inspect_addon"
    description = "Inspect full metadata, configuration settings, enabled status, documentation links, and preference properties for a specific Blender add-on."

    def execute(self, params: dict) -> dict:
        addon_name = params.get("addon_name")
        if not addon_name:
            return {"success": False, "message": "'addon_name' is required"}

        addon_utils.modules_refresh()
        target_mod = None
        for mod in addon_utils.modules():
            if mod.__name__ == addon_name or getattr(mod, "bl_info", {}).get("name") == addon_name:
                target_mod = mod
                break

        if not target_mod:
            return {"success": False, "message": f"Addon '{addon_name}' not found in Blender module path"}

        info = addon_utils.module_bl_info(target_mod)
        is_enabled, is_loaded = addon_utils.check(target_mod.__name__)

        # Query Preferences
        pref_props = {}
        addon_entry = bpy.context.preferences.addons.get(target_mod.__name__)
        if addon_entry and hasattr(addon_entry, "preferences") and addon_entry.preferences:
            p = addon_entry.preferences
            for key in dir(p):
                if not key.startswith("_") and not key.startswith("rna_") and key not in ("bl_rna",):
                    try:
                        val = getattr(p, key)
                        if isinstance(val, (int, float, str, bool, list)):
                            pref_props[key] = val
                    except Exception:
                        pass

        return {
            "success": True,
            "module_name": target_mod.__name__,
            "name": info.get("name", target_mod.__name__),
            "author": info.get("author", "Unknown"),
            "version": info.get("version", ()),
            "blender_version": info.get("blender", ()),
            "category": info.get("category", "General"),
            "description": info.get("description", ""),
            "doc_url": info.get("doc_url", info.get("wiki_url", "")),
            "tracker_url": info.get("tracker_url", ""),
            "is_enabled": is_enabled,
            "is_loaded": is_loaded,
            "preferences": pref_props,
            "file_path": getattr(target_mod, "__file__", None),
        }
