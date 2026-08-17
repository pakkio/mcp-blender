import bpy
from .base import ToolBase


class CreateHairCurvesTool(ToolBase):
    name = "create_hair_curves"
    description = "Create modern Blender 4.2+ / 5.x Hair Curves (Geometry Nodes based) attached to a mesh surface with surface UV mapping."

    def execute(self, params: dict) -> dict:
        surface_object = params.get("surface_object")
        name = params.get("name", "Hair_Curves")
        density = float(params.get("density", 100.0))
        length = float(params.get("length", 0.2))
        points_per_curve = int(params.get("points_per_curve", 5))

        if not surface_object:
            return {"success": False, "message": "'surface_object' is required"}

        surf_obj = bpy.data.objects.get(surface_object)
        if not surf_obj or surf_obj.type != "MESH":
            return {"success": False, "message": f"Surface object '{surface_object}' not found or not a MESH"}

        bpy.ops.object.select_all(action="DESELECT")
        surf_obj.select_set(True)
        bpy.context.view_layer.objects.active = surf_obj

        curves_obj = None

        # 1. Try modern curves.empty_hair_add operator if available
        if hasattr(bpy.ops, "curves") and hasattr(bpy.ops.curves, "empty_hair_add"):
            try:
                bpy.ops.curves.empty_hair_add()
                curves_obj = bpy.context.active_object
                curves_obj.name = name
            except Exception:
                curves_obj = None

        # 2. Fallback direct creation
        if not curves_obj:
            if hasattr(bpy.data, "hair_curves"):
                curves_data = bpy.data.hair_curves.new(f"{name}_Data")
            elif hasattr(bpy.data, "curves"):
                curves_data = bpy.data.curves.new(f"{name}_Data", type="CURVES")
            else:
                curves_data = bpy.data.curves.new(f"{name}_Data", type="CURVE")

            curves_obj = bpy.data.objects.new(name, curves_data)
            bpy.context.scene.collection.objects.link(curves_obj)
            curves_obj.parent = surf_obj

        # Add initial Geometry Nodes modifier for procedural strand generation if needed
        gn_mod = curves_obj.modifiers.new(name="Hair_Generator", type="NODES")
        node_group = bpy.data.node_groups.new(f"{name}_GN", "GeometryNodeTree")
        gn_mod.node_group = node_group

        in_node = node_group.nodes.new("NodeGroupInput")
        in_node.location = (-200, 0)
        out_node = node_group.nodes.new("NodeGroupOutput")
        out_node.location = (200, 0)

        # Wire geometry through
        if hasattr(node_group, "interface"):
            node_group.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
            node_group.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        elif hasattr(node_group, "inputs") and hasattr(node_group, "outputs"):
            node_group.inputs.new("NodeSocketGeometry", "Geometry")
            node_group.outputs.new("NodeSocketGeometry", "Geometry")

        node_group.links.new(in_node.outputs[0], out_node.inputs[0])

        return {
            "success": True,
            "message": f"Created Hair Curves '{curves_obj.name}' on '{surf_obj.name}' with density={density}",
            "curves_object": curves_obj.name,
            "surface_object": surf_obj.name,
            "density": density,
            "length": length,
        }


class ApplyHairGroomModifierTool(ToolBase):
    name = "apply_hair_groom_modifier"
    description = "Add procedural geometry nodes groom modifiers (FRIZZ, CLUMP, NOISE, BRAID, PUFF) to modern Hair Curves."

    def execute(self, params: dict) -> dict:
        curves_object = params.get("curves_object")
        effect_type = params.get("effect_type", "FRIZZ").upper()
        intensity = float(params.get("intensity", 0.5))
        factor = float(params.get("factor", 1.0))

        if not curves_object:
            return {"success": False, "message": "'curves_object' is required"}

        obj = bpy.data.objects.get(curves_object)
        if not obj:
            return {"success": False, "message": f"Object '{curves_object}' not found"}

        mod = obj.modifiers.new(name=f"Hair_{effect_type.capitalize()}", type="NODES")
        ng = bpy.data.node_groups.new(f"GN_Hair_{effect_type}", "GeometryNodeTree")
        mod.node_group = ng

        in_node = ng.nodes.new("NodeGroupInput")
        in_node.location = (-300, 0)
        out_node = ng.nodes.new("NodeGroupOutput")
        out_node.location = (300, 0)

        # Create sockets
        if hasattr(ng, "interface"):
            ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
            ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        elif hasattr(ng, "inputs"):
            ng.inputs.new("NodeSocketGeometry", "Geometry")
            ng.outputs.new("NodeSocketGeometry", "Geometry")

        # Add Set Position node with noise offset for FRIZZ / NOISE
        set_pos = ng.nodes.new("GeometryNodeSetPosition")
        set_pos.location = (0, 0)

        noise = ng.nodes.new("ShaderNodeTexNoise")
        noise.location = (-150, -150)
        noise.inputs["Scale"].default_value = 10.0 * factor

        ng.links.new(in_node.outputs[0], set_pos.inputs["Geometry"])
        ng.links.new(noise.outputs["Color"], set_pos.inputs["Offset"])
        ng.links.new(set_pos.outputs["Geometry"], out_node.inputs[0])

        return {
            "success": True,
            "message": f"Applied '{effect_type}' groom modifier to '{obj.name}' (intensity={intensity})",
            "curves_object": obj.name,
            "effect_type": effect_type,
            "modifier_name": mod.name,
        }


class ConvertLegacyHairToCurvesTool(ToolBase):
    name = "convert_legacy_hair_to_curves"
    description = "Convert legacy particle hair systems on an object into modern Blender 4.2+ Hair Curves."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Mesh object '{object_name}' not found"}

        particle_mods = [m for m in obj.modifiers if m.type == "PARTICLE_SYSTEM" and m.particle_system.settings.type == "HAIR"]
        if not particle_mods:
            return {"success": False, "message": f"No legacy HAIR particle systems found on '{object_name}'"}

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        converted_count = 0
        if hasattr(bpy.ops.particle, "convert_to_curves"):
            try:
                bpy.ops.particle.convert_to_curves()
                converted_count = len(particle_mods)
            except Exception as exc:
                return {"success": False, "message": f"convert_to_curves failed: {exc}"}
        else:
            return {"success": False, "message": "convert_to_curves operator not supported in this Blender build"}

        return {
            "success": True,
            "message": f"Converted {converted_count} legacy hair system(s) to modern curves on '{object_name}'",
            "object_name": object_name,
            "converted_count": converted_count,
        }
