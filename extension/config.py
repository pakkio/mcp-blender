"""Shared config for the in-Blender bridge server.

The MCP server process (a separate, non-bpy process) has no way to ask
Blender for the port it's listening on, so the addon writes a small JSON
file to a well-known, discoverable path on register(); the MCP server reads
it back (config.py in mcp_server), with an env var able to override either
side. This mirrors mcp-unity's ProjectSettings/McpUnitySettings.json
cross-process contract, minus the project-root walk (Blender has no
equivalent of a project directory).
"""

import json
import os
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876

ENV_HOST = "MCP_BLENDER_HOST"
ENV_PORT = "MCP_BLENDER_PORT"


def settings_path() -> Path:
    """Well-known path both processes agree on.

    Deliberately NOT bpy.utils.user_resource("CONFIG") -- that path is
    Blender-version- and platform-specific in ways the external mcp_server
    process (no bpy available) cannot reliably reproduce. A plain
    Path.home()-based path keeps both sides' config.py computing the exact
    same location with zero Blender-version coupling.
    """
    return Path.home() / ".mcp-blender" / "settings.json"


def resolved_host() -> str:
    return os.environ.get(ENV_HOST, DEFAULT_HOST)


def resolved_port() -> int:
    raw = os.environ.get(ENV_PORT)
    return int(raw) if raw else DEFAULT_PORT


def write_settings(host: str, port: int) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"host": host, "port": port}, indent=2))


def load_env_vars() -> None:
    """Load keys from .env files into os.environ if not already present."""
    candidates = [
        Path.home() / ".mcp-blender" / ".env",
        Path.home() / ".env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]
    for candidate in candidates:
        if candidate.is_file():
            try:
                for line in candidate.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"\'')
                        if k and k not in os.environ:
                            os.environ[k] = v
            except Exception:
                pass
