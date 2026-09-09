"""Addon preferences panel: connection status + manual start/stop + API keys.

Mirrors mcp-unity's "Server Window" concept -- a small always-available
place to see whether the bridge is listening and on what port, plus a
manual override in case the user disabled auto-start or needs to restart
after changing the port.

API keys (Sketchfab, OpenRouter, Meshy, Tripo, Trellis/HF) are editable
right here so nobody has to hand-edit a .env file: Save writes them to
~/.mcp-blender/.env (the same file the MCP server process reads) and
applies them to this Blender process immediately.
"""

import sys

import addon_utils
import bpy

from .. import ADDON_PACKAGE, config
from ..bridge import current_address, dispatch, is_running, start_server, stop_server

# AddonPreferences property name -> .env key. Property names are lowercase
# identifiers; env keys are the canonical UPPER_SNAKE names both processes
# agree on (see config.MANAGED_KEYS).
PREF_PROP_TO_ENV = {
    "sketchfab_api_token": "SKETCHFAB_API_TOKEN",
    "openrouter_api_key": "OPENROUTER_API_KEY",
    "meshy_api_key": "MESHY_API_KEY",
    "tripo_api_key": "TRIPO_API_KEY",
    "trellis_api_key": "TRELLIS_API_KEY",
    "hf_token": "HF_TOKEN",
    "openrouter_vision_model": "OPENROUTER_VISION_MODEL",
    "trellis_endpoint_url": "TRELLIS_ENDPOINT_URL",
}

_SECRET_PROPS = {
    "sketchfab_api_token",
    "openrouter_api_key",
    "meshy_api_key",
    "tripo_api_key",
    "trellis_api_key",
    "hf_token",
}

# One-shot per-session flag: the prefs form mirrors the .env file, but
# Blender also persists prefs into userpref.blend -- on a fresh enable the
# form fields are empty while .env already has values, so the first draw
# pulls .env/os.environ into the form once instead of showing blanks.
# Subsequent draws must NOT re-pull, or they'd wipe the user's in-progress
# edits on every redraw.
_API_KEYS_SYNCED = False


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
        return f"MCP Bridge v{version} — Stopped", "X"

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
    return f"MCP Bridge v{version} — waiting on port {address[1]}", "CHECKMARK"


class MCP_OT_start_server(bpy.types.Operator):
    bl_idname = "mcp_bridge.start_server"
    bl_label = "Start MCP Bridge"

    def execute(self, context):
        address = start_server()
        if address is None:
            self.report({"ERROR"}, "Failed to start MCP bridge server")
            return {"CANCELLED"}
        self.report({"INFO"}, f"MCP bridge listening on {address[0]}:{address[1]}")
        return {"FINISHED"}


class MCP_OT_stop_server(bpy.types.Operator):
    bl_idname = "mcp_bridge.stop_server"
    bl_label = "Stop MCP Bridge"

    def execute(self, context):
        stop_server()
        self.report({"INFO"}, "MCP bridge stopped")
        return {"FINISHED"}


class MCP_OT_save_api_keys(bpy.types.Operator):
    bl_idname = "mcp_bridge.save_api_keys"
    bl_label = "Save API Keys"
    bl_description = (
        "Save the API keys below to ~/.mcp-blender/.env so you never have to "
        "edit the file by hand. Applies immediately to this Blender session; "
        "restart the MCP server process so it picks them up too"
    )

    def execute(self, context):
        prefs = context.preferences.addons[ADDON_PACKAGE].preferences
        values = {env: getattr(prefs, prop, "") or "" for prop, env in PREF_PROP_TO_ENV.items()}
        try:
            path = config.save_managed_keys(values)
        except OSError as exc:
            self.report({"ERROR"}, f"Could not write .env: {exc}")
            return {"CANCELLED"}
        count = sum(1 for v in values.values() if v)
        self.report({"INFO"}, f"Saved {count} key(s) to {path} (MCP server needs a restart)")
        return {"FINISHED"}


