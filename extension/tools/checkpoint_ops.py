import os
import tempfile
import time
from pathlib import Path
import bpy

from .base import ToolBase

CHECKPOINT_DIR = Path(tempfile.gettempdir()) / "mcp_blender_checkpoints"


def _ensure_checkpoint_dir() -> Path:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    return CHECKPOINT_DIR


class CreateSceneCheckpointTool(ToolBase):
    name = "create_scene_checkpoint"
    description = "Create a snapshot checkpoint of the current Blender scene state to disk that can be reverted to anytime."

    def execute(self, params: dict) -> dict:
        checkpoint_name = params.get("name", f"checkpoint_{int(time.time())}")
        clean_name = "".join(c for c in checkpoint_name if c.isalnum() or c in ("-", "_"))
        target_dir = _ensure_checkpoint_dir()
        file_path = target_dir / f"{clean_name}.blend"

        try:
            bpy.ops.wm.save_as_mainfile(filepath=str(file_path), copy=True)
            return {
                "success": True,
                "message": f"Scene checkpoint '{clean_name}' created successfully",
                "checkpoint_name": clean_name,
                "filepath": str(file_path),
                "timestamp": time.time(),
            }
        except Exception as exc:
            return {"success": False, "message": f"Failed to create checkpoint: {exc}"}


class RestoreSceneCheckpointTool(ToolBase):
    name = "restore_scene_checkpoint"
    description = "Restore the scene to a previously saved checkpoint snapshot."

    def execute(self, params: dict) -> dict:
        checkpoint_name = params.get("name")
        if not checkpoint_name:
            return {"success": False, "message": "'name' is required"}

        clean_name = "".join(c for c in checkpoint_name if c.isalnum() or c in ("-", "_"))
        target_dir = _ensure_checkpoint_dir()
        file_path = target_dir / f"{clean_name}.blend"

        if not file_path.exists():
            return {"success": False, "message": f"Checkpoint '{clean_name}' not found at {file_path}"}

        filepath_str = str(file_path)

        def _deferred_load():
            bpy.ops.wm.open_mainfile(filepath=filepath_str)
            return None

        try:
            bpy.app.timers.register(_deferred_load, first_interval=0.1)
            return {
                "success": True,
                "message": f"Scene restore to checkpoint '{clean_name}' scheduled (loading in ~0.1s)",
                "checkpoint_name": clean_name,
            }
        except Exception as exc:
            return {"success": False, "message": f"Failed to restore checkpoint: {exc}"}


class ListSceneCheckpointsTool(ToolBase):
    name = "list_scene_checkpoints"
    description = "List all available scene checkpoints saved during this session."

    def execute(self, params: dict) -> dict:
        target_dir = _ensure_checkpoint_dir()
        checkpoints = []
        for p in target_dir.glob("*.blend"):
            stat = p.stat()
            checkpoints.append({
                "name": p.stem,
                "filepath": str(p),
                "size_bytes": stat.st_size,
                "created_time": stat.st_mtime,
            })
        checkpoints.sort(key=lambda x: x["created_time"], reverse=True)
        return {
            "success": True,
            "count": len(checkpoints),
            "checkpoints": checkpoints,
        }
