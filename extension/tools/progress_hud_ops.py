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
    # Cursor-following badge (small "% - what" pill drawn next to the mouse
    # while a blocking run holds the WAIT cursor -- the user stares at the
    # cursor, not the top-right card, during a long simplify).
    "cursor_badge": False,
    "badge_text": "",
}

_DRAW_HANDLER = None

# Last-known mouse position, window coordinates (origin bottom-left, matching
# event.mouse_x/mouse_y). Written by MCP_OT_track_cursor on every mouse move;
# read by the badge painter to anchor itself next to the cursor. t == 0 means
# "never recorded" (tracker couldn't start, e.g. background mode) and the
# badge stays hidden -- the card still shows progress.
CURSOR_STATE = {"x": 0, "y": 0, "window_ptr": 0, "t": 0.0}

# Tracker lifecycle: WANT is set at addon register and cleared at unregister;
# RUNNING tracks the live modal operator. A file load kills modal operators
# silently, so the statusbar tick re-runs ensure_cursor_tracker() (which
# no-ops while RUNNING) and a load_post handler resets RUNNING to force it.
TRACKER_WANT = False
_TRACKER_RUNNING = False


def record_cursor(x, y, window_ptr) -> None:
    CURSOR_STATE["x"] = int(x)
    CURSOR_STATE["y"] = int(y)
    CURSOR_STATE["window_ptr"] = int(window_ptr or 0)
    CURSOR_STATE["t"] = time.time()


class MCP_OT_track_cursor(bpy.types.Operator):
    """Internal: remember the mouse position for the progress badge.

    Pure observer -- PASS_THROUGH on every event, so it never steals input.
    """

    bl_idname = "mcp_bridge.track_cursor"
    bl_label = "Track Cursor for Progress Badge"
    bl_options = {"INTERNAL"}

    def invoke(self, context, event):
        global _TRACKER_RUNNING
        _TRACKER_RUNNING = True
        context.window_manager.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        global _TRACKER_RUNNING
        if not TRACKER_WANT:
            _TRACKER_RUNNING = False
            return {"CANCELLED"}
        if event.type in {"MOUSEMOVE", "INBETWEEN_MOUSEMOVE"}:
            try:
                record_cursor(event.mouse_x, event.mouse_y, context.window.as_pointer())
            except Exception:
                pass
        return {"PASS_THROUGH"}

    def cancel(self, context):
        global _TRACKER_RUNNING
        _TRACKER_RUNNING = False


def ensure_cursor_tracker() -> bool:
    """Start the cursor tracker if wanted and not already running.

    Safe to call every second (the statusbar tick does): two bool checks
    when healthy, one guarded operator invoke after a file load killed it.
    """
    if not TRACKER_WANT or _TRACKER_RUNNING or bpy.app.background:
        return _TRACKER_RUNNING
    try:
        bpy.ops.mcp_bridge.track_cursor("INVOKE_DEFAULT")
        return True
    except Exception:
        return False


def _on_file_loaded(_dummy) -> None:
    """load_post handler: file loads silently kill modal operators, so drop
    the flag and let the next statusbar tick restart the tracker."""
    global _TRACKER_RUNNING
    _TRACKER_RUNNING = False


def _get_builtin_shader(name_2d, name_legacy):
    if hasattr(gpu.shader, "from_builtin"):
        try:
            return gpu.shader.from_builtin(name_2d)
        except Exception:
            return gpu.shader.from_builtin(name_legacy)
    return None


def _draw_box(shader, x0, y0, x1, y1, color) -> None:
    """Filled 2D rect with the already-resolved builtin shader (same call
    pattern as the card below, so any Blender-version shader quirk that
    breaks one breaks both -- no silent second code path)."""
    verts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    batch = batch_for_shader(shader, "TRIS", {"pos": verts}, indices=[(0, 1, 2), (2, 3, 0)])
    shader.bind()
    shader.uniform_float("color", color)
    batch.draw(shader)


