import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional


class JobStatus:
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


@dataclass
class Job:
    id: str
    name: str
    status: str = JobStatus.QUEUED
    progress: float = 0.0
    message: str = ""
    result: Optional[dict] = None
    error: Optional[str] = None
    cancelled: bool = False
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None

    def to_dict(self) -> dict:
        duration = round((self.end_time or time.time()) - self.start_time, 2)
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "progress": round(self.progress * 100.0, 1),
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "cancelled": self.cancelled,
            "duration_seconds": duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
        }


class JobManager:
    def __init__(self):
        self._jobs: dict[str, Job] = {}

    def create_job(self, name: str, job_id: Optional[str] = None) -> Job:
        jid = job_id or f"job_{uuid.uuid4().hex[:10]}"
        job = Job(id=jid, name=name, status=JobStatus.RUNNING)
        self._jobs[jid] = job
        return job

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def cancel_job(self, job_id: str) -> bool:
        job = self._jobs.get(job_id)
        if not job:
            return False
        job.cancelled = True
        if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
            job.status = JobStatus.CANCELLED
            job.end_time = time.time()
            job.message = "Job cancelled by user request"
        return True

    def complete_job(self, job_id: str, result: Optional[dict] = None) -> None:
        job = self._jobs.get(job_id)
        if job and not job.cancelled:
            job.status = JobStatus.COMPLETED
            job.progress = 1.0
            job.result = result
            job.end_time = time.time()

    def fail_job(self, job_id: str, error: str) -> None:
        job = self._jobs.get(job_id)
        if job and not job.cancelled:
            job.status = JobStatus.FAILED
            job.error = error
            job.end_time = time.time()

    def list_jobs(self, limit: int = 20) -> list[dict]:
        sorted_jobs = sorted(self._jobs.values(), key=lambda j: j.start_time, reverse=True)
        return [j.to_dict() for j in sorted_jobs[:limit]]


GLOBAL_JOB_MANAGER = JobManager()
