import bpy

from .base import ToolBase


class ConfigureRenderEffectsTool(ToolBase):
    name = "configure_render_effects"
    description = "Configure high-end rendering effects: Ambient Occlusion (distance/factor), EEVEE Next Raytracing & Screen Space Reflections, Refractions, Motion Blur, Depth of Field, Volumetrics, and Film Transparency (Alpha channel rendering)."

    def execute(self, params: dict) -> dict:
        ambient_occlusion = params.get("ambient_occlusion")
        ao_distance = params.get("ao_distance")
        ao_factor = params.get("ao_factor")
        reflections = params.get("reflections")
        refraction = params.get("refraction")
        motion_blur = params.get("motion_blur")
        shutter = params.get("motion_blur_shutter")
        depth_of_field = params.get("depth_of_field")
        film_transparent = params.get("film_transparent")
        volumetric_start = params.get("volumetric_start")
        volumetric_end = params.get("volumetric_end")

        scene = bpy.context.scene
        updated = {}

        # Film Transparency
        if film_transparent is not None:
            scene.render.film_transparent = bool(film_transparent)
            updated["film_transparent"] = scene.render.film_transparent

        # Motion Blur
        if motion_blur is not None:
            scene.render.use_motion_blur = bool(motion_blur)
            updated["motion_blur"] = scene.render.use_motion_blur
        if shutter is not None and hasattr(scene.render, "motion_blur_shutter"):
            scene.render.motion_blur_shutter = float(shutter)
            updated["motion_blur_shutter"] = scene.render.motion_blur_shutter

        # EEVEE Next / EEVEE Effects
        eevee = getattr(scene, "eevee", None)
        if eevee:
            # Ambient Occlusion (EEVEE / EEVEE Next)
            if ambient_occlusion is not None:
                if hasattr(eevee, "use_gtao"):
                    eevee.use_gtao = bool(ambient_occlusion)
                    updated["ambient_occlusion"] = eevee.use_gtao
                elif hasattr(eevee, "use_fast_gi"):
                    eevee.use_fast_gi = bool(ambient_occlusion)
                    updated["fast_gi_ao"] = eevee.use_fast_gi

            if ao_distance is not None:
                if hasattr(eevee, "gtao_distance"):
                    eevee.gtao_distance = float(ao_distance)
                    updated["ao_distance"] = eevee.gtao_distance
                elif hasattr(eevee, "fast_gi_distance"):
                    eevee.fast_gi_distance = float(ao_distance)
                    updated["ao_distance"] = eevee.fast_gi_distance

            if ao_factor is not None and hasattr(eevee, "gtao_factor"):
                eevee.gtao_factor = float(ao_factor)
                updated["ao_factor"] = eevee.gtao_factor

            # Reflections & Raytracing
            if reflections is not None:
                if hasattr(eevee, "use_raytracing"):  # EEVEE Next (Blender 4.2+ / 5.x)
                    eevee.use_raytracing = bool(reflections)
                    updated["raytracing"] = eevee.use_raytracing
                elif hasattr(eevee, "use_ssr"):  # Legacy SSR
                    eevee.use_ssr = bool(reflections)
                    updated["screen_space_reflections"] = eevee.use_ssr

            if refraction is not None:
                if hasattr(eevee, "use_ssr_refraction"):
                    eevee.use_ssr_refraction = bool(refraction)
                    updated["refraction"] = eevee.use_ssr_refraction

            # Volumetrics
            if volumetric_start is not None and hasattr(eevee, "volumetric_start"):
                eevee.volumetric_start = float(volumetric_start)
                updated["volumetric_start"] = eevee.volumetric_start
            if volumetric_end is not None and hasattr(eevee, "volumetric_end"):
                eevee.volumetric_end = float(volumetric_end)
                updated["volumetric_end"] = eevee.volumetric_end

        # Depth of Field on Active Camera
        if depth_of_field is not None and scene.camera and hasattr(scene.camera.data, "dof"):
            scene.camera.data.dof.use_dof = bool(depth_of_field)
            updated["camera_dof"] = scene.camera.data.dof.use_dof

        return {
            "success": True,
            "message": f"Updated render effects: {', '.join(updated.keys()) if updated else 'no changes'}",
            "effects": updated,
        }


class ConfigureMaterialTransparencyTool(ToolBase):
    name = "configure_material_transparency"
    description = "Configure advanced glass, liquid, acrylic, and transparent shader properties: Transmission weight, Index of Refraction (IOR), Alpha blend modes, screen refraction, backface culling, and roughness."

    def execute(self, params: dict) -> dict:
        mat_name = params.get("material_name")
        transmission = params.get("transmission_weight")
        ior = params.get("ior")
        roughness = params.get("roughness")
        alpha = params.get("alpha")
        blend_mode = params.get("blend_mode", "BLEND").upper()
        shadow_mode = params.get("shadow_mode", "HASHED").upper()
        use_screen_refraction = params.get("use_screen_refraction")
        backface_culling = params.get("backface_culling")

        if not mat_name:
            return {"success": False, "message": "'material_name' is required"}

        mat = bpy.data.materials.get(mat_name)
        if not mat:
            mat = bpy.data.materials.new(name=mat_name)
            mat.use_nodes = True

        mat.use_nodes = True
        nodes = mat.node_tree.nodes

        # Transparency blend modes
        if hasattr(mat, "blend_method"):
            mat.blend_method = blend_mode
        if hasattr(mat, "shadow_method"):
            mat.shadow_method = shadow_mode
        if hasattr(mat, "surface_render_method"):  # Blender 4.2+ / 5.x EEVEE Next
            mat.surface_render_method = "BLENDED" if blend_mode == "BLEND" else "DITHERED"

        if use_screen_refraction is not None and hasattr(mat, "use_screen_refraction"):
            mat.use_screen_refraction = bool(use_screen_refraction)

        if backface_culling is not None and hasattr(mat, "use_backface_culling"):
            mat.use_backface_culling = bool(backface_culling)

        # Update Principled BSDF Sockets
        principled = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
        if not principled:
            principled = nodes.new("ShaderNodeBsdfPrincipled")
            out_node = next((n for n in nodes if n.type == "OUTPUT_MATERIAL"), None)
            if out_node:
                mat.node_tree.links.new(principled.outputs["BSDF"], out_node.inputs["Surface"])

        if transmission is not None:
            # Check "Transmission Weight" (Blender 4.0+) or "Transmission"
            sock = principled.inputs.get("Transmission Weight") or principled.inputs.get("Transmission")
            if sock:
                sock.default_value = float(transmission)

        if ior is not None:
            sock = principled.inputs.get("IOR")
            if sock:
                sock.default_value = float(ior)

        if roughness is not None:
            sock = principled.inputs.get("Roughness")
            if sock:
                sock.default_value = float(roughness)

        if alpha is not None:
            sock = principled.inputs.get("Alpha")
            if sock:
                sock.default_value = float(alpha)

        return {
            "success": True,
            "message": f"Configured material transparency on '{mat.name}' (Transmission: {transmission}, IOR: {ior}, Blend: {blend_mode})",
            "material_name": mat.name,
            "blend_mode": blend_mode,
            "transmission": transmission,
            "ior": ior,
            "roughness": roughness,
            "alpha": alpha,
        }
