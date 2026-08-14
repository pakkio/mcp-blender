import math
import bpy

from .base import ToolBase


class ConfigureSculptModeTool(ToolBase):
    name = "configure_sculpt_mode"
    description = "Enter/exit Sculpt Mode, select sculpting brushes (Draw, Clay, Clay Strips, Crease, Smooth, Flatten, Grab, Snake Hook, Elastic Deform, Pinch, Cloth, Scrape), configure brush radius/strength, symmetry, and dynamic topology (Dyntopo)."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        action = params.get("action", "ENTER").upper()
        brush_type = params.get("brush_type")
        brush_size = params.get("brush_size")
        brush_strength = params.get("brush_strength")
        symmetry_x = params.get("use_symmetry_x")
        symmetry_y = params.get("use_symmetry_y")
        symmetry_z = params.get("use_symmetry_z")
        use_dyntopo = params.get("use_dyntopo")
        dyntopo_detail = params.get("dyntopo_detail")
        dyntopo_detail_type = params.get("dyntopo_detail_type", "RELATIVE").upper()

        if not object_name:
            active = bpy.context.active_object
            if not active or active.type != "MESH":
                return {"success": False, "message": "No active MESH object found and 'object_name' was not specified"}
            obj = active
        else:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != "MESH":
                return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        # Handle Mode Switch
        if action == "EXIT":
            if bpy.context.mode != "OBJECT":
                bpy.ops.object.mode_set(mode="OBJECT")
            return {
                "success": True,
                "message": f"Exited Sculpt Mode for '{obj.name}'",
                "object_name": obj.name,
                "current_mode": bpy.context.mode,
            }

        if bpy.context.mode != "SCULPT":
            bpy.ops.object.mode_set(mode="SCULPT")

        # Configure Brush
        ts = bpy.context.tool_settings.sculpt

        if brush_type:
            tool_id_map = {
                "DRAW": "builtin_brush.Draw",
                "CLAY": "builtin_brush.Clay",
                "CLAY_STRIPS": "builtin_brush.Clay Strips",
                "SMOOTH": "builtin_brush.Smooth",
                "FLATTEN": "builtin_brush.Flatten",
                "GRAB": "builtin_brush.Grab",
                "SNAKE_HOOK": "builtin_brush.Snake Hook",
                "ELASTIC_DEFORM": "builtin_brush.Elastic Deform",
                "PINCH": "builtin_brush.Pinch",
                "CREASE": "builtin_brush.Crease",
                "INFLATE": "builtin_brush.Inflate",
                "BLOB": "builtin_brush.Blob",
                "CLOTH": "builtin_brush.Cloth",
                "DRAW_SHARP": "builtin_brush.Draw Sharp",
                "MASK": "builtin_brush.Mask",
            }
            tool_id = tool_id_map.get(brush_type.upper())
            if tool_id:
                try:
                    bpy.ops.wm.tool_set_by_id(name=tool_id)
                except Exception:
                    pass

        if ts.brush:
            if brush_size is not None:
                try:
                    ts.brush.size = int(brush_size)
                except Exception:
                    pass
            if brush_strength is not None:
                try:
                    ts.brush.strength = max(0.0, min(10.0, float(brush_strength)))
                except Exception:
                    pass
        active_brush_name = ts.brush.name if ts.brush else None

        # Symmetry
        if symmetry_x is not None:
            ts.use_symmetry_x = bool(symmetry_x)
        if symmetry_y is not None:
            ts.use_symmetry_y = bool(symmetry_y)
        if symmetry_z is not None:
            ts.use_symmetry_z = bool(symmetry_z)

        # Dyntopo
        dyntopo_active = False
        if use_dyntopo is not None:
            try:
                if use_dyntopo and not obj.use_dynamic_topology_sculpting:
                    bpy.ops.sculpt.dynamic_topology_toggle()
                elif not use_dyntopo and getattr(obj, "use_dynamic_topology_sculpting", False):
                    bpy.ops.sculpt.dynamic_topology_toggle()
            except Exception:
                pass

        if getattr(obj, "use_dynamic_topology_sculpting", False):
            dyntopo_active = True
            if dyntopo_detail is not None and hasattr(ts, "detail_size"):
                ts.detail_size = float(dyntopo_detail)
            if hasattr(ts, "detail_type_method"):
                ts.detail_type_method = dyntopo_detail_type

        return {
            "success": True,
            "message": f"Configured Sculpt Mode on '{obj.name}' (Brush: {active_brush_name})",
            "object_name": obj.name,
            "current_mode": "SCULPT",
            "active_brush": active_brush_name,
            "brush_size": getattr(ts.brush, "size", None) if ts.brush else None,
            "brush_strength": getattr(ts.brush, "strength", None) if ts.brush else None,
            "symmetry": {
                "x": ts.use_symmetry_x,
                "y": ts.use_symmetry_y,
                "z": ts.use_symmetry_z,
            },
            "dyntopo_active": dyntopo_active,
        }


