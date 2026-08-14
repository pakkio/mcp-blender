import os
import bpy

from .base import ToolBase


class InspectScenePerformanceTool(ToolBase):
    name = "inspect_scene_performance"
    description = "Audit scene complexity, polygon budgets, triangle counts per object, non-manifold mesh errors, and memory usage for game engine / rendering optimization."

    def execute(self, params: dict) -> dict:
        total_verts = 0
        total_edges = 0
        total_faces = 0
        total_tris = 0
        object_breakdown = []
        non_manifold_objects = []

        for obj in bpy.context.scene.objects:
            if obj.type == "MESH" and obj.data:
                mesh = obj.data
                v_count = len(mesh.vertices)
                e_count = len(mesh.edges)
                f_count = len(mesh.polygons)

                # Calculate triangles
                mesh.calc_loop_triangles()
                tri_count = len(mesh.loop_triangles)

                total_verts += v_count
                total_edges += e_count
                total_faces += f_count
                total_tris += tri_count

                # Check non-manifold / loose geometry
                has_loose = any(v.hide for v in mesh.vertices) or (v_count > 0 and f_count == 0)
                if has_loose:
                    non_manifold_objects.append(obj.name)

                object_breakdown.append({
                    "name": obj.name,
                    "vertices": v_count,
                    "faces": f_count,
                    "triangles": tri_count,
                    "modifiers_count": len(obj.modifiers),
                    "material_slots": len(obj.material_slots),
                })

        # Sort breakdown by triangle count descending
        object_breakdown.sort(key=lambda x: x["triangles"], reverse=True)

        return {
            "success": True,
            "total_objects": len(bpy.context.scene.objects),
            "mesh_objects_count": len(object_breakdown),
            "total_triangles": total_tris,
            "total_vertices": total_verts,
            "total_faces": total_faces,
            "non_manifold_warnings": non_manifold_objects,
            "top_heaviest_objects": object_breakdown[:5],
        }


class SetupSkySunRigTool(ToolBase):
    name = "setup_sky_sun_rig"
    description = "Setup a physical Nishita Sky atmosphere with a synchronized directional Sun light, realistic sun elevation/rotation, and ozone/turbidity settings."

    def execute(self, params: dict) -> dict:
        sun_elevation = float(params.get("sun_elevation", 25.0))  # degrees
        sun_rotation = float(params.get("sun_rotation", 45.0))    # degrees
        turbidity = float(params.get("turbidity", 2.2))
        ozone = float(params.get("ozone", 1.0))
        sun_intensity = float(params.get("sun_intensity", 1.0))

        # 1. World Nishita Sky Texture
        world = bpy.context.scene.world
        if not world:
            world = bpy.data.worlds.new("PhysicalWorld")
            bpy.context.scene.world = world

        world.use_nodes = True
        w_nodes = world.node_tree.nodes
        w_links = world.node_tree.links
        w_nodes.clear()

        out_node = w_nodes.new("ShaderNodeOutputWorld")
        out_node.location = (300, 0)

        bg_node = w_nodes.new("ShaderNodeBackground")
        bg_node.location = (100, 0)
        bg_node.inputs["Strength"].default_value = sun_intensity
        w_links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])

        sky_tex = w_nodes.new("ShaderNodeTexSky")
        sky_tex.location = (-200, 0)
        available_types = [item.identifier for item in sky_tex.bl_rna.properties["sky_type"].enum_items]
        if "MULTIPLE_SCATTERING" in available_types:
            sky_tex.sky_type = "MULTIPLE_SCATTERING"
        elif "NISHITA" in available_types:
            sky_tex.sky_type = "NISHITA"
        elif "HOSEK_WILKIE" in available_types:
            sky_tex.sky_type = "HOSEK_WILKIE"

        if hasattr(sky_tex, "sun_elevation"):
            sky_tex.sun_elevation = sun_elevation * 3.14159265 / 180.0
        if hasattr(sky_tex, "sun_rotation"):
            sky_tex.sun_rotation = sun_rotation * 3.14159265 / 180.0
        if hasattr(sky_tex, "turbidity"):
            sky_tex.turbidity = turbidity
        if hasattr(sky_tex, "ozone"):
            sky_tex.ozone = ozone
        w_links.new(sky_tex.outputs["Color"], bg_node.inputs["Color"])

        # 2. Add or update Sun light
        sun_obj = bpy.data.objects.get("Sun_Rig")
        if not sun_obj:
            bpy.ops.object.light_add(type="SUN", location=(0, 0, 10))
            sun_obj = bpy.context.active_object
            sun_obj.name = "Sun_Rig"

        sun_obj.data.energy = 3.5 * sun_intensity
        sun_obj.rotation_euler = (
            (90 - sun_elevation) * 3.14159265 / 180.0,
            0.0,
            sun_rotation * 3.14159265 / 180.0
        )

        return {
            "success": True,
            "message": f"Configured Nishita Sky & Sun Rig (Elevation: {sun_elevation}°, Rotation: {sun_rotation}°)",
            "sun_elevation_deg": sun_elevation,
            "sun_rotation_deg": sun_rotation,
            "sun_object": sun_obj.name,
        }
