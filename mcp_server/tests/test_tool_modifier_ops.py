from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.modifier_ops import register_modifier_tools


@pytest.mark.asyncio
async def test_add_modifier_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Cube",
        "modifier_name": "Subsurf",
        "modifier_type": "SUBSURF",
    }
    add_mod, apply_mod, remove_mod, set_mod = register_modifier_tools(FakeMCP(), bridge)

    result = await add_mod(object_name="Cube", modifier_type="SUBSURF", properties={"levels": 2})

    bridge.send_request.assert_awaited_once_with(
        "add_modifier",
        {
            "object_name": "Cube",
            "modifier_type": "SUBSURF",
            "name": None,
            "properties": {"levels": 2},
        },
    )
    assert result["modifier_name"] == "Subsurf"


@pytest.mark.asyncio
async def test_apply_modifier_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "object_name": "Cube", "modifier_name": "Subsurf"}
    add_mod, apply_mod, remove_mod, set_mod = register_modifier_tools(FakeMCP(), bridge)

    result = await apply_mod(object_name="Cube", modifier_name="Subsurf")

    bridge.send_request.assert_awaited_once_with(
        "apply_modifier",
        {"object_name": "Cube", "modifier_name": "Subsurf"},
    )
    assert result["success"] is True
