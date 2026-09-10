from unittest.mock import AsyncMock
import pytest

from conftest import FakeMCP
from mcp_blender.errors import BridgeError
from mcp_blender.tools.job_ops import register_job_tools


@pytest.mark.asyncio
async def test_submit_job_returns_immediately_with_job_id():
    bridge = AsyncMock()
    bridge.send_request.return_value = {
        "success": True,
        "job_id": "job_abc123",
        "method": "separate_logical_areas",
        "chunked": True,
        "message": "Queued 'separate_logical_areas' as job 'job_abc123'.",
    }
    (submit_fn, _status_fn, _cancel_fn, _list_fn, _delete_fn, _prune_fn) = register_job_tools(FakeMCP(), bridge)

    result = await submit_fn(method="separate_logical_areas", params={"lang": "it"})

    assert result["job_id"] == "job_abc123"
    assert result["chunked"] is True
    bridge.send_request.assert_awaited_with(
        "submit_job",
        {"method": "separate_logical_areas", "params": {"lang": "it"}},
        timeout=5.0,
    )


@pytest.mark.asyncio
async def test_submit_job_defaults_to_empty_params():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "job_id": "job_x", "chunked": False}
    (submit_fn, _status_fn, _cancel_fn, _list_fn, _delete_fn, _prune_fn) = register_job_tools(FakeMCP(), bridge)

    await submit_fn(method="list_jobs")

    bridge.send_request.assert_awaited_with(
        "submit_job", {"method": "list_jobs", "params": {}}, timeout=5.0
    )


@pytest.mark.asyncio
async def test_submit_job_raises_on_unknown_method():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "Unknown method 'nope'"}
    (submit_fn, _status_fn, _cancel_fn, _list_fn, _delete_fn, _prune_fn) = register_job_tools(FakeMCP(), bridge)

    with pytest.raises(BridgeError):
        await submit_fn(method="nope", params={})


@pytest.mark.asyncio
async def test_delete_job_forwards_and_returns():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "message": "Deleted job 'job_x'", "job_id": "job_x"}
    (_submit_fn, _status_fn, _cancel_fn, _list_fn, delete_fn, _prune_fn) = register_job_tools(
        FakeMCP(), bridge
    )

    result = await delete_fn(job_id="job_x")

    assert result["job_id"] == "job_x"
    bridge.send_request.assert_awaited_with("delete_job", {"job_id": "job_x"})


@pytest.mark.asyncio
async def test_delete_job_raises_for_active_job():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": False, "message": "still active"}
    (_submit_fn, _status_fn, _cancel_fn, _list_fn, delete_fn, _prune_fn) = register_job_tools(
        FakeMCP(), bridge
    )

    with pytest.raises(BridgeError):
        await delete_fn(job_id="job_x")


@pytest.mark.asyncio
async def test_prune_jobs_defaults_to_one_day():
    bridge = AsyncMock()
    bridge.send_request.return_value = {"success": True, "deleted": 3, "older_than_days": 1.0}
    (_submit_fn, _status_fn, _cancel_fn, _list_fn, _delete_fn, prune_fn) = register_job_tools(
        FakeMCP(), bridge
    )

    result = await prune_fn()

    assert result["deleted"] == 3
    bridge.send_request.assert_awaited_with("prune_jobs", {"older_than_days": 1.0})
