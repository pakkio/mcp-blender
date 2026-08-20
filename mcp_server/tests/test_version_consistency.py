"""Guards against the extension and MCP server versions drifting apart.

They did drift: commits for 2.0.13 -- 2.0.18 bumped
`extension/blender_manifest.toml` but left `mcp_server/pyproject.toml` on 2.0.8,
which only caught up at 2.0.19. The two ship as one unit -- the README quotes a
single version and the built zip is named from the manifest -- so a mismatch
means the install instructions name a file the build does not produce.
"""

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MANIFEST = REPO_ROOT / "extension" / "blender_manifest.toml"
PYPROJECT = REPO_ROOT / "mcp_server" / "pyproject.toml"
PACKAGE_INIT = REPO_ROOT / "mcp_server" / "src" / "mcp_blender_pakkio" / "__init__.py"

_VERSION_RE = re.compile(r'^\s*version\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
_DUNDER_VERSION_RE = re.compile(r'^\s*__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)


def _read_version(path: Path) -> str:
    if not path.is_file():
        pytest.skip(f"{path} not present")
    match = _VERSION_RE.search(path.read_text(encoding="utf-8"))
    assert match, f"no version field found in {path}"
    return match.group(1)


def test_extension_and_server_versions_match():
    manifest_version = _read_version(MANIFEST)
    pyproject_version = _read_version(PYPROJECT)
    assert manifest_version == pyproject_version, (
        f"version drift: extension/blender_manifest.toml is {manifest_version} "
        f"but mcp_server/pyproject.toml is {pyproject_version}. "
        "Bump both together -- the build names the zip from the manifest while "
        "the README and package metadata quote pyproject."
    )


def test_package_dunder_version_matches():
    """`__version__` is what `import mcp_blender_pakkio` reports at runtime.

    It sat at 2.0.8 while the project shipped through 2.0.23 -- nothing compared
    it against anything, so it drifted 15 releases without notice.
    """
    if not PACKAGE_INIT.is_file():
        pytest.skip(f"{PACKAGE_INIT} not present")
    match = _DUNDER_VERSION_RE.search(PACKAGE_INIT.read_text(encoding="utf-8"))
    assert match, f"no __version__ found in {PACKAGE_INIT}"
    assert match.group(1) == _read_version(PYPROJECT), (
        f"__version__ is {match.group(1)} but pyproject.toml is "
        f"{_read_version(PYPROJECT)}; bump both together."
    )


def test_version_is_semver_like():
    version = _read_version(PYPROJECT)
    assert re.fullmatch(r"\d+\.\d+\.\d+", version), f"unexpected version format: {version}"


def test_readme_quotes_the_current_version():
    """The README states the version in its title and install instructions;
    a stale value sends users looking for a zip the build never produced."""
    readme = REPO_ROOT / "README.md"
    if not readme.is_file():
        pytest.skip("README.md not present")
    version = _read_version(PYPROJECT)
    text = readme.read_text(encoding="utf-8")

    assert f"(v{version})" in text, (
        f"README title/table does not mention current version v{version}"
    )
    assert f"mcp_bridge_pakkio-{version}.zip" in text, (
        f"README install instructions do not reference "
        f"mcp_bridge_pakkio-{version}.zip, the artifact the build actually emits"
    )
