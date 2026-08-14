"""Discovers where the Blender-side bridge is listening.

Precedence: env var > settings file (written by the extension on register())
> hardcoded default. The settings-file path must match extension/config.py's
settings_path() exactly -- see that module's docstring for why this file is
the cross-process contract instead of e.g. a CLI flag (the MCP client
launches this process over stdio and doesn't know or care about Blender's
address, mirroring mcp-unity's ProjectSettings/McpUnitySettings.json).
"""

import json
import os
from pathlib import Path

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 9876

ENV_HOST = "MCP_BLENDER_HOST"
ENV_PORT = "MCP_BLENDER_PORT"


def settings_path(home: Path | None = None) -> Path:
    """Must match extension/config.py's settings_path() exactly."""
    home = home or Path.home()
    return home / ".mcp_blender_pakkio" / "settings.json"


def resolve_host_port(home: Path | None = None) -> tuple[str, int]:
    env_host = os.environ.get(ENV_HOST)
    env_port = os.environ.get(ENV_PORT)
    if env_host and env_port:
        return env_host, int(env_port)

    path = settings_path(home)
    if path.exists():
        try:
            data = json.loads(path.read_text())
            return (
                env_host or data.get("host", DEFAULT_HOST),
                int(env_port or data.get("port", DEFAULT_PORT)),
            )
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    return env_host or DEFAULT_HOST, int(env_port) if env_port else DEFAULT_PORT
