"""Tool contract for Blender-side tools.

Deliberately minimal: execute() always runs on Blender's main thread
(guaranteed by dispatch.py's drain_queue), takes/returns plain dicts, and
raises on unexpected failure — dispatch.py catches that and turns it into a
tool_execution_error wire response. There is no schema/type validation here
on purpose: parameter validation lives once, client-side, in the paired
mcp_server tool (pydantic) — this side only does lightweight required-field
checks because it's only ever called by its own paired MCP server.
"""

import abc


class ToolBase(abc.ABC):
    name: str
    description: str

    @abc.abstractmethod
    def execute(self, params: dict) -> dict:
        """Run on Blender's main thread. Return a JSON-serializable dict."""
        raise NotImplementedError

    # Optional async protocol for long tools. A tool MAY define
    #   def iter_steps(self, params: dict, ctx) -> generator
    # yielding once per work chunk and returning the result dict. The bridge
    # scheduler (bridge/scheduler.py) drives one chunk per timer tick so
    # other bridge requests interleave between chunks; execute() should drive
    # the same generator to completion (via bridge.jobs.drive_to_completion)
    # so the synchronous and async paths run identical code. ctx is a
    # bridge.jobs.JobCtx: ctx.report(fraction_0_1, status) mirrors progress
    # into the job record (null-safe no-op with JobCtx() on the sync path,
    # which already pushes the viewport HUD itself).
