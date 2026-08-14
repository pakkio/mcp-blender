import math
import bpy
from mathutils import Vector

from .base import ToolBase


class ConfigureViewportDisplayTool(ToolBase):
    name = "configure_viewport_display"
    description = "Control 3D Viewport shading mode (SOLID, MATERIAL, RENDERED, WIREFRAME), studio lighting/matcaps, cavity/shadows, and overlays (face orientation normal check, wireframe, scene statistics)."

    def execute(self, params: dict) -> dict:
        shading_type = params.get("shading_type")
        color_type = params.get("color_type")
        show_cavity = params.get("show_cavity")
        show_shadows = params.get("show_shadows")
        show_wireframe = params.get("show_wireframe")
        show_face_orientation = params.get("show_face_orientation")
        show_stats = params.get("show_stats")
        matcap_name = params.get("matcap_name")

        updated = {}
        for window in bpy.context.window_manager.windows:
            screen = window.screen
            for area in screen.areas:
                if area.type == "VIEW_3D":
                    for space in area.spaces:
                        if space.type == "VIEW_3D":
                            shading = space.shading
                            overlay = space.overlay

                            if shading_type:
                                shading.type = shading_type.upper()
                                updated["shading_type"] = shading.type

                            if color_type and hasattr(shading, "color_type"):
                                shading.color_type = color_type.upper()
                                updated["color_type"] = shading.color_type

                            if show_cavity is not None and hasattr(shading, "show_cavity"):
                                shading.show_cavity = bool(show_cavity)
                                updated["show_cavity"] = shading.show_cavity

                            if show_shadows is not None and hasattr(shading, "show_shadows"):
                                shading.show_shadows = bool(show_shadows)
                                updated["show_shadows"] = shading.show_shadows

                            if matcap_name and hasattr(shading, "studio_light"):
                                shading.light = "MATCAP"
                                shading.studio_light = matcap_name

                            # Overlays
                            if show_wireframe is not None and hasattr(overlay, "show_wireframes"):
                                overlay.show_wireframes = bool(show_wireframe)
                                updated["show_wireframe"] = overlay.show_wireframes

                            if show_face_orientation is not None and hasattr(overlay, "show_face_orientation"):
                                overlay.show_face_orientation = bool(show_face_orientation)
                                updated["show_face_orientation"] = overlay.show_face_orientation

                            if show_stats is not None and hasattr(overlay, "show_stats"):
                                overlay.show_stats = bool(show_stats)
                                updated["show_stats"] = overlay.show_stats

        return {
            "success": True,
            "message": f"Updated viewport display: {', '.join(updated.keys()) if updated else 'no changes'}",
            "updated_settings": updated,
        }


class PurgeOrphansAndCleanupTool(ToolBase):
    name = "purge_orphans_and_cleanup"
    description = "Purge unused orphan datablocks (materials, meshes, textures, node groups, actions) and manage packed file resources."

    def execute(self, params: dict) -> dict:
        action = params.get("action", "PURGE_ORPHANS").upper()
        num_passes = int(params.get("num_passes", 3))

        if action == "PURGE_ORPHANS":
            purged = 0
            for _ in range(max(1, num_passes)):
                res = bpy.ops.outliner.orphans_purge(
                    do_local_ids=True,
                    do_linked_ids=True,
                    do_recursive=True,
                )
                if "CANCELLED" in res:
                    break
                purged += 1

            return {
                "success": True,
                "message": f"Executed orphan data purge ({purged} passes completed)",
                "action": action,
            }

        elif action == "PACK_ALL_LIBRARIES":
            try:
                bpy.ops.file.pack_all()
                return {"success": True, "message": "Packed all external image/texture libraries into the .blend file"}
            except Exception as exc:
                return {"success": False, "message": f"Failed to pack files: {exc}"}

        elif action == "UNPACK_ALL_LIBRARIES":
            try:
                bpy.ops.file.unpack_all(method="USE_LOCAL")
                return {"success": True, "message": "Unpacked all external file resources locally"}
            except Exception as exc:
                return {"success": False, "message": f"Failed to unpack files: {exc}"}

        else:
            return {"success": False, "message": f"Unknown action '{action}'"}


class AlignDistributeObjectsTool(ToolBase):
    name = "align_distribute_objects"
    description = "Align, distribute in 3D grid/linear patterns, or snap objects down to ground level (Z=0)."

    def execute(self, params: dict) -> dict:
        object_names = params.get("object_names") or []
        action = params.get("action", "ALIGN_X").upper()
        spacing = float(params.get("spacing", 2.0))
        cols = int(params.get("grid_columns", 3))

        if not object_names:
            # Fallback to selected objects
            objs = [o for o in bpy.context.selected_objects]
        else:
            objs = [bpy.data.objects.get(name) for name in object_names if bpy.data.objects.get(name)]

        if not objs:
            return {"success": False, "message": "No valid objects found to align/distribute"}

        if action == "SNAP_TO_GROUND":
            # Set each object's lowest vertex / bounding box coordinate to Z = 0
            for obj in objs:
                bbox = [obj.matrix_world @ Vector(b) for b in obj.bound_box]
                min_z = min(b.z for b in bbox)
                obj.location.z -= min_z
            return {"success": True, "message": f"Snapped {len(objs)} objects to ground (Z=0)"}

        elif action == "ALIGN_X":
            ref_x = objs[0].location.x
            for o in objs[1:]:
                o.location.x = ref_x
        elif action == "ALIGN_Y":
            ref_y = objs[0].location.y
            for o in objs[1:]:
                o.location.y = ref_y
        elif action == "ALIGN_Z":
            ref_z = objs[0].location.z
            for o in objs[1:]:
                o.location.z = ref_z
        elif action == "ALIGN_CENTERS":
            ref_loc = objs[0].location.copy()
            for o in objs[1:]:
                o.location = ref_loc.copy()

        elif action == "DISTRIBUTE_LINEAR":
            axis = params.get("axis", "X").upper()
            for i, o in enumerate(objs):
                if axis == "X":
                    o.location.x = i * spacing
                elif axis == "Y":
                    o.location.y = i * spacing
                else:
                    o.location.z = i * spacing

        elif action == "DISTRIBUTE_GRID":
            cols = max(1, cols)
            for i, o in enumerate(objs):
                row = i // cols
                col = i % cols
                o.location.x = col * spacing
                o.location.y = row * spacing

        return {
            "success": True,
            "message": f"Successfully performed '{action}' on {len(objs)} objects",
            "action": action,
            "objects_count": len(objs),
        }
