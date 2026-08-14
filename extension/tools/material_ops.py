import bpy

from .base import ToolBase


def _get_bsdf_node(material):
    if not material.use_nodes or not material.node_tree:
        return None
    for node in material.node_tree.nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


def _set_bsdf_input(bsdf_node, possible_names, value):
    for name in possible_names:
        if name in bsdf_node.inputs:
            bsdf_node.inputs[name].default_value = value
            return True
    return False


def _get_bsdf_input(bsdf_node, possible_names):
    for name in possible_names:
        if name in bsdf_node.inputs:
            val = bsdf_node.inputs[name].default_value
            if hasattr(val, "__iter__"):
                return [round(x, 4) for x in val]
            return round(val, 4) if isinstance(val, float) else val
    return None


class CreateMaterialTool(ToolBase):
    name = "create_material"
    description = "Create a PBR material with Principled BSDF shader and optionally assign it to an object."

    def execute(self, params: dict) -> dict:
        name = params.get("name")
        if not name:
            return {"success": False, "message": "'name' is required"}

        # Create or get material
        mat = bpy.data.materials.get(name)
        if not mat:
            mat = bpy.data.materials.new(name=name)

        mat.use_nodes = True
        bsdf = _get_bsdf_node(mat)

        if bsdf is None and mat.node_tree:
            bsdf = mat.node_tree.nodes.new(type="ShaderNodeBsdfPrincipled")
            output_node = None
            for node in mat.node_tree.nodes:
                if node.type == "OUTPUT_MATERIAL":
                    output_node = node
                    break
            if not output_node:
                output_node = mat.node_tree.nodes.new(type="ShaderNodeOutputMaterial")
            mat.node_tree.links.new(bsdf.outputs["BSDF"], output_node.inputs["Surface"])

        if bsdf:
            if params.get("base_color") is not None:
                _set_bsdf_input(bsdf, ["Base Color"], tuple(params["base_color"]))
            if params.get("metallic") is not None:
                _set_bsdf_input(bsdf, ["Metallic"], float(params["metallic"]))
            if params.get("roughness") is not None:
                _set_bsdf_input(bsdf, ["Roughness"], float(params["roughness"]))
            if params.get("specular") is not None:
                _set_bsdf_input(bsdf, ["Specular IOR Level", "Specular"], float(params["specular"]))
            if params.get("ior") is not None:
                _set_bsdf_input(bsdf, ["IOR"], float(params["ior"]))
            if params.get("transmission") is not None:
                _set_bsdf_input(bsdf, ["Transmission Weight", "Transmission"], float(params["transmission"]))
            if params.get("emission_color") is not None:
                _set_bsdf_input(bsdf, ["Emission Color", "Emission"], tuple(params["emission_color"]))
            if params.get("emission_strength") is not None:
                _set_bsdf_input(bsdf, ["Emission Strength"], float(params["emission_strength"]))
            if params.get("alpha") is not None:
                _set_bsdf_input(bsdf, ["Alpha"], float(params["alpha"]))

        # Optionally assign to object
        assign_to = params.get("assign_to_object")
        if assign_to:
            obj = bpy.data.objects.get(assign_to)
            if obj:
                if obj.data and hasattr(obj.data, "materials"):
                    if not obj.data.materials:
                        obj.data.materials.append(mat)
                    else:
                        obj.data.materials[0] = mat

        return {
            "success": True,
            "message": f"Created material '{mat.name}'",
            "material_name": mat.name,
            "assigned_to": assign_to if assign_to else None,
        }


