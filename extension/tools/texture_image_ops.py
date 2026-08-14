import os
from pathlib import Path
import bpy

from .base import ToolBase


class ImportImageAsPlaneTool(ToolBase):
    name = "import_image_as_plane"
    description = "Import an image file as a textured 3D plane mesh with correct aspect ratio, material node graph, and alpha transparency."

    def execute(self, params: dict) -> dict:
        image_path = params.get("image_path")
        name = params.get("name")
        location = params.get("location", [0, 0, 0])
        rotation = params.get("rotation_euler", [0, 0, 0])
        plane_height = float(params.get("height", 2.0))
        emit_strength = float(params.get("emit_strength", 0.0))
        alpha_mode = params.get("alpha_mode", "BLEND").upper()

        if not image_path:
            return {"success": False, "message": "'image_path' is required"}

        clean_path = os.path.abspath(os.path.expanduser(image_path))
        if not os.path.isfile(clean_path):
            return {"success": False, "message": f"Image file not found: '{clean_path}'"}

        # Load image into Blender
        img = bpy.data.images.load(clean_path, check_existing=True)
        img_width = img.size[0]
        img_height = img.size[1]
        aspect = (img_width / img_height) if img_height > 0 else 1.0

        plane_width = plane_height * aspect
        obj_name = name or Path(clean_path).stem

        # Create mesh plane
        bpy.ops.mesh.primitive_plane_add(
            size=1.0,
            location=location,
            rotation=rotation,
        )
        plane_obj = bpy.context.active_object
        plane_obj.name = obj_name
        plane_obj.scale = (plane_width, plane_height, 1.0)
        bpy.ops.object.transform_apply(scale=True)

        # Create Material
        mat = bpy.data.materials.new(name=f"M_{obj_name}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        out_node = nodes.new(type="ShaderNodeOutputMaterial")
        out_node.location = (400, 0)

        bsdf_node = nodes.new(type="ShaderNodeBsdfPrincipled")
        bsdf_node.location = (100, 0)
        bsdf_node.inputs["Roughness"].default_value = 0.8

        tex_node = nodes.new(type="ShaderNodeTexImage")
        tex_node.location = (-250, 0)
        tex_node.image = img

        links.new(tex_node.outputs["Color"], bsdf_node.inputs["Base Color"])
        links.new(tex_node.outputs["Alpha"], bsdf_node.inputs["Alpha"])

        if emit_strength > 0:
            links.new(tex_node.outputs["Color"], bsdf_node.inputs["Emission Color"])
            if "Emission Strength" in bsdf_node.inputs:
                bsdf_node.inputs["Emission Strength"].default_value = emit_strength

        links.new(bsdf_node.outputs["BSDF"], out_node.inputs["Surface"])

        # Handle material transparency blend mode
        if hasattr(mat, "blend_method"):
            mat.blend_method = alpha_mode

        plane_obj.data.materials.append(mat)

        return {
            "success": True,
            "message": f"Created image plane '{plane_obj.name}' ({img_width}x{img_height}, aspect {aspect:.2f})",
            "name": plane_obj.name,
            "image_path": clean_path,
            "dimensions": [round(plane_width, 4), round(plane_height, 4)],
            "resolution": [img_width, img_height],
            "material_name": mat.name,
        }


class ProjectImageTextureTool(ToolBase):
    name = "project_image_texture"
    description = "Project an image texture onto an object using camera projection or empty-driven decal projection mapping."

    def execute(self, params: dict) -> dict:
        target_name = params.get("target_object")
        image_path = params.get("image_path")
        projection_type = params.get("projection_type", "CAMERA").upper()
        camera_name = params.get("camera_name")
        empty_name = params.get("empty_name")
        material_name = params.get("material_name")

        if not target_name:
            return {"success": False, "message": "'target_object' is required"}
        if not image_path:
            return {"success": False, "message": "'image_path' is required"}

        target_obj = bpy.data.objects.get(target_name)
        if not target_obj or target_obj.type != "MESH":
            return {"success": False, "message": f"Target object '{target_name}' not found or not a MESH"}

        clean_path = os.path.abspath(os.path.expanduser(image_path))
        if not os.path.isfile(clean_path):
            return {"success": False, "message": f"Image file not found: '{clean_path}'"}

        img = bpy.data.images.load(clean_path, check_existing=True)

        # Get or create material
        mat = None
        if material_name:
            mat = bpy.data.materials.get(material_name)
        if not mat:
            mat = bpy.data.materials.new(name=material_name or f"M_Projected_{target_name}")
            mat.use_nodes = True
            if not target_obj.data.materials:
                target_obj.data.materials.append(mat)
            else:
                target_obj.data.materials[0] = mat

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Find or create Principled BSDF & Output
        bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not bsdf:
            bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        output = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
        if not output:
            output = nodes.new("ShaderNodeOutputMaterial")
            links.new(bsdf.outputs["BSDF"], output.inputs["Surface"])

        # Texture and mapping nodes
        tex_node = nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        tex_node.extension = "CLIP"

        coord_node = nodes.new("ShaderNodeTexCoord")
        mapping_node = nodes.new("ShaderNodeMapping")

        if projection_type == "CAMERA":
            cam = bpy.data.objects.get(camera_name) if camera_name else bpy.context.scene.camera
            if cam:
                coord_node.object = cam
                links.new(coord_node.outputs["Window"], tex_node.inputs["Vector"])
            else:
                links.new(coord_node.outputs["Camera"], tex_node.inputs["Vector"])
        elif projection_type == "DECAL_EMPTY":
            empty = bpy.data.objects.get(empty_name) if empty_name else None
            if not empty:
                # Create empty for decal projection
                bpy.ops.object.empty_add(type="PLAIN_AXES", location=target_obj.location)
                empty = bpy.context.active_object
                empty.name = f"Decal_Empty_{target_name}"

            coord_node.object = empty
            links.new(coord_node.outputs["Object"], mapping_node.inputs["Vector"])
            links.new(mapping_node.outputs["Vector"], tex_node.inputs["Vector"])
        else:
            links.new(coord_node.outputs["UV"], mapping_node.inputs["Vector"])
            links.new(mapping_node.outputs["Vector"], tex_node.inputs["Vector"])

        links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])
        if "Alpha" in bsdf.inputs and "Alpha" in tex_node.outputs:
            links.new(tex_node.outputs["Alpha"], bsdf.inputs["Alpha"])

        return {
            "success": True,
            "message": f"Set up {projection_type} projection of '{Path(clean_path).name}' on '{target_name}'",
            "target_object": target_name,
            "projection_type": projection_type,
            "material_name": mat.name,
            "image_path": clean_path,
        }
