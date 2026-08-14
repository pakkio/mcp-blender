from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender_pakkio.tools.advanced_material_ops import register_advanced_material_tools


@pytest.mark.asyncio
async def test_edit_material_nodes_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "message": "Connected 'Noise.Color' -> 'BSDF.Base Color'",
    }
    edit_mat, manage_col = register_advanced_material_tools(FakeMCP(), bridge)

    result = await edit_mat(
        material_name="ProceduralMat",
        action="CONNECT_NODES",
        from_node="Noise",
        from_socket="Color",
        to_node="BSDF",
        to_socket="Base Color",
    )
    bridge.send_request.assert_awaited_once_with(
        "edit_material_nodes",
        {
            "material_name": "ProceduralMat",
            "action": "CONNECT_NODES",
            "node_type": None,
            "node_name": None,
            "node_location": [0.0, 0.0],
            "from_node": "Noise",
            "from_socket": "Color",
            "to_node": "BSDF",
            "to_socket": "Base Color",
            "input_socket": None,
            "input_value": None,
        },
    )
    assert result["success"] is True


@pytest.mark.asyncio
async def test_manage_color_attributes_happy_path():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "object_name": "MeshObj",
        "attribute_name": "Color",
        "fill_mode": "SOLID",
    }
    edit_mat, manage_col = register_advanced_material_tools(FakeMCP(), bridge)

    result = await manage_col(
        object_name="MeshObj",
        action="CREATE",
        attribute_name="Color",
        color=[0.0, 1.0, 0.0, 1.0],
        fill_mode="SOLID",
    )
    bridge.send_request.assert_awaited_once_with(
        "manage_color_attributes",
        {
            "object_name": "MeshObj",
            "action": "CREATE",
            "attribute_name": "Color",
            "domain": "CORNER",
            "data_type": "FLOAT_COLOR",
            "color": [0.0, 1.0, 0.0, 1.0],
            "fill_mode": "SOLID",
        },
    )
    assert result["attribute_name"] == "Color"
