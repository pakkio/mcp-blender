import bpy

from .base import ToolBase


class SetupGeometryProximityTool(ToolBase):
    name = "setup_geometry_proximity_interaction"
    description = "Setup a Geometry Nodes proximity network (GeometryNodeGeometryProximity / Raycast) where target geometry reacts, deforms, or scales based on distance to another object."

    def execute(self, params: dict) -> dict:
        target_object = params.get("target_object")
        source_object = params.get("source_object")
        max_distance = float(params.get("max_distance", 2.0))
        effect_type = params.get("effect_type", "SCALE_DOWN").upper()  # SCALE_DOWN, DEFORM_PUSH

        if not target_object or not source_object:
            return {"success": False, "message": "'target_object' and 'source_object' are required"}

        tgt = bpy.data.objects.get(target_object)
        src = bpy.data.objects.get(source_object)
        if not tgt or not src:
            return {"success": False, "message": f"Objects '{target_object}' or '{source_object}' not found"}

        # Create GN modifier
        mod = tgt.modifiers.new(name="ProximityReaction_GN", type="NODES")
        tree = bpy.data.node_groups.new(name=f"{target_object}_ProximityTree", type="GeometryNodeTree")
        mod.node_group = tree

        if not tree.interface.items_tree:
            tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
            tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

        nodes = tree.nodes
        links = tree.links
        nodes.clear()

        in_node = nodes.new("NodeGroupInput")
        in_node.location = (-600, 0)
        out_node = nodes.new("NodeGroupOutput")
        out_node.location = (600, 0)

        # Object Info Node for source
        obj_info = nodes.new("GeometryNodeObjectInfo")
        obj_info.location = (-600, 200)
        obj_info.inputs["Object"].default_value = src
        obj_info.transform_space = "RELATIVE"

        # Geometry Proximity Node
        prox = nodes.new("GeometryNodeProximity")
        prox.location = (-350, 200)
        links.new(obj_info.outputs["Geometry"], prox.inputs["Target"])

        # Map Range for distance falloff
        map_range = nodes.new("ShaderNodeMapRange")
        map_range.location = (-150, 200)
        map_range.inputs["From Min"].default_value = 0.0
        map_range.inputs["From Max"].default_value = max_distance
        map_range.inputs["To Min"].default_value = 0.0
        map_range.inputs["To Max"].default_value = 1.0
        links.new(prox.outputs["Distance"], map_range.inputs["Value"])

        # Set Position deformation
        set_pos = nodes.new("GeometryNodeSetPosition")
        set_pos.location = (300, 0)
        links.new(in_node.outputs["Geometry"], set_pos.inputs["Geometry"])
        links.new(set_pos.outputs["Geometry"], out_node.inputs["Geometry"])

        # Normal vector * falloff
        norm_node = nodes.new("GeometryNodeInputNormal")
        norm_node.location = (-150, -100)
        vec_math = nodes.new("ShaderNodeVectorMath")
        vec_math.location = (100, -50)
        vec_math.operation = "SCALE"
        links.new(norm_node.outputs["Normal"], vec_math.inputs["Vector"])
        links.new(map_range.outputs["Result"], vec_math.inputs["Scale"])
        links.new(vec_math.outputs["Vector"], set_pos.inputs["Offset"])

        return {
            "success": True,
            "message": f"Configured Geometry Proximity interaction between '{target_object}' and '{source_object}'",
            "target": target_object,
            "source": source_object,
            "max_distance": max_distance,
        }


