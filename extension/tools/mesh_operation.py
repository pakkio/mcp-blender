import bmesh
import bpy

from .base import ToolBase


class MeshOperationTool(ToolBase):
    name = "mesh_operation"
    description = "Perform mesh-level operations like smooth/flat shading, subdivision, normal recalculation, merge vertices, join, or origin adjustment."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        operation = (params.get("operation") or "").upper()

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}
        if not operation:
            return {"success": False, "message": "'operation' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        # Ensure object mode and selection
        if bpy.context.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")

        prev_active = bpy.context.active_object
        prev_selected = [o for o in bpy.context.selected_objects]

        try:
            bpy.ops.object.select_all(action="DESELECT")
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

            if operation == "SHADE_SMOOTH":
                bpy.ops.object.shade_smooth()
            elif operation == "SHADE_FLAT":
                bpy.ops.object.shade_flat()
            elif operation == "AUTO_SMOOTH":
                # In Blender 4.1+, auto-smooth is typically done via modifier or mesh attribute
                # In Blender 4.0 and earlier: mesh.use_auto_smooth = True
                if hasattr(obj.data, "use_auto_smooth"):
                    obj.data.use_auto_smooth = True
                else:
                    try:
                        bpy.ops.object.shade_smooth_by_angle()
                    except Exception:
                        bpy.ops.object.shade_smooth()
            elif operation == "SET_ORIGIN_TO_GEOMETRY":
                bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")
            elif operation == "SET_ORIGIN_TO_CURSOR":
                bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
            elif operation == "SET_ORIGIN_TO_MASS_CENTER":
                bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS")
            elif operation == "CONVERT_TO_MESH":
                bpy.ops.object.convert(target="MESH")
            elif operation == "JOIN_SELECTED":
                join_targets = params.get("join_with_objects") or []
                for j_name in join_targets:
                    j_obj = bpy.data.objects.get(j_name)
                    if j_obj:
                        j_obj.select_set(True)
                bpy.ops.object.join()
            elif operation in (
                "SUBDIVIDE",
                "TRIANGULATE",
                "FLIP_NORMALS",
                "RECALCULATE_NORMALS",
                "MERGE_BY_DISTANCE",
                "CONVEX_HULL",
                "DISSOLVE_DEGENERATE",
                "BEVEL",
                "INSET_FACES",
                "SYMMETRIZE",
            ):
                if obj.type != "MESH" or not obj.data:
                    return {"success": False, "message": f"Object '{obj.name}' is not a mesh"}

                bm = bmesh.new()
                bm.from_mesh(obj.data)

                if operation == "SUBDIVIDE":
                    cuts = params.get("subdivision_cuts", 1)
                    bmesh.ops.subdivide_edges(bm, edges=bm.edges, cuts=cuts, use_grid_fill=True)
                elif operation == "TRIANGULATE":
                    bmesh.ops.triangulate(bm, faces=bm.faces)
                elif operation == "FLIP_NORMALS":
                    for f in bm.faces:
                        f.normal_flip()
                elif operation == "RECALCULATE_NORMALS":
                    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
                elif operation == "MERGE_BY_DISTANCE":
                    dist = params.get("merge_distance", 0.0001)
                    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
                elif operation == "CONVEX_HULL":
                    bmesh.ops.convex_hull(bm, input=bm.verts)
                elif operation == "DISSOLVE_DEGENERATE":
                    dist = params.get("merge_distance", 0.0001)
                    bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges)
                elif operation == "BEVEL":
                    offset = float(params.get("bevel_offset", 0.1))
                    segments = int(params.get("bevel_segments", 2))
                    bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=offset, segments=segments, affect="EDGES")
                elif operation == "INSET_FACES":
                    thickness = float(params.get("inset_thickness", 0.05))
                    depth = float(params.get("inset_depth", 0.0))
                    bmesh.ops.inset_individual(bm, faces=bm.faces, thickness=thickness, depth=depth)
                elif operation == "SYMMETRIZE":
                    direction = params.get("symmetrize_direction", "-X")
                    axis_map = {"-X": 0, "+X": 0, "-Y": 1, "+Y": 1, "-Z": 2, "+Z": 2}
                    axis = axis_map.get(direction.upper(), 0)
                    bmesh.ops.symmetrize(bm, input=list(bm.verts) + list(bm.edges) + list(bm.faces), direction=direction.upper())

                bm.to_mesh(obj.data)
                bm.free()
                obj.data.update()
            elif operation == "SEPARATE_BY_LOOSE_PARTS":
                bpy.ops.mesh.separate(type="LOOSE")
            else:
                return {"success": False, "message": f"Unsupported operation '{operation}'"}

        finally:
            bpy.ops.object.select_all(action="DESELECT")
            for o in prev_selected:
                if o.name in bpy.data.objects:
                    o.select_set(True)
            if prev_active and prev_active.name in bpy.data.objects:
                bpy.context.view_layer.objects.active = prev_active

        # Return updated mesh stats if mesh
        stats = {}
        if obj.type == "MESH" and obj.data:
            stats = {
                "vertices": len(obj.data.vertices),
                "edges": len(obj.data.edges),
                "faces": len(obj.data.polygons),
            }

        return {
            "success": True,
            "message": f"Successfully performed '{operation}' on '{obj.name}'",
            "object_name": obj.name,
            "operation": operation,
            "mesh_stats": stats,
        }
