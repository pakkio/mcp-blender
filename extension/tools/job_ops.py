from .base import ToolBase
from ..bridge.jobs import GLOBAL_JOB_MANAGER, JobStatus


class GetJobStatusTool(ToolBase):
    name = "get_job_status"
    description = "Check the execution status, progress percentage, error state, and output payload of a background job."

    def execute(self, params: dict) -> dict:
        job_id = params.get("job_id")
        if not job_id:
            return {"success": False, "message": "'job_id' is required"}

        job = GLOBAL_JOB_MANAGER.get_job(job_id)
        if not job:
            return {"success": False, "message": f"Job '{job_id}' not found"}

        return {
            "success": True,
            "job": job.to_dict(),
        }


class CancelJobTool(ToolBase):
    name = "cancel_job"
    description = "Signal cancellation for an active or queued background task in Blender."

    def execute(self, params: dict) -> dict:
        job_id = params.get("job_id")
        if not job_id:
            return {"success": False, "message": "'job_id' is required"}

        cancelled = GLOBAL_JOB_MANAGER.cancel_job(job_id)
        if not cancelled:
            return {"success": False, "message": f"Job '{job_id}' not found"}

        return {
            "success": True,
            "message": f"Job '{job_id}' cancellation requested",
            "job_id": job_id,
        }


class ListJobsTool(ToolBase):
    name = "list_jobs"
    description = "List all recent and active background jobs tracked in Blender."

    def execute(self, params: dict) -> dict:
        limit = int(params.get("limit", 20))
        jobs = GLOBAL_JOB_MANAGER.list_jobs(limit=limit)
        return {
            "success": True,
            "count": len(jobs),
            "jobs": jobs,
        }