def _badge_rect(region_w, region_h, area_x, area_y, mx, my, box_w, box_h):
    """Top-left-anchored badge rect next to the cursor, pure math (no bpy).

    Returns (x0, y0) or None when the cursor is outside this region (another
    region or window) so the caller simply skips painting there.
    """
    lx, ly = mx - area_x, my - area_y
    if not (-50 <= lx <= region_w + 50 and -50 <= ly <= region_h + 50):
        return None
    box_w = min(box_w, max(40, region_w - 8))
    x0 = lx + 18
    if x0 + box_w > region_w - 4:
        x0 = lx - 18 - box_w  # flip to the left of the cursor
    y0 = ly - 14 - box_h
    x0 = max(4, min(x0, region_w - box_w - 4))
    y0 = max(4, min(y0, region_h - box_h - 4))
    return (x0, y0)


def _draw_cursor_badge(shader) -> None:
    """Small "% - what" pill at the last-known mouse position."""
    area = bpy.context.area
    if not area or CURSOR_STATE["t"] <= 0:
        return
    if CURSOR_STATE["window_ptr"]:
        try:
            if bpy.context.window.as_pointer() != CURSOR_STATE["window_ptr"]:
                return  # badge belongs to another window
        except Exception:
            pass

    pct = max(0, min(100, int(round(HUD_STATE["progress"]))))
    hint = HUD_STATE.get("badge_text") or HUD_STATE.get("status") or ""
    text = "%d%% - %s" % (pct, hint)

    font_id = 0
    blf.size(font_id, 12)
    text_w, text_h = blf.dimensions(font_id, text)
    pad, bar_w, bar_h = 8, 110, 6
    box_w = max(text_w, bar_w) + pad * 2
    box_h = text_h + bar_h + pad * 2 + 4

    pos = _badge_rect(area.width, area.height, area.x, area.y, CURSOR_STATE["x"], CURSOR_STATE["y"], box_w, box_h)
    if pos is None:
        return
    x0, y0 = pos

    gpu.state.blend_set("ALPHA")
    _draw_box(shader, x0, y0, x0 + box_w, y0 + box_h, (0.08, 0.09, 0.12, 0.93))
    # Mini bar under the text, same cyan->emerald ramp as the card.
    fill = bar_w * pct / 100.0
    _draw_box(shader, x0 + pad, y0 + pad, x0 + pad + bar_w, y0 + pad + bar_h, (0.18, 0.2, 0.25, 0.95))
    if fill > 0:
        _draw_box(
            shader,
            x0 + pad, y0 + pad, x0 + pad + fill, y0 + pad + bar_h,
            (0.0, 0.8 + 0.2 * pct / 100.0, 1.0 - 0.5 * pct / 100.0, 1.0),
        )
    gpu.state.blend_set("NONE")

    blf.color(font_id, 1.0, 1.0, 1.0, 1.0)
    blf.position(font_id, x0 + pad, y0 + pad + bar_h + 4, 0)
    blf.draw(font_id, text)


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

    # Cursor badge: "% - what" pill next to the mouse, for blocking runs
    # where the user stares at the hourglass instead of this card.
    if HUD_STATE.get("cursor_badge"):
        try:
            _draw_cursor_badge(shader)
        except Exception:
            pass  # draw callbacks must never raise into Blender's draw loop


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
    cursor_badge=None,
    badge_text: str = "",
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
    # Badge follows the card: callers that don't mention it (None) never
    # disturb it, so an outer flow's plain push can't kill a badge an inner
    # run just raised. ASCII-only text -- the default BLF font has no emoji.
    if cursor_badge is not None or not show_hud:
        HUD_STATE["cursor_badge"] = bool(cursor_badge) and bool(show_hud)
    if badge_text:
        HUD_STATE["badge_text"] = "".join(c if ord(c) < 128 else "?" for c in badge_text)[:64]

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
        HUD_STATE["cursor_badge"] = False
        HUD_STATE["badge_text"] = ""

        for window in bpy.context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.tag_redraw()

        return {
            "success": True,
            "message": "Cleared and hid progress HUD",
        }
