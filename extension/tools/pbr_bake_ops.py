import os
import bpy

from .base import ToolBase


class SetupPBRMaterialsTool(ToolBase):
    name = "setup_pbr_materials"
    description = "Automatically build and connect a full PBR material node tree (Albedo, Normal, Roughness, Metallic, Height/Displacement, Emission, AO) with appropriate color spaces."

    def execute(self, params: dict) -> dict:
        material_name = params.get("material_name")
        object_name = params.get("object_name")
        albedo_path = params.get("albedo_path")
        normal_path = params.get("normal_path")
        roughness_path = params.get("roughness_path")
        metallic_path = params.get("metallic_path")
        height_path = params.get("height_path")
        emission_path = params.get("emission_path")
        ao_path = params.get("ao_path")
        uv_scale = params.get("uv_scale", [1.0, 1.0, 1.0])

        if not material_name:
            return {"success": False, "message": "'material_name' is required"}

        mat = bpy.data.materials.get(material_name)
        if not mat:
            mat = bpy.data.materials.new(name=material_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        # Output & Principled BSDF
        out_node = nodes.new("ShaderNodeOutputMaterial")
        out_node.location = (600, 0)

        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (250, 0)
        links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])

        # Mapping & TexCoord
        coord = nodes.new("ShaderNodeTexCoord")
        coord.location = (-800, 0)

        mapping = nodes.new("ShaderNodeMapping")
        mapping.location = (-600, 0)
        if hasattr(mapping.inputs.get("Scale"), "default_value"):
            mapping.inputs["Scale"].default_value = uv_scale
        links.new(coord.outputs["UV"], mapping.inputs["Vector"])

        connected_maps = []

        def _load_tex(file_path: str, is_color: bool = False):
            clean = os.path.abspath(os.path.expanduser(file_path))
            if not os.path.isfile(clean):
                return None
            img = bpy.data.images.load(clean, check_existing=True)
            if not is_color and hasattr(img, "colorspace_settings"):
                img.colorspace_settings.name = "Non-Color"
            return img

        # 1. Albedo / Base Color
        if albedo_path:
            img = _load_tex(albedo_path, is_color=True)
            if img:
                tex = nodes.new("ShaderNodeTexImage")
                tex.location = (-300, 300)
                tex.image = img
                links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
                links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
                if "Alpha" in tex.outputs and "Alpha" in bsdf.inputs:
                    links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
                connected_maps.append("albedo")

        # 2. Normal Map
        if normal_path:
            img = _load_tex(normal_path, is_color=False)
            if img:
                tex = nodes.new("ShaderNodeTexImage")
                tex.location = (-300, -200)
                tex.image = img
                norm_node = nodes.new("ShaderNodeNormalMap")
                norm_node.location = (-50, -200)
                links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
                links.new(tex.outputs["Color"], norm_node.inputs["Color"])
                links.new(norm_node.outputs["Normal"], bsdf.inputs["Normal"])
                connected_maps.append("normal")

        # 3. Roughness
        if roughness_path:
            img = _load_tex(roughness_path, is_color=False)
            if img:
                tex = nodes.new("ShaderNodeTexImage")
                tex.location = (-300, 50)
                tex.image = img
                links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
                links.new(tex.outputs["Color"], bsdf.inputs["Roughness"])
                connected_maps.append("roughness")

        # 4. Metallic
        if metallic_path:
            img = _load_tex(metallic_path, is_color=False)
            if img:
                tex = nodes.new("ShaderNodeTexImage")
                tex.location = (-300, -50)
                tex.image = img
                links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
                links.new(tex.outputs["Color"], bsdf.inputs["Metallic"])
                connected_maps.append("metallic")

        # 5. Emission
        if emission_path:
            img = _load_tex(emission_path, is_color=True)
            if img:
                tex = nodes.new("ShaderNodeTexImage")
                tex.location = (-300, -450)
                tex.image = img
                links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
                links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
                if "Emission Strength" in bsdf.inputs:
                    bsdf.inputs["Emission Strength"].default_value = 1.0
                connected_maps.append("emission")

        # 6. Displacement / Height
        if height_path:
            img = _load_tex(height_path, is_color=False)
            if img:
                tex = nodes.new("ShaderNodeTexImage")
                tex.location = (-300, -700)
                tex.image = img
                disp = nodes.new("ShaderNodeDisplacement")
                disp.location = (250, -400)
                links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
                links.new(tex.outputs["Color"], disp.inputs["Height"])
                links.new(disp.outputs["Displacement"], out_node.inputs["Displacement"])
                connected_maps.append("displacement")

        # Assign to object if specified
        if object_name:
            obj = bpy.data.objects.get(object_name)
            if obj and obj.type == "MESH":
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat

        return {
            "success": True,
            "message": f"Built PBR material '{material_name}' with maps: {', '.join(connected_maps)}",
            "material_name": material_name,
            "connected_maps": connected_maps,
            "assigned_to": object_name,
        }


