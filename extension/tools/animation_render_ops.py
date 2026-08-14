import os
import bpy

from .base import ToolBase


class BakeObjectAnimationTool(ToolBase):
    name = "bake_object_animation"
    description = "Bake object constraints, follow-paths, or physics simulations into permanent transform keyframes across a frame range for game engine export (Unity/Unreal)."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        frame_start = int(params.get("frame_start", bpy.context.scene.frame_start))
        frame_end = int(params.get("frame_end", bpy.context.scene.frame_end))
        bake_visual = bool(params.get("visual_keying", True))
        clear_constraints = bool(params.get("clear_constraints", False))

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        # Select only this object
        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj

        # Bake animation
        bpy.ops.nla.bake(
            frame_start=frame_start,
            frame_end=frame_end,
            step=1,
            only_selected=True,
            visual_keying=bake_visual,
            clear_constraints=clear_constraints,
            bake_types={"OBJECT"},
        )

        return {
            "success": True,
            "message": f"Baked animation for '{object_name}' from frame {frame_start} to {frame_end}",
            "object_name": object_name,
            "frame_range": [frame_start, frame_end],
            "action_name": obj.animation_data.action.name if obj.animation_data and obj.animation_data.action else None,
        }


class RenderAnimationSequenceTool(ToolBase):
    name = "render_animation_sequence"
    description = "Render an entire animation frame sequence or video (MP4/H.264 or PNG sequence) to disk with timeline range and resolution controls."

    def execute(self, params: dict) -> dict:
        output_filepath = params.get("output_filepath")
        format_type = params.get("format", "FFMPEG").upper()  # FFMPEG, PNG, OPEN_EXR
        frame_start = int(params.get("frame_start", bpy.context.scene.frame_start))
        frame_end = int(params.get("frame_end", min(bpy.context.scene.frame_start + 10, bpy.context.scene.frame_end)))
        resolution_x = int(params.get("resolution_x", 1280))
        resolution_y = int(params.get("resolution_y", 720))

        if not output_filepath:
            output_filepath = os.path.join(bpy.app.tempdir, "blender_animation_output")

        scene = bpy.context.scene
        scene.render.filepath = output_filepath
        scene.render.resolution_x = resolution_x
        scene.render.resolution_y = resolution_y
        scene.frame_start = frame_start
        scene.frame_end = frame_end

        if format_type == "FFMPEG":
            scene.render.image_settings.file_format = "FFMPEG"
            scene.render.ffmpeg.format = "MPEG4"
            scene.render.ffmpeg.codec = "H264"
        elif format_type == "OPEN_EXR":
            scene.render.image_settings.file_format = "OPEN_EXR"
        else:
            scene.render.image_settings.file_format = "PNG"

        # Render animation
        bpy.ops.render.render(animation=True)

        return {
            "success": True,
            "message": f"Rendered animation sequence from frame {frame_start} to {frame_end}",
            "output_filepath": output_filepath,
            "frame_range": [frame_start, frame_end],
            "format": format_type,
            "resolution": [resolution_x, resolution_y],
        }
