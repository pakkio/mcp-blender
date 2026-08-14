import bpy

from .base import ToolBase


class ManageShapeKeysTool(ToolBase):
    name = "manage_shape_keys"
    description = "Manage shape keys (morph targets) on a mesh: create Basis, add shape keys, set weights (0.0 to 1.0), and keyframe shape key animation."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        action = params.get("action", "ADD_KEY").upper()
        key_name = params.get("key_name")
        value = params.get("value")
        frame = params.get("frame")

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        if action in ("CREATE_BASIS", "ADD_KEY"):
            # Ensure basis exists
            if not obj.data.shape_keys:
                obj.shape_key_add(name="Basis", from_mix=False)

            if action == "CREATE_BASIS":
                return {
                    "success": True,
                    "message": f"Created Basis shape key on '{object_name}'",
                    "object_name": object_name,
                    "key_name": "Basis",
                }

            # Add new target key
            target_key_name = key_name or f"Key_{len(obj.data.shape_keys.key_blocks)}"
            sk = obj.shape_key_add(name=target_key_name, from_mix=False)
            if value is not None:
                sk.value = float(value)

            return {
                "success": True,
                "message": f"Created shape key '{sk.name}' on '{object_name}'",
                "object_name": object_name,
                "key_name": sk.name,
                "value": sk.value,
            }

        elif action == "SET_VALUE":
            if not key_name:
                return {"success": False, "message": "'key_name' is required for SET_VALUE"}
            if not obj.data.shape_keys:
                return {"success": False, "message": f"Object '{object_name}' has no shape keys"}

            kb = obj.data.shape_keys.key_blocks.get(key_name)
            if not kb:
                return {"success": False, "message": f"Shape key '{key_name}' not found on '{object_name}'"}

            if value is not None:
                kb.value = float(value)

            if frame is not None:
                kb.keyframe_insert(data_path="value", frame=int(frame))

            return {
                "success": True,
                "message": f"Set shape key '{key_name}' value to {kb.value}" + (f" at frame {frame}" if frame is not None else ""),
                "object_name": object_name,
                "key_name": key_name,
                "value": kb.value,
                "frame": frame,
            }

        elif action == "REMOVE_KEY":
            if not key_name:
                return {"success": False, "message": "'key_name' is required for REMOVE_KEY"}
            if not obj.data.shape_keys:
                return {"success": False, "message": f"Object '{object_name}' has no shape keys"}

            kb = obj.data.shape_keys.key_blocks.get(key_name)
            if not kb:
                return {"success": False, "message": f"Shape key '{key_name}' not found on '{object_name}'"}

            obj.shape_key_remove(kb)
            return {
                "success": True,
                "message": f"Removed shape key '{key_name}' from '{object_name}'",
                "object_name": object_name,
                "key_name": key_name,
            }

        else:
            return {
                "success": False,
                "message": f"Unknown shape key action '{action}'. Supported: CREATE_BASIS, ADD_KEY, SET_VALUE, REMOVE_KEY",
            }
