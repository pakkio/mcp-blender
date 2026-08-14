"""FakeBlenderServer: a real websockets.serve() standing in for the Blender
extension, so BlenderBridge is exercised against genuine WebSocket behavior
rather than a hand-mocked `websockets` object.
"""

import asyncio
import json
import socket
from contextlib import asynccontextmanager

import pytest
import pytest_asyncio
import websockets


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FakeBlenderServer:
    """Pluggable per-test handler: handler(method, params) -> dict (result)
    or raises FakeBlenderServer.WireError(type, message) to send a wire
    error, or FakeBlenderServer.NoReply to accept the connection but never
    answer (for timeout tests).
    """

    class NoReply(Exception):
        pass

    class WireError(Exception):
        def __init__(self, error_type: str, message: str):
            self.error_type = error_type
            self.message = message

    def __init__(self, host: str, port: int):
        self.host = host
        self.port = port
        self.handler = None
        self._server = None
        self.drop_next_connection = False

    def set_handler(self, handler) -> None:
        self.handler = handler

    async def _handle(self, websocket) -> None:
        if self.drop_next_connection:
            self.drop_next_connection = False
            await websocket.close()
            return

        async for raw in websocket:
            message = json.loads(raw)
            request_id = message.get("id")
            method = message.get("method")
            params = message.get("params") or {}

            if self.handler is None:
                await websocket.send(json.dumps({"id": request_id, "result": {"success": True}}))
                continue

            try:
                result = self.handler(method, params)
            except FakeBlenderServer.NoReply:
                continue
            except FakeBlenderServer.WireError as exc:
                await websocket.send(
                    json.dumps(
                        {
                            "id": request_id,
                            "error": {"type": exc.error_type, "message": exc.message},
                        }
                    )
                )
                continue

            await websocket.send(json.dumps({"id": request_id, "result": result}))

    async def start(self) -> None:
        self._server = await websockets.serve(self._handle, self.host, self.port)

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None


class FakeMCP:
    """Stand-in for FastMCP in tool-registration tests: `.tool(...)` just
    returns the function unchanged, like FastMCP's own decorator does, so
    register_x_tool()'s returned handler can be called directly without
    spinning up a real FastMCP server/session.
    """

    def tool(self, *args, **kwargs):
        def decorator(func):
            return func

        return decorator


@pytest_asyncio.fixture
async def fake_blender_server():
    port = _free_port()
    server = FakeBlenderServer("127.0.0.1", port)
    await server.start()
    try:
        yield server
    finally:
        await server.stop()
