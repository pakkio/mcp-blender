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


class DeleteJobTool(ToolBase):
    name = "delete_job"
    description = (
        "Forget one finished background job record (COMPLETED/CANCELLED/FAILED). "
        "Refuses jobs that are still QUEUED/RUNNING -- abort them via cancel_job first."
    )

    def execute(self, params: dict) -> dict:
        job_id = params.get("job_id")
        if not job_id:
            return {"success": False, "message": "'job_id' is required"}

        outcome = GLOBAL_JOB_MANAGER.delete_job(job_id)
        if outcome == "not_found":
            return {"success": False, "message": f"Job '{job_id}' not found"}
        if outcome == "active":
            return {
                "success": False,
                "message": f"Job '{job_id}' is still active -- abort it via cancel_job first",
            }
        return {"success": True, "message": f"Deleted job '{job_id}'", "job_id": job_id}


class PruneJobsTool(ToolBase):
    name = "prune_jobs"
    description = (
        "Forget finished background job records older than a cutoff "
        "(default 1 day). Active (QUEUED/RUNNING) jobs are never touched."
    )

    def execute(self, params: dict) -> dict:
        try:
            days = float(params.get("older_than_days", 1.0))
        except (TypeError, ValueError):
            return {"success": False, "message": "'older_than_days' must be a number"}
        if days < 0:
            return {"success": False, "message": "'older_than_days' must be >= 0"}

        count = GLOBAL_JOB_MANAGER.prune_older_than(days * 86400.0)
        return {
            "success": True,
            "message": f"Deleted {count} job(s) older than {days:g} day(s)",
            "deleted": count,
            "older_than_days": days,
        }
