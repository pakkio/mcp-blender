"""Content-addressed local cache for downloaded assets, so re-importing the
same asset_id is a disk hit instead of a re-download.
"""

from pathlib import Path


def cache_dir(provider: str, asset_id: str, home: Path | None = None) -> Path:
    home = home or Path.home()
    safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in asset_id)
    path = home / ".mcp_blender_pakkio" / "assets" / provider / safe_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_cached_file(provider: str, asset_id: str, home: Path | None = None) -> Path | None:
    directory = cache_dir(provider, asset_id, home)
    for candidate in sorted(directory.glob("*")):
        if candidate.is_file() and not candidate.name.endswith(".json"):
            return candidate
    return None
