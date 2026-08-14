"""Addon preferences panel: connection status + manual start/stop.

Mirrors mcp-unity's "Server Window" concept -- a small always-available
place to see whether the bridge is listening and on what port, plus a
manual override in case the user disabled auto-start or needs to restart
after changing the port.
"""

import bpy

from .. import ADDON_PACKAGE, config
from ..bridge import current_address, is_running, start_server, stop_server


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
        row = layout.row()
        if is_running():
            address = current_address()
            row.label(text=f"Running on {address[0]}:{address[1]}", icon="CHECKMARK")
            row.operator(MCP_OT_stop_server.bl_idname, text="Stop")
        else:
            row.label(text="Stopped", icon="X")
            row.operator(MCP_OT_start_server.bl_idname, text="Start")

        layout.label(text=f"Settings file: {config.settings_path()}")


CLASSES = (MCP_OT_start_server, MCP_OT_stop_server, MCPBridgePreferences)
