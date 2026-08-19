"""Best-effort push of a human-readable status line to Blender's own status
bar, for multi-step mcp_server-side workflows that Blender's per-RPC busy
tracking can't see on its own -- e.g. import_online_asset spends real time
on an HTTP download before it ever calls Blender, and needs to name the
provider and license/attribution it found, which never gets sent to Blender
as part of any individual bpy call's params.

See extension/bridge/dispatch.py's _client_status for the receiving side.
"""

from contextlib import asynccontextmanager
from typing import Optional

from .bridge import BlenderBridge

_STATUS_PUSH_TIMEOUT_S = 5.0


async def _push(bridge: BlenderBridge, text: Optional[str]) -> None:
    try:
        await bridge.send_request("set_client_status", {"text": text}, timeout=_STATUS_PUSH_TIMEOUT_S)
    except Exception:
        pass  # best-effort: a status push must never fail the workflow it describes


@asynccontextmanager
async def track(bridge: BlenderBridge, initial_text: str):
    """Usage: `async with track(bridge, "Downloading...") as set_status: ...
    await set_status("Simplifying...")`. Always clears the status on exit,
    including on an exception or an early return, so a crash mid-workflow
    can't leave a stale message stuck in the status bar forever."""
    await _push(bridge, initial_text)
    try:
        async def set_status(text: str) -> None:
            await _push(bridge, text)

        yield set_status
    finally:
        await _push(bridge, None)
