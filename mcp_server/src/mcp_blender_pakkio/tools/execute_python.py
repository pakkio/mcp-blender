from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType


class ExecuteBlenderPythonParams(BaseModel):
    code: str = Field(..., min_length=1)


def register_execute_blender_python_tool(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="execute_blender_python",
        description=(
            "Execute arbitrary Python code inside Blender with bpy/bmesh/mathutils "
            "available. TRUSTED, LOCAL-ONLY, UNSANDBOXED -- equivalent to Blender's "
            "own Python console. Assign to a variable named `result` to return a value. "
            "Use the dedicated tools (create_object, set_object_transform, delete_object, "
            "get_scene_info) instead of this whenever they cover what you need."
        ),
    )
    async def execute_blender_python(code: str) -> dict:
        params = ExecuteBlenderPythonParams(code=code)
        result = await bridge.send_request("execute_blender_python", params.model_dump())
        if not result.get("success"):
            raise BridgeError(
                ErrorType.TOOL_EXECUTION, result.get("message", "execute_blender_python failed")
            )
        return result

    return execute_blender_python
