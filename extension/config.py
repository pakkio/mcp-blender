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

# API keys editable from the addon preferences form (no .env editing needed).
# Secrets use password fields in the UI; public config is shown verbatim.
MANAGED_SECRET_KEYS = (
    "SKETCHFAB_API_TOKEN",
    "OPENROUTER_API_KEY",
    "MESHY_API_KEY",
    "TRIPO_API_KEY",
    "TRELLIS_API_KEY",
    "HF_TOKEN",
)
MANAGED_PUBLIC_KEYS = (
    "OPENROUTER_VISION_MODEL",
    "TRELLIS_ENDPOINT_URL",
)
MANAGED_KEYS = MANAGED_SECRET_KEYS + MANAGED_PUBLIC_KEYS


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


def env_file_candidates() -> list[Path]:
    """.env search path, in precedence order (first hit wins per key)."""
    return [
        Path.home() / ".mcp-blender" / ".env",
        Path.home() / ".env",
        Path.cwd() / ".env",
        Path(__file__).resolve().parent.parent / ".env",
    ]


def parse_env_text(text: str) -> dict[str, str]:
    """Parse simple KEY=VALUE lines from .env file text into a dict.

    Shared by load_env_vars (which applies these to os.environ) and
    env_info_ops (which reports them without mutating os.environ), so the
    two stay in sync automatically.
    """
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"\'')
            if k:
                values[k] = v
    return values


def load_env_vars() -> None:
    """Load keys from .env files into os.environ if not already present."""
    for candidate in env_file_candidates():
        if candidate.is_file():
            try:
                for k, v in parse_env_text(candidate.read_text(encoding="utf-8")).items():
                    if k not in os.environ:
                        os.environ[k] = v
            except Exception:
                pass


def writable_env_file() -> Path:
    """Canonical user-writable .env location the preferences form saves to.

    First entry of env_file_candidates(), so it wins per-key over every
    other candidate -- and one of the two files the MCP server process
    reads (see mcp_server config.load_dotenv), so keys saved here apply
    to both processes (server picks them up on restart, Blender immediately).
    """
    return Path.home() / ".mcp-blender" / ".env"


def read_managed_keys() -> dict[str, str]:
    """Effective values for the form-editable keys (env var wins over .env).

    Ensures .env files are loaded into os.environ first, so a fresh Blender
    process shows the persisted values even before any tool ran.
    """
    load_env_vars()
    return {k: os.environ.get(k, "") or "" for k in MANAGED_KEYS}


def apply_keys_to_environ(values: dict[str, str]) -> None:
    """Push form values into this process's os.environ for immediate use.

    Non-empty values are set; empty ones are removed so clearing a field
    takes effect without a restart (a real env var of the same name will
    reappear on next process start -- that precedence is intentional).
    """
    for k in MANAGED_KEYS:
        if k not in values:
            continue
        v = values[k] or ""
        if v:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)


def _quote_env_value(value: str) -> str:
    if any(c in value for c in (' ', '\t', '#', '"', "'")):
        return '"' + value.replace('"', "") + '"'
    return value


def save_managed_keys(values: dict[str, str]) -> Path:
    """Persist form values to the writable .env file, preserving the rest.

    - Existing lines for unrelated keys and comments are kept verbatim.
    - Managed keys given a non-empty value are added/updated in place.
    - Managed keys given an empty value are removed (shown as unset).
    - Applies the same values to os.environ so Blender tools use them
      immediately without a restart.
    Returns the file path written.
    """
    path = writable_env_file()
    path.parent.mkdir(parents=True, exist_ok=True)

    updates = {k: (values.get(k) or "") for k in MANAGED_KEYS if k in values}

    lines: list[str] = []
    if path.is_file():
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            lines = []

    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _, _ = stripped.partition("=")
            k = k.strip()
            if k in updates:
                seen.add(k)
                if updates[k]:
                    out.append(f"{k}={_quote_env_value(updates[k])}")
                # empty -> drop the line (key becomes unset)
                continue
        out.append(line)

    for k in MANAGED_KEYS:
        if k in updates and updates[k] and k not in seen:
            out.append(f"{k}={_quote_env_value(updates[k])}")

    path.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
    apply_keys_to_environ(updates)
    return path
