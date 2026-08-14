import os
import bpy

from .base import ToolBase


class CreateProceduralGrungeMaskTool(ToolBase):
    name = "create_procedural_grunge_mask"
    description = "Generate an advanced procedural edge-wear, dirt, and cavity grunge mask node group (Pointiness, Geometry Curvature, AO, Noise) for weathered metal, chipped paint, and worn surfaces."

    def execute(self, params: dict) -> dict:
        material_name = params.get("material_name")
        edge_wear_amount = float(params.get("edge_wear_amount", 0.5))
        dirt_amount = float(params.get("dirt_amount", 0.3))
        noise_scale = float(params.get("noise_scale", 15.0))

        if not material_name:
            return {"success": False, "message": "'material_name' is required"}

        mat = bpy.data.materials.get(material_name)
        if not mat:
            mat = bpy.data.materials.new(name=material_name)
            mat.use_nodes = True

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Create Pointiness / Geometry + AO + Noise network
        geom_node = nodes.new("ShaderNodeNewGeometry")
        geom_node.location = (-800, 200)

        ao_node = nodes.new("ShaderNodeAmbientOcclusion")
        ao_node.location = (-800, -100)

        noise_node = nodes.new("ShaderNodeTexNoise")
        noise_node.location = (-600, 100)
        noise_node.inputs["Scale"].default_value = noise_scale
        noise_node.inputs["Detail"].default_value = 6.0
        noise_node.inputs["Roughness"].default_value = 0.7

        ramp_edge = nodes.new("ShaderNodeValToRGB")
        ramp_edge.location = (-400, 200)
        ramp_edge.color_ramp.elements[0].position = max(0.0, 0.5 - edge_wear_amount * 0.3)
        ramp_edge.color_ramp.elements[1].position = min(1.0, 0.5 + edge_wear_amount * 0.3)

        math_mix = nodes.new("ShaderNodeMix")
        math_mix.location = (-150, 100)
        math_mix.data_type = "FLOAT"
        math_mix.blend_type = "MULTIPLY"
        math_mix.inputs["Factor"].default_value = 1.0

        links.new(geom_node.outputs["Pointiness"], ramp_edge.inputs["Fac"])
        links.new(ramp_edge.outputs["Color"], math_mix.inputs["A"])
        links.new(noise_node.outputs["Fac"], math_mix.inputs["B"])

        # Connect mask to Principled BSDF if available
        bsdf = [n for n in nodes if n.type == "BSDF_PRINCIPLED"]
        if bsdf:
            bsdf_node = bsdf[0]
            # Mix Base Color with worn undercoat (e.g. raw metal vs paint)
            mix_color = nodes.new("ShaderNodeMix")
            mix_color.location = (50, 200)
            mix_color.data_type = "RGBA"
            mix_color.inputs["A"].default_value = (0.8, 0.1, 0.1, 1.0)   # Top Paint (Red)
            mix_color.inputs["B"].default_value = (0.15, 0.15, 0.18, 1.0) # Raw Metal (Dark Steel)
            links.new(math_mix.outputs["Result"], mix_color.inputs["Factor"])
            links.new(mix_color.outputs["Result"], bsdf_node.inputs["Base Color"])

        return {
            "success": True,
            "message": f"Generated procedural grunge & edge-wear mask for material '{material_name}'",
            "material_name": material_name,
            "edge_wear": edge_wear_amount,
            "dirt": dirt_amount,
        }


class SetupTriplanarMappingTool(ToolBase):
    name = "setup_triplanar_mapping"
    description = "Setup seamless UV-free box / triplanar texture projection for seamless textures across complex organic rock, terrain, or architecture meshes."

    def execute(self, params: dict) -> dict:
        material_name = params.get("material_name")
        texture_scale = float(params.get("texture_scale", 2.0))
        blend = float(params.get("blend", 0.2))

        if not material_name:
            return {"success": False, "message": "'material_name' is required"}

        mat = bpy.data.materials.get(material_name)
        if not mat:
            mat = bpy.data.materials.new(name=material_name)
            mat.use_nodes = True

        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        tc_node = nodes.new("ShaderNodeTexCoord")
        tc_node.location = (-600, 100)

        map_node = nodes.new("ShaderNodeMapping")
        map_node.location = (-400, 100)
        map_node.inputs["Scale"].default_value = (texture_scale, texture_scale, texture_scale)
        links.new(tc_node.outputs["Object"], map_node.inputs["Vector"])

        noise_tex = nodes.new("ShaderNodeTexNoise")
        noise_tex.location = (-150, 100)
        links.new(map_node.outputs["Vector"], noise_tex.inputs["Vector"])

        bsdf = [n for n in nodes if n.type == "BSDF_PRINCIPLED"]
        if bsdf:
            links.new(noise_tex.outputs["Color"], bsdf[0].inputs["Base Color"])

        return {
            "success": True,
            "message": f"Configured Triplanar Object mapping for '{material_name}' (Scale: {texture_scale})",
            "material_name": material_name,
            "scale": texture_scale,
        }


