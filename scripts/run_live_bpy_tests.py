#!/usr/bin/env python3
"""Runner for live in-Blender integration tests.

When run from normal Python:
  Discovers the Blender binary and invokes itself inside headless Blender:
    blender --background --factory-startup --python-exit-code 1 --python scripts/run_live_bpy_tests.py

When run inside Blender:
  Discovers and runs all live unittest cases in `tests_live/` against the real `bpy` runtime.
"""

import argparse
import glob
import os
import shutil
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent


def find_blender(custom_path: str = None) -> str | None:
    """Find blender executable via argument, env var, PATH, or standard OS install paths."""
    if custom_path and os.path.exists(custom_path):
        return custom_path

    env_blender = os.environ.get("BLENDER_BIN")
    if env_blender and os.path.exists(env_blender):
        return env_blender

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


def run_inside_blender(args) -> int:
    """Execute live test suite using Python unittest inside Blender."""
    import bpy

    print("=" * 70)
    print(f" MCP-BLENDER LIVE BPY TEST SUITE (Blender {bpy.app.version_string})")
    print(f" Python {sys.version.split()[0]} | Platform: {sys.platform}")
    print("=" * 70)

    # Ensure repository root is on sys.path
    if str(ROOT_DIR) not in sys.path:
        sys.path.insert(0, str(ROOT_DIR))

    tests_dir = ROOT_DIR / "tests_live"
    if not tests_dir.is_dir():
        print(f"ERROR: tests_live directory not found at {tests_dir}")
        return 1

    loader = unittest.TestLoader()
    pattern = args.pattern if hasattr(args, "pattern") and args.pattern else "test_live_*.py"
    suite = loader.discover(start_dir=str(tests_dir), pattern=pattern, top_level_dir=str(ROOT_DIR))

    start_time = time.time()
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    elapsed = time.time() - start_time

    print("=" * 70)
    print(f" Ran {result.testsRun} live tests in {elapsed:.2f}s")
    if result.wasSuccessful():
        print(" [PASSED] ALL LIVE BPY TESTS EXECUTED SUCCESSFULLY")
        print("=" * 70)
        return 0
    else:
        print(f" [FAILED] Failures: {len(result.failures)} | Errors: {len(result.errors)}")
        print("=" * 70)
        return 1


def main() -> None:
    try:
        import bpy  # noqa: F401

        inside_blender = True
    except ImportError:
        inside_blender = False

    if inside_blender:
        # Running inside Blender's python runtime
        parser = argparse.ArgumentParser(description="Live in-Blender Test Runner")
        parser.add_argument("--pattern", default="test_live_*.py", help="Test discovery filename pattern")
        
        # Extract arguments after '--' delimiter if invoked via Blender CLI
        if "--" in sys.argv:
            raw_args = sys.argv[sys.argv.index("--") + 1 :]
        else:
            raw_args = []
        args = parser.parse_args(raw_args)

        exit_code = run_inside_blender(args)
        sys.exit(exit_code)
    else:
        # Running outside Blender - find Blender and spawn subprocess
        parser = argparse.ArgumentParser(description="Launch live in-Blender test suite")
        parser.add_argument("--blender-bin", default=None, help="Path to blender executable")
        parser.add_argument("--pattern", default="test_live_*.py", help="Test discovery filename pattern")
        args = parser.parse_args()

        blender_bin = find_blender(args.blender_bin)
        if not blender_bin:
            print("ERROR: Blender executable not found!")
            print("Please set BLENDER_BIN environment variable or pass --blender-bin <path>")
            sys.exit(1)

        print(f"Found Blender: {blender_bin}")
        print("Launching headless live test runner...\n")

        cmd = [
            blender_bin,
            "--background",
            "--factory-startup",
            "--python-exit-code",
            "1",
            "--python",
            str(Path(__file__).resolve()),
            "--",
            "--pattern",
            args.pattern,
        ]

        result = subprocess.run(cmd)
        sys.exit(result.returncode)


if __name__ == "__main__":
    main()
