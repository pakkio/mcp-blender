from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.collection_ops import register_collection_tools


@pytest.mark.asyncio
async def test_manage_collection_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "collection_name": "Props",
    }
    handler = register_collection_tools(FakeMCP(), bridge)

    result = await handler(action="CREATE", name="Props")

    bridge.send_request.assert_awaited_once_with(
        "manage_collection",
        {
            "action": "CREATE",
            "name": "Props",
            "new_name": None,
            "object_name": None,
            "parent_collection": None,
            "hide_viewport": None,
            "hide_render": None,
        },
    )
    assert result["collection_name"] == "Props"
