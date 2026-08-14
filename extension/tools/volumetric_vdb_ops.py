import os
import bpy

from .base import ToolBase


class CreateVolumeVDBTool(ToolBase):
    name = "create_volume_vdb"
    description = "Create an OpenVDB volume object from file or create a procedural volumetric fog/cloud domain box."

    def execute(self, params: dict) -> dict:
        name = params.get("name", "VolumeDomain")
        vdb_filepath = params.get("vdb_filepath")
        location = params.get("location", [0, 0, 1])
        scale = params.get("scale", [2, 2, 2])

        if vdb_filepath and os.path.isfile(vdb_filepath):
            bpy.ops.object.volume_import(filepath=os.path.abspath(vdb_filepath))
            vol_obj = bpy.context.active_object
            vol_obj.name = name
            vol_obj.location = location
            vol_obj.scale = scale
            return {
                "success": True,
                "message": f"Imported OpenVDB volume '{name}' from '{vdb_filepath}'",
                "name": vol_obj.name,
                "is_vdb": True,
            }

        # Create procedural volume bounding cube
        bpy.ops.mesh.primitive_cube_add(location=location, scale=scale)
        box_obj = bpy.context.active_object
        box_obj.name = name

        # Add default Volume material
        mat = bpy.data.materials.new(f"M_Volume_{name}")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        out_node = nodes.new("ShaderNodeOutputMaterial")
        vol_shader = nodes.new("ShaderNodeVolumePrincipled")
        vol_shader.inputs["Density"].default_value = float(params.get("density", 0.05))
        links.new(vol_shader.outputs["Volume"], out_node.inputs["Volume"])

        box_obj.data.materials.append(mat)

        return {
            "success": True,
            "message": f"Created procedural volumetric fog box '{box_obj.name}'",
            "name": box_obj.name,
            "density": params.get("density", 0.05),
        }


class ConfigureVolumeShaderTool(ToolBase):
    name = "configure_volume_shader"
    description = "Configure Principled Volume shader properties: density, color, absorption color, emission strength, and blackbody temperature."

    def execute(self, params: dict) -> dict:
        material_name = params.get("material_name")
        object_name = params.get("object_name")
        density = float(params.get("density", 0.1))
        color = params.get("color", [1.0, 1.0, 1.0, 1.0])
        absorption_color = params.get("absorption_color", [0.0, 0.0, 0.0, 1.0])
        emission_strength = float(params.get("emission_strength", 0.0))
        blackbody_intensity = float(params.get("blackbody_intensity", 0.0))

        if not material_name:
            material_name = f"M_Vol_{object_name}" if object_name else "M_VolumeShader"

        mat = bpy.data.materials.get(material_name)
        if not mat:
            mat = bpy.data.materials.new(name=material_name)
            mat.use_nodes = True

        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links

        # Find or create Volume Principled node
        vol_node = None
        for n in nodes:
            if n.type in ("VOLUME_PRINCIPLED", "BSDF_VOLUME_PRINCIPLED"):
                vol_node = n
                break

        if not vol_node:
            nodes.clear()
            out_node = nodes.new("ShaderNodeOutputMaterial")
            vol_node = nodes.new("ShaderNodeVolumePrincipled")
            links.new(vol_node.outputs["Volume"], out_node.inputs["Volume"])

        if "Density" in vol_node.inputs:
            vol_node.inputs["Density"].default_value = density
        if "Color" in vol_node.inputs:
            vol_node.inputs["Color"].default_value = tuple(color) if len(color) == 4 else (*color, 1.0)
        if "Emission Strength" in vol_node.inputs:
            vol_node.inputs["Emission Strength"].default_value = emission_strength
        if "Blackbody Intensity" in vol_node.inputs:
            vol_node.inputs["Blackbody Intensity"].default_value = blackbody_intensity

        if object_name:
            obj = bpy.data.objects.get(object_name)
            if obj:
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat

        return {
            "success": True,
            "message": f"Configured Principled Volume shader on '{material_name}' (Density: {density})",
            "material_name": material_name,
            "density": density,
        }


class BakeFluidDomainTool(ToolBase):
    name = "bake_fluid_domain"
    description = "Configure Mantaflow smoke, fire, or liquid simulation domains and start background simulation bake."

    def execute(self, params: dict) -> dict:
        domain_object = params.get("domain_object") or params.get("name")
        domain_type = params.get("domain_type", "GAS").upper()  # GAS, LIQUID
        resolution = int(params.get("resolution_max", 64))

        if not domain_object:
            return {"success": False, "message": "'domain_object' is required"}

        obj = bpy.data.objects.get(domain_object)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Domain object '{domain_object}' not found or not a MESH"}

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        mod = obj.modifiers.get("Fluid")
        if not mod:
            mod = obj.modifiers.new(name="Fluid", type="FLUID")

        mod.fluid_type = "DOMAIN"
        if mod.domain_settings:
            mod.domain_settings.domain_type = domain_type
            mod.domain_settings.resolution_max = resolution

        return {
            "success": True,
            "message": f"Configured {domain_type} fluid simulation domain on '{domain_object}' (Resolution: {resolution})",
            "domain_object": domain_object,
            "domain_type": domain_type,
            "resolution": resolution,
        }
