"""Content-addressed local cache for downloaded assets, so re-importing the
same asset_id is a disk hit instead of a re-download.
"""

from pathlib import Path


def cache_dir(provider: str, asset_id: str, home: Path | None = None) -> Path:
    home = home or Path.home()
    safe_id = "".join(c if c.isalnum() or c in "-_." else "_" for c in asset_id)
    path = home / ".mcp-blender" / "assets" / provider / safe_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_cached_file(provider: str, asset_id: str, home: Path | None = None) -> Path | None:
    directory = cache_dir(provider, asset_id, home)

    # A texture-map set (multiple loose image files, e.g. Poly Haven textures)
    # is cached under a "textures" subdirectory precisely so it stays
    # distinguishable from a single-file (model/HDRI) cache hit below --
    # otherwise glob("*") would pick one arbitrary map file and hand it to
    # callers expecting either a whole file or a whole folder, never one map.
    texture_dir = directory / "textures"
    if texture_dir.is_dir() and any(texture_dir.iterdir()):
        return texture_dir

    for candidate in sorted(directory.glob("*")):
        if candidate.is_file() and not candidate.name.endswith(".json"):
            return candidate
    return None
