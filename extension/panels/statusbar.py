"""Status display: two complementary surfaces so the connection/busy summary
is visible regardless of workspace layout.

STATUSBAR_HT_header.append() is the documented Blender API for this and
works when the current workspace layout has a STATUSBAR area -- but plenty
of saved/custom workspaces don't (confirmed live: a real user's own default
"Layout" screen had none at all, and forcing a full window redraw via
bpy.ops.wm.redraw_timer proved the appended draw function was never even
called -- there's no widget to call it). Area.header_text_set() on every
VIEW_3D area is the reliable fallback: a 3D viewport is present in virtually
every real workspace, and header_text_set() is the same primitive Blender's
own job-progress UI and other addons use for exactly this "show status text
without a dedicated panel" case.
"""

import bpy

from .preferences import status_text_and_icon
from ..bridge import dispatch

_REDRAW_INTERVAL_S = 1.0

# Only used for the tag_redraw() half (STATUSBAR_HT_header path): STATUSBAR
# itself isn't guaranteed to exist (see module docstring), and the
# Preferences window/area otherwise only repaints on user interaction
# (mouse-over, resize), not on a timer.
_TAG_REDRAW_AREA_TYPES = ("STATUSBAR", "PREFERENCES")


def draw_bridge_status(self, context) -> None:
    """STATUSBAR_HT_header.append() target -- renders when the current
    workspace layout actually has a STATUSBAR area. See module docstring."""
    text, icon = status_text_and_icon()
    self.layout.label(text=text, icon=icon)


def tick_statusbar_redraw() -> float:
    """bpy.app.timers callback, always registered (not just while busy):
    it has to keep ticking at idle too, so a busy -> idle transition clears
    the VIEW_3D header text promptly instead of leaving it stuck.

    For an in-progress heavy bpy call (save, render, bake...) this can't
    force a mid-operation update -- that blocks Blender's main thread and
    its own redraw loop completely -- but it does mean everything updates
    promptly the moment control returns. For client_status (mcp_server
    mid-workflow, e.g. downloading an asset over HTTP) the main thread is
    genuinely free the whole time, so this ticks the "running for Xs"
    display live.
    """
    status = dispatch.get_status()
    text, icon = status_text_and_icon()
    # Only override the viewport header while there's something to say --
    # permanently showing "waiting on port 9876" there would sit on top of
    # the normal View/Select/Add menus for no reason when idle.
    header_text = text if status["busy"] else None

    wm = getattr(bpy.context, "window_manager", None)
    if wm is not None:
        for window in wm.windows:
            for area in window.screen.areas:
                if area.type == "VIEW_3D":
                    area.header_text_set(header_text)
                elif status["busy"] and area.type in _TAG_REDRAW_AREA_TYPES:
                    area.tag_redraw()
    return _REDRAW_INTERVAL_S
