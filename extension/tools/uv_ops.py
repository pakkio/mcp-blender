import math
import bpy

from .base import ToolBase


class UVUnwrapTool(ToolBase):
    name = "uv_unwrap"
    description = "Unwrap UV coordinates on an object using SMART_PROJECT, LIGHTMAP_PACK, CUBE_PROJECT, SPHERE_PROJECT, CYLINDER_PROJECT, PROJECT_FROM_VIEW, UNWRAP (Angle/Conformal), or PACK_ISLANDS."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        method = params.get("method", "SMART_PROJECT").upper()
        angle_limit = float(params.get("angle_limit", 66.0))
        island_margin = float(params.get("island_margin", 0.02))
        correct_aspect = bool(params.get("correct_aspect", True))
        scale_to_bounds = bool(params.get("scale_to_bounds", False))
        cube_size = float(params.get("cube_size", 1.0))
        pack_margin = float(params.get("pack_islands_margin", 0.02))

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        # Ensure object is active and in EDIT mode
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")

        try:
            if method == "SMART_PROJECT":
                bpy.ops.uv.smart_project(
                    angle_limit=math.radians(angle_limit),
                    island_margin=island_margin,
                    correct_aspect=correct_aspect,
                    scale_to_bounds=scale_to_bounds,
                )
            elif method == "LIGHTMAP_PACK":
                bpy.ops.uv.lightmap_pack(
                    PREF_MARGIN_DIV=island_margin,
                )
            elif method == "CUBE_PROJECT":
                bpy.ops.uv.cube_project(
                    cube_size=cube_size,
                    correct_aspect=correct_aspect,
                    clip_to_bounds=scale_to_bounds,
                )
            elif method == "CYLINDER_PROJECT":
                bpy.ops.uv.cylinder_project(
                    correct_aspect=correct_aspect,
                    clip_to_bounds=scale_to_bounds,
                )
            elif method == "SPHERE_PROJECT":
                bpy.ops.uv.sphere_project(
                    correct_aspect=correct_aspect,
                    clip_to_bounds=scale_to_bounds,
                )
            elif method == "PROJECT_FROM_VIEW":
                bpy.ops.uv.project_from_view(
                    camera_bounds=True,
                    correct_aspect=correct_aspect,
                    scale_to_bounds=scale_to_bounds,
                )
            elif method == "UNWRAP":
                bpy.ops.uv.unwrap(
                    method="ANGLE_BASED",
                    margin=island_margin,
                    correct_aspect=correct_aspect,
                )
            elif method == "FOLLOW_ACTIVE_QUADS":
                bpy.ops.uv.follow_active_quads()
            elif method == "PACK_ISLANDS":
                bpy.ops.uv.pack_islands(
                    margin=pack_margin,
                    rotate=True,
                )
            else:
                return {
                    "success": False,
                    "message": f"Unknown UV unwrap method '{method}'. Supported: SMART_PROJECT, LIGHTMAP_PACK, CUBE_PROJECT, CYLINDER_PROJECT, SPHERE_PROJECT, PROJECT_FROM_VIEW, UNWRAP, FOLLOW_ACTIVE_QUADS, PACK_ISLANDS",
                }
        finally:
            bpy.ops.object.mode_set(mode="OBJECT")

        uv_layers = [uv.name for uv in obj.data.uv_layers]

        return {
            "success": True,
            "message": f"Successfully performed UV unwrap '{method}' on '{object_name}'",
            "object_name": object_name,
            "method": method,
            "uv_layers": uv_layers,
        }
