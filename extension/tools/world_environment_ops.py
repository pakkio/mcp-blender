import math
import os
from pathlib import Path
import bpy

from .base import ToolBase


class ConfigureWorldEnvironmentTool(ToolBase):
    name = "configure_world_environment"
    description = "Configure the 3D World background (solid color, lighting strength, or 360 HDRI environment map texture with Z-axis rotation)."

    def execute(self, params: dict) -> dict:
        color = params.get("color")
        strength = params.get("strength")
        hdri_path = params.get("hdri_path")
        hdri_rot_z = float(params.get("hdri_rotation_z", 0.0))

        world = bpy.context.scene.world
        if not world:
            world = bpy.data.worlds.new("World")
            bpy.context.scene.world = world

        world.use_nodes = True
        nodes = world.node_tree.nodes
        links = world.node_tree.links

        # Find or create Background and World Output
        out_node = next((n for n in nodes if n.type == "OUTPUT_WORLD"), None)
        if not out_node:
            out_node = nodes.new("ShaderNodeOutputWorld")
            out_node.location = (300, 0)

        bg_node = next((n for n in nodes if n.type == "BACKGROUND"), None)
        if not bg_node:
            bg_node = nodes.new("ShaderNodeBackground")
            bg_node.location = (0, 0)
            links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])

        if color is not None:
            bg_node.inputs["Color"].default_value = tuple(color) if len(color) == 4 else (*color, 1.0)

        if strength is not None:
            bg_node.inputs["Strength"].default_value = float(strength)

        hdri_loaded = None
        if hdri_path:
            clean_path = os.path.abspath(os.path.expanduser(hdri_path))
            if not os.path.isfile(clean_path):
                return {"success": False, "message": f"HDRI file not found: '{clean_path}'"}

            img = bpy.data.images.load(clean_path, check_existing=True)

            # Create environment texture and mapping
            env_tex = nodes.new("ShaderNodeTexEnvironment")
            env_tex.location = (-300, 0)
            env_tex.image = img

            tex_coord = nodes.new("ShaderNodeTexCoord")
            tex_coord.location = (-700, 0)

            mapping = nodes.new("ShaderNodeMapping")
            mapping.location = (-500, 0)
            if hasattr(mapping.inputs.get("Rotation"), "default_value"):
                mapping.inputs["Rotation"].default_value[2] = math.radians(hdri_rot_z)

            links.new(tex_coord.outputs["Generated"], mapping.inputs["Vector"])
            links.new(mapping.outputs["Vector"], env_tex.inputs["Vector"])
            links.new(env_tex.outputs["Color"], bg_node.inputs["Color"])

            hdri_loaded = clean_path

        return {
            "success": True,
            "message": f"Configured World environment" + (f" with HDRI '{Path(hdri_loaded).name}'" if hdri_loaded else ""),
            "world_name": world.name,
            "background_strength": bg_node.inputs["Strength"].default_value,
            "hdri_path": hdri_loaded,
        }


class ConfigureScenePhysicsTool(ToolBase):
    name = "configure_scene_physics"
    description = "Configure global scene gravity, metric/imperial unit scales, and Color Management transforms (AgX, Filmic, Exposure, Gamma, Look)."

    def execute(self, params: dict) -> dict:
        gravity = params.get("gravity")
        unit_system = params.get("unit_system")
        unit_scale = params.get("unit_scale")
        view_transform = params.get("color_space_view_transform")
        look = params.get("color_space_look")
        exposure = params.get("color_space_exposure")
        gamma = params.get("color_space_gamma")

        scene = bpy.context.scene
        updated = {}

        # Gravity
        if gravity is not None:
            scene.gravity = tuple(gravity)
            updated["gravity"] = list(scene.gravity)

        # Units
        if unit_system is not None:
            scene.unit_settings.system = unit_system.upper()
            updated["unit_system"] = scene.unit_settings.system

        if unit_scale is not None:
            scene.unit_settings.scale_length = float(unit_scale)
            updated["unit_scale"] = scene.unit_settings.scale_length

        # Color Management
        vs = scene.view_settings
        if view_transform is not None:
            vs.view_transform = view_transform
            updated["view_transform"] = vs.view_transform

        if look is not None:
            vs.look = look
            updated["look"] = vs.look

        if exposure is not None:
            vs.exposure = float(exposure)
            updated["exposure"] = vs.exposure

        if gamma is not None:
            vs.gamma = float(gamma)
            updated["gamma"] = vs.gamma

        return {
            "success": True,
            "message": f"Updated scene physics and color settings: {', '.join(updated.keys())}",
            "settings": updated,
        }


class SwitchWorkspaceTool(ToolBase):
    name = "switch_workspace"
    description = "Switch the active Blender workspace layout (Layout, Modeling, Sculpting, UV Editing, Texture Paint, Shading, Animation, Rendering, Compositing, Geometry Nodes, Scripting)."

    def execute(self, params: dict) -> dict:
        workspace_name = params.get("workspace_name")

        if not workspace_name:
            return {"success": False, "message": "'workspace_name' is required"}

        ws = bpy.data.workspaces.get(workspace_name)
        if not ws:
            # Try case-insensitive matching
            for w in bpy.data.workspaces:
                if w.name.lower() == workspace_name.lower():
                    ws = w
                    break

        if not ws:
            return {
                "success": False,
                "message": f"Workspace '{workspace_name}' not found. Available: {[w.name for w in bpy.data.workspaces]}",
            }

        bpy.context.window.workspace = ws

        return {
            "success": True,
            "message": f"Switched active workspace to '{ws.name}'",
            "active_workspace": ws.name,
        }
