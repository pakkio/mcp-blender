from typing import Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class GetJobStatusParams(BaseModel):
    job_id: str = Field(..., description="ID of the background job to inspect")


class CancelJobParams(BaseModel):
    job_id: str = Field(..., description="ID of the background job to cancel")


class ListJobsParams(BaseModel):
    limit: int = Field(20, description="Maximum number of recent jobs to return")


class DeleteJobParams(BaseModel):
    job_id: str = Field(..., description="ID of the finished background job to forget")


class PruneJobsParams(BaseModel):
    older_than_days: float = Field(1.0, description="Forget finished jobs older than this many days")


class SubmitJobParams(BaseModel):
    method: str = Field(..., description="Bridge tool/method to run, e.g. 'separate_logical_areas'")
    params: dict = Field(default_factory=dict, description="Params for that tool, as usual")


def register_job_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="submit_job",
        description=(
            "Run a Blender tool as a background async job and return immediately with a job_id, "
            "instead of blocking until it finishes. Use this for long operations "
            "(separate_logical_areas, regen_element_names with use_vision, simplify_geometry, "
            "renders, bakes) so you can keep working meanwhile: poll get_job_status(job_id) for "
            "progress/message/result, and get_bridge_status for the live viewport-HUD % bar. "
            "Blender runs one job at a time and interleaves other requests between work chunks, "
            "so short calls still answer while a job advances. Chunked tools (regen_element_names, "
            "separate_logical_areas) also free the main thread between steps; single-C-call tools "
            "(render, bake) stay busy for the whole run but the client is never stuck awaiting. "
            "Don't mutate the job's inputs (selected objects, scene structure) from another call "
            "while it runs. Cancel anytime with cancel_job. Params: method (bridge tool name), "
            "params (that tool's usual params dict)."
        ),
    )
    async def submit_job(method: str, params: dict = {}) -> dict:
        SubmitJobParams(method=method, params=params or {})
        result = await bridge.send_request(
            "submit_job", {"method": method, "params": params or {}}, timeout=5.0
        )
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "submit_job failed"))
        return result

    @mcp.tool(
        name="get_job_status",
        description="Check the execution status, progress percentage, error state, and output payload of a background job.",
    )
    async def get_job_status(job_id: str) -> dict:
        params = GetJobStatusParams(job_id=job_id)
        result = await bridge.send_request("get_job_status", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "get_job_status failed"))
        return result

    @mcp.tool(
        name="cancel_job",
        description="Signal cancellation for an active or queued background task in Blender.",
    )
    async def cancel_job(job_id: str) -> dict:
        params = CancelJobParams(job_id=job_id)
        result = await bridge.send_request("cancel_job", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "cancel_job failed"))
        return result

    @mcp.tool(
        name="list_jobs",
        description="List all recent and active background jobs tracked in Blender.",
    )
    async def list_jobs(limit: int = 20) -> dict:
        params = ListJobsParams(limit=limit)
        result = await bridge.send_request("list_jobs", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "list_jobs failed"))
        return result

    @mcp.tool(
        name="delete_job",
        description=(
            "Forget one finished background job record. Refuses jobs that are still "
            "queued/running -- abort them via cancel_job first."
        ),
    )
    async def delete_job(job_id: str) -> dict:
        params = DeleteJobParams(job_id=job_id)
        result = await bridge.send_request("delete_job", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "delete_job failed"))
        return result

    @mcp.tool(
        name="prune_jobs",
        description=(
            "Forget finished background job records older than a cutoff (default 1 day). "
            "Active (queued/running) jobs are never touched."
        ),
    )
    async def prune_jobs(older_than_days: float = 1.0) -> dict:
        params = PruneJobsParams(older_than_days=older_than_days)
        result = await bridge.send_request("prune_jobs", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "prune_jobs failed"))
        return result

    return (submit_job, get_job_status, cancel_job, list_jobs, delete_job, prune_jobs)
