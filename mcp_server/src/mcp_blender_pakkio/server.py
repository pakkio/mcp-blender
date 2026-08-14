"""Bootstrap: one FastMCP instance, one BlenderBridge, flat tool registration,
stdio transport. Mirrors mcp-unity's Server~/src/index.ts bootstrap shape.
"""

import asyncio
import logging
import signal
import sys

from mcp.server.fastmcp import FastMCP

from .bridge import BlenderBridge
from .config import resolve_host_port
from .tools import register_all_tools

logger = logging.getLogger(__name__)


def build_server() -> tuple[FastMCP, BlenderBridge]:
    host, port = resolve_host_port()
    bridge = BlenderBridge(host, port)
    mcp = FastMCP(
        name="mcp-blender-pakkio",
        instructions="Bridges MCP clients to a running Blender instance via the mcp-blender-pakkio extension.",
    )
    register_all_tools(mcp, bridge)
    return mcp, bridge


async def run() -> None:
    mcp, bridge = build_server()

    try:
        await bridge.connect()
        logger.info("Connected to Blender bridge at %s", bridge.url)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "Could not connect to Blender bridge yet (%s) -- tool calls will fail until "
            "the mcp_bridge_pakkio extension is running in Blender.",
            exc,
        )

    loop = asyncio.get_running_loop()
    shutdown_event = asyncio.Event()

    def _request_shutdown() -> None:
        shutdown_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_shutdown)
        except NotImplementedError:
            pass  # not available on Windows for some signals; stdio close still works

    server_task = asyncio.create_task(mcp.run_stdio_async())
    shutdown_task = asyncio.create_task(shutdown_event.wait())

    done, pending = await asyncio.wait(
        {server_task, shutdown_task}, return_when=asyncio.FIRST_COMPLETED
    )
    for task in pending:
        task.cancel()

    await bridge.close()


def main() -> None:
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        pass
