from unittest.mock import AsyncMock
import pytest
from pydantic import ValidationError

from conftest import FakeMCP
from mcp_blender.tools.mesh_operation import register_mesh_operation_tool


@pytest.mark.asyncio
async def test_mesh_operation_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "Cube",
        "operation": "SHADE_SMOOTH",
    }
    handler = register_mesh_operation_tool(FakeMCP(), bridge)

    result = await handler(object_name="Cube", operation="SHADE_SMOOTH")

    bridge.send_request.assert_awaited_once_with(
        "mesh_operation",
        {
            "object_name": "Cube",
            "operation": "SHADE_SMOOTH",
            "join_with_objects": None,
            "merge_distance": 0.0001,
            "subdivision_cuts": 1,
        },
    )
    assert result["operation"] == "SHADE_SMOOTH"


@pytest.mark.asyncio
async def test_invalid_mesh_operation():
    bridge = AsyncMock()
    handler = register_mesh_operation_tool(FakeMCP(), bridge)

    with pytest.raises(ValidationError):
        await handler(object_name="Cube", operation="EXPLODE_EVERYTHING")