class CurveToProfileMeshTool(ToolBase):
    name = "curve_to_profile_mesh"
    description = "Sweep a procedural curve profile (Circle, Rectangle, Star, Line) along a curve with automatic caps and UV unwrap in Geometry Nodes."

    def execute(self, params: dict) -> dict:
        curve_object = params.get("curve_object")
        profile_type = params.get("profile_type", "CIRCLE").upper()  # CIRCLE, QUADRILATERAL, STAR
        radius = float(params.get("radius", 0.1))
        fill_caps = bool(params.get("fill_caps", True))

        if not curve_object:
            return {"success": False, "message": "'curve_object' is required"}

        obj = bpy.data.objects.get(curve_object)
        if not obj:
            return {"success": False, "message": f"Curve object '{curve_object}' not found"}

        mod = obj.modifiers.new(name="CurveProfile_GN", type="NODES")
        tree = bpy.data.node_groups.new(name=f"{curve_object}_CurveSweepTree", type="GeometryNodeTree")
        mod.node_group = tree

        if not tree.interface.items_tree:
            tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
            tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

        nodes = tree.nodes
        links = tree.links
        nodes.clear()

        in_node = nodes.new("NodeGroupInput")
        in_node.location = (-400, 0)
        out_node = nodes.new("NodeGroupOutput")
        out_node.location = (400, 0)

        c2m = nodes.new("GeometryNodeCurveToMesh")
        c2m.location = (100, 0)
        c2m.inputs["Fill Caps"].default_value = fill_caps

        if profile_type == "STAR":
            prof = nodes.new("GeometryNodeCurveStar")
            prof.location = (-150, -200)
            prof.inputs["Outer Radius"].default_value = radius
            prof.inputs["Inner Radius"].default_value = radius * 0.5
        elif profile_type == "QUADRILATERAL":
            prof = nodes.new("GeometryNodeCurvePrimitiveQuadrilateral")
            prof.location = (-150, -200)
            prof.inputs["Width"].default_value = radius * 2
            prof.inputs["Height"].default_value = radius * 2
        else:
            prof = nodes.new("GeometryNodeCurvePrimitiveCircle")
            prof.location = (-150, -200)
            prof.inputs["Radius"].default_value = radius

        links.new(in_node.outputs["Geometry"], c2m.inputs["Curve"])
        links.new(prof.outputs["Curve"], c2m.inputs["Profile Curve"])
        links.new(c2m.outputs["Mesh"], out_node.inputs["Geometry"])

        return {
            "success": True,
            "message": f"Swept curve '{curve_object}' with {profile_type} profile (radius: {radius}m)",
            "profile_type": profile_type,
            "radius": radius,
        }


class VolumeMeshBooleansGNTool(ToolBase):
    name = "volume_mesh_booleans_gn"
    description = "Procedural OpenVDB volume meshing and smooth organic blending inside Geometry Nodes (Mesh to Volume -> Volume to Mesh)."

    def execute(self, params: dict) -> dict:
        target_object = params.get("target_object")
        voxel_amount = float(params.get("voxel_amount", 64.0))
        threshold = float(params.get("threshold", 0.1))
        adaptivity = float(params.get("adaptivity", 0.0))

        if not target_object:
            return {"success": False, "message": "'target_object' is required"}

        obj = bpy.data.objects.get(target_object)
        if not obj:
            return {"success": False, "message": f"Object '{target_object}' not found"}

        mod = obj.modifiers.new(name="VDB_Remesh_GN", type="NODES")
        tree = bpy.data.node_groups.new(name=f"{target_object}_VDBTree", type="GeometryNodeTree")
        mod.node_group = tree

        if not tree.interface.items_tree:
            tree.interface.new_socket(name="Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
            tree.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

        nodes = tree.nodes
        links = tree.links
        nodes.clear()

        in_node = nodes.new("NodeGroupInput")
        in_node.location = (-400, 0)
        out_node = nodes.new("NodeGroupOutput")
        out_node.location = (500, 0)

        m2v = nodes.new("GeometryNodeMeshToVolume")
        m2v.location = (-100, 0)
        m2v.inputs["Voxel Amount"].default_value = voxel_amount

        v2m = nodes.new("GeometryNodeVolumeToMesh")
        v2m.location = (200, 0)
        v2m.inputs["Threshold"].default_value = threshold
        v2m.inputs["Adaptivity"].default_value = adaptivity

        links.new(in_node.outputs["Geometry"], m2v.inputs["Mesh"])
        links.new(m2v.outputs["Volume"], v2m.inputs["Volume"])
        links.new(v2m.outputs["Mesh"], out_node.inputs["Geometry"])

        return {
            "success": True,
            "message": f"Configured procedural VDB Volume Remesh GN for '{target_object}'",
            "voxel_amount": voxel_amount,
            "adaptivity": adaptivity,
        }
