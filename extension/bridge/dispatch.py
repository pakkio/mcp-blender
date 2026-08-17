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
"""

import queue
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
