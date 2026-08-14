from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError

from conftest import FakeMCP
from mcp_blender_pakkio.errors import BridgeError, ErrorType
from mcp_blender_pakkio.tools.select_objects import register_select_objects_tool


@pytest.mark.asyncio
async def test_select_objects_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "selected_objects": ["Cube", "Light"],
        "active_object": "Cube",
        "current_mode": "OBJECT",
    }
    handler = register_select_objects_tool(FakeMCP(), bridge)

    result = await handler(names=["Cube", "Light"], action="SET", active_object="Cube")

    bridge.send_request.assert_awaited_once_with(
        "select_objects",
        {
            "names": ["Cube", "Light"],
            "action": "SET",
            "active_object": "Cube",
            "mode": None,
        },
    )
    assert len(result["selected_objects"]) == 2
    assert result["active_object"] == "Cube"


@pytest.mark.asyncio
async def test_invalid_action_rejected():
    bridge = AsyncMock()
    handler = register_select_objects_tool(FakeMCP(), bridge)

    with pytest.raises(ValidationError):
        await handler(action="INVALID_ACTION")
