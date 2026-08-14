import os
import bpy

from .base import ToolBase


class ManageSequencerStripsTool(ToolBase):
    name = "manage_sequencer_strips"
    description = "Add audio sound effects, background music, video clips, or color adjustment strips to Blender's Video Sequence Editor (VSE) timeline."

    def execute(self, params: dict) -> dict:
        action = params.get("action", "ADD_SOUND").upper()
        filepath = params.get("filepath")
        name = params.get("name", "Strip")
        channel = int(params.get("channel", 1))
        frame_start = int(params.get("frame_start", 1))

        scene = bpy.context.scene
        if not scene.sequence_editor:
            scene.sequence_editor_create()

        se = scene.sequence_editor
        seqs = getattr(se, "strips", getattr(se, "sequences", None))

        if action in ("ADD_SOUND", "ADD_AUDIO"):
            if not filepath:
                return {"success": False, "message": "'filepath' is required for ADD_SOUND"}
            filepath = os.path.abspath(os.path.expanduser(filepath))
            if not os.path.isfile(filepath):
                return {"success": False, "message": f"Audio file '{filepath}' not found"}

            strip = seqs.new_sound(name=name, filepath=filepath, channel=channel, frame_start=frame_start)
            return {
                "success": True,
                "message": f"Added audio strip '{strip.name}' at frame {frame_start} (channel {channel})",
                "strip_name": strip.name,
                "channel": channel,
                "frame_start": frame_start,
            }

        elif action == "ADD_COLOR":
            length = int(params.get("length", 50))
            color = params.get("color", [0.0, 0.0, 0.0])
            try:
                strip = seqs.new_effect(
                    name=name,
                    type="COLOR",
                    channel=channel,
                    frame_start=frame_start,
                    length=length,
                )
            except TypeError:
                strip = seqs.new_effect(
                    name=name,
                    type="COLOR",
                    channel=channel,
                    frame_start=frame_start,
                    frame_end=frame_start + length,
                )

            if hasattr(strip, "color"):
                strip.color = tuple(color[:3])

            return {
                "success": True,
                "message": f"Added color strip '{strip.name}' ({length} frames)",
                "strip_name": strip.name,
                "channel": channel,
            }

        elif action == "CLEAR_ALL":
            for s in list(seqs):
                seqs.remove(s)
            return {
                "success": True,
                "message": "Cleared all sequencer strips",
            }

        return {"success": False, "message": f"Unknown action '{action}'. Supported: ADD_SOUND, ADD_COLOR, CLEAR_ALL"}


class ConfigureSequencerAudioTool(ToolBase):
    name = "configure_sequencer_audio"
    description = "Adjust audio volume, pan, pitch, and mute state on timeline audio strips."

    def execute(self, params: dict) -> dict:
        strip_name = params.get("strip_name") or params.get("name")
        volume = params.get("volume")
        pan = params.get("pan")
        pitch = params.get("pitch")
        mute = params.get("mute")

        scene = bpy.context.scene
        if not scene.sequence_editor:
            return {"success": False, "message": "No sequence editor found in scene"}

        se = scene.sequence_editor
        seqs = getattr(se, "strips", getattr(se, "sequences", None))
        strip = seqs.get(strip_name) if (strip_name and seqs) else (seqs[0] if (seqs and len(seqs) > 0) else None)
        if not strip:
            return {"success": False, "message": f"Sequencer strip '{strip_name}' not found"}

        if volume is not None and hasattr(strip, "volume"):
            strip.volume = float(volume)
        if pan is not None and hasattr(strip, "pan"):
            strip.pan = float(pan)
        if pitch is not None and hasattr(strip, "pitch"):
            strip.pitch = float(pitch)
        if mute is not None:
            strip.mute = bool(mute)

        return {
            "success": True,
            "message": f"Configured audio strip '{strip.name}' (Volume: {getattr(strip, 'volume', 1.0)})",
            "strip_name": strip.name,
            "volume": getattr(strip, "volume", 1.0),
        }
