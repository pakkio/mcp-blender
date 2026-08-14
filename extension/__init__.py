"""MCP Bridge Pakkio -- exposes Blender to MCP clients (e.g. Claude) over a
localhost WebSocket, driven by a companion `mcp-blender-pakkio` MCP stdio
server process (see ../mcp_server).

register()/unregister() are Blender's addon lifecycle hooks, called on
enable/disable and on "Reload Scripts" -- there is no domain-reload concept
in Blender to hook into (unlike mcp-unity's AssemblyReloadEvents), so this
is the entire lifecycle surface that matters.
"""

bl_info = {
    "name": "MCP Bridge Pakkio",
    "author": "Claudio Pacchiega",
    "version": (1, 0, 1),
    "blender": (4, 2, 0),
    "location": "View3D > Sidebar > MCP Bridge",
    "description": "WebSocket bridge exposing Blender to MCP clients like Claude",
    "warning": "",
    "doc_url": "https://github.com/claudiopacchiega/mcp-blender-pakkio",
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

from . import config  # noqa: E402
from .bridge import dispatch, start_server, stop_server  # noqa: E402
from .panels import CLASSES  # noqa: E402
from .tools.progress_hud_ops import remove_draw_handler  # noqa: E402


_TIMER_REGISTERED = False


def register() -> None:
    global _TIMER_REGISTERED

    for cls in CLASSES:
        bpy.utils.register_class(cls)

    dispatch.bump_generation()

    if not _TIMER_REGISTERED:
        bpy.app.timers.register(dispatch.drain_queue, first_interval=0.05, persistent=True)
        _TIMER_REGISTERED = True

    start_server()


def unregister() -> None:
    global _TIMER_REGISTERED

    dispatch.bump_generation()
    stop_server()

    if _TIMER_REGISTERED and bpy.app.timers.is_registered(dispatch.drain_queue):
        bpy.app.timers.unregister(dispatch.drain_queue)
    _TIMER_REGISTERED = False

    remove_draw_handler()

    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