class CreateProceduralMaterialTool(ToolBase):
    name = "create_procedural_material"
    description = "Generate a procedural material using NOISE, VORONOI, WAVE, BRICK, CHECKER, or GRADIENT texture networks."

    def execute(self, params: dict) -> dict:
        material_name = params.get("material_name")
        pattern = params.get("pattern", "NOISE").upper()
        scale = float(params.get("scale", 5.0))
        detail = float(params.get("detail", 4.0))
        roughness = float(params.get("roughness", 0.5))
        color1 = params.get("color1", [0.8, 0.2, 0.2, 1.0])
        color2 = params.get("color2", [0.1, 0.1, 0.3, 1.0])
        bump_strength = float(params.get("bump_strength", 0.1))
        metallic = float(params.get("metallic", 0.0))
        object_name = params.get("object_name")

        if not material_name:
            return {"success": False, "message": "'material_name' is required"}

        mat = bpy.data.materials.get(material_name) or bpy.data.materials.new(name=material_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        # Output and Principled BSDF
        out_node = nodes.new("ShaderNodeOutputMaterial")
        out_node.location = (600, 0)

        bsdf = nodes.new("ShaderNodeBsdfPrincipled")
        bsdf.location = (250, 0)
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
        links.new(bsdf.outputs["BSDF"], out_node.inputs["Surface"])

        coord = nodes.new("ShaderNodeTexCoord")
        coord.location = (-800, 0)

        mapping = nodes.new("ShaderNodeMapping")
        mapping.location = (-600, 0)
        links.new(coord.outputs["Object"], mapping.inputs["Vector"])

        # Texture Node
        if pattern == "VORONOI":
            tex_node = nodes.new("ShaderNodeTexVoronoi")
            if "Scale" in tex_node.inputs:
                tex_node.inputs["Scale"].default_value = scale
            fac_output = tex_node.outputs.get("Distance") or tex_node.outputs[0]
        elif pattern == "WAVE":
            tex_node = nodes.new("ShaderNodeTexWave")
            if "Scale" in tex_node.inputs:
                tex_node.inputs["Scale"].default_value = scale
            fac_output = tex_node.outputs["Color"]
        elif pattern == "BRICK":
            tex_node = nodes.new("ShaderNodeTexBrick")
            if "Scale" in tex_node.inputs:
                tex_node.inputs["Scale"].default_value = scale
            fac_output = tex_node.outputs["Color"]
        elif pattern == "CHECKER":
            tex_node = nodes.new("ShaderNodeTexChecker")
            if "Scale" in tex_node.inputs:
                tex_node.inputs["Scale"].default_value = scale
            fac_output = tex_node.outputs["Fac"]
        elif pattern == "GRADIENT":
            tex_node = nodes.new("ShaderNodeTexGradient")
            fac_output = tex_node.outputs["Color"]
        else:  # NOISE default
            tex_node = nodes.new("ShaderNodeTexNoise")
            if "Scale" in tex_node.inputs:
                tex_node.inputs["Scale"].default_value = scale
            if "Detail" in tex_node.inputs:
                tex_node.inputs["Detail"].default_value = detail
            fac_output = tex_node.outputs.get("Fac") or tex_node.outputs["Color"]

        tex_node.location = (-400, 0)
        links.new(mapping.outputs["Vector"], tex_node.inputs["Vector"])

        # ColorRamp
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (-150, 100)
        ramp.color_ramp.elements[0].color = color1
        ramp.color_ramp.elements[1].color = color2
        links.new(fac_output, ramp.inputs["Fac"])
        links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        # Bump
        if bump_strength > 0:
            bump = nodes.new("ShaderNodeBump")
            bump.location = (-50, -150)
            bump.inputs["Strength"].default_value = bump_strength
            links.new(fac_output, bump.inputs["Height"])
            links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

        if object_name:
            obj = bpy.data.objects.get(object_name)
            if obj and obj.type == "MESH":
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat

        return {
            "success": True,
            "message": f"Created procedural '{pattern}' material '{material_name}'",
            "material_name": material_name,
            "pattern": pattern,
            "assigned_to": object_name,
        }


class BakeTexturesTool(ToolBase):
    name = "bake_textures"
    description = "Bake lighting, diffuse, normal maps, roughness, or ambient occlusion to an image texture using the Cycles render engine."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        bake_type = params.get("bake_type", "DIFFUSE").upper()
        output_filepath = params.get("output_filepath")
        width = int(params.get("width", 1024))
        height = int(params.get("height", 1024))
        samples = int(params.get("samples", 16))

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}
        if not output_filepath:
            return {"success": False, "message": "'output_filepath' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        if not obj.data.materials or not obj.data.materials[0]:
            return {"success": False, "message": f"Object '{object_name}' has no materials to bake"}

        scene = bpy.context.scene

        # Snapshot everything this tool mutates so it can be fully restored,
        # whether the bake succeeds, fails, or raises.
        prev_active = bpy.context.view_layer.objects.active
        prev_selected = [o for o in bpy.context.selected_objects]
        orig_engine = scene.render.engine
        orig_samples = scene.cycles.samples if hasattr(scene.cycles, "samples") else None

        scene.render.engine = "CYCLES"
        if hasattr(scene.cycles, "samples"):
            scene.cycles.samples = samples

        img = None
        bake_node = None
        mat = obj.data.materials[0]
        baked_ok = False

        try:
            # Create target bake image
            img_name = f"Bake_{object_name}_{bake_type}"
            img = bpy.data.images.new(name=img_name, width=width, height=height)

            # Insert Image Texture node into object's active material as bake target
            mat.use_nodes = True
            bake_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
            bake_node.image = img
            mat.node_tree.nodes.active = bake_node

            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            # Perform Bake
            bpy.ops.object.bake(type=bake_type)
            baked_ok = True

            # Save image
            clean_path = os.path.abspath(os.path.expanduser(output_filepath))
            os.makedirs(os.path.dirname(clean_path), exist_ok=True)
            img.filepath_raw = clean_path
            img.file_format = "PNG"
            img.save()

            # Clean up temporary node
            mat.node_tree.nodes.remove(bake_node)

            return {
                "success": True,
                "message": f"Bake '{bake_type}' completed for '{object_name}' -> '{clean_path}'",
                "object_name": object_name,
                "bake_type": bake_type,
                "output_filepath": clean_path,
                "resolution": [width, height],
            }
        finally:
            # On failure, discard the incomplete temp image/node rather than
            # leaving orphaned datablocks behind.
            if not baked_ok:
                if bake_node and bake_node.name in mat.node_tree.nodes:
                    mat.node_tree.nodes.remove(bake_node)
                if img and img.name in bpy.data.images:
                    bpy.data.images.remove(img)

            bpy.ops.object.select_all(action="DESELECT")
            for o in prev_selected:
                if o.name in bpy.data.objects:
                    o.select_set(True)
            if prev_active and prev_active.name in bpy.data.objects:
                bpy.context.view_layer.objects.active = prev_active

            if orig_samples is not None:
                scene.cycles.samples = orig_samples
            scene.render.engine = orig_engine
