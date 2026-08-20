import asyncio

import pytest

from mcp_blender import bridge as bridge_module
from mcp_blender.bridge import BlenderBridge, ConnectionState
from mcp_blender.errors import BridgeError, ErrorType

from conftest import FakeBlenderServer, _free_port


@pytest.mark.asyncio
async def test_connect_and_round_trip_correlation(fake_blender_server):
    fake_blender_server.set_handler(lambda method, params: {"success": True, "echo": params})

    client = BlenderBridge(fake_blender_server.host, fake_blender_server.port)
    await client.connect()
    assert client.state is ConnectionState.CONNECTED

    result = await client.send_request("get_scene_info", {"a": 1})
    assert result == {"success": True, "echo": {"a": 1}}

    await client.close()


@pytest.mark.asyncio
async def test_timeout_when_server_never_replies(fake_blender_server):
    def handler(method, params):
        raise FakeBlenderServer.NoReply

    fake_blender_server.set_handler(handler)

    client = BlenderBridge(fake_blender_server.host, fake_blender_server.port)
    await client.connect()

    with pytest.raises(BridgeError) as exc_info:
        await client.send_request("get_scene_info", {}, timeout=0.2)
    assert exc_info.value.error_type is ErrorType.TIMEOUT

    await client.close()


@pytest.mark.asyncio
async def test_connection_error_when_nothing_listening():
    client = BlenderBridge("127.0.0.1", _free_port())
    with pytest.raises(BridgeError) as exc_info:
        await client.connect()
    assert exc_info.value.error_type is ErrorType.CONNECTION


@pytest.mark.asyncio
async def test_wire_error_becomes_bridge_error(fake_blender_server):
    def handler(method, params):
        raise FakeBlenderServer.WireError("tool_execution_error", "Object 'Foo' not found")

    fake_blender_server.set_handler(handler)

    client = BlenderBridge(fake_blender_server.host, fake_blender_server.port)
    await client.connect()

    with pytest.raises(BridgeError) as exc_info:
        await client.send_request("delete_object", {"name": "Foo"})
    assert exc_info.value.error_type is ErrorType.TOOL_EXECUTION
    assert "Foo" in exc_info.value.message

    await client.close()


@pytest.mark.asyncio
async def test_send_request_without_connection_raises_connection_error():
    client = BlenderBridge("127.0.0.1", _free_port())
    with pytest.raises(BridgeError) as exc_info:
        await client.send_request("get_scene_info", {})
    assert exc_info.value.error_type is ErrorType.CONNECTION


@pytest.mark.asyncio
async def test_unmatched_id_message_is_dropped_not_raised(fake_blender_server):
    fake_blender_server.set_handler(lambda method, params: {"success": True})

    client = BlenderBridge(fake_blender_server.host, fake_blender_server.port)
    await client.connect()

    # Directly exercise the internal message handler with an id that has no
    # pending request -- must log and drop, never raise.
    client._handle_message('{"id": "does-not-exist", "result": {"success": true}}')

    result = await client.send_request("get_scene_info", {})
    assert result == {"success": True}

    await client.close()


@pytest.mark.asyncio
async def test_reconnects_with_backoff_after_server_restart(fake_blender_server, monkeypatch):
    monkeypatch.setattr(bridge_module, "MIN_RECONNECT_DELAY_S", 0.05)
    monkeypatch.setattr(bridge_module, "MAX_RECONNECT_DELAY_S", 0.2)

    fake_blender_server.set_handler(lambda method, params: {"success": True})

    client = BlenderBridge(fake_blender_server.host, fake_blender_server.port)
    await client.connect()
    assert client.state is ConnectionState.CONNECTED

    await fake_blender_server.stop()
    for _ in range(50):
        if client.state is not ConnectionState.CONNECTED:
            break
        await asyncio.sleep(0.05)
    assert client.state in (ConnectionState.RECONNECTING, ConnectionState.DISCONNECTED)

    await fake_blender_server.start()

    for _ in range(100):
        if client.state is ConnectionState.CONNECTED:
            break
        await asyncio.sleep(0.05)
    assert client.state is ConnectionState.CONNECTED

    await client.close()