class AssignMaterialTool(ToolBase):
    name = "assign_material"
    description = "Assign a material to an object."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        material_name = params.get("material_name")
        slot_index = params.get("slot_index")

        if not object_name or not material_name:
            return {"success": False, "message": "'object_name' and 'material_name' are required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        mat = bpy.data.materials.get(material_name)
        if not mat:
            return {"success": False, "message": f"Material '{material_name}' not found"}

        if not obj.data or not hasattr(obj.data, "materials"):
            return {"success": False, "message": f"Object '{object_name}' does not support materials"}

        if slot_index is not None and slot_index < len(obj.material_slots):
            obj.material_slots[slot_index].material = mat
        else:
            if not obj.data.materials:
                obj.data.materials.append(mat)
            else:
                obj.data.materials.append(mat)

        return {
            "success": True,
            "message": f"Assigned material '{material_name}' to '{object_name}'",
            "object_name": object_name,
            "material_name": material_name,
            "slots_count": len(obj.material_slots),
        }


class GetMaterialInfoTool(ToolBase):
    name = "get_material_info"
    description = "Get detailed information about a material and its shader nodes."

    def execute(self, params: dict) -> dict:
        material_name = params.get("material_name")
        if not material_name:
            return {"success": False, "message": "'material_name' is required"}

        mat = bpy.data.materials.get(material_name)
        if not mat:
            return {"success": False, "message": f"Material '{material_name}' not found"}

        info = {
            "success": True,
            "name": mat.name,
            "users": mat.users,
            "use_nodes": mat.use_nodes,
        }

        bsdf = _get_bsdf_node(mat)
        if bsdf:
            info["principled_bsdf"] = {
                "base_color": _get_bsdf_input(bsdf, ["Base Color"]),
                "metallic": _get_bsdf_input(bsdf, ["Metallic"]),
                "roughness": _get_bsdf_input(bsdf, ["Roughness"]),
                "specular": _get_bsdf_input(bsdf, ["Specular IOR Level", "Specular"]),
                "ior": _get_bsdf_input(bsdf, ["IOR"]),
                "transmission": _get_bsdf_input(bsdf, ["Transmission Weight", "Transmission"]),
                "emission_color": _get_bsdf_input(bsdf, ["Emission Color", "Emission"]),
                "emission_strength": _get_bsdf_input(bsdf, ["Emission Strength"]),
                "alpha": _get_bsdf_input(bsdf, ["Alpha"]),
            }

        if mat.use_nodes and mat.node_tree:
            info["nodes"] = [
                {"name": n.name, "type": n.type, "label": n.label}
                for n in mat.node_tree.nodes
            ]

        return info


class SetMaterialPropertiesTool(ToolBase):
    name = "set_material_properties"
    description = "Update properties on an existing material's Principled BSDF shader."

    def execute(self, params: dict) -> dict:
        material_name = params.get("material_name")
        if not material_name:
            return {"success": False, "message": "'material_name' is required"}

        mat = bpy.data.materials.get(material_name)
        if not mat:
            return {"success": False, "message": f"Material '{material_name}' not found"}

        bsdf = _get_bsdf_node(mat)
        if not bsdf:
            return {"success": False, "message": f"Material '{material_name}' has no Principled BSDF node"}

        if params.get("base_color") is not None:
            _set_bsdf_input(bsdf, ["Base Color"], tuple(params["base_color"]))
        if params.get("metallic") is not None:
            _set_bsdf_input(bsdf, ["Metallic"], float(params["metallic"]))
        if params.get("roughness") is not None:
            _set_bsdf_input(bsdf, ["Roughness"], float(params["roughness"]))
        if params.get("specular") is not None:
            _set_bsdf_input(bsdf, ["Specular IOR Level", "Specular"], float(params["specular"]))
        if params.get("ior") is not None:
            _set_bsdf_input(bsdf, ["IOR"], float(params["ior"]))
        if params.get("transmission") is not None:
            _set_bsdf_input(bsdf, ["Transmission Weight", "Transmission"], float(params["transmission"]))
        if params.get("emission_color") is not None:
            _set_bsdf_input(bsdf, ["Emission Color", "Emission"], tuple(params["emission_color"]))
        if params.get("emission_strength") is not None:
            _set_bsdf_input(bsdf, ["Emission Strength"], float(params["emission_strength"]))
        if params.get("alpha") is not None:
            _set_bsdf_input(bsdf, ["Alpha"], float(params["alpha"]))

        return {
            "success": True,
            "message": f"Updated material properties for '{material_name}'",
            "material_name": material_name,
        }
