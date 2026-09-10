"""Cooperative async jobs: long tools without blocking the MCP client.

Why this exists: every bpy call must run on Blender's main thread, so a
heavy tool.execute() holds that thread (and every queued bridge request
behind it) for minutes. The MCP client awaiting that one call can't do
anything else meanwhile -- not even poll progress. The scheduler fixes the
client side of that: submit_job records a QUEUED job and answers
immediately; a bpy.app.timers tick (pump_jobs) then runs the job one chunk
at a time on the main thread. Between two chunks Blender's event loop runs
normally, so drain_queue serves other bridge requests -- other tools, job
polls, and the instant bridge_status read -- while the long job advances.
The client polls get_job_status (this job's %, message, and final result)
and/or get_bridge_status (the same tools' viewport-HUD % bar) and meanwhile
issues whatever other calls it wants.

What "chunked" means per tool: a tool opts in by defining
iter_steps(params, ctx) -- a generator that yields once per work chunk and
returns the result dict. Tools without it run as a single chunk (still
async from the client's perspective: queued, cancellable while queued,
result fetched via get_job_status -- but Blender itself stays busy for the
whole run, exactly like a synchronous call). regen_element_names and
separate_logical_areas are chunked (one chunk per vision candidate / group);
render/bake/decimate-style single C calls cannot be split and stay
single-chunk -- documented on the submit_job MCP tool, not silently
implied.

Cancellation is cooperative: cancel_job flags the record and the pump
drops remaining chunks before the next one starts. A chunk already running
(a render, an HTTP round-trip) still runs to its own end.
"""

import time
import traceback

from . import dispatch
from .jobs import GLOBAL_JOB_MANAGER, JobCtx, JobStatus

PUMP_ACTIVE_INTERVAL_S = 0.2
PUMP_IDLE_INTERVAL_S = 1.0


def _single_shot(tool, params: dict, ctx: JobCtx):
    """iter_steps adapter for tools without chunking: the whole execute()
    is one chunk. The unreachable yield makes this a generator function, so
    the pump completes it via StopIteration(result) on the tick that starts
    it -- no special-casing in the pump loop."""
    result = tool.execute(params)
    ctx.report(1.0, "Done")
    if False:  # noqa: SIM188 -- marks this a generator function
        yield
    return result


def submit_job(method: str, params: dict) -> dict:
    """Create a QUEUED job and return immediately. Called straight off the
    WebSocket thread (server.py) -- plain dict writes only, never bpy, never
    blocking. Unknown methods fail fast here rather than as stuck jobs."""
    from ..tools import TOOL_REGISTRY

    method = str(method or "")
    tool = TOOL_REGISTRY.get(method)
    if tool is None:
        return {"success": False, "message": f"Unknown method '{method}'"}
    job = GLOBAL_JOB_MANAGER.create_job(
        name=method,
        method=method,
        params=dict(params or {}),
        generation=dispatch.get_generation(),
    )
    return {
        "success": True,
        "job_id": job.id,
        "method": method,
        "chunked": hasattr(tool, "iter_steps"),
        "message": (
            f"Queued '{method}' as job '{job.id}'. Poll get_job_status for "
            "progress/result (and get_bridge_status for the live HUD % bar); "
            "meanwhile you can issue other calls."
        ),
    }


_active_job_id: str | None = None
_active_gen = None


def _clear_active() -> None:
    global _active_job_id, _active_gen
    _active_job_id = None
    _active_gen = None
    try:
        dispatch.clear_active_job()
    except Exception:
        pass


def _finish_card(title: str, status: str, summary: str) -> None:
    try:
        from ..tools.progress_hud_ops import push_hud_update

        push_hud_update(
            title=title,
            status=status,
            progress_percent=100.0,
            completed_summary=summary,
            auto_hide_seconds=6.0,
            force_redraw=True,
            cursor_badge=False,
        )
    except Exception:
        pass


def reset() -> None:
    """Fail everything outstanding -- addon disable/reload orphans generators
    referencing stale module objects, so they must never resume."""
    global _active_job_id, _active_gen
    _active_job_id = None
    _active_gen = None
    try:
        dispatch.clear_active_job()
    except Exception:
        pass
    mgr = GLOBAL_JOB_MANAGER
    terminal = set()
    for job in list(mgr.list_jobs(limit=1000)):
        if job["status"] in (JobStatus.QUEUED, JobStatus.RUNNING):
            if mgr.fail_if_active(job["id"], "Blender bridge was reloaded before this job could run"):
                terminal.add(job["id"])
    return terminal


def pump_jobs() -> float:
    """bpy.app.timers callback: advance the active job by exactly one chunk,
    then yield to the event loop so queued bridge requests interleave.
    Must return a float to stay registered; never raises into Blender."""
    global _active_job_id, _active_gen
    try:
        mgr = GLOBAL_JOB_MANAGER

        if _active_job_id is None:
            nxt = mgr.next_queued()
            if nxt is None:
                return PUMP_IDLE_INTERVAL_S
            if nxt.generation != dispatch.get_generation():
                mgr.fail_job(nxt.id, "Blender bridge was reloaded before this job could run")
                return PUMP_ACTIVE_INTERVAL_S
            from ..tools import TOOL_REGISTRY

            tool = TOOL_REGISTRY.get(nxt.method)
            if tool is None:
                mgr.fail_job(nxt.id, f"Unknown method '{nxt.method}'")
                return PUMP_ACTIVE_INTERVAL_S
            started = mgr.mark_running(nxt.id)
            if started is None:  # cancelled between pick-up and start
                _cancel_cleanup(nxt.id, nxt.method)
                return PUMP_ACTIVE_INTERVAL_S
            _active_job_id = nxt.id
            try:
                dispatch.set_active_job({"job_id": nxt.id, "method": nxt.method})
            except Exception:
                pass
            ctx = JobCtx(nxt.id)
            if hasattr(tool, "iter_steps"):
                _active_gen = tool.iter_steps(dict(nxt.params), ctx)
            else:
                _active_gen = _single_shot(tool, dict(nxt.params), ctx)

        job = mgr.get_job(_active_job_id)
        if job is None or job.cancelled:
            _cancel_cleanup(_active_job_id, job.method if job else "")
            return PUMP_ACTIVE_INTERVAL_S

        try:
            next(_active_gen)
        except StopIteration as done:
            result = done.value
            if job.cancelled:
                _cancel_cleanup(job.id, job.method)
            else:
                mgr.complete_job(job.id, result if isinstance(result, dict) else {"result": result})
                _clear_active()
        except Exception as exc:  # noqa: BLE001 -- a failing job must never kill the pump
            mgr.fail_job(job.id, f"{job.method} failed: {exc}")
            _finish_card(job.method or "Job", f"Failed: {exc}", f"Job failed: {exc}"[:80])
            try:
                traceback.print_exc()
            except Exception:
                pass
            _clear_active()
        return PUMP_ACTIVE_INTERVAL_S
    except Exception:
        return PUMP_ACTIVE_INTERVAL_S


def _cancel_cleanup(job_id: str | None, method: str) -> None:
    if job_id:
        job = GLOBAL_JOB_MANAGER.get_job(job_id)
        if job is not None and job.status != JobStatus.CANCELLED:
            job.status = JobStatus.CANCELLED
            job.end_time = time.time()
            if not job.message or job.message == "Job cancelled by user request":
                job.message = "Job cancelled by user request"
    _finish_card(method or "Job", "Cancelled -- remaining steps dropped", "Job cancelled"[:80])
    _clear_active()
