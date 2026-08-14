#!/usr/bin/env python3
"""Manual smoke test: talks directly to the Blender extension's WebSocket
bridge, bypassing MCP entirely. Proves the extension half works before
layering the MCP server (mcp_server/) on top.

Usage:
    1. In Blender, install & enable the extension (see README.md), confirm
       its Preferences panel shows "Running" and note the host:port.
    2. pip install websockets   (into whatever Python runs this script --
       it does NOT need to be the mcp_server venv)
    3. python scripts/manual_smoke_test.py [host] [port]

Expected output: a get_scene_info response, then a create_object response,
and a cube should appear in Blender's 3D viewport in real time.
"""

import asyncio
import json
import sys
import uuid

import websockets


async def call(ws, method: str, params: dict) -> dict:
    request_id = str(uuid.uuid4())
    await ws.send(json.dumps({"id": request_id, "method": method, "params": params}))
    raw = await ws.recv()
    response = json.loads(raw)
    print(f"--> {method}({params})\n<-- {json.dumps(response, indent=2)}\n")
    return response


async def main() -> None:
    host = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9876

    async with websockets.connect(f"ws://{host}:{port}") as ws:
        await call(ws, "get_scene_info", {})
        await call(
            ws,
            "create_object",
            {"object_type": "CUBE", "name": "SmokeTestCube", "location": [2, 0, 0]},
        )


if __name__ == "__main__":
    asyncio.run(main())
