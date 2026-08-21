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
    "completed_summary": "",
    "next_steps": [],
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
    details_shown = HUD_STATE["details"][-4:]
    next_steps_shown = HUD_STATE["next_steps"][-3:]
    card_h = 45 + max(1, len(details_shown)) * 18 + 30
    if HUD_STATE["completed_summary"]:
        card_h += 22
    if next_steps_shown:
        card_h += 18 + len(next_steps_shown) * 16
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
    for detail in details_shown:
        blf.color(font_id, 0.55, 0.65, 0.75, 0.95)
        blf.position(font_id, x_min + 20, y_cursor, 0)
        blf.draw(font_id, f"• {detail[:42]}")
        y_cursor -= 18

    # Completed Summary (what was done) - Emerald accent
    if HUD_STATE["completed_summary"]:
        blf.size(font_id, 11)
        blf.color(font_id, 0.35, 0.9, 0.55, 1.0)
        blf.position(font_id, x_min + 15, y_cursor - 4, 0)
        blf.draw(font_id, f"✔ Done: {HUD_STATE['completed_summary'][:45]}")
        y_cursor -= 22

    # Next Steps (what you can do next) - Amber accent
    if next_steps_shown:
        blf.size(font_id, 10)
        blf.color(font_id, 0.95, 0.75, 0.3, 1.0)
        blf.position(font_id, x_min + 15, y_cursor - 4, 0)
        blf.draw(font_id, "Next steps:")
        y_cursor -= 18
        for step in next_steps_shown:
            blf.color(font_id, 0.85, 0.8, 0.6, 0.95)
            blf.position(font_id, x_min + 20, y_cursor, 0)
            blf.draw(font_id, f"→ {step[:42]}")
            y_cursor -= 16


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


def push_hud_update(
    title: str,
    status: str,
    progress_percent: float,
    step_current: int = 0,
    step_total: int = 0,
    details=None,
    completed_summary: str = "",
    next_steps=None,
    show_hud: bool = True,
    auto_hide_seconds: float = 0.0,
    force_redraw: bool = False,
) -> None:
    """Direct (non-JSON-tool) entry point other extension modules call to
    drive the floating HUD from inside their own long-running loops.

    A plain area.tag_redraw() only schedules a repaint for Blender's next
    trip through its event loop -- fine for update_progress_hud's normal
    callers (each a separate bridge round-trip from the external mcp_server
    process, so control already returns to the event loop between calls) but
    useless for a loop that runs entirely inside one Operator.execute() call
    (e.g. RegenElementNamesTool's or SeparateLogicalAreasTool's vision-assist
    pass): the event loop never runs until execute() itself returns, so nothing
    would visibly update until the whole operation is already finished -- from
    the user's perspective, indistinguishable from a frozen UI. force_redraw
    additionally forces one real, immediate redraw+buffer-swap via
    wm.redraw_timer so the HUD actually appears on screen mid-loop.
    """
    _ensure_draw_handler()

    HUD_STATE["visible"] = show_hud
    HUD_STATE["title"] = title
    HUD_STATE["status"] = status
    HUD_STATE["progress"] = progress_percent
    HUD_STATE["step_current"] = step_current
    HUD_STATE["step_total"] = step_total
    HUD_STATE["last_update"] = time.time()
    HUD_STATE["completed_summary"] = completed_summary

    if isinstance(next_steps, list):
        HUD_STATE["next_steps"] = next_steps
    elif isinstance(next_steps, str) and next_steps:
        HUD_STATE["next_steps"] = [next_steps]
    elif next_steps is None:
        pass
    else:
        HUD_STATE["next_steps"] = []

    if isinstance(details, list):
        HUD_STATE["details"] = details
    elif isinstance(details, str):
        HUD_STATE["details"].append(details)

    if auto_hide_seconds > 0:
        HUD_STATE["auto_hide_time"] = time.time() + auto_hide_seconds
    elif progress_percent >= 100.0:
        HUD_STATE["auto_hide_time"] = time.time() + 6.0
    else:
        HUD_STATE["auto_hide_time"] = 0.0

    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.tag_redraw()

    if force_redraw:
        try:
            bpy.ops.wm.redraw_timer(type="DRAW_WIN_SWAP", iterations=1)
        except Exception:
            pass


class UpdateProgressHUDTool(ToolBase):
    name = "update_progress_hud"
    description = "Display or update a non-modal floating progress HUD card in Blender with progress percentage (0-100%), task title, status, detailed step explanations, a completed-work summary, and suggested next steps, without blocking user interaction."

    def execute(self, params: dict) -> dict:
        title = params.get("title", "MCP Task")
        status = params.get("status", "Working...")
        progress = float(params.get("progress_percent", 0.0))
        step_current = int(params.get("step_current", 0))
        step_total = int(params.get("step_total", 0))
        details = params.get("details", [])
        show_hud = bool(params.get("show_hud", True))
        auto_hide_seconds = float(params.get("auto_hide_seconds", 0.0))
        completed_summary = params.get("completed_summary", "")
        next_steps = params.get("next_steps", [])

        push_hud_update(
            title=title,
            status=status,
            progress_percent=progress,
            step_current=step_current,
            step_total=step_total,
            details=details,
            completed_summary=completed_summary,
            next_steps=next_steps,
            show_hud=show_hud,
            auto_hide_seconds=auto_hide_seconds,
            force_redraw=False,
        )

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
        HUD_STATE["completed_summary"] = ""
        HUD_STATE["next_steps"] = []

        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

        return {
            "success": True,
            "message": "Cleared and hid progress HUD",
        }
