import base64
from unittest.mock import AsyncMock

import pytest

from conftest import FakeMCP
from mcp_blender.errors import BridgeError
from mcp_blender.tools.localization_ops import register_localization_tools

_STRUCTURAL_TREE = {
    "old_name": "Scene Collection",
    "new_name": "Scene Collection",
    "renamed": False,
    "objects_count": 0,
    "is_empty_node": False,
    "objects": [],
    "children": [
        {
            "old_name": "Furniture",
            "new_name": "Arredamento",
            "renamed": True,
            "objects_count": 1,
            "is_empty_node": False,
            # Shape must match what the Blender-side _regen_object() actually
            # emits: old_name/new_name/type/renamed/parent -- there is no bare
            # "name" key. The vision pass targets the post-rename new_name.
            "objects": [
                {
                    "old_name": "Chair_Mesh",
                    "new_name": "Chair_Mesh",
                    "type": "MESH",
                    "renamed": False,
                    "parent": "Arredamento",
                }
            ],
            "children": [],
        },
        {
            "old_name": "Props",
            "new_name": "Oggetti",
            "renamed": True,
            "objects_count": 0,
            "is_empty_node": True,
            "objects": [],
            "children": [],
        },
    ],
}


def _bridge_with_structural_result(extra_responses=None):
    bridge = AsyncMock()
    responses = {"regen_element_names": {"success": True, "message": "Regenerated names for 'Scene Collection' (lang=it)", "root": _STRUCTURAL_TREE}}
    if extra_responses:
        responses.update(extra_responses)

    async def send_request(method, params, timeout=None):
        if method in responses:
            resp = responses[method]
            return resp(params) if callable(resp) else resp
        return {"success": True}

    bridge.send_request.side_effect = send_request
    return bridge


@pytest.mark.asyncio
async def test_regen_names_structural_only_by_default(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    bridge = _bridge_with_structural_result()
    handler, _separate_tool = register_localization_tools(FakeMCP(), bridge)

    result = await handler()

    bridge.send_request.assert_awaited_once_with(
        "regen_element_names", {"lang": "it", "element": None}, timeout=600.0
    )
    assert result["success"] is True
    assert result["structural"] == _STRUCTURAL_TREE
    assert result["vision_used"] is False
    assert result["vision_renames"] == []


@pytest.mark.asyncio
async def test_regen_names_structural_failure_raises(monkeypatch):
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "no such element"}
    handler, _separate_tool = register_localization_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError, match="no such element"):
        await handler(element="Nonexistent")


@pytest.mark.asyncio
async def test_regen_names_vision_skipped_without_api_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    bridge = _bridge_with_structural_result()
    handler, _separate_tool = register_localization_tools(FakeMCP(), bridge)

    result = await handler(use_vision=True)

    assert result["vision_used"] is False
    assert result["vision_note"] and "OPENROUTER_API_KEY" in result["vision_note"]
    assert result["vision_renames"] == []
    # Only the structural call went out -- no inspect_focus_shot attempted.
    assert bridge.send_request.await_count == 1


