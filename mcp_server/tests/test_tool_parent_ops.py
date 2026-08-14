from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.parent_ops import register_parent_tools


@pytest.mark.asyncio
async def test_parent_objects_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "parent_name": "Parent",
        "children": ["Child1", "Child2"],
    }
    parent_tool, unparent_tool = register_parent_tools(FakeMCP(), bridge)

    result = await parent_tool(parent_name="Parent", child_names=["Child1", "Child2"])

    bridge.send_request.assert_awaited_once_with(
        "parent_objects",
        {
            "parent_name": "Parent",
            "child_names": ["Child1", "Child2"],
            "keep_transform": True,
            "parent_type": "OBJECT",
        },
    )
    assert result["parent_name"] == "Parent"


@pytest.mark.asyncio
async def test_unparent_objects_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "unparented": ["Child1"],
    }
    parent_tool, unparent_tool = register_parent_tools(FakeMCP(), bridge)

    result = await unparent_tool(names=["Child1"])

    bridge.send_request.assert_awaited_once_with(
        "unparent_objects",
        {
            "names": ["Child1"],
            "keep_transform": True,
        },
    )
    assert result["unparented"] == ["Child1"]
