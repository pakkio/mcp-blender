import os
from pathlib import Path
import bpy

from .base import ToolBase


class BakeAdvancedTool(ToolBase):
    name = "bake_advanced"
    description = "Advanced high-to-low poly baking, multi-pass baking (NORMAL, COMBINED, DIFFUSE, ROUGHNESS, AO, SHADOW, EMISSION), cage/extrusion ray distance, and baking to vertex color attributes."

    def execute(self, params: dict) -> dict:
        target_name = params.get("target_object")
        source_names = params.get("source_objects") or []
        bake_type = params.get("bake_type", "NORMAL").upper()
        selected_to_active = bool(params.get("selected_to_active", False) or bool(source_names))
        cage_object = params.get("cage_object")
        cage_extrusion = float(params.get("cage_extrusion", 0.05))
        bake_to_vertex_colors = bool(params.get("bake_to_vertex_colors", False))
        vertex_color_layer = params.get("vertex_color_layer", "BakedColor")
        output_filepath = params.get("output_filepath")
        width = int(params.get("width", 2048))
        height = int(params.get("height", 2048))
        margin = int(params.get("margin", 16))
        samples = int(params.get("samples", 32))
        denoise = bool(params.get("denoise", False))

        if not target_name:
            return {"success": False, "message": "'target_object' is required"}

        target_obj = bpy.data.objects.get(target_name)
        if not target_obj or target_obj.type != "MESH":
            return {"success": False, "message": f"Target object '{target_name}' not found or not a MESH"}

        # Ensure Cycles is active for bake
        scene = bpy.context.scene
        orig_engine = scene.render.engine
        scene.render.engine = "CYCLES"
        if hasattr(scene.cycles, "samples"):
            scene.cycles.samples = samples
        if hasattr(scene.cycles, "use_denoising"):
            scene.cycles.use_denoising = denoise

        # Configure Bake Settings
        cb = scene.render.bake
        cb.use_selected_to_active = selected_to_active
        cb.margin = margin
        if selected_to_active:
            cb.cage_extrusion = cage_extrusion
            if cage_object:
                c_obj = bpy.data.objects.get(cage_object)
                if c_obj:
                    cb.cage_object = c_obj

        try:
            # Setup target image or vertex color
            bake_node = None
            img = None
            clean_out = None

            if bake_to_vertex_colors:
                cb.target = "VERTEX_COLORS"
                # Ensure color attribute exists on target
                if hasattr(target_obj.data, "color_attributes"):
                    attr = target_obj.data.color_attributes.get(vertex_color_layer)
                    if not attr:
                        target_obj.data.color_attributes.new(
                            name=vertex_color_layer,
                            type="FLOAT_COLOR",
                            domain="CORNER",
                        )
                    target_obj.data.color_attributes.active_color_name = vertex_color_layer
            else:
                cb.target = "IMAGE_TEXTURES"
                img_name = f"Bake_{target_name}_{bake_type}"
                img = bpy.data.images.new(name=img_name, width=width, height=height, float_buffer=(bake_type == "NORMAL"))

                # Ensure material on target
                if not target_obj.data.materials or not target_obj.data.materials[0]:
                    mat = bpy.data.materials.new(f"M_BakeTarget_{target_name}")
                    mat.use_nodes = True
                    target_obj.data.materials.append(mat)

                mat = target_obj.data.materials[0]
                mat.use_nodes = True
                bake_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
                bake_node.image = img
                mat.node_tree.nodes.active = bake_node

            # Selection setup
            bpy.ops.object.select_all(action="DESELECT")
            if selected_to_active:
                for s_name in source_names:
                    s_obj = bpy.data.objects.get(s_name)
                    if s_obj:
                        s_obj.select_set(True)

            target_obj.select_set(True)
            bpy.context.view_layer.objects.active = target_obj

            # Perform Bake
            bpy.ops.object.bake(type=bake_type)

            file_size = 0
            if img and output_filepath:
                clean_out = os.path.abspath(os.path.expanduser(output_filepath))
                os.makedirs(os.path.dirname(clean_out), exist_ok=True)
                img.filepath_raw = clean_out
                img.file_format = "PNG"
                img.save()
                file_size = os.path.getsize(clean_out) if os.path.isfile(clean_out) else 0

            # Clean up bake node
            if bake_node and mat:
                mat.node_tree.nodes.remove(bake_node)

            return {
                "success": True,
                "message": f"Successfully baked {bake_type} for '{target_name}'" + (f" -> '{clean_out}'" if clean_out else ""),
                "target_object": target_name,
                "bake_type": bake_type,
                "selected_to_active": selected_to_active,
                "sources": source_names if selected_to_active else [],
                "output_filepath": clean_out,
                "file_size_bytes": file_size,
                "resolution": [width, height] if img else None,
                "baked_to_vertex_colors": bake_to_vertex_colors,
            }
        finally:
            scene.render.engine = orig_engine


class ConfigureLightProbeTool(ToolBase):
    name = "configure_light_probe"
    description = "Create and configure EEVEE Light Probes (GRID Irradiance Volume, SPHERE Reflection Probe, PLANE Reflection Plane) and trigger lighting cache bake."

    def execute(self, params: dict) -> dict:
        probe_type = params.get("probe_type", "GRID").upper()
        name = params.get("name")
        location = params.get("location", [0, 0, 0])
        resolution = params.get("resolution", [4, 4, 4])
        influence_distance = float(params.get("influence_distance", 5.0))
        bake_cache = bool(params.get("bake_cache", False))

        probe_name = name or f"Probe_{probe_type.title()}"

        if probe_type in ("GRID", "VOLUME"):
            bpy.ops.object.lightprobe_add(type="VOLUME", location=location)
            probe_obj = bpy.context.active_object
            probe_obj.name = probe_name
            if hasattr(probe_obj.data, "grid_resolution_x"):
                probe_obj.data.grid_resolution_x = int(resolution[0])
                probe_obj.data.grid_resolution_y = int(resolution[1])
                probe_obj.data.grid_resolution_z = int(resolution[2])
        elif probe_type == "SPHERE":
            bpy.ops.object.lightprobe_add(type="SPHERE", location=location)
            probe_obj = bpy.context.active_object
            probe_obj.name = probe_name
            if hasattr(probe_obj.data, "influence_distance"):
                probe_obj.data.influence_distance = influence_distance
        elif probe_type == "PLANE":
            bpy.ops.object.lightprobe_add(type="PLANE", location=location)
            probe_obj = bpy.context.active_object
            probe_obj.name = probe_name
            if hasattr(probe_obj.data, "influence_distance"):
                probe_obj.data.influence_distance = influence_distance
        else:
            return {"success": False, "message": f"Unsupported probe_type '{probe_type}'. Must be GRID, VOLUME, SPHERE, or PLANE"}

        if bake_cache and hasattr(bpy.ops.scene, "light_cache_bake"):
            try:
                bpy.ops.scene.light_cache_bake()
            except Exception:
                pass

        return {
            "success": True,
            "message": f"Created Light Probe '{probe_obj.name}' ({probe_type}) at {location}",
            "probe_name": probe_obj.name,
            "probe_type": probe_type,
            "location": location,
            "cache_baked": bake_cache,
        }
