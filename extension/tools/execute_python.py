"""Escape-hatch tool: run arbitrary Python inside Blender.

Deliberately unsandboxed and trusted-only, equivalent in power to Blender's
own Python console (mirrors ahujasid/blender-mcp's execute_code tool). This
process is only ever reachable from localhost by the paired mcp_server
process running as the same user, so there is no additional privilege
boundary being crossed by allowing exec() here -- but it means anyone who
can reach the WebSocket port can run arbitrary code as this user. Keep the
bridge server bound to localhost unless you understand that trade-off.
"""

import contextlib
import io
import traceback

import bmesh
import bpy
import mathutils

from .base import ToolBase


class ExecuteBlenderPythonTool(ToolBase):
    name = "execute_blender_python"
    description = (
        "Execute arbitrary Python code inside Blender with bpy/bmesh/mathutils "
        "available. TRUSTED, LOCAL-ONLY, UNSANDBOXED -- equivalent to Blender's "
        "own Python console. Assign to a variable named `result` to return a value."
    )

    def execute(self, params: dict) -> dict:
        code = params.get("code")
        if not code:
            return {"success": False, "message": "'code' is required"}

        namespace = {"bpy": bpy, "bmesh": bmesh, "mathutils": mathutils, "result": None}
        stdout = io.StringIO()

        try:
            with contextlib.redirect_stdout(stdout):
                exec(code, namespace)  # noqa: S102 - deliberate escape hatch, see module docstring
        except Exception as exc:  # noqa: BLE001
            return {
                "success": False,
                "message": str(exc),
                "traceback": traceback.format_exc(),
                "stdout": stdout.getvalue(),
            }

        return {
            "success": True,
            "message": "Executed successfully",
            "stdout": stdout.getvalue(),
            "result": repr(namespace.get("result")),
        }
