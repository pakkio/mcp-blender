from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.material_ops import register_material_tools


@pytest.mark.asyncio
async def test_create_material_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "material_name": "Gold",
        "assigned_to": "Cube",
    }
    create_mat, assign_mat, get_mat, set_mat = register_material_tools(FakeMCP(), bridge)

    result = await create_mat(
        name="Gold",
        base_color=(1.0, 0.8, 0.2, 1.0),
        metallic=1.0,
        roughness=0.2,
        assign_to_object="Cube",
    )

    bridge.send_request.assert_awaited_once_with(
        "create_material",
        {
            "name": "Gold",
            "base_color": (1.0, 0.8, 0.2, 1.0),
            "metallic": 1.0,
            "roughness": 0.2,
            "specular": 0.5,
            "ior": 1.45,
            "transmission": 0.0,
            "emission_color": (0.0, 0.0, 0.0, 1.0),
            "emission_strength": 1.0,
            "alpha": 1.0,
            "assign_to_object": "Cube",
        },
    )
    assert result["material_name"] == "Gold"


@pytest.mark.asyncio
async def test_assign_material_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "object_name": "Cube", "material_name": "Gold"}
    create_mat, assign_mat, get_mat, set_mat = register_material_tools(FakeMCP(), bridge)

    result = await assign_mat(object_name="Cube", material_name="Gold")

    bridge.send_request.assert_awaited_once_with(
        "assign_material",
        {"object_name": "Cube", "material_name": "Gold", "slot_index": None},
    )
    assert result["success"] is True
