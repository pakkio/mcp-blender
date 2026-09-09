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
ENV_TOOL_MODE = "MCP_BLENDER_TOOL_MODE"  # "AGGREGATED" (default, 13 tools) or "FULL" (138 tools)

# API keys settable without hand-editing a .env file (MCP set_api_keys tool
# + Blender addon preferences form). Must stay in sync with
# extension/config.py's MANAGED_KEYS -- both processes persist to the same
# ~/.mcp-blender/.env file.
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


def parse_env_text(text: str) -> dict[str, str]:
    """Parse simple KEY=VALUE lines from .env file text into a dict.

    Shared by _load_env_file (which applies these to os.environ) and
    env_info_ops (which reports them without mutating os.environ), so the
    two stay in sync automatically.
    """
    values: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            values[key] = value
    return values


def _load_env_file(path: Path) -> None:
    """Parse simple KEY=VALUE lines from a .env file into os.environ.

    Real environment variables always win -- this only fills in gaps.
    No python-dotenv dependency; this repo's config style is zero-dep.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return
    for key, value in parse_env_text(text).items():
        if key not in os.environ:
            os.environ[key] = value


def load_dotenv(home: Path | None = None) -> None:
    """Load .env from cwd, then ~/.mcp-blender/.env (cwd wins on conflicts)."""
    home = home or Path.home()
    for candidate in (Path.cwd() / ".env", home / ".mcp-blender" / ".env"):
        if candidate.exists():
            _load_env_file(candidate)


def settings_path(home: Path | None = None) -> Path:
    """Must match extension/config.py's settings_path() exactly."""
    home = home or Path.home()
    return home / ".mcp-blender" / "settings.json"


def writable_env_file(home: Path | None = None) -> Path:
    """Canonical user-writable .env location (mirrors extension/config.py)."""
    home = home or Path.home()
    return home / ".mcp-blender" / ".env"


def _quote_env_value(value: str) -> str:
    if any(c in value for c in (" ", "\t", "#", '"', "'")):
        return '"' + value.replace('"', "") + '"'
    return value


def save_env_keys(values: dict[str, str], home: Path | None = None) -> Path:
    """Persist API keys to ~/.mcp-blender/.env, preserving unrelated lines.

    Only MANAGED_KEYS present in `values` are touched: non-empty values are
    added/updated, empty values remove the line (key becomes unset). Applies
    the same values to os.environ so the running server uses them without
    a restart. Returns the file path written.
    """
    path = writable_env_file(home)
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
                continue
        out.append(line)

    for k in MANAGED_KEYS:
        if k in updates and updates[k] and k not in seen:
            out.append(f"{k}={_quote_env_value(updates[k])}")

    path.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")

    for k, v in updates.items():
        if v:
            os.environ[k] = v
        else:
            os.environ.pop(k, None)
    return path


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


def resolve_tool_mode() -> str:
    """Return tool registration mode: 'AGGREGATED' (13 tools) or 'FULL' (138 tools)."""
    return os.environ.get(ENV_TOOL_MODE, "AGGREGATED").upper()
