"""Server-side environment disclosure: which venv is the MCP server running
from, and which secret-bearing keys are present in its environment.

Values are never returned in full -- each is masked to its first 3 and last 3
characters (or fully masked when too short to hide anything that way), so the
LLM can verify *which* keys are configured without pulling API keys or tokens
into the conversation context. Each key entry carries the source path (which
.env file declares it, or "environment" for real env vars). Keys whose value
is null/empty are cancelled: their name is struck through (~~NAME~~) and the
masked value reads "cancelled".
"""

import os
import re
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from ..bridge import BlenderBridge

KNOWN_SECRET_KEYS = (
    "SKETCHFAB_API_TOKEN",
    "OPENROUTER_API_KEY",
    "MESHY_API_KEY",
    "TRIPO_API_KEY",
    "TRELLIS_API_KEY",
    "HF_TOKEN",
)

# Non-secret config values: masking them would only mangle useful info
# (e.g. which vision model is selected), so they are returned verbatim.
PUBLIC_KEYS = (
    "OPENROUTER_VISION_MODEL",
)

SECRET_NAME_RE = re.compile(r"(KEY|TOKEN|SECRET|PASSWORD|PASSWD)", re.IGNORECASE)

MIN_MASKABLE_LEN = 8
CANCELLED = "cancelled"


def mask_secret(value: str) -> str:
    if len(value) < MIN_MASKABLE_LEN:
        return "***"
    return f"{value[:3]}...{value[-3:]}"


def _parse_env_file(path: Path) -> dict[str, str]:
    """Same lenient KEY=VALUE parsing as config._load_env_file, but returns
    the raw declarations instead of mutating os.environ."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
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


def collect_env_info(home: os.PathLike | str | None = None) -> dict:
    home = home or os.path.expanduser("~")
    candidates = [Path(os.getcwd()) / ".env", Path(home) / ".mcp-blender" / ".env"]
    env_files = [{"path": str(path), "exists": path.exists()} for path in candidates]

    # Source attribution: cwd/.env wins over ~/.mcp-blender/.env, matching
    # config.load_dotenv's precedence.
    sources: dict[str, str] = {}
    values: dict[str, str] = {}
    for path in reversed(candidates):
        for name, declared in _parse_env_file(path).items():
            sources[name] = str(path)
            values[name] = declared

    names = set(KNOWN_SECRET_KEYS) | set(PUBLIC_KEYS) | set(sources)
    names.update(name for name in os.environ if SECRET_NAME_RE.search(name))

    keys: dict[str, dict] = {}
    for name in sorted(names):
        env_value = os.environ.get(name)
        if name in values:
            # Declared in a .env file: attribute to the file unless a real,
            # different env var overrides it (dotenv itself never overrides).
            value = values[name]
            source: str | None = sources[name]
            if env_value and env_value != value:
                value, source = env_value, "environment"
        else:
            value, source = env_value, "environment"
        if value:
            masked = value if name in PUBLIC_KEYS else mask_secret(value)
            keys[name] = {"masked": masked, "source": source}
        else:
            keys[f"~~{name}~~"] = {"masked": CANCELLED, "source": source}

    return {
        "success": True,
        "python": {
            "executable": sys.executable,
            "venv_path": sys.prefix,
            "base_prefix": sys.base_prefix,
            "in_venv": sys.prefix != sys.base_prefix,
            "version": sys.version.split()[0],
        },
        "env_files": env_files,
        "keys": keys,
        "masking": (
            f"secrets shown as first3...last3 (fully masked when shorter than {MIN_MASKABLE_LEN} chars); "
            f"non-secret config like OPENROUTER_VISION_MODEL is returned verbatim; "
            f'null/empty keys are cancelled as ~~NAME~~ with masked="{CANCELLED}"'
        ),
    }


def register_env_info_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="get_env_info",
        description=(
            "Disclose the full path of the Python venv the MCP server process runs from "
            "(executable, venv prefix, whether it is a venv at all) and which API keys / secrets "
            "are present in its environment (.env files plus real env vars). Secrets show a masked "
            "value (first3...last3 chars only) plus the source path of the .env file that declares "
            "them ('environment' for real env vars); non-secret config such as OPENROUTER_VISION_MODEL "
            "is returned verbatim; keys with null/empty values are cancelled -- name struck through as "
            "~~NAME~~ with masked='cancelled'. Use this before "
            "asset generation or vision tools to check whether MESHY_API_KEY, OPENROUTER_API_KEY, "
            "SKETCHFAB_API_TOKEN, etc. are configured."
        ),
    )
    async def get_env_info() -> dict:
        return collect_env_info()

    return (get_env_info,)