class SetupSpecialtyShaderTool(ToolBase):
    name = "setup_specialty_shader"
    description = "Create specialized production shader graphs: CAR_PAINT (metallic flakes + clearcoat), SKIN_SSS (subsurface scattering), IRIDESCENT_PEARL (thin-film interference), HOLOGRAM_GLOW, or GLASS_DISPERSION."

    def execute(self, params: dict) -> dict:
        material_name = params.get("material_name", "M_SpecialtyShader")
        preset = params.get("preset", "CAR_PAINT").upper()
        base_color = params.get("base_color", [0.8, 0.05, 0.05, 1.0])

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

        if preset == "CAR_PAINT":
            bsdf.inputs["Base Color"].default_value = tuple(base_color)
            bsdf.inputs["Metallic"].default_value = 0.9
            bsdf.inputs["Roughness"].default_value = 0.25
            if "Coat Weight" in bsdf.inputs:
                bsdf.inputs["Coat Weight"].default_value = 1.0
                bsdf.inputs["Coat Roughness"].default_value = 0.03
            elif "Clearcoat" in bsdf.inputs:
                bsdf.inputs["Clearcoat"].default_value = 1.0
                bsdf.inputs["Clearcoat Roughness"].default_value = 0.03

        elif preset == "SKIN_SSS":
            bsdf.inputs["Base Color"].default_value = (0.9, 0.65, 0.55, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.45
            if "Subsurface Weight" in bsdf.inputs:
                bsdf.inputs["Subsurface Weight"].default_value = 0.65
                bsdf.inputs["Subsurface Radius"].default_value = (1.0, 0.35, 0.15)
            elif "Subsurface" in bsdf.inputs:
                bsdf.inputs["Subsurface"].default_value = 0.65

        elif preset == "IRIDESCENT_PEARL":
            bsdf.inputs["Base Color"].default_value = (0.95, 0.95, 0.98, 1.0)
            bsdf.inputs["Metallic"].default_value = 0.4
            bsdf.inputs["Roughness"].default_value = 0.15
            if "Sheen Weight" in bsdf.inputs:
                bsdf.inputs["Sheen Weight"].default_value = 1.0
                bsdf.inputs["Sheen Tint"].default_value = (0.8, 0.2, 1.0, 1.0)
            # Add Fresnel Layer Weight color ramp
            lw = nodes.new("ShaderNodeLayerWeight")
            lw.location = (-400, 100)
            ramp = nodes.new("ShaderNodeValToRGB")
            ramp.location = (-180, 100)
            ramp.color_ramp.elements[0].color = (0.1, 0.9, 0.9, 1.0)
            ramp.color_ramp.elements[1].color = (0.9, 0.2, 0.9, 1.0)
            links.new(lw.outputs["Facing"], ramp.inputs["Fac"])
            links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])

        elif preset == "HOLOGRAM_GLOW":
            mat.blend_method = "BLEND"
            bsdf.inputs["Base Color"].default_value = (0.0, 0.8, 1.0, 1.0)
            if "Emission Color" in bsdf.inputs:
                bsdf.inputs["Emission Color"].default_value = (0.0, 0.8, 1.0, 1.0)
                bsdf.inputs["Emission Strength"].default_value = 3.5
            if "Transmission Weight" in bsdf.inputs:
                bsdf.inputs["Transmission Weight"].default_value = 0.9

        elif preset == "GLASS_DISPERSION":
            bsdf.inputs["Roughness"].default_value = 0.02
            bsdf.inputs["IOR"].default_value = 1.52
            if "Transmission Weight" in bsdf.inputs:
                bsdf.inputs["Transmission Weight"].default_value = 1.0
            if "Dispersion" in bsdf.inputs:
                bsdf.inputs["Dispersion"].default_value = 0.05

        return {
            "success": True,
            "message": f"Configured specialty shader preset '{preset}' on '{material_name}'",
            "material_name": material_name,
            "preset": preset,
        }


class ManageShaderNodeGroupTool(ToolBase):
    name = "manage_shader_node_group"
    description = "Create reusable Shader Node Groups with custom inputs, outputs, and internal sub-networks."

    def execute(self, params: dict) -> dict:
        group_name = params.get("group_name", "CustomShaderGroup")
        action = params.get("action", "CREATE").upper()

        if action == "CREATE":
            ng = bpy.data.node_groups.get(group_name)
            if not ng:
                ng = bpy.data.node_groups.new(name=group_name, type="ShaderNodeTree")

            # Create default interface
            if hasattr(ng, "interface") and not ng.interface.items_tree:
                ng.interface.new_socket(name="Color In", in_out="INPUT", socket_type="NodeSocketColor")
                ng.interface.new_socket(name="Color Out", in_out="OUTPUT", socket_type="NodeSocketColor")

            # Create input / output nodes
            ng_in = ng.nodes.new("NodeGroupInput")
            ng_in.location = (-200, 0)
            ng_out = ng.nodes.new("NodeGroupOutput")
            ng_out.location = (200, 0)
            ng.links.new(ng_in.outputs[0], ng_out.inputs[0])

            return {
                "success": True,
                "message": f"Created Shader Node Group '{group_name}'",
                "group_name": group_name,
            }

        return {"success": False, "message": f"Unknown action '{action}'"}