class MCP_OT_reload_api_keys(bpy.types.Operator):
    bl_idname = "mcp_bridge.reload_api_keys"
    bl_label = "Reload from .env"
    bl_description = "Discard form edits and reload the fields from .env / environment"

    def execute(self, context):
        prefs = context.preferences.addons[ADDON_PACKAGE].preferences
        _sync_prefs_from_env(prefs, force=True)
        self.report({"INFO"}, "API key fields reloaded from .env")
        return {"FINISHED"}


def _sync_prefs_from_env(prefs, force: bool = False) -> None:
    """Pull effective .env/os.environ values into the prefs form fields."""
    global _API_KEYS_SYNCED
    if not force and _API_KEYS_SYNCED:
        return
    try:
        current = config.read_managed_keys()
    except Exception:
        return
    for prop, env in PREF_PROP_TO_ENV.items():
        try:
            setattr(prefs, prop, current.get(env, "") or "")
        except Exception:
            pass
    _API_KEYS_SYNCED = True


class MCPBridgePreferences(bpy.types.AddonPreferences):
    bl_idname = ADDON_PACKAGE

    sketchfab_api_token: bpy.props.StringProperty(
        name="Sketchfab API Token",
        description="Needed only to DOWNLOAD Sketchfab models (search works without it). Get one at sketchfab.com > Settings > Password (API Token tab)",
        default="",
        subtype="PASSWORD",
    )
    openrouter_api_key: bpy.props.StringProperty(
        name="OpenRouter API Key",
        description="Powers LLM renaming, vision-assisted naming and scene critique. Get one at openrouter.ai/keys",
        default="",
        subtype="PASSWORD",
    )
    meshy_api_key: bpy.props.StringProperty(
        name="Meshy API Key",
        description="AI text/image-to-3D generation via Meshy AI (meshy.ai)",
        default="",
        subtype="PASSWORD",
    )
    tripo_api_key: bpy.props.StringProperty(
        name="Tripo API Key",
        description="AI text/image-to-3D generation via Tripo3D (tripo3d.ai)",
        default="",
        subtype="PASSWORD",
    )
    trellis_api_key: bpy.props.StringProperty(
        name="Trellis API Key",
        description="Bearer token for your Trellis image-to-3D endpoint (or use HF Token below)",
        default="",
        subtype="PASSWORD",
    )
    hf_token: bpy.props.StringProperty(
        name="Hugging Face Token",
        description="Alternative bearer token for the Trellis endpoint (huggingface.co)",
        default="",
        subtype="PASSWORD",
    )
    openrouter_vision_model: bpy.props.StringProperty(
        name="Vision Model",
        description="Optional override for the cheap vision model (e.g. google/gemini-2.5-flash). Empty = default",
        default="",
    )
    trellis_endpoint_url: bpy.props.StringProperty(
        name="Trellis Endpoint URL",
        description="Active Hugging Face Inference Endpoint running a Trellis image-to-3D handler",
        default="",
    )

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

        layout.separator()
        _sync_prefs_from_env(self)
        box = layout.box()
        box.label(text="API Keys (saved to ~/.mcp-blender/.env -- no file editing needed)", icon="LOCKED")
        for prop in (
            "sketchfab_api_token",
            "openrouter_api_key",
            "meshy_api_key",
            "tripo_api_key",
            "trellis_api_key",
            "hf_token",
        ):
            r = box.row()
            r.prop(self, prop)
            r.label(text="set" if (getattr(self, prop, "") or "") else "not set",
                    icon="CHECKMARK" if (getattr(self, prop, "") or "") else "X")
        box.prop(self, "openrouter_vision_model")
        box.prop(self, "trellis_endpoint_url")
        row_btn = box.row(align=True)
        row_btn.operator(MCP_OT_save_api_keys.bl_idname, text="Save API Keys", icon="FILE_TICK")
        row_btn.operator(MCP_OT_reload_api_keys.bl_idname, text="Reload from .env", icon="FILE_REFRESH")
        box.label(text="Save applies instantly here; restart the MCP server to apply there.",
                  icon="INFO")


CLASSES = (
    MCP_OT_start_server,
    MCP_OT_stop_server,
    MCP_OT_save_api_keys,
    MCP_OT_reload_api_keys,
    MCPBridgePreferences,
)
