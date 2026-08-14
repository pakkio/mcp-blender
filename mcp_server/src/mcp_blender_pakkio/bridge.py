"""WebSocket client connecting this MCP stdio server to the Blender extension.

Modeled on mcp-unity's mcpUnity.ts/unityConnection.ts split (request
correlation via a client-generated uuid + a pending-request map, a small
connection state machine, exponential backoff reconnection), deliberately
simplified for Phase 0: no in-flight read/mutation replay-on-reconnect and
no offline command queue -- both are documented here as follow-ups rather
than built now.
"""

import asyncio
import enum
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from .errors import BridgeError, ErrorType

logger = logging.getLogger(__name__)

DEFAULT_REQUEST_TIMEOUT_S = 15.0
# Bake/render/batch/fluid-sim operations can legitimately run for minutes;
# tool wrappers for those methods pass this explicitly to send_request().
HEAVY_REQUEST_TIMEOUT_S = 600.0
MIN_RECONNECT_DELAY_S = 1.0
MAX_RECONNECT_DELAY_S = 30.0
RECONNECT_MULTIPLIER = 2.0


class ConnectionState(enum.Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"


@dataclass
class _PendingRequest:
    future: "asyncio.Future[dict]"


class BlenderBridge:
    def __init__(self, host: str, port: int, request_timeout: float = DEFAULT_REQUEST_TIMEOUT_S):
        self._host = host
        self._port = port
        self._request_timeout = request_timeout
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._state = ConnectionState.DISCONNECTED
        self._pending: dict[str, _PendingRequest] = {}
        self._recv_task: Optional[asyncio.Task] = None
        self._closing = False

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def url(self) -> str:
        return f"ws://{self._host}:{self._port}"

    async def connect(self) -> None:
        self._closing = False
        await self._connect_once()

    async def _connect_once(self) -> None:
        self._state = ConnectionState.CONNECTING
        try:
            self._ws = await websockets.connect(self.url, open_timeout=self._request_timeout)
        except (OSError, websockets.exceptions.WebSocketException, asyncio.TimeoutError) as exc:
            self._state = ConnectionState.DISCONNECTED
            raise BridgeError(
                ErrorType.CONNECTION, f"Could not connect to Blender bridge at {self.url}: {exc}"
            ) from exc
        self._state = ConnectionState.CONNECTED
        self._recv_task = asyncio.create_task(self._recv_loop())

    async def _recv_loop(self) -> None:
        assert self._ws is not None
        try:
            async for raw_message in self._ws:
                self._handle_message(raw_message)
        except ConnectionClosed:
            pass
        finally:
            self._on_disconnected()

    def _handle_message(self, raw_message: str) -> None:
        try:
            message = json.loads(raw_message)
        except json.JSONDecodeError:
            logger.warning("Dropping malformed message from Blender bridge: %r", raw_message)
            return

        request_id = message.get("id")
        pending = self._pending.pop(request_id, None) if request_id is not None else None
        if pending is None:
            logger.warning("Dropping message with unmatched id: %r", request_id)
            return

        if not pending.future.done():
            pending.future.set_result(message)

    def _on_disconnected(self) -> None:
        self._state = ConnectionState.DISCONNECTED
        for pending in self._pending.values():
            if not pending.future.done():
                pending.future.set_exception(
                    BridgeError(ErrorType.CONNECTION, "Connection to Blender bridge was lost")
                )
        self._pending.clear()
        if not self._closing:
            asyncio.create_task(self._reconnect_with_backoff())

    async def _reconnect_with_backoff(self) -> None:
        self._state = ConnectionState.RECONNECTING
        delay = MIN_RECONNECT_DELAY_S
        while not self._closing:
            await asyncio.sleep(delay)
            try:
                await self._connect_once()
                return
            except Exception:
                # Catch broadly: any failure during reconnect (BridgeError,
                # or anything _connect_once didn't anticipate) must retry
                # with backoff rather than let this task die silently and
                # strand the connection in RECONNECTING forever.
                logger.warning("Reconnect attempt to %s failed, retrying in %.1fs", self.url, delay)
                self._state = ConnectionState.RECONNECTING
                delay = min(delay * RECONNECT_MULTIPLIER, MAX_RECONNECT_DELAY_S)

    async def send_request(self, method: str, params: dict, timeout: Optional[float] = None) -> dict:
        if self._state != ConnectionState.CONNECTED or self._ws is None:
            raise BridgeError(ErrorType.CONNECTION, "Not connected to Blender bridge")

        request_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        pending = _PendingRequest(future=loop.create_future())
        self._pending[request_id] = pending

        await self._ws.send(json.dumps({"id": request_id, "method": method, "params": params}))

        try:
            message = await asyncio.wait_for(pending.future, timeout=timeout or self._request_timeout)
        except asyncio.TimeoutError:
            self._pending.pop(request_id, None)
            raise BridgeError(ErrorType.TIMEOUT, f"Timed out waiting for '{method}' response")

        if "error" in message:
            error = message["error"]
            try:
                error_type = ErrorType(error.get("type"))
            except ValueError:
                error_type = ErrorType.INTERNAL
            raise BridgeError(error_type, error.get("message", "Unknown error"), error.get("details"))

        return message.get("result", {})

    async def close(self) -> None:
        self._closing = True
        if self._recv_task is not None:
            self._recv_task.cancel()
        if self._ws is not None:
            await self._ws.close()
        self._state = ConnectionState.DISCONNECTED
