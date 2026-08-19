"""Addon preferences panel: connection status + manual start/stop.

Mirrors mcp-unity's "Server Window" concept -- a small always-available
place to see whether the bridge is listening and on what port, plus a
manual override in case the user disabled auto-start or needs to restart
after changing the port.
"""

import sys

import addon_utils
import bpy

from .. import ADDON_PACKAGE, config
from ..bridge import current_address, dispatch, is_running, start_server, stop_server


def _addon_version_string() -> str:
    """Reads the version Blender resolved from blender_manifest.toml at load
    time (via addon_utils), rather than hardcoding it a second place here --
    the manifest is the single source of truth extension builds are tagged
    from."""
    mod = sys.modules.get(ADDON_PACKAGE)
    if mod is None:
        return ""
    version = addon_utils.module_bl_info(mod).get("version")
    return ".".join(str(part) for part in version) if version else ""


def status_text_and_icon() -> tuple[str, str]:
    """Shared by the preferences panel and the status bar so both always
    agree -- one one-line summary of connection + busy state, not two
    independently-maintained copies of the same logic."""
    version = _addon_version_string()
    if not is_running():
        return f"MCP Bridge Pakkio v{version} — Stopped", "X"

    status = dispatch.get_status()
    # An actual bpy call in flight is the more concrete fact when both are
    # present (e.g. mcp_server's client_status says "simplifying..." right as
    # the simplify_geometry RPC it describes starts running) -- prefer it.
    if status["current"] is not None:
        return f"MCP v{version} — {status['current']['description']}", "SORTTIME"
    if status["client_status"] is not None:
        client = status["client_status"]
        return f"MCP v{version} — {client['text']} ({client['running_for_s']}s)", "SORTTIME"

    address = current_address()
    return f"MCP Bridge Pakkio v{version} — waiting on port {address[1]}", "CHECKMARK"


class MCP_OT_start_server(bpy.types.Operator):
    bl_idname = "mcp_bridge_pakkio.start_server"
    bl_label = "Start MCP Bridge"

    def execute(self, context):
        address = start_server()
        if address is None:
            self.report({"ERROR"}, "Failed to start MCP bridge server")
            return {"CANCELLED"}
        self.report({"INFO"}, f"MCP bridge listening on {address[0]}:{address[1]}")
        return {"FINISHED"}


class MCP_OT_stop_server(bpy.types.Operator):
    bl_idname = "mcp_bridge_pakkio.stop_server"
    bl_label = "Stop MCP Bridge"

    def execute(self, context):
        stop_server()
        self.report({"INFO"}, "MCP bridge stopped")
        return {"FINISHED"}


class MCPBridgePreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_PACKAGE

    def draw(self, context):
        layout = self.layout
        text, icon = status_text_and_icon()
        row = layout.row()
        row.label(text=text, icon=icon)
        if is_running():
            row.operator(MCP_OT_stop_server.bl_idname, text="Stop")
        else:
            row.operator(MCP_OT_start_server.bl_idname, text="Start")

        layout.label(text=f"Settings file: {config.settings_path()}")


CLASSES = (MCP_OT_start_server, MCP_OT_stop_server, MCPBridgePreferences)
