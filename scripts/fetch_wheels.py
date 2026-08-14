#!/usr/bin/env python3
"""Downloads the `websockets` wheels the extension bundles (extension/wheels/),
one per platform, matching Blender 4.2 LTS's embedded CPython 3.11 (cp311).

Blender's own embedded Python has no pip access, so the Extension
Platform's `wheels = [...]` manifest field is how third-party packages get
onto sys.path -- Blender picks whichever wheel's platform/ABI tag matches
the running Blender. Run this once before `blender --command extension
build`. If you bump blender_version_min past a Blender release that changes
its embedded Python version, re-run this with an updated --python-version.
"""

import subprocess
import sys
from pathlib import Path

WEBSOCKETS_VERSION = "13.1"
PYTHON_VERSION = "311"
ABI = "cp311"
OUT_DIR = Path(__file__).resolve().parent.parent / "extension" / "wheels"

TARGETS = [
    "win_amd64",
    "manylinux2014_x86_64",
    "macosx_10_9_x86_64",
    "macosx_11_0_arm64",
]
PY_VERSIONS = [
    ("311", "cp311"),
    ("312", "cp312"),
    ("313", "cp313"),
]


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for py_ver, abi in PY_VERSIONS:
        for platform_tag in TARGETS:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "download",
                    f"websockets=={WEBSOCKETS_VERSION}",
                    "--no-deps",
                    "--platform",
                    platform_tag,
                    "--python-version",
                    py_ver,
                    "--implementation",
                    "cp",
                    "--abi",
                    abi,
                    "--only-binary=:all:",
                    "-d",
                    str(OUT_DIR),
                ],
                check=True,
            )
    print(f"\nWheels written to {OUT_DIR}")
    print("Update the `wheels = [...]` list in extension/blender_manifest.toml if filenames changed.")


if __name__ == "__main__":
    main()

