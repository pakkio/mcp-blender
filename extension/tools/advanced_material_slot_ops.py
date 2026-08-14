import os
import re
import bpy

from .base import ToolBase


class AutoLoadPBRTextureSetTool(ToolBase):
    name = "auto_load_pbr_texture_set"
    description = "Automatically inspect a texture folder, detect PBR maps (Albedo/BaseColor, Roughness, Metallic, Normal, Height/Displacement, AO) with regex matching, and generate a fully wired Principled BSDF PBR material."

    def execute(self, params: dict) -> dict:
        folder_path = params.get("folder_path")
        material_name = params.get("material_name", "M_AutoPBR")

        if not folder_path or not os.path.exists(folder_path):
            return {"success": False, "message": f"Folder '{folder_path}' does not exist"}

        files = os.listdir(folder_path)
        valid_exts = {".png", ".jpg", ".jpeg", ".exr", ".tif", ".tiff", ".tga"}

        detected_maps = {}
        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in valid_exts:
                continue
            name_lower = f.lower()
            full_path = os.path.join(folder_path, f)

            if any(k in name_lower for k in ["basecolor", "base_color", "albedo", "diffuse", "col", "color"]):
                detected_maps["base_color"] = full_path
            elif any(k in name_lower for k in ["roughness", "rough", "rgh"]):
                detected_maps["roughness"] = full_path
            elif any(k in name_lower for k in ["metallic", "metalness", "metal", "met"]):
                detected_maps["metallic"] = full_path
            elif any(k in name_lower for k in ["normal", "norm", "nor", "nrm"]):
                detected_maps["normal"] = full_path
            elif any(k in name_lower for k in ["height", "displacement", "disp", "bump"]):
                detected_maps["displacement"] = full_path
            elif any(k in name_lower for k in ["ambient_occlusion", "ao", "occlusion"]):
                detected_maps["ao"] = full_path

        # Create Material
        mat = bpy.data.materials.get(material_name)
        if not mat:
            mat = bpy.data.materials.new(name=material_name)
            mat.use_nodes = True

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        out_node = nodes.new("ShaderNodeOutputMaterial")
        out_node.location = (400, 0)
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (100, 0)
        links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])

        tc_node = nodes.new("ShaderNodeTexCoord")
        tc_node.location = (-900, 0)
        map_node = nodes.new("ShaderNodeMapping")
        map_node.location = (-700, 0)
        links.new(tc_node.outputs["UV"], map_node.inputs["Vector"])

        loaded_slots = []

        # Base Color
        if "base_color" in detected_maps:
            img = bpy.data.images.load(detected_maps["base_color"], check_existing=True)
            tex_node = nodes.new("ShaderNodeTexImage")
            tex_node.location = (-400, 200)
            tex_node.image = img
            links.new(map_node.outputs["Vector"], tex_node.inputs["Vector"])
            links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
            loaded_slots.append("base_color")

        # Roughness
        if "roughness" in detected_maps:
            img = bpy.data.images.load(detected_maps["roughness"], check_existing=True)
            img.colorspace_settings.name = "Non-Color"
            tex_node = nodes.new("ShaderNodeTexImage")
            tex_node.location = (-400, -50)
            tex_node.image = img
            links.new(map_node.outputs["Vector"], tex_node.inputs["Vector"])
            links.new(tex_node.outputs["Color"], bsdf.inputs["Roughness"])
            loaded_slots.append("roughness")

        # Metallic
        if "metallic" in detected_maps:
            img = bpy.data.images.load(detected_maps["metallic"], check_existing=True)
            img.colorspace_settings.name = "Non-Color"
            tex_node = nodes.new("ShaderNodeTexImage")
            tex_node.location = (-400, -300)
            tex_node.image = img
            links.new(map_node.outputs["Vector"], tex_node.inputs["Vector"])
            links.new(tex_node.outputs["Color"], bsdf.inputs["Metallic"])
            loaded_slots.append("metallic")

        # Normal Map
        if "normal" in detected_maps:
            img = bpy.data.images.load(detected_maps["normal"], check_existing=True)
            img.colorspace_settings.name = "Non-Color"
            tex_node = nodes.new("ShaderNodeTexImage")
            tex_node.location = (-400, -550)
            tex_node.image = img
            norm_map = nodes.new("ShaderNodeNormalMap")
            norm_map.location = (-150, -550)
            links.new(map_node.outputs["Vector"], tex_node.inputs["Vector"])
            links.new(tex_node.outputs["Color"], norm_map.inputs["Color"])
            links.new(norm_map.outputs["Normal"], bsdf.inputs["Normal"])
            loaded_slots.append("normal")

        return {
            "success": True,
            "message": f"Successfully loaded {len(loaded_slots)} PBR texture maps into '{material_name}'",
            "material_name": material_name,
            "loaded_maps": loaded_slots,
            "detected_files": detected_maps,
        }


