from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from ..bridge import BlenderBridge
from ..errors import BridgeError, ErrorType

ComputeDeviceType = Literal["NONE", "CUDA", "OPTIX", "HIP", "ONEAPI", "METAL"]
ViewRotateMethod = Literal["TURNTABLE", "TRACKBALL"]


class ConfigurePreferencesParams(BaseModel):
    compute_device_type: Optional[ComputeDeviceType] = None
    use_cpu_with_gpu: Optional[bool] = None
    undo_steps: Optional[int] = None
    undo_memory_limit_mb: Optional[int] = None
    autosave_interval_minutes: Optional[int] = None
    view_rotate_method: Optional[ViewRotateMethod] = None
    save_user_preferences: bool = False


class GetSystemInfoParams(BaseModel):
    pass


def register_preference_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="configure_preferences",
        description="Configure Blender User Preferences (Cycles compute devices like CUDA/OptiX/Metal/HIP, undo memory/steps, autosave interval, view rotation method) with optional disk persistence.",
    )
    async def configure_preferences(
        compute_device_type: Optional[ComputeDeviceType] = None,
        use_cpu_with_gpu: Optional[bool] = None,
        undo_steps: Optional[int] = None,
        undo_memory_limit_mb: Optional[int] = None,
        autosave_interval_minutes: Optional[int] = None,
        view_rotate_method: Optional[ViewRotateMethod] = None,
        save_user_preferences: bool = False,
    ) -> dict:
        params = ConfigurePreferencesParams(
            compute_device_type=compute_device_type,
            use_cpu_with_gpu=use_cpu_with_gpu,
            undo_steps=undo_steps,
            undo_memory_limit_mb=undo_memory_limit_mb,
            autosave_interval_minutes=autosave_interval_minutes,
            view_rotate_method=view_rotate_method,
            save_user_preferences=save_user_preferences,
        )
        result = await bridge.send_request("configure_preferences", params.model_dump())
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "configure_preferences failed"))
        return result

    @mcp.tool(
        name="get_system_info",
        description="Retrieve comprehensive system and hardware info: Blender version, OS, Python runtime, GPU devices (CUDA/OptiX/HIP/Metal), CPU threads, memory, and active workspaces.",
    )
    async def get_system_info() -> dict:
        result = await bridge.send_request("get_system_info", {})
        if not result.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", "get_system_info failed"))
        return result

    return configure_preferences, get_system_info
