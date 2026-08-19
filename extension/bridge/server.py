"""In-Blender WebSocket server.

Runs on its own asyncio event loop, itself running on a dedicated daemon
thread — Blender's own main loop is not asyncio-native. This module never
imports bpy and never touches Blender data; all it does is speak WebSocket
and hand requests to dispatch.py's thread-safe queue, then await the
concurrent.futures.Future that dispatch.py resolves once the corresponding
tool has run on the main thread.

Deliberately uses the `websockets` library rather than a hand-rolled RFC6455
implementation: mcp-unity's C# bridge had to roll its own HTTP-handshake
line reader and shipped a real bug there (a naive per-line reader silently
dropped buffered bytes past the first newline, including the start of the
first WS frame, causing the connection to hang forever). `websockets`
already gets this buffering right, so there's no reason to repeat that
class of bug in Python.
"""

import asyncio
import json
import logging
import threading
from typing import Optional

import websockets

from . import dispatch, protocol
from .. import config

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_S = 15.0
# Must stay >= the mcp_server-side HEAVY_REQUEST_TIMEOUT_S (mcp_server/src/
# mcp_blender_pakkio/bridge.py) -- otherwise this side gives up and reports
# a timeout to the client before the mcp_server-side wait would have, even
# though Blender is still working. Kept as a superset of tool names rather
# than an exact mirror since new-but-similarly-heavy tools default safely
# to the short timeout if omitted here (fail fast) rather than the long one.
HEAVY_REQUEST_TIMEOUT_S = 600.0
HEAVY_METHODS = frozenset({
    "bake_advanced",
    "configure_light_probe",
    "bake_textures",
    "bake_fluid_domain",
    "bake_geometry_nodes",
    "bake_object_animation",
    "render_scene",
    "render_animation_sequence",
    "execute_batch",
    "decimate_mesh",
    "remesh_mesh",
    "simplify_geometry",
    "create_scene_checkpoint",
    "restore_scene_checkpoint",
    "regen_element_names",
})

_loop: Optional[asyncio.AbstractEventLoop] = None
_thread: Optional[threading.Thread] = None
_server: Optional["websockets.WebSocketServer"] = None
_address: Optional[tuple] = None
_stop_event: Optional[asyncio.Event] = None


def is_running() -> bool:
    return _thread is not None and _thread.is_alive()


def current_address() -> Optional[tuple]:
    return _address


async def _handle_client(websocket) -> None:
    tasks = set()

    async def _process_request(raw_message: str) -> None:
        request_id = None
        try:
            message = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError):
            try:
                await websocket.send(
                    json.dumps(
                        protocol.error_envelope(None, protocol.INVALID_JSON, "Malformed JSON request")
                    )
                )
            except Exception:
                pass
            return

        request_id = message.get("id")
        method = message.get("method")
        params = message.get("params") or {}

        if not method:
            try:
                await websocket.send(
                    json.dumps(
                        protocol.error_envelope(
                            request_id, protocol.INVALID_JSON, "Request is missing 'method'"
                        )
                    )
                )
            except Exception:
                pass
            return

        if method == "bridge_status":
            # Answered here, never enqueued: dispatch.get_status() only reads
            # a lock-guarded snapshot, so this replies instantly even while
            # the main thread is stuck inside a heavy tool for minutes --
            # that immediacy is the entire point of a busy-check.
            try:
                await websocket.send(
                    json.dumps(protocol.success_envelope(request_id, dispatch.get_status()))
                )
            except Exception:
                pass
            return

        if method == "set_client_status":
            # Also answered here rather than enqueued: it's a plain metadata
            # write (see dispatch.set_client_status), not a bpy operation, so
            # there's no reason to make it wait behind whatever's already
            # queued -- and it needs to work precisely when the main thread
            # is busy, since that's when mcp_server calls it.
            dispatch.set_client_status(params.get("text"))
            try:
                await websocket.send(
                    json.dumps(protocol.success_envelope(request_id, {"success": True}))
                )
            except Exception:
                pass
            return

        future = dispatch.enqueue(request_id, method, params)
        timeout = HEAVY_REQUEST_TIMEOUT_S if method in HEAVY_METHODS else REQUEST_TIMEOUT_S
        try:
            envelope = await asyncio.wait_for(
                asyncio.wrap_future(future), timeout=timeout
            )
        except asyncio.TimeoutError:
            envelope = protocol.error_envelope(
                request_id,
                protocol.INTERNAL_ERROR,
                "Blender did not respond in time (main thread busy or addon disabled)",
            )
        except Exception as exc:
            envelope = protocol.error_envelope(
                request_id,
                protocol.INTERNAL_ERROR,
                f"Unexpected bridge error: {exc}",
            )
        try:
            await websocket.send(json.dumps(envelope))
        except Exception:
            pass

    try:
        async for raw_message in websocket:
            task = asyncio.create_task(_process_request(raw_message))
            tasks.add(task)
            task.add_done_callback(tasks.discard)
    finally:
        for t in list(tasks):
            t.cancel()


async def _serve(host: str, port: int, ready: threading.Event) -> None:
    global _server, _address, _stop_event
    _stop_event = asyncio.Event()
    async with websockets.serve(_handle_client, host, port) as server:
        _server = server
        sock = server.sockets[0] if server.sockets else None
        _address = sock.getsockname() if sock else (host, port)
        ready.set()
        await _stop_event.wait()
    # `async with` block above has now closed the listening socket cleanly.


def _run_loop(host: str, port: int, ready: threading.Event) -> None:
    global _loop
    loop = asyncio.new_event_loop()
    _loop = loop
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_serve(host, port, ready))
    finally:
        loop.close()


def start_server(host: str = None, port: int = None) -> tuple:
    """Idempotent: no-op if already running. Returns the bound (host, port)."""
    global _thread

    if is_running():
        return _address

    host = host or config.resolved_host()
    port = port or config.resolved_port()

    ready = threading.Event()
    _thread = threading.Thread(
        target=_run_loop, args=(host, port, ready), daemon=True, name="mcp-blender-pakkio-ws"
    )
    _thread.start()
    ready.wait(timeout=5.0)

    if _address is not None:
        config.write_settings(*_address)
    return _address


def stop_server() -> None:
    global _thread, _loop, _server, _address, _stop_event

    loop = _loop
    thread = _thread
    stop_event = _stop_event
    if loop is not None and loop.is_running() and stop_event is not None:
        loop.call_soon_threadsafe(stop_event.set)
    if thread is not None:
        thread.join(timeout=2.0)

    _thread = None
    _loop = None
    _server = None
    _address = None
    _stop_event = None
