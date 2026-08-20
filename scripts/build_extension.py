#!/usr/bin/env python3
"""Builds the installable Blender extension/addon zip file in dist/.

If Blender is available, it uses `blender --command extension build`.
Otherwise, it packages the zip archive directly using Python's zipfile module.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = Path(__file__).resolve().parent
EXTENSION_DIR = ROOT_DIR / "extension"
WHEELS_DIR = EXTENSION_DIR / "wheels"
DIST_DIR = ROOT_DIR / "dist"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))


def find_blender() -> str | None:
    """Find blender executable on PATH or common OS installation paths."""
    on_path = shutil.which("blender")
    if on_path:
        return on_path

    if sys.platform == "win32":
        candidates = sorted(
            glob.glob(r"C:\Program Files\Blender Foundation\Blender *\blender.exe"),
            reverse=True,
        )
        if candidates:
            return candidates[0]
    elif sys.platform == "darwin":
        mac_app = Path("/Applications/Blender.app/Contents/MacOS/Blender")
        if mac_app.exists():
            return str(mac_app)
    else:
        for loc in ["/usr/bin/blender", "/snap/bin/blender", "/usr/local/bin/blender"]:
            if os.path.exists(loc):
                return loc

    return None


def get_extension_version() -> str:
    manifest = EXTENSION_DIR / "blender_manifest.toml"
    if manifest.is_file():
        for line in manifest.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("version") and "=" in line:
                return line.split("=")[1].strip().strip('"\'')
    return "0.1.0"


def ensure_wheels() -> None:
    whls = list(WHEELS_DIR.glob("*.whl")) if WHEELS_DIR.is_dir() else []
    if not whls:
        print("Wheels not found. Running scripts/fetch_wheels.py...")
        from fetch_wheels import main as fetch_main

        fetch_main()


def build_with_blender(blender_bin: str, output_dir: Path) -> Path | None:
    print(f"Building extension package using Blender: {blender_bin}")
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd = [
        blender_bin,
        "--command",
        "extension",
        "build",
        "--source-dir",
        str(EXTENSION_DIR),
        "--output-dir",
        str(output_dir),
    ]
    res = subprocess.run(cmd)
    if res.returncode != 0:
        return None

    version = get_extension_version()
    zip_path = output_dir / f"mcp_bridge-{version}.zip"
    return zip_path if zip_path.is_file() else None


def build_with_python(output_dir: Path) -> Path:
    print("Building extension package using Python zipfile fallback...")
    output_dir.mkdir(parents=True, exist_ok=True)
    version = get_extension_version()
    zip_path = output_dir / f"mcp_bridge-{version}.zip"

    ignore_patterns = {
        "__pycache__",
        ".pytest_cache",
        ".DS_Store",
        "Thumbs.db",
    }

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(EXTENSION_DIR):
            dirs[:] = [d for d in dirs if d not in ignore_patterns and not d.startswith(".")]
            for file in files:
                if file in ignore_patterns or file.endswith(".pyc"):
                    continue
                file_path = Path(root) / file
                arcname = file_path.relative_to(EXTENSION_DIR).as_posix()
                zf.write(file_path, arcname)

    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build MCP Blender add-on zip package.")
    parser.add_argument(
        "--output-dir",
        default=str(DIST_DIR),
        help="Destination directory for the built zip file",
    )
    parser.add_argument(
        "--force-python",
        action="store_true",
        help="Force packaging with Python zipfile instead of Blender CLI",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir).resolve()
    ensure_wheels()

    zip_path = None
    if not args.force_python:
        blender_bin = find_blender()
        if blender_bin:
            zip_path = build_with_blender(blender_bin, out_dir)

    if not zip_path:
        zip_path = build_with_python(out_dir)

    size_kb = zip_path.stat().st_size / 1024
    print(f"\nSuccessfully built addon zip:")
    print(f"  Path: {zip_path}")
    print(f"  Size: {size_kb:.1f} KB")
    print("\nTo install in Blender (4.2+):")
    print("  1. Open Blender")
    print("  2. Edit > Preferences > Get Extensions (or Add-ons)")
    print("  3. Click top-right dropdown arrow > 'Install from Disk...'")
    print(f"  4. Select: {zip_path.name}")
    print("  5. Enable 'MCP Bridge'")


if __name__ == "__main__":
    main()