class ApplySculptFilterTool(ToolBase):
    name = "apply_sculpt_filter"
    description = "Apply full-mesh sculpt deformation filters (SMOOTH, SCALE, INFLATE, SPHERE, RANDOM, RELAX, RELAX_FACE_SETS, SURFACE_SMOOTH, SHARPEN, ENHANCE_DETAILS)."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        filter_type = params.get("filter_type", "SMOOTH").upper()
        strength = float(params.get("strength", 0.5))
        iterations = int(params.get("iterations", 1))
        deform_axis = params.get("deform_axis", "XYZ").upper()

        if not object_name:
            obj = bpy.context.active_object
            if not obj or obj.type != "MESH":
                return {"success": False, "message": "No active MESH object found"}
        else:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != "MESH":
                return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        orig_mode = bpy.context.mode
        if orig_mode != "SCULPT":
            bpy.ops.object.mode_set(mode="SCULPT")

        # deform_axis must be a set in Blender (e.g. {'X', 'Y', 'Z'})
        if isinstance(deform_axis, str):
            if deform_axis.upper() == "XYZ":
                axis_set = {"X", "Y", "Z"}
            else:
                axis_set = {ch.upper() for ch in deform_axis if ch.upper() in ("X", "Y", "Z")} or {"X", "Y", "Z"}
        else:
            axis_set = set(deform_axis)

        try:
            for _ in range(max(1, iterations)):
                bpy.ops.sculpt.mesh_filter(
                    type=filter_type,
                    strength=strength,
                    deform_axis=axis_set,
                )
        finally:
            if orig_mode != "SCULPT":
                bpy.ops.object.mode_set(mode=orig_mode)

        return {
            "success": True,
            "message": f"Applied sculpt filter '{filter_type}' ({iterations}x, strength: {strength}) on '{obj.name}'",
            "object_name": obj.name,
            "filter_type": filter_type,
            "strength": strength,
            "iterations": iterations,
            "deform_axis": deform_axis,
        }


class SculptMaskFaceSetsTool(ToolBase):
    name = "sculpt_mask_facesets"
    description = "Manage sculpt masks and Face Sets (CLEAR_MASK, INVERT_MASK, SMOOTH_MASK, MASK_BY_CAVITY, INIT_FACE_SETS_BY_LOOSE_PARTS, INIT_FACE_SETS_BY_MATERIALS, CREATE_FACE_SET_FROM_MASK)."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        action = params.get("action", "CLEAR_MASK").upper()

        if not object_name:
            obj = bpy.context.active_object
            if not obj or obj.type != "MESH":
                return {"success": False, "message": "No active MESH object found"}
        else:
            obj = bpy.data.objects.get(object_name)
            if not obj or obj.type != "MESH":
                return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        orig_mode = bpy.context.mode
        if orig_mode != "SCULPT":
            bpy.ops.object.mode_set(mode="SCULPT")

        try:
            if action == "CLEAR_MASK":
                bpy.ops.paint.mask_flood_fill(mode="VALUE", value=0.0)
            elif action == "INVERT_MASK":
                bpy.ops.paint.mask_flood_fill(mode="INVERT")
            elif action == "SMOOTH_MASK":
                bpy.ops.paint.mask_flood_fill(mode="SMOOTH")
            elif action == "INIT_FACE_SETS_BY_LOOSE_PARTS":
                bpy.ops.sculpt.face_sets_init(mode="LOOSE_PARTS")
            elif action == "INIT_FACE_SETS_BY_MATERIALS":
                bpy.ops.sculpt.face_sets_init(mode="MATERIALS")
            elif action == "CREATE_FACE_SET_FROM_MASK":
                bpy.ops.sculpt.face_sets_create_from_mask()
            else:
                return {
                    "success": False,
                    "message": f"Unknown action '{action}'. Supported: CLEAR_MASK, INVERT_MASK, SMOOTH_MASK, INIT_FACE_SETS_BY_LOOSE_PARTS, INIT_FACE_SETS_BY_MATERIALS, CREATE_FACE_SET_FROM_MASK",
                }
        finally:
            if orig_mode != "SCULPT":
                bpy.ops.object.mode_set(mode=orig_mode)

        return {
            "success": True,
            "message": f"Executed sculpt mask/face set action '{action}' on '{obj.name}'",
            "object_name": obj.name,
            "action": action,
        }
