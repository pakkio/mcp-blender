"""Guards a cross-repo invariant that has no other test coverage: every
bridge method the mcp_server side calls with the 600s heavy timeout must
also be in extension/bridge/server.py's HEAVY_METHODS set.

There are two independent 15s/600s timeout pairs, one per side of the wire
(mcp_server/bridge.py's DEFAULT/HEAVY_REQUEST_TIMEOUT_S is the client-side
wait; extension/bridge/server.py's REQUEST_TIMEOUT_S/HEAVY_METHODS is how
long *Blender itself* waits for its own dispatch queue before giving up).
If a method is heavy only on the mcp_server side, Blender's own bridge
times out first at 15s ("Blender did not respond in time") while the tool
keeps running on the main thread -- the eventual result is computed but
never sent, so the client sees a false failure. simplify_geometry shipped
in 2.0.3 with exactly this gap; extension/bridge/server.py imports bpy
transitively (via dispatch -> extension.tools), so this reads its source
as text rather than importing it.
"""

import re
from pathlib import Path

_SERVER_PATH = Path(__file__).resolve().parents[2] / "extension" / "bridge" / "server.py"
_TOOLS_DIR = Path(__file__).resolve().parents[1] / "src" / "mcp_blender" / "tools"


def _extension_heavy_methods():
    text = _SERVER_PATH.read_text(encoding="utf-8")
    match = re.search(r"HEAVY_METHODS\s*=\s*frozenset\(\{(.*?)\}\)", text, re.S)
    assert match, "extension/bridge/server.py's HEAVY_METHODS set moved or was renamed"
    return set(re.findall(r'"([^"]+)"', match.group(1)))


def _mcp_server_heavy_send_requests():
    """Method names passed to bridge.send_request(..., timeout=HEAVY_REQUEST_TIMEOUT_S),
    where the method name is a literal string on the same or the immediately
    preceding non-blank call-opening line (covers both single-line and
    multi-line send_request calls used across the tools/ package)."""
    methods = set()
    for path in _TOOLS_DIR.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        for call_match in re.finditer(r"send_request\((.*?)\)", text, re.S):
            call_body = call_match.group(1)
            if "HEAVY_REQUEST_TIMEOUT_S" not in call_body:
                continue
            name_match = re.search(r'"([a-z_]+)"', call_body)
            if name_match:
                methods.add(name_match.group(1))
    return methods


def test_every_mcp_server_heavy_call_is_heavy_on_the_extension_side():
    extension_heavy = _extension_heavy_methods()
    mcp_server_heavy = _mcp_server_heavy_send_requests()

    assert mcp_server_heavy, "sanity check: expected to find at least one heavy send_request call"

    missing = mcp_server_heavy - extension_heavy
    assert not missing, (
        f"{sorted(missing)} use the 600s HEAVY_REQUEST_TIMEOUT_S on the mcp_server side but are "
        "missing from extension/bridge/server.py's HEAVY_METHODS -- Blender's own bridge will give "
        "up on these after 15s while the tool keeps running, and the eventual result is dropped."
    )
