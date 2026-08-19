"""Main-thread dispatch: the one load-bearing correctness mechanism here.

Nearly every bpy call must happen on Blender's main thread. The WebSocket
server (server.py) runs on a background asyncio thread and must never touch
bpy directly. Instead it enqueues a QueuedRequest carrying a
concurrent.futures.Future; a bpy.app.timers callback registered on
register() drains the queue on the main thread, runs the tool, and resolves
the Future. asyncio.wrap_future() on the server side bridges the two
worlds with zero hand-rolled locking (concurrent.futures.Future.set_result
is thread-safe by design).

A generation counter guards against stale queued work surviving an addon
disable/enable or "Reload Scripts": register() bumps it, and any item
dequeued under an older generation is failed instead of executed.

_current_execution tracks whatever tool.execute() call is presently running
on the main thread (or None). server.py's "bridge_status" method reads it
directly from the background asyncio thread, guarded by a lock that is only
ever held for the instant it takes to set/clear the record -- never for the
duration of the tool call itself -- so a status check answers immediately
even while a heavy tool blocks drain_queue for minutes. This is what lets a
client poll "is Blender still busy with my last request" without waiting
through that request's own timeout.

_client_status is a separate, narrower overlay: mcp_server-side workflows
that make several sequential bridge calls with real work in between that
never touches bpy at all (e.g. import_online_asset downloading over HTTP
before any Blender RPC happens) are invisible to _current_execution -- there
is no bpy call in flight to report. mcp_server pushes a human-readable
description of what it's doing via the "set_client_status" wire method
(server.py, also answered without enqueueing) so Blender's own status bar
can show it. Cleared the same way when the workflow finishes.
"""

import json
import queue
import threading
import time
import traceback
from concurrent.futures import Future
from dataclasses import dataclass
from typing import Any, Optional

from . import protocol
from ..tools import TOOL_REGISTRY

_queue: "queue.Queue[QueuedRequest]" = queue.Queue()
_generation = 0

_ACTIVE_INTERVAL_S = 0.05
_MAX_IDLE_INTERVAL_S = 0.3
_idle_streak = 0

_status_lock = threading.Lock()
_current_execution: Optional[dict] = None
_client_status: Optional[dict] = None

# Some params blobs are huge and not useful in a status check (execute_python's
# "code", execute_batch's "commands"): cap the preview rather than ship the
# whole thing over the wire on every busy poll.
_PARAMS_PREVIEW_MAX_CHARS = 200


def _preview_params(params: dict) -> str:
    try:
        text = json.dumps(params, default=str)
    except Exception:
        text = str(params)
    if len(text) > _PARAMS_PREVIEW_MAX_CHARS:
        text = text[:_PARAMS_PREVIEW_MAX_CHARS] + "...(truncated)"
    return text


@dataclass
class QueuedRequest:
    request_id: Any
    method: str
    params: dict
    future: Future
    generation: int


class StaleGenerationError(Exception):
    pass


def bump_generation() -> int:
    global _generation
    _generation += 1
    return _generation


def get_generation() -> int:
    return _generation


def enqueue(request_id, method: str, params: dict) -> Future:
    future: Future = Future()
    _queue.put(QueuedRequest(request_id, method, params, future, _generation))
    return future


def drain_queue() -> float:
    """bpy.app.timers callback. Must return a float to stay registered.

    Polls at _ACTIVE_INTERVAL_S (20Hz) whenever there's real work, but backs
    off gradually up to _MAX_IDLE_INTERVAL_S while the queue stays empty --
    bpy.app.timers has no way to be woken early by the background WebSocket
    thread enqueueing work, so this only trades a bit of idle-to-first-poll
    latency (well under human-perceptible) for far fewer needless wakeups
    during long idle stretches.
    """
    global _idle_streak
    processed = False
    try:
        while True:
            try:
                item = _queue.get_nowait()
            except queue.Empty:
                break
            processed = True
            try:
                _handle_item(item)
            except Exception as e:
                pass

        if processed:
            _idle_streak = 0
            return _ACTIVE_INTERVAL_S

        _idle_streak += 1
        return min(_ACTIVE_INTERVAL_S * (1 + _idle_streak * 0.5), _MAX_IDLE_INTERVAL_S)
    except Exception:
        return _ACTIVE_INTERVAL_S


def _handle_item(item: QueuedRequest) -> None:
    if item.future.cancelled() or item.future.done():
        return
    if item.generation != _generation:
        if not item.future.done():
            item.future.set_result(
                protocol.error_envelope(
                    item.request_id,
                    protocol.INTERNAL_ERROR,
                    "Blender bridge was reloaded before this request could run",
                )
            )
        return

    tool = TOOL_REGISTRY.get(item.method)
    if tool is None:
        if not item.future.done():
            item.future.set_result(
                protocol.error_envelope(
                    item.request_id,
                    protocol.UNKNOWN_METHOD,
                    f"Unknown method '{item.method}'",
                )
            )
        return

    with _status_lock:
        global _current_execution
        _current_execution = {
            "method": item.method,
            "params_preview": _preview_params(item.params),
            "request_id": item.request_id,
            "started_at": time.time(),
        }
    try:
        result = tool.execute(item.params)
        if not item.future.done():
            item.future.set_result(protocol.success_envelope(item.request_id, result))
    except Exception as exc:  # noqa: BLE001 - must never crash the drain loop
        if not item.future.done():
            item.future.set_result(
                protocol.error_envelope(
                    item.request_id,
                    protocol.TOOL_EXECUTION_ERROR,
                    str(exc),
                    details=traceback.format_exc(),
                )
            )
    finally:
        with _status_lock:
            _current_execution = None


def set_client_status(text: Optional[str]) -> None:
    """Called from server.py for the "set_client_status" wire method. Passing
    None/empty clears it -- mcp_server does this in a finally so a crashed
    workflow can't leave a stale "Importing..." message stuck forever."""
    global _client_status
    with _status_lock:
        _client_status = {"text": text, "started_at": time.time()} if text else None


def get_status() -> dict:
    """Non-blocking snapshot, safe to call from the background asyncio thread
    even while the main thread is deep inside a heavy tool.execute() call."""
    with _status_lock:
        current = dict(_current_execution) if _current_execution else None
        client = dict(_client_status) if _client_status else None
    if current is not None:
        current["running_for_s"] = round(time.time() - current["started_at"], 2)
        current["description"] = (
            f"{current['method']}({current['params_preview']}) "
            f"— running for {current['running_for_s']}s"
        )
    if client is not None:
        client["running_for_s"] = round(time.time() - client["started_at"], 2)
    return {
        "success": True,
        "busy": current is not None or client is not None,
        "current": current,
        "client_status": client,
        "queue_depth": _queue.qsize(),
    }
