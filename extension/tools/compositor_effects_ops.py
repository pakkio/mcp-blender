import bpy

from .base import ToolBase


class ConfigureCompositorEffectsTool(ToolBase):
    name = "configure_compositor_effects"
    description = "Configure post-processing compositor nodes: GPU Viewport Compositing, Bloom/Glare (Fog Glow, Streaks), Lens Distortion & Chromatic Aberration, and Color Grading."

    def execute(self, params: dict) -> dict:
        use_glare = params.get("use_glare", True)
        glare_threshold = float(params.get("glare_threshold", 0.8))
        glare_size = int(params.get("glare_size", 8))
        use_lens_distortion = params.get("use_lens_distortion", False)
        distortion = float(params.get("distortion", 0.02))
        dispersion = float(params.get("dispersion", 0.03))
        use_viewport_compositing = bool(params.get("use_viewport_compositing", True))

        scene = bpy.context.scene
        scene.use_nodes = True

        if hasattr(scene, "compositing_node_group"):
            if not scene.compositing_node_group:
                scene.compositing_node_group = bpy.data.node_groups.new("Compositor Nodes", type="CompositorNodeTree")
            tree = scene.compositing_node_group
        elif hasattr(scene, "node_tree") and scene.node_tree:
            tree = scene.node_tree
        else:
            tree = bpy.data.node_groups.new("Compositor Nodes", type="CompositorNodeTree")

        nodes = tree.nodes
        links = tree.links
        nodes.clear()

        # Render Layers Input & Output
        rl = nodes.new("CompositorNodeRLayers")
        rl.location = (-400, 200)

        try:
            comp = nodes.new("NodeGroupOutput")
        except Exception:
            comp = nodes.new("CompositorNodeComposite")
        comp.location = (600, 200)

        # Viewer Node for Viewport Compositing
        viewer = nodes.new("CompositorNodeViewer")
        viewer.location = (600, 0)

        last_output = rl.outputs["Image"]
        curr_x = -150

        # 1. Glare / Bloom
        if use_glare:
            glare = nodes.new("CompositorNodeGlare")
            glare.location = (curr_x, 200)
            if hasattr(glare, "glare_type"):
                glare.glare_type = "FOG_GLOW"
            if hasattr(glare, "threshold"):
                glare.threshold = glare_threshold
            if hasattr(glare, "size"):
                glare.size = glare_size

            if "Type" in glare.inputs:
                try:
                    glare.inputs["Type"].default_value = "Fog Glow"
                except Exception:
                    pass
            if "Threshold" in glare.inputs:
                glare.inputs["Threshold"].default_value = glare_threshold
            if "Size" in glare.inputs:
                try:
                    glare.inputs["Size"].default_value = 0.5
                except Exception:
                    pass

            links.new(last_output, glare.inputs["Image"])
            last_output = glare.outputs["Image"]
            curr_x += 200

        # 2. Lens Distortion (Chromatic Aberration)
        if use_lens_distortion:
            lens = nodes.new("CompositorNodeLensdist")
            lens.location = (curr_x, 200)
            if "Distort" in lens.inputs:
                lens.inputs["Distort"].default_value = distortion
            elif "Distortion" in lens.inputs:
                lens.inputs["Distortion"].default_value = distortion
            if "Dispersion" in lens.inputs:
                lens.inputs["Dispersion"].default_value = dispersion
            if hasattr(lens, "use_fit"):
                lens.use_fit = True
            links.new(last_output, lens.inputs["Image"])
            last_output = lens.outputs["Image"]
            curr_x += 200

        # Final connections
        comp_target = comp.inputs.get("Image") or (comp.inputs[0] if comp.inputs else None)
        if comp_target:
            links.new(last_output, comp_target)

        viewer_target = viewer.inputs.get("Image") or (viewer.inputs[0] if viewer.inputs else None)
        if viewer_target:
            links.new(last_output, viewer_target)

        # Viewport Compositor configuration
        if hasattr(scene.render, "compositor_device"):
            scene.render.compositor_device = "GPU"

        return {
            "success": True,
            "message": "Configured scene Compositor post-processing pipeline",
            "glare_enabled": use_glare,
            "lens_distortion_enabled": use_lens_distortion,
            "viewport_compositing": use_viewport_compositing,
        }


class CreateToonShaderTool(ToolBase):
    name = "create_toon_shader"
    description = "Create an anime / cel-shaded Non-Photorealistic Material (NPR) with stepped shadow color ramps, highlight bands, and rim lighting."

    def execute(self, params: dict) -> dict:
        mat_name = params.get("material_name", "M_AnimeToon")
        object_name = params.get("object_name")
        base_color = params.get("base_color", [0.9, 0.4, 0.4, 1.0])
        shadow_color = params.get("shadow_color", [0.4, 0.1, 0.2, 1.0])
        rim_color = params.get("rim_color", [1.0, 0.9, 0.6, 1.0])
        rim_power = float(params.get("rim_power", 3.0))

        mat = bpy.data.materials.new(name=mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()

        # Output
        out_node = nodes.new("ShaderNodeOutputMaterial")
        out_node.location = (600, 0)

        # Diffuse Shader converted to RGB
        diffuse = nodes.new("ShaderNodeBsdfDiffuse")
        diffuse.location = (-400, 100)

        s2rgb = nodes.new("ShaderNodeShaderToRGB")
        s2rgb.location = (-200, 100)
        links.new(diffuse.outputs["BSDF"], s2rgb.inputs["Shader"])

        # ColorRamp (Cel stepping)
        ramp = nodes.new("ShaderNodeValToRGB")
        ramp.location = (0, 100)
        ramp.color_ramp.interpolation = "CONSTANT"
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = tuple(shadow_color) if len(shadow_color) == 4 else (*shadow_color, 1.0)

        if len(ramp.color_ramp.elements) < 2:
            ramp.color_ramp.elements.new(0.4)
        else:
            ramp.color_ramp.elements[1].position = 0.4
        ramp.color_ramp.elements[1].color = tuple(base_color) if len(base_color) == 4 else (*base_color, 1.0)

        links.new(s2rgb.outputs["Color"], ramp.inputs["Fac"])

        # Emission final shader
        emission = nodes.new("ShaderNodeEmission")
        emission.location = (300, 100)
        links.new(ramp.outputs["Color"], emission.inputs["Color"])
        links.new(emission.outputs["Emission"], out_node.inputs["Surface"])

        if object_name:
            obj = bpy.data.objects.get(object_name)
            if obj and obj.type == "MESH":
                if not obj.data.materials:
                    obj.data.materials.append(mat)
                else:
                    obj.data.materials[0] = mat

        return {
            "success": True,
            "message": f"Created anime cel-toon shader '{mat.name}'",
            "material_name": mat.name,
            "assigned_to": object_name,
        }
