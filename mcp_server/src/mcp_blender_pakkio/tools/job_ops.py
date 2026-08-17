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


def register_job_tools(mcp: FastMCP, bridge: BlenderBridge):
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

    return (get_job_status, cancel_job, list_jobs)
