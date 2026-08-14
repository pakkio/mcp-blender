import time
import blf
import bpy
import gpu
from gpu_extras.batch import batch_for_shader

from .base import ToolBase

# Global state for non-modal HUD
HUD_STATE = {
    "visible": False,
    "title": "MCP Agent Progress",
    "status": "Idle",
    "progress": 0.0,  # 0.0 to 100.0
    "step_current": 0,
    "step_total": 0,
    "details": [],
    "last_update": 0.0,
    "auto_hide_time": 0.0,
}

_DRAW_HANDLER = None


def _get_builtin_shader(name_2d, name_legacy):
    if hasattr(gpu.shader, "from_builtin"):
        try:
            return gpu.shader.from_builtin(name_2d)
        except Exception:
            return gpu.shader.from_builtin(name_legacy)
    return None


def _draw_hud_callback():
    if not HUD_STATE["visible"]:
        return

    # Check auto-hide
    if HUD_STATE["auto_hide_time"] > 0 and time.time() > HUD_STATE["auto_hide_time"]:
        HUD_STATE["visible"] = False
        return

    # Viewport dimensions
    area = bpy.context.area
    if not area:
        return
    width = area.width
    height = area.height

    # HUD Box dimensions (Top-Right Floating Glass Card)
    card_w = 360
    card_h = 45 + max(1, len(HUD_STATE["details"])) * 18 + 30
    x_max = width - 20
    x_min = x_max - card_w
    y_max = height - 50
    y_min = y_max - card_h

    # Shader for 2D geometry
    try:
        shader = _get_builtin_shader("POLYLINE_UNIFORM_COLOR", "2D_UNIFORM_COLOR") or gpu.shader.from_builtin("UNIFORM_COLOR")
    except Exception:
        return

    gpu.state.blend_set("ALPHA")

    # 1. Background Card (Dark Translucent Glass)
    bg_verts = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max)]
    bg_indices = [(0, 1, 2), (2, 3, 0)]
    batch_bg = batch_for_shader(shader, "TRIS", {"pos": bg_verts}, indices=bg_indices)
    shader.bind()
    shader.uniform_float("color", (0.08, 0.09, 0.12, 0.92))
    batch_bg.draw(shader)

    # 2. Border Outline (Neon Cyan Accent)
    border_verts = [(x_min, y_min), (x_max, y_min), (x_max, y_max), (x_min, y_max), (x_min, y_min)]
    batch_border = batch_for_shader(shader, "LINE_STRIP", {"pos": border_verts})
    shader.uniform_float("color", (0.0, 0.8, 1.0, 0.7))
    batch_border.draw(shader)

    # 3. Progress Bar Track & Fill
    bar_x_min = x_min + 15
    bar_x_max = x_max - 15
    bar_y_max = y_max - 42
    bar_y_min = bar_y_max - 8
    bar_total_w = bar_x_max - bar_x_min

    # Track (Dark Gray)
    track_verts = [(bar_x_min, bar_y_min), (bar_x_max, bar_y_min), (bar_x_max, bar_y_max), (bar_x_min, bar_y_max)]
    batch_track = batch_for_shader(shader, "TRIS", {"pos": track_verts}, indices=bg_indices)
    shader.uniform_float("color", (0.18, 0.2, 0.25, 0.9))
    batch_track.draw(shader)

    # Fill (Gradient Cyan / Emerald)
    pct = max(0.0, min(100.0, HUD_STATE["progress"])) / 100.0
    fill_x_max = bar_x_min + bar_total_w * pct
    if fill_x_max > bar_x_min:
        fill_verts = [(bar_x_min, bar_y_min), (fill_x_max, bar_y_min), (fill_x_max, bar_y_max), (bar_x_min, bar_y_max)]
        batch_fill = batch_for_shader(shader, "TRIS", {"pos": fill_verts}, indices=bg_indices)
        # Color transitions from Cyan to Emerald at 100%
        r = 0.0
        g = 0.8 + 0.2 * pct
        b = 1.0 - 0.5 * pct
        shader.uniform_float("color", (r, g, b, 1.0))
        batch_fill.draw(shader)

    gpu.state.blend_set("NONE")

    # 4. Text Typography using BLF
    font_id = 0
    # Title
    blf.size(font_id, 14)
    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
    blf.position(font_id, x_min + 15, y_max - 24, 0)
    blf.draw(font_id, f"⚡ {HUD_STATE['title']}")

    # Percentage / Step count
    blf.size(font_id, 12)
    step_str = f"[{HUD_STATE['step_current']}/{HUD_STATE['step_total']}] " if HUD_STATE['step_total'] > 0 else ""
    pct_text = f"{step_str}{int(HUD_STATE['progress'])}%"
    blf.color(font_id, 0.0, 0.85, 1.0, 1.0)
    blf.position(font_id, x_max - 85, y_max - 24, 0)
    blf.draw(font_id, pct_text)

    # Status / Explanation
    blf.size(font_id, 11)
    blf.color(font_id, 0.75, 0.82, 0.9, 1.0)
    blf.position(font_id, x_min + 15, y_max - 60, 0)
    blf.draw(font_id, f"Status: {HUD_STATE['status']}")

    # Detailed Step History
    y_cursor = y_max - 80
    blf.size(font_id, 10)
    for detail in HUD_STATE["details"][-4:]:  # Show last 4 details
        blf.color(font_id, 0.55, 0.65, 0.75, 0.95)
        blf.position(font_id, x_min + 20, y_cursor, 0)
        blf.draw(font_id, f"• {detail[:42]}")
        y_cursor -= 18


