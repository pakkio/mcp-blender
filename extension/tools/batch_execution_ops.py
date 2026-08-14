import time
import bpy

from .base import ToolBase
from .progress_hud_ops import HUD_STATE, _ensure_draw_handler


class ExecuteBatchTool(ToolBase):
    name = "execute_batch"
    description = "Execute a sequence of multiple MCP tool operations in a single optimized batch roundtrip with real-time HUD progress updates, error rollback, and comprehensive per-step reporting."

    def execute(self, params: dict) -> dict:
        commands = params.get("commands", [])
        stop_on_error = bool(params.get("stop_on_error", True))
        update_hud = bool(params.get("update_hud", True))
        batch_title = params.get("title", "Batch Execution")

        if not commands:
            return {"success": False, "message": "No commands provided in batch"}

        from bl_ext.user_default.mcp_bridge_pakkio.bridge.dispatch import TOOL_REGISTRY

        results = []
        total = len(commands)
        failed_index = None

        if update_hud:
            _ensure_draw_handler()
            HUD_STATE["visible"] = True
            HUD_STATE["title"] = batch_title
            HUD_STATE["step_total"] = total
            HUD_STATE["details"] = []

        start_time = time.time()

        for idx, cmd in enumerate(commands):
            tool_name = cmd.get("tool")
            tool_params = cmd.get("params", {})
            optional = bool(cmd.get("optional", False))
            description = cmd.get("description", f"Step {idx + 1}: {tool_name}")

            # Update HUD
            pct = round((idx / total) * 100.0, 1)
            if update_hud:
                HUD_STATE["progress"] = pct
                HUD_STATE["step_current"] = idx + 1
                HUD_STATE["status"] = description
                HUD_STATE["details"].append(f"[{idx + 1}/{total}] {tool_name}")
                for w in bpy.context.window_manager.windows:
                    for a in w.screen.areas:
                        if a.type == "VIEW_3D":
                            a.tag_redraw()

            tool = TOOL_REGISTRY.get(tool_name)
            if not tool:
                res = {"success": False, "message": f"Tool '{tool_name}' not found in registry"}
            else:
                try:
                    res = tool.execute(tool_params)
                except Exception as exc:
                    res = {"success": False, "message": f"Exception in '{tool_name}': {exc}"}

            results.append({
                "index": idx,
                "tool": tool_name,
                "description": description,
                "result": res,
                "success": res.get("success", False),
            })

            if not res.get("success", False) and not optional:
                failed_index = idx
                if stop_on_error:
                    break

        duration = round(time.time() - start_time, 3)
        all_ok = failed_index is None

        if update_hud:
            HUD_STATE["progress"] = 100.0 if all_ok else pct
            HUD_STATE["status"] = "Completed Successfully" if all_ok else f"Failed at step {failed_index + 1}"
            HUD_STATE["auto_hide_time"] = time.time() + 5.0
            for w in bpy.context.window_manager.windows:
                for a in w.screen.areas:
                    if a.type == "VIEW_3D":
                        a.tag_redraw()

        return {
            "success": all_ok,
            "message": f"Batch '{batch_title}' executed {len(results)}/{total} commands in {duration}s",
            "total_commands": total,
            "total_executed": len(results),
            "failed_index": failed_index,
            "duration_seconds": duration,
            "results": results,
        }
