import os
from pathlib import Path
import bpy

from .base import ToolBase


class ExportUnityFBXTool(ToolBase):
    name = "export_unity_fbx"
    description = "Export models/rigs/animations specifically tailored for Unity (fixes -90 degree axis rotation bug, strips leaf bones, bakes unit scales, embeds textures)."

    def execute(self, params: dict) -> dict:
        filepath = params.get("filepath")
        selected_only = bool(params.get("selected_only", False))
        bake_anim = bool(params.get("bake_anim", True))
        apply_modifiers = bool(params.get("apply_modifiers", True))
        embed_textures = bool(params.get("embed_textures", False))

        if not filepath:
            return {"success": False, "message": "'filepath' is required"}

        clean_path = os.path.abspath(os.path.expanduser(filepath))
        if not clean_path.lower().endswith(".fbx"):
            clean_path += ".fbx"

        os.makedirs(os.path.dirname(clean_path), exist_ok=True)

        # Unity-tailored FBX export parameters
        fbx_kwargs = {
            "filepath": clean_path,
            "use_selection": selected_only,
            "axis_forward": "-Z",
            "axis_up": "Y",
            "apply_unit_scale": True,
            "apply_scale_options": "FBX_SCALE_UNITS",
            "bake_space_transform": True,
            "use_mesh_modifiers": apply_modifiers,
            "mesh_smooth_type": "FACE",
            "add_leaf_bones": False,  # Crucial for Unity Humanoid / Generic rigs
            "primary_bone_axis": "Y",
            "secondary_bone_axis": "X",
            "armature_nodetype": "NULL",
            "bake_anim": bake_anim,
            "bake_anim_use_all_bones": True,
            "bake_anim_use_nla_strips": True,
            "bake_anim_use_all_actions": False,
            "bake_anim_force_startend_keying": True,
            "path_mode": "COPY" if embed_textures else "AUTO",
            "embed_textures": embed_textures,
        }

        # Check for FBX exporter addon / operator
        if not hasattr(bpy.ops.export_scene, "fbx"):
            return {
                "success": False,
                "message": "Blender FBX export addon is not enabled in this Blender install",
            }

        bpy.ops.export_scene.fbx(**fbx_kwargs)

        file_size = os.path.getsize(clean_path) if os.path.isfile(clean_path) else 0

        return {
            "success": True,
            "message": f"Exported Unity-optimized FBX to '{clean_path}' ({file_size} bytes)",
            "filepath": clean_path,
            "file_size_bytes": file_size,
            "axis_conversion": "Forward: -Z, Up: Y (Unity Native)",
            "leaf_bones_stripped": True,
            "animations_baked": bake_anim,
        }


class GenerateLODsTool(ToolBase):
    name = "generate_lods"
    description = "Automatically generate a multi-level Level of Detail (LOD0..LODn) hierarchy with polygon reduction for game engines."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        ratios = params.get("ratios", [1.0, 0.5, 0.25, 0.1])
        group_name = params.get("group_name")

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        src_obj = bpy.data.objects.get(object_name)
        if not src_obj or src_obj.type != "MESH":
            return {"success": False, "message": f"Source object '{object_name}' not found or not a MESH"}

        base_name = group_name or src_obj.name

        # Create LOD root empty
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=src_obj.location)
        lod_root = bpy.context.active_object
        lod_root.name = f"{base_name}_LODGroup"

        created_lods = []

        for i, ratio in enumerate(ratios):
            lod_name = f"{base_name}_LOD{i}"

            if i == 0 and ratio >= 1.0:
                # Rename or duplicate source
                lod_obj = src_obj.copy()
                lod_obj.data = src_obj.data.copy()
                lod_obj.name = lod_name
                bpy.context.scene.collection.objects.link(lod_obj)
            else:
                # Duplicate and decimate
                lod_obj = src_obj.copy()
                lod_obj.data = src_obj.data.copy()
                lod_obj.name = lod_name
                bpy.context.scene.collection.objects.link(lod_obj)

                # Clear shape keys on decimated LODs to allow modifier application
                if lod_obj.data.shape_keys:
                    lod_obj.shape_key_clear()

                # Decimate
                mod = lod_obj.modifiers.new(name="LOD_Decimate", type="DECIMATE")
                mod.ratio = max(0.01, min(1.0, ratio))
                bpy.context.view_layer.objects.active = lod_obj
                bpy.ops.object.modifier_apply(modifier=mod.name)

            # Parent to LODGroup
            lod_obj.parent = lod_root
            lod_obj.matrix_parent_inverse = lod_root.matrix_world.inverted()

            created_lods.append({
                "name": lod_obj.name,
                "level": i,
                "ratio": ratio,
                "vertices": len(lod_obj.data.vertices),
                "faces": len(lod_obj.data.polygons),
            })

        return {
            "success": True,
            "message": f"Generated {len(created_lods)} LOD levels for '{object_name}' under '{lod_root.name}'",
            "lod_group": lod_root.name,
            "lods": created_lods,
        }
