import os
import platform
import sys
import bpy

from .base import ToolBase


def _process_memory_mb():
    """Best-effort resident memory of this Blender process, in MB, or None
    if unavailable. Uses only the stdlib so it works without psutil."""
    try:
        if platform.system() == "Windows":
            import ctypes
            from ctypes import wintypes

            class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
                _fields_ = [
                    ("cb", wintypes.DWORD),
                    ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t),
                    ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t),
                ]

            counters = PROCESS_MEMORY_COUNTERS()
            counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
            handle = ctypes.windll.kernel32.GetCurrentProcess()
            if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return round(counters.WorkingSetSize / (1024 * 1024), 2)
            return None
        else:
            import resource

            ru_maxrss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            # ru_maxrss is KB on Linux, bytes on macOS
            divisor = 1024 if platform.system() == "Linux" else (1024 * 1024)
            return round(ru_maxrss / divisor, 2)
    except Exception:
        return None


class ConfigurePreferencesTool(ToolBase):
    name = "configure_preferences"
    description = "Configure Blender User Preferences (Cycles compute devices like CUDA/OptiX/Metal/HIP, undo memory/steps, autosave interval, view rotation method) with optional disk persistence."

    def execute(self, params: dict) -> dict:
        compute_device_type = params.get("compute_device_type")
        use_cpu_with_gpu = params.get("use_cpu_with_gpu")
        undo_steps = params.get("undo_steps")
        undo_memory_limit_mb = params.get("undo_memory_limit_mb")
        autosave_interval = params.get("autosave_interval_minutes")
        view_rotate_method = params.get("view_rotate_method")
        save_prefs = bool(params.get("save_user_preferences", False))

        prefs = bpy.context.preferences
        updated = {}

        # Configure Cycles Compute Device (CUDA, OPTIX, HIP, ONEAPI, METAL)
        if compute_device_type is not None:
            cprefs = prefs.addons.get("cycles")
            if cprefs and hasattr(cprefs, "preferences"):
                cp = cprefs.preferences
                target_type = compute_device_type.upper()
                if hasattr(cp, "compute_device_type"):
                    cp.compute_device_type = target_type
                    # Refresh devices
                    if hasattr(cp, "get_devices"):
                        cp.get_devices()
                    if hasattr(cp, "devices"):
                        for d in cp.devices:
                            if target_type == "NONE":
                                d.use = (d.type == "CPU")
                            else:
                                if d.type == "CPU":
                                    d.use = bool(use_cpu_with_gpu)
                                else:
                                    d.use = True
                    updated["compute_device_type"] = target_type
                    updated["use_cpu_with_gpu"] = use_cpu_with_gpu

        # Undo Settings
        if undo_steps is not None and hasattr(prefs.edit, "undo_steps"):
            prefs.edit.undo_steps = max(1, min(256, int(undo_steps)))
            updated["undo_steps"] = prefs.edit.undo_steps

        if undo_memory_limit_mb is not None and hasattr(prefs.edit, "undo_memory_limit"):
            prefs.edit.undo_memory_limit = max(0, int(undo_memory_limit_mb))
            updated["undo_memory_limit_mb"] = prefs.edit.undo_memory_limit

        # Autosave
        if autosave_interval is not None and hasattr(prefs.filepaths, "save_version"):
            if hasattr(prefs.filepaths, "auto_save_time"):
                prefs.filepaths.auto_save_time = max(1, int(autosave_interval))
                updated["autosave_interval_minutes"] = prefs.filepaths.auto_save_time

        # Viewport Rotation Method
        if view_rotate_method is not None and hasattr(prefs.inputs, "view_rotate_method"):
            prefs.inputs.view_rotate_method = view_rotate_method.upper()
            updated["view_rotate_method"] = prefs.inputs.view_rotate_method

        if save_prefs:
            try:
                bpy.ops.wm.save_userpref()
                updated["saved_to_disk"] = True
            except Exception as exc:
                updated["saved_to_disk"] = f"Failed: {exc}"

        return {
            "success": True,
            "message": f"Updated preferences: {', '.join(updated.keys()) if updated else 'no changes'}",
            "updated_preferences": updated,
        }


class GetSystemInfoTool(ToolBase):
    name = "get_system_info"
    description = "Retrieve comprehensive system and hardware info: Blender version, OS, Python runtime, GPU devices (CUDA/OptiX/HIP/Metal), CPU threads, memory, and active workspaces."

    def execute(self, params: dict) -> dict:
        prefs = bpy.context.preferences

        # Compute devices
        devices = []
        cprefs = prefs.addons.get("cycles")
        if cprefs and hasattr(cprefs, "preferences"):
            cp = cprefs.preferences
            if hasattr(cp, "get_devices"):
                try:
                    cp.get_devices()
                except Exception:
                    pass
            if hasattr(cp, "devices"):
                for d in cp.devices:
                    devices.append({
                        "name": d.name,
                        "type": d.type,
                        "use": getattr(d, "use", False),
                    })

        return {
            "success": True,
            "blender_version": bpy.app.version_string,
            "blender_binary": bpy.app.binary_path,
            "os_platform": platform.platform(),
            "os_system": platform.system(),
            "os_release": platform.release(),
            "python_version": sys.version.split()[0],
            "cpu_threads": os.cpu_count(),
            "process_memory_mb": _process_memory_mb(),
            "compute_devices": devices,
            "active_workspace": bpy.context.workspace.name if hasattr(bpy.context, "workspace") else None,
            "workspaces": [w.name for w in bpy.data.workspaces],
            "undo_steps": getattr(prefs.edit, "undo_steps", None),
            "autosave_minutes": getattr(prefs.filepaths, "auto_save_time", None),
        }
