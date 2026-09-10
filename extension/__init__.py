"""MCP Bridge -- exposes Blender to MCP clients (e.g. Claude) over a
localhost WebSocket, driven by a companion `mcp-blender` MCP stdio
server process (see ../mcp_server).

register()/unregister() are Blender's addon lifecycle hooks, called on
enable/disable and on "Reload Scripts" -- there is no domain-reload concept
in Blender to hook into (unlike mcp-unity's AssemblyReloadEvents), so this
is the entire lifecycle surface that matters.
"""

bl_info = {
    "name": "MCP Bridge",
    "author": "Claudio Pacchiega",
    "version": (2, 0, 35),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > MCP Bridge",
    "description": "WebSocket bridge exposing Blender to MCP clients like Claude",
    "warning": "",
    "doc_url": "https://github.com/claudiopacchiega/mcp-blender",
    "category": "Development",
}

import sys
from pathlib import Path

# Ensure bundled wheels are available on sys.path if not already present
try:
    import websockets
except ImportError:
    wheels_dir = Path(__file__).resolve().parent / "wheels"
    if wheels_dir.is_dir():
        py_tag = f"cp{sys.version_info.major}{sys.version_info.minor}"
        for whl in wheels_dir.glob("*.whl"):
            whl_str = str(whl)
            if py_tag in whl.name or "none-any" in whl.name:
                if whl_str not in sys.path:
                    sys.path.insert(0, whl_str)

import bpy

ADDON_PACKAGE = __package__

# If reloading within an existing Blender session, clear stale cached submodules
# so Python imports fresh definitions instead of holding onto outdated module objects.
for mod_name in list(sys.modules.keys()):
    if (ADDON_PACKAGE and mod_name.startswith(ADDON_PACKAGE + ".")) or mod_name.startswith(__name__ + "."):
        sys.modules.pop(mod_name, None)

from . import config  # noqa: E402
from .bridge import dispatch, start_server, stop_server  # noqa: E402
from .bridge import scheduler  # noqa: E402
from .panels import CLASSES, draw_bridge_status, tick_statusbar_redraw, tick_tasks_redraw  # noqa: E402
from .tools import progress_hud_ops  # noqa: E402
from .tools.progress_hud_ops import remove_draw_handler  # noqa: E402


_TIMER_REGISTERED = False


def _kick_cursor_tracker():
    """One-shot timer: start the cursor tracker (progress badge anchor) once
    a window exists to host its modal operator. Returns a retry delay until
    it sticks, then never reschedules. The statusbar tick keeps it alive
    afterwards across file loads."""
    try:
        if progress_hud_ops.ensure_cursor_tracker():
            return None
    except Exception:
        pass
    return 0.5


def register() -> None:
    global _TIMER_REGISTERED

    # .env keys must be in os.environ before any tool reads them -- tools
    # call load_env_vars() lazily too, but doing it here covers the prefs
    # form's first draw as well.
    try:
        config.load_env_vars()
    except Exception:
        pass
    try:
        from .panels import preferences as _prefs_mod

        _prefs_mod._API_KEYS_SYNCED = False
    except Exception:
        pass

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    progress_hud_ops.TRACKER_WANT = True
    if progress_hud_ops._on_file_loaded not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(progress_hud_ops._on_file_loaded)
    if not bpy.app.timers.is_registered(_kick_cursor_tracker):
        bpy.app.timers.register(_kick_cursor_tracker, first_interval=0.5)

    dispatch.bump_generation()

    if not _TIMER_REGISTERED:
        bpy.app.timers.register(dispatch.drain_queue, first_interval=0.05, persistent=True)
        _TIMER_REGISTERED = True

    # Async-job pump: one work chunk per tick so queued bridge requests (and
    # the viewport) interleave with long chunked jobs instead of freezing
    # behind them. Same lifetime as drain_queue.
    if not bpy.app.timers.is_registered(scheduler.pump_jobs):
        bpy.app.timers.register(scheduler.pump_jobs, first_interval=0.2, persistent=True)

    if not bpy.app.timers.is_registered(tick_statusbar_redraw):
        bpy.app.timers.register(tick_statusbar_redraw, first_interval=1.0, persistent=True)

    # Live task-box refresh: twice a second while a background task runs
    # (the tick itself no-ops otherwise), so the current task's lines follow
    # it with no clicks.
    if not bpy.app.timers.is_registered(tick_tasks_redraw):
        bpy.app.timers.register(tick_tasks_redraw, first_interval=0.5, persistent=True)

    bpy.types.STATUSBAR_HT_header.append(draw_bridge_status)

    start_server()


def unregister() -> None:
    global _TIMER_REGISTERED

    progress_hud_ops.TRACKER_WANT = False
    if progress_hud_ops._on_file_loaded in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(progress_hud_ops._on_file_loaded)
    if bpy.app.timers.is_registered(_kick_cursor_tracker):
        bpy.app.timers.unregister(_kick_cursor_tracker)

    dispatch.bump_generation()
    scheduler.reset()
    stop_server()

    bpy.types.STATUSBAR_HT_header.remove(draw_bridge_status)

    if bpy.app.timers.is_registered(tick_statusbar_redraw):
        bpy.app.timers.unregister(tick_statusbar_redraw)

    if bpy.app.timers.is_registered(tick_tasks_redraw):
        bpy.app.timers.unregister(tick_tasks_redraw)

    # Clear any header_text_set() the timer left behind -- otherwise a
    # disable while busy leaves stale status text stuck over the normal
    # View/Select/Add menus forever, since nothing else will ever clear it.
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "VIEW_3D":
                area.header_text_set(None)

    if _TIMER_REGISTERED and bpy.app.timers.is_registered(dispatch.drain_queue):
        bpy.app.timers.unregister(dispatch.drain_queue)
    _TIMER_REGISTERED = False

    if bpy.app.timers.is_registered(scheduler.pump_jobs):
        bpy.app.timers.unregister(scheduler.pump_jobs)

    remove_draw_handler()

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