@pytest.mark.asyncio
async def test_regen_names_vision_pass_renames_mesh_leaf_with_semantic_prompt(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    raw = b"fake-png"
    uri = "data:image/png;base64," + base64.b64encode(raw).decode()

    bridge = _bridge_with_structural_result(
        extra_responses={
            "inspect_focus_shot": {"success": True, "image_base64": uri},
            "set_object_properties": lambda p: {"success": True, "name": p["new_name"]},
        }
    )
    handler, _separate_tool = register_localization_tools(FakeMCP(), bridge)

    seen_questions = []

    async def fake_critique(question, png_bytes, model=None):
        seen_questions.append(question)
        assert png_bytes == raw
        return {"critique": "  Sedile.  ", "model": "m", "prompt_tokens": 1, "completion_tokens": 1}

    monkeypatch.setattr("mcp_blender.tools.localization_ops.critique_image", fake_critique)

    result = await handler(use_vision=True)

    assert result["vision_used"] is True
    assert result["vision_renames"] == [{"old_name": "Chair_Mesh", "new_name": "Sedile"}]
    # The prompt must steer away from geometric-shape naming and toward
    # semantic role, and carry the object's category as context.
    assert len(seen_questions) == 1
    assert "cube" in seen_questions[0].lower()
    assert "semantic" in seen_questions[0].lower()
    assert "Arredamento" in seen_questions[0]

    rename_call = next(
        c for c in bridge.send_request.await_args_list if c.args[0] == "set_object_properties"
    )
    assert rename_call.args[1] == {"name": "Chair_Mesh", "new_name": "Sedile"}


@pytest.mark.asyncio
async def test_regen_names_vision_pass_skips_object_on_capture_failure(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    bridge = _bridge_with_structural_result(
        extra_responses={"inspect_focus_shot": {"success": False, "message": "no camera"}}
    )
    handler, _separate_tool = register_localization_tools(FakeMCP(), bridge)

    async def fake_critique(question, png_bytes, model=None):
        raise AssertionError("must not be called when capture fails")

    monkeypatch.setattr("mcp_blender.tools.localization_ops.critique_image", fake_critique)

    result = await handler(use_vision=True)

    assert result["vision_renames"] == []


@pytest.mark.asyncio
async def test_regen_names_respects_max_vision_renames_cap(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    tree = {
        "old_name": "Scene Collection",
        "new_name": "Scene Collection",
        "renamed": False,
        "objects_count": 0,
        "is_empty_node": False,
        "objects": [
            {
                "old_name": f"Part_{i}",
                "new_name": f"Part_{i}",
                "type": "MESH",
                "renamed": False,
                "parent": None,
            }
            for i in range(5)
        ],
        "children": [],
    }
    bridge = AsyncMock()

    async def send_request(method, params, timeout=None):
        if method == "regen_element_names":
            return {"success": True, "message": "ok", "root": tree}
        if method == "inspect_focus_shot":
            return {"success": True, "image_base64": base64.b64encode(b"x").decode()}
        if method == "set_object_properties":
            return {"success": True, "name": params["new_name"]}
        return {"success": True}

    bridge.send_request.side_effect = send_request
    handler, _separate_tool = register_localization_tools(FakeMCP(), bridge)

    async def fake_critique(question, png_bytes, model=None):
        return {"critique": "Parte", "model": "m", "prompt_tokens": 1, "completion_tokens": 1}

    monkeypatch.setattr("mcp_blender.tools.localization_ops.critique_image", fake_critique)

    result = await handler(use_vision=True, max_vision_renames=2)

    assert len(result["vision_renames"]) == 2


@pytest.mark.asyncio
async def test_regen_names_vision_only_generic_skips_already_renamed_leaves(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    tree = {
        "old_name": "Scene Collection",
        "new_name": "Scene Collection",
        "renamed": False,
        "objects_count": 0,
        "is_empty_node": False,
        "objects": [
            {"old_name": "Wheel", "new_name": "Ruota", "type": "MESH", "renamed": True, "parent": None},
            {"old_name": "Chair_Mesh", "new_name": "Chair_Mesh", "type": "MESH", "renamed": False, "parent": None},
        ],
        "children": [],
    }
    bridge = AsyncMock()

    async def send_request(method, params, timeout=None):
        if method == "regen_element_names":
            return {"success": True, "message": "ok", "root": tree}
        if method == "inspect_focus_shot":
            return {"success": True, "image_base64": base64.b64encode(b"x").decode()}
        if method == "set_object_properties":
            return {"success": True, "name": params["new_name"]}
        return {"success": True}

    bridge.send_request.side_effect = send_request
    handler, _separate_tool = register_localization_tools(FakeMCP(), bridge)

    async def fake_critique(question, png_bytes, model=None):
        return {"critique": "Sedile", "model": "m", "prompt_tokens": 1, "completion_tokens": 1}

    monkeypatch.setattr("mcp_blender.tools.localization_ops.critique_image", fake_critique)

    result = await handler(use_vision=True, vision_only_generic=True)

    assert result["vision_renames"] == [{"old_name": "Chair_Mesh", "new_name": "Sedile"}]


@pytest.mark.asyncio
async def test_separate_logical_areas_selects_then_separates():
    bridge = AsyncMock()

    async def send_request(method, params, timeout=None):
        if method == "select_objects":
            return {"success": True}
        if method == "separate_logical_areas":
            return {"success": True, "message": "Successfully separated into 3 parts across 2 groups."}
        return {"success": True}

    bridge.send_request.side_effect = send_request
    _regen_tool, separate_tool = register_localization_tools(FakeMCP(), bridge)

    result = await separate_tool(objects=["Chair_Mesh", "Table_Mesh"])

    assert result["success"] is True
    select_call, separate_call = bridge.send_request.await_args_list
    assert select_call.args == (
        "select_objects",
        {"names": ["Chair_Mesh", "Table_Mesh"], "action": "SET", "active_object": "Chair_Mesh", "mode": "OBJECT"},
    )
    assert separate_call.args[0] == "separate_logical_areas"
    assert separate_call.args[1]["lang"] == "it"
    assert separate_call.kwargs["timeout"] == 600.0


@pytest.mark.asyncio
async def test_separate_logical_areas_requires_at_least_one_object():
    bridge = AsyncMock()
    _regen_tool, separate_tool = register_localization_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError, match="at least one mesh object"):
        await separate_tool(objects=[])

    bridge.send_request.assert_not_awaited()


@pytest.mark.asyncio
async def test_separate_logical_areas_select_failure_raises():
    bridge = AsyncMock()
    bridge.send_request.side_effect = [{"success": False, "message": "no such object"}]
    _regen_tool, separate_tool = register_localization_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError, match="no such object"):
        await separate_tool(objects=["Missing"])


@pytest.mark.asyncio
async def test_separate_logical_areas_bridge_failure_raises():
    bridge = AsyncMock()

    async def send_request(method, params, timeout=None):
        if method == "select_objects":
            return {"success": True}
        return {"success": False, "message": "Please select at least one MESH object"}

    bridge.send_request.side_effect = send_request
    _regen_tool, separate_tool = register_localization_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError, match="Please select at least one MESH object"):
        await separate_tool(objects=["NotAMesh"])
