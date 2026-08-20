from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.assets.registry import get_provider, all_providers
from mcp_blender.tools.checkpoint_ops import register_checkpoint_tools
from mcp_blender.tools.batch_execution_ops import register_batch_execution_tools
from mcp_blender.tools.job_ops import register_job_tools
from mcp_blender.tools.rigging_ops import register_rigging_tools
from mcp_blender.tools.hair_curves_ops import register_hair_curves_tools
from mcp_blender.tools.grease_pencil_ops import register_grease_pencil_tools
from mcp_blender.tools.vfx_tracking_ops import register_vfx_tracking_tools


@pytest.mark.asyncio
async def test_checkpoint_tools():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "checkpoint_name": "test_snap", "checkpoints": []}
    create_fn, restore_fn, list_fn = register_checkpoint_tools(FakeMCP(), bridge)

    r1 = await create_fn(name="test_snap")
    assert r1["success"] is True
    assert bridge.send_request.call_args[0][0] == "create_scene_checkpoint"

    r2 = await restore_fn(name="test_snap")
    assert r2["success"] is True
    assert bridge.send_request.call_args[0][0] == "restore_scene_checkpoint"

    r3 = await list_fn()
    assert r3["success"] is True
    assert bridge.send_request.call_args[0][0] == "list_scene_checkpoints"


@pytest.mark.asyncio
async def test_batch_execution_with_rollback():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "rolled_back": False, "total_commands": 2}
    (exec_batch,) = register_batch_execution_tools(FakeMCP(), bridge)

    cmds = [{"tool": "create_object", "params": {"object_type": "CUBE"}}]
    r = await exec_batch(commands=cmds, rollback_on_failure=True)
    assert r["success"] is True
    payload = bridge.send_request.call_args[0][1]
    assert payload["rollback_on_failure"] is True


@pytest.mark.asyncio
async def test_job_tools():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "job": {"id": "job_123", "status": "RUNNING"}, "jobs": []}
    get_fn, cancel_fn, list_fn = register_job_tools(FakeMCP(), bridge)

    r1 = await get_fn(job_id="job_123")
    assert r1["success"] is True
    assert bridge.send_request.call_args[0][0] == "get_job_status"

    r2 = await cancel_fn(job_id="job_123")
    assert r2["success"] is True
    assert bridge.send_request.call_args[0][0] == "cancel_job"

    r3 = await list_fn(limit=10)
    assert r3["success"] is True
    assert bridge.send_request.call_args[0][0] == "list_jobs"


@pytest.mark.asyncio
async def test_rigging_ik_and_preset_tools():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "armature_name": "Arm", "bones": ["Root", "Hips"]}
    create_fn, pose_fn, ik_fn, humanoid_fn, spline_fn = register_rigging_tools(FakeMCP(), bridge)

    r1 = await ik_fn(armature_name="Arm", bone_name="Forearm_L", target_name="IK_Hand_L", chain_length=2)
    assert r1["success"] is True
    assert bridge.send_request.call_args[0][0] == "setup_ik_constraint"

    r2 = await humanoid_fn(name="Hero_Rig", height=1.8, generate_ik=True)
    assert r2["success"] is True
    assert bridge.send_request.call_args[0][0] == "setup_humanoid_rig_preset"

    r3 = await spline_fn(armature_name="Arm", bone_name="Tail", curve_name="TailCurve", chain_length=5)
    assert r3["success"] is True
    assert bridge.send_request.call_args[0][0] == "setup_spline_ik_constraint"


@pytest.mark.asyncio
async def test_hair_curves_tools():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "curves_object": "Hair_Curves"}
    create_fn, groom_fn, convert_fn = register_hair_curves_tools(FakeMCP(), bridge)

    r1 = await create_fn(surface_object="HeadMesh", name="CharacterHair", density=200.0)
    assert r1["success"] is True
    assert bridge.send_request.call_args[0][0] == "create_hair_curves"

    r2 = await groom_fn(curves_object="CharacterHair", effect_type="CLUMP", intensity=0.8)
    assert r2["success"] is True
    assert bridge.send_request.call_args[0][0] == "apply_hair_groom_modifier"

    r3 = await convert_fn(object_name="OldHead")
    assert r3["success"] is True
    assert bridge.send_request.call_args[0][0] == "convert_legacy_hair_to_curves"


@pytest.mark.asyncio
async def test_grease_pencil_and_vfx_tracking_tools():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True}
    setup_line_fn, layer_fn, stroke_fn = register_grease_pencil_tools(FakeMCP(), bridge)

    r1 = await layer_fn(gp_object="Inks", layer_name="Outlines", color=[0, 0, 0, 1])
    assert r1["success"] is True
    assert bridge.send_request.call_args[0][0] == "create_grease_pencil_layer"

    r2 = await stroke_fn(gp_object="Inks", layer_name="Outlines", strokes=[{"points": [[0, 0, 0], [1, 1, 1]]}])
    assert r2["success"] is True
    assert bridge.send_request.call_args[0][0] == "draw_grease_pencil_strokes"

    cam_track_fn, shadow_fn = register_vfx_tracking_tools(FakeMCP(), bridge)
    r3 = await cam_track_fn(camera_name="Camera", focal_length=50.0, sensor_width=36.0)
    assert r3["success"] is True
    assert bridge.send_request.call_args[0][0] == "setup_camera_tracking"

    r4 = await shadow_fn(name="VFX_Floor", size=20.0, transparent_film=True)
    assert r4["success"] is True
    assert bridge.send_request.call_args[0][0] == "setup_vfx_shadow_catcher"


@pytest.mark.asyncio
async def test_ai_asset_providers_registry():
    meshy = get_provider("meshy")
    assert meshy.name == "meshy"
    assert meshy.requires_token is True

    tripo = get_provider("tripo")
    assert tripo.name == "tripo"
    assert tripo.requires_token is True

    trellis = get_provider("trellis")
    assert trellis.name == "trellis"
    assert trellis.requires_token is True

    providers = all_providers()
    provider_names = [p.name for p in providers]
    assert "polyhaven" in provider_names
    assert "sketchfab" in provider_names
    assert "ambientcg" in provider_names
    assert "meshy" in provider_names
    assert "tripo" in provider_names
    assert "trellis" in provider_names

    # Test search fallbacks without keys
    hits_meshy = await meshy.search("wooden chest", "MODEL", 5)
    assert len(hits_meshy) >= 1
    assert "wooden chest" in hits_meshy[0].name.lower() or "meshy" in hits_meshy[0].name.lower()

    hits_tripo = await tripo.search("space helmet", "MODEL", 5)
    assert len(hits_tripo) >= 1

    hits_trellis = await trellis.search("cyberpunk car", "MODEL", 5)
    assert len(hits_trellis) >= 1
