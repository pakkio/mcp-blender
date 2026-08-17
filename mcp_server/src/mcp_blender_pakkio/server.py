"""Bootstrap: one FastMCP instance, one BlenderBridge, flat tool registration,
stdio transport. Mirrors mcp-unity's Server~/src/index.ts bootstrap shape.
"""

import asyncio
import logging
import signal
import sys

from mcp.server.fastmcp import FastMCP

from .bridge import BlenderBridge
from .config import load_dotenv, resolve_host_port
from .tools import register_all_tools

logger = logging.getLogger(__name__)

SERVER_INSTRUCTIONS = """Bridges MCP clients to a running Blender instance via the mcp-blender-pakkio extension.

Unified Domain Controllers:
- blender_docs: Query multi-step 3D workflow recipes, parameters, and best practices.
- blender_mesh: 3D modeling, transforms, boolean, decimate (<10k budget), remesh, UVs, modifiers.
- blender_material: PBR shading, procedural grunge, toon shaders, transparency, material slots.
- blender_assets: Online 3D asset search (Poly Haven/Sketchfab) & AI generation (Meshy/Tripo/Trellis).
- blender_scene: Scene inspection, hierarchy organization, snapshot checkpoints & background jobs.
- blender_rigging_anim: Armatures, bone posing, IK rigs, Blender 4.2+ hair curves, animation keyframes.
- blender_camera_lighting: Studio & sun/sky lighting rigs, camera tracking/framing, viewport screenshots.
- blender_physics_sim: Rigid body, cloth simulation, wind/vortex forces, fluid domain baking.
- blender_render_pipeline: Image/animation rendering, PBR texture map baking, Unity FBX & LOD export.
- execute_blender_python: Direct raw Python execution.

Workflow Best Practices:
1. Query `blender_docs` for multi-step recipes or parameter details when starting unfamiliar workflows.
2. For real-world objects, search online or generate with AI (`blender_assets`) before hand-modeling.
3. Save checkpoints (`blender_scene(action='checkpoint_create')`) before destructive operations."""


def build_server() -> tuple[FastMCP, BlenderBridge]:
    load_dotenv()
    host, port = resolve_host_port()
    bridge = BlenderBridge(host, port)
    mcp = FastMCP(
        name="mcp-blender-pakkio",
        instructions=SERVER_INSTRUCTIONS,
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
            "Could not connect to Blender bridge yet (%s) -- will keep retrying in the "
            "background until the mcp_bridge_pakkio extension is running in Blender.",
            exc,
        )
        asyncio.create_task(bridge.reconnect_with_backoff())

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