class ManageMaterialSlotsTool(ToolBase):
    name = "manage_material_slots"
    description = "Add, remove, or assign multi-material slots on an object, or assign specific materials to face selections or polygon indices."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        action = params.get("action", "ASSIGN_SLOT").upper()  # ADD_SLOT, REMOVE_SLOT, ASSIGN_SLOT, ASSIGN_FACES
        material_name = params.get("material_name")
        slot_index = int(params.get("slot_index", 0))
        face_indices = params.get("face_indices", [])

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Mesh object '{object_name}' not found"}

        mat = bpy.data.materials.get(material_name) if material_name else None

        if action == "ADD_SLOT":
            obj.data.materials.append(mat)
            return {
                "success": True,
                "message": f"Added material slot to '{object_name}'",
                "total_slots": len(obj.material_slots),
            }

        elif action == "ASSIGN_SLOT":
            if not mat:
                return {"success": False, "message": f"Material '{material_name}' not found"}
            while len(obj.material_slots) <= slot_index:
                obj.data.materials.append(None)
            obj.material_slots[slot_index].material = mat
            return {
                "success": True,
                "message": f"Assigned '{material_name}' to slot {slot_index} of '{object_name}'",
                "slot_index": slot_index,
            }

        elif action == "ASSIGN_FACES":
            if not mat:
                return {"success": False, "message": f"Material '{material_name}' not found"}
            # Ensure material is in slots
            found_slot = -1
            for idx, slot in enumerate(obj.material_slots):
                if slot.material == mat:
                    found_slot = idx
                    break
            if found_slot == -1:
                obj.data.materials.append(mat)
                found_slot = len(obj.material_slots) - 1

            # Assign to faces
            mesh = obj.data
            assigned_count = 0
            for poly in mesh.polygons:
                if not face_indices or poly.index in face_indices:
                    poly.material_index = found_slot
                    assigned_count += 1

            return {
                "success": True,
                "message": f"Assigned '{material_name}' to {assigned_count} faces on '{object_name}'",
                "material_slot": found_slot,
                "assigned_faces": assigned_count,
            }

        return {"success": False, "message": f"Unknown action '{action}'"}


class ProjectDecalMaterialTool(ToolBase):
    name = "project_decal_material"
    description = "Create a floating alpha decal projection plane parented and shrinkwrapped to a target mesh surface."

    def execute(self, params: dict) -> dict:
        target_object = params.get("target_object")
        decal_name = params.get("decal_name", "Decal_Graphic")
        material_name = params.get("material_name")
        location = params.get("location", [0, 0, 1])
        size = float(params.get("size", 1.0))
        offset = float(params.get("surface_offset", 0.002))

        if not target_object:
            return {"success": False, "message": "'target_object' is required"}

        tgt = bpy.data.objects.get(target_object)
        if not tgt:
            return {"success": False, "message": f"Target '{target_object}' not found"}

        # Create plane
        bpy.ops.mesh.primitive_plane_add(size=size, location=tuple(location))
        decal = bpy.context.active_object
        decal.name = decal_name

        # Add Shrinkwrap modifier
        sw = decal.modifiers.new(name="Decal_Shrinkwrap", type="SHRINKWRAP")
        sw.target = tgt
        sw.wrap_method = "NEAREST_SURFACEPOINT"
        sw.offset = offset

        # Parent to target
        decal.parent = tgt
        decal.matrix_parent_inverse = tgt.matrix_world.inverted()

        if material_name:
            mat = bpy.data.materials.get(material_name)
            if mat:
                decal.data.materials.append(mat)

        return {
            "success": True,
            "message": f"Created projected decal '{decal_name}' attached to '{target_object}'",
            "decal_object": decal_name,
            "target": target_object,
            "surface_offset": offset,
        }
