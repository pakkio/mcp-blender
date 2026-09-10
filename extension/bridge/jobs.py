"""Background-job records shared by the WebSocket thread and the main thread.

submit_job (server.py, answered straight off the asyncio thread) creates a
QUEUED record and returns its id immediately; the main-thread scheduler
(bridge/scheduler.py, driven by a bpy.app.timers tick) picks records up,
runs them chunk by chunk, and writes progress/result back here. get_job_status
reads the same records back over the wire. Two threads touch this dict, so
every access goes through the manager's lock -- held only for plain dict
ops, never for the duration of any tool work.
"""

import threading
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
    # What to run: bridge method + params. Kept off the wire -- to_dict()
    # never ships params (they can be huge: execute_python's "code",
    # execute_batch's "commands").
    method: str = ""
    params: dict = field(default_factory=dict)
    generation: int = 0

    def to_dict(self) -> dict:
        duration = round((self.end_time or time.time()) - self.start_time, 2)
        try:
            created = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(self.start_time))
        except Exception:
            created = ""
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
            "created": created,
            "end_time": self.end_time,
        }


class JobManager:
    def __init__(self, max_terminal: int = 50):
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()
        self._max_terminal = max_terminal

    def create_job(
        self,
        name: str,
        method: str = "",
        params: Optional[dict] = None,
        generation: int = 0,
        job_id: Optional[str] = None,
    ) -> Job:
        jid = job_id or f"job_{uuid.uuid4().hex[:10]}"
        job = Job(
            id=jid,
            name=name,
            status=JobStatus.QUEUED,
            method=method,
            params=dict(params or {}),
            generation=generation,
        )
        with self._lock:
            self._jobs[jid] = job
            self._prune_locked()
        return job

    def _prune_locked(self) -> None:
        """Cap memory: drop the oldest terminal records beyond the cap.
        QUEUED/RUNNING records are never pruned."""
        terminal = sorted(
            (j for j in self._jobs.values() if j.status not in (JobStatus.QUEUED, JobStatus.RUNNING)),
            key=lambda j: j.start_time,
        )
        overflow = len(terminal) - self._max_terminal
        for job in terminal[: max(0, overflow)]:
            del self._jobs[job.id]

    def get_job(self, job_id: str) -> Optional[Job]:
        with self._lock:
            return self._jobs.get(job_id)

    def next_queued(self) -> Optional[Job]:
        """Oldest QUEUED job, or None. The scheduler runs one job at a
        time; the rest wait their turn (visible via list_jobs)."""
        with self._lock:
            queued = [j for j in self._jobs.values() if j.status == JobStatus.QUEUED]
        if not queued:
            return None
        return min(queued, key=lambda j: j.start_time)

    def mark_running(self, job_id: str) -> Optional[Job]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.cancelled:
                return None
            job.status = JobStatus.RUNNING
            return job

    def update_job(self, job_id: str, progress: float, message: str) -> None:
        """Per-chunk progress report from the scheduler. No-ops on unknown
        or already-terminal jobs so a stale reporter can't resurrect one."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status != JobStatus.RUNNING:
                return
            job.progress = max(0.0, min(1.0, float(progress)))
            job.message = str(message)

    def cancel_job(self, job_id: str) -> bool:
        job = self.get_job(job_id)
        if not job:
            return False
        with self._lock:
            job.cancelled = True
            if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                job.status = JobStatus.CANCELLED
                job.end_time = time.time()
                job.message = "Job cancelled by user request"
        return True

    def complete_job(self, job_id: str, result: Optional[dict] = None) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and not job.cancelled:
                job.status = JobStatus.COMPLETED
                job.progress = 1.0
                job.result = result
                job.end_time = time.time()

    def fail_job(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job and not job.cancelled:
                job.status = JobStatus.FAILED
                job.error = error
                job.end_time = time.time()

    def fail_if_active(self, job_id: str, error: str) -> bool:
        """Mark FAILED only if still QUEUED/RUNNING (addon-reload path):
        never clobber a record that already reached a terminal state."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
                return False
            job.status = JobStatus.FAILED
            job.error = error
            job.end_time = time.time()
            return True

    def delete_job(self, job_id: str) -> str:
        """Forget one job record. Returns "deleted" / "not_found" / "active":
        a QUEUED/RUNNING job is refused -- abort it via cancel_job first so
        the scheduler never loses a record out from under a live generator."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return "not_found"
            if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                return "active"
            del self._jobs[job_id]
            return "deleted"

    def prune_older_than(self, older_than_s: float) -> int:
        """Forget terminal (COMPLETED/CANCELLED/FAILED) records older than
        the cutoff. Active jobs are never touched. Returns the count."""
        cutoff = time.time() - max(0.0, float(older_than_s))
        with self._lock:
            stale = [
                jid
                for jid, job in self._jobs.items()
                if job.status
                not in (JobStatus.QUEUED, JobStatus.RUNNING)
                and (job.end_time or job.start_time) < cutoff
            ]
            for jid in stale:
                del self._jobs[jid]
        return len(stale)

    def list_jobs(self, limit: int = 20) -> list[dict]:
        with self._lock:
            jobs = list(self._jobs.values())
        sorted_jobs = sorted(jobs, key=lambda j: j.start_time, reverse=True)
        return [j.to_dict() for j in sorted_jobs[:limit]]


GLOBAL_JOB_MANAGER = JobManager()


class JobCtx:
    """Progress reporter handed to iter_steps generators (see ToolBase).
    Null-safe: with job_id="" (the synchronous execute() path) report() is
    a no-op, so the same step code drives both paths -- the sync path
    already pushes the viewport HUD itself, it just has no job record to
    mirror into. Lives here (leaf module, no bpy/tools imports) so tool
    modules can import it at top level without import cycles."""

    def __init__(self, job_id: str = ""):
        self.job_id = job_id

    def report(self, fraction: float, status: str) -> None:
        if not self.job_id:
            return
        try:
            GLOBAL_JOB_MANAGER.update_job(self.job_id, fraction, status)
        except Exception:
            pass


NULL_CTX = JobCtx()


def drive_to_completion(gen):
    """Run a step generator to its `return result` (the synchronous path:
    ToolBase.execute() driving its own iter_steps in one go -- same chunks,
    same HUD pushes, just no yield to the event loop between them)."""
    try:
        while True:
            next(gen)
    except StopIteration as done:
        return done.value