def _ensure_draw_handler():
    global _DRAW_HANDLER
    if _DRAW_HANDLER is None:
        _DRAW_HANDLER = bpy.types.SpaceView3D.draw_handler_add(
            _draw_hud_callback, (), "WINDOW", "POST_PIXEL"
        )


def remove_draw_handler():
    """Called from extension unregister() so disable/"Reload Scripts" doesn't
    accumulate a new draw handler on every re-register."""
    global _DRAW_HANDLER
    if _DRAW_HANDLER is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_DRAW_HANDLER, "WINDOW")
        _DRAW_HANDLER = None


class UpdateProgressHUDTool(ToolBase):
    name = "update_progress_hud"
    description = "Display or update a non-modal floating progress HUD card in Blender with progress percentage (0-100%), task title, status, and detailed step explanations without blocking user interaction."

    def execute(self, params: dict) -> dict:
        _ensure_draw_handler()

        title = params.get("title", "MCP Task")
        status = params.get("status", "Working...")
        progress = float(params.get("progress_percent", 0.0))
        step_current = int(params.get("step_current", 0))
        step_total = int(params.get("step_total", 0))
        details = params.get("details", [])
        show_hud = bool(params.get("show_hud", True))
        auto_hide_seconds = float(params.get("auto_hide_seconds", 0.0))

        HUD_STATE["visible"] = show_hud
        HUD_STATE["title"] = title
        HUD_STATE["status"] = status
        HUD_STATE["progress"] = progress
        HUD_STATE["step_current"] = step_current
        HUD_STATE["step_total"] = step_total
        HUD_STATE["last_update"] = time.time()

        if isinstance(details, list):
            HUD_STATE["details"] = details
        elif isinstance(details, str):
            HUD_STATE["details"].append(details)

        if auto_hide_seconds > 0:
            HUD_STATE["auto_hide_time"] = time.time() + auto_hide_seconds
        elif progress >= 100.0:
            HUD_STATE["auto_hide_time"] = time.time() + 6.0
        else:
            HUD_STATE["auto_hide_time"] = 0.0

        # Tag all viewports for redraw
        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

        return {
            "success": True,
            "message": f"Updated HUD: '{title}' - {progress}% ({status})",
            "progress_percent": progress,
            "visible": show_hud,
        }


class ClearProgressHUDTool(ToolBase):
    name = "clear_progress_hud"
    description = "Hide and clear the floating non-modal progress HUD window in Blender."

    def execute(self, params: dict) -> dict:
        HUD_STATE["visible"] = False
        HUD_STATE["details"] = []
        HUD_STATE["progress"] = 0.0

        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

        return {
            "success": True,
            "message": "Cleared and hid progress HUD",
        }
