from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.tools.boolean_ops import register_boolean_tools


@pytest.mark.asyncio
async def test_boolean_operation_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "target_object": "Cube",
        "operand_object": "Sphere",
        "operation": "DIFFERENCE",
        "solver": "EXACT",
        "applied": True,
    }
    bool_op = register_boolean_tools(FakeMCP(), bridge)

    result = await bool_op(
        target_object="Cube",
        operand_object="Sphere",
        operation="DIFFERENCE",
        solver="EXACT",
        apply_immediately=True,
    )

    bridge.send_request.assert_awaited_once_with(
        "boolean_operation",
        {
            "target_object": "Cube",
            "operand_object": "Sphere",
            "operation": "DIFFERENCE",
            "solver": "EXACT",
            "apply_immediately": True,
            "delete_operand": False,
        },
    )
    assert result["success"] is True
    assert result["operation"] == "DIFFERENCE"
