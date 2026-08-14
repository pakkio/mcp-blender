import bmesh
import bpy
from mathutils import Vector

from .base import ToolBase


class AdvancedMeshEditTool(ToolBase):
    name = "advanced_mesh_edit"
    description = "Advanced direct mesh editing: Bridge Edge Loops, Bisect plane cuts with cap fill, Extrude along normals / individual faces, Edge Crease, Bevel Weights, Separate by loose parts/materials, and Join meshes."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        op = params.get("operation", "BRIDGE_EDGE_LOOPS").upper()

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        if op == "JOIN_OBJECTS":
            other_names = params.get("other_objects") or []
            joined = 0
            for name in other_names:
                o = bpy.data.objects.get(name)
                if o and o.type == "MESH":
                    o.select_set(True)
                    joined += 1
            if joined > 0:
                bpy.ops.object.join()
            return {"success": True, "message": f"Joined {joined} object(s) into '{obj.name}'", "active_object": obj.name}

        elif op == "SEPARATE_BY_LOOSE_PARTS":
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.separate(type="LOOSE")
            bpy.ops.object.mode_set(mode="OBJECT")
            return {"success": True, "message": f"Separated '{obj.name}' by loose parts"}

        elif op == "SEPARATE_BY_MATERIAL":
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.mesh.separate(type="MATERIAL")
            bpy.ops.object.mode_set(mode="OBJECT")
            return {"success": True, "message": f"Separated '{obj.name}' by materials"}

        # BMesh operations
        bm = bmesh.new()
        bm.from_mesh(obj.data)

        try:
            if op == "BISECT":
                plane_co = Vector(params.get("plane_co", [0, 0, 0]))
                plane_no = Vector(params.get("plane_no", [0, 0, 1]))
                clear_inner = bool(params.get("clear_inner", False))
                clear_outer = bool(params.get("clear_outer", False))
                use_fill = bool(params.get("use_fill", True))

                geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
                res = bmesh.ops.bisect_plane(
                    bm,
                    geom=geom,
                    plane_co=plane_co,
                    plane_no=plane_no,
                    clear_inner=clear_inner,
                    clear_outer=clear_outer,
                    use_snap_center=False,
                )
                if use_fill and (clear_inner or clear_outer):
                    cut_edges = [e for e in res["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
                    if cut_edges:
                        bmesh.ops.edgeloop_fill(bm, edges=cut_edges)

            elif op == "BRIDGE_EDGE_LOOPS":
                cuts = int(params.get("number_cuts", 0))
                # Select boundary loops or all open edges
                open_edges = [e for e in bm.edges if len(e.link_faces) == 1]
                if open_edges:
                    bmesh.ops.bridge_loops(bm, edges=open_edges, number_cuts=cuts)
                else:
                    return {"success": False, "message": "No open/boundary edge loops found to bridge"}

            elif op in ("EXTRUDE_ALONG_NORMALS", "EXTRUDE_INDIVIDUAL_FACES"):
                offset = float(params.get("offset", 0.2))
                faces = [f for f in bm.faces if f.select] or bm.faces[:]
                if op == "EXTRUDE_INDIVIDUAL_FACES":
                    res = bmesh.ops.extrude_discrete_faces(bm, faces=faces)
                    for f in res["faces"]:
                        for v in f.verts:
                            v.co += f.normal * offset
                else:
                    res = bmesh.ops.extrude_face_region(bm, geom=faces)
                    ext_verts = [v for v in res["geom"] if isinstance(v, bmesh.types.BMVert)]
                    for v in ext_verts:
                        v.co += v.normal * offset

            elif op == "SET_EDGE_CREASE":
                crease_val = float(params.get("crease_value", 1.0))
                crease_layer = bm.edges.layers.crease.verify()
                for e in bm.edges:
                    e[crease_layer] = crease_val

            elif op == "SET_BEVEL_WEIGHT":
                bw_val = float(params.get("weight_value", 1.0))
                bw_layer = bm.edges.layers.bevel_weight.verify()
                for e in bm.edges:
                    e[bw_layer] = bw_val

            else:
                return {"success": False, "message": f"Unsupported operation '{op}'"}

            bm.to_mesh(obj.data)
            obj.data.update()
        finally:
            bm.free()

        return {
            "success": True,
            "message": f"Successfully performed '{op}' on '{obj.name}'",
            "object_name": obj.name,
            "operation": op,
            "vertices_count": len(obj.data.vertices),
            "faces_count": len(obj.data.polygons),
        }


class ManipulateOriginCursorTool(ToolBase):
    name = "manipulate_origin_cursor"
    description = "Manipulate 3D Cursor and object origin points (Origin to Geometry, Origin to Cursor, Origin to Bottom bounding box for floor snapping, Origin to Center of Mass, Cursor to Selected, Set Cursor/Origin Location)."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        action = params.get("action", "ORIGIN_TO_GEOMETRY").upper()
        location = params.get("location")

        scene = bpy.context.scene
        cursor = scene.cursor

        if action == "CURSOR_TO_ORIGIN":
            cursor.location = (0.0, 0.0, 0.0)
            cursor.rotation_euler = (0.0, 0.0, 0.0)
            return {"success": True, "message": "Reset 3D Cursor to World Origin", "cursor_location": [0.0, 0.0, 0.0]}

        elif action == "SET_CURSOR_LOCATION":
            if not location:
                return {"success": False, "message": "'location' [x, y, z] is required"}
            cursor.location = tuple(location)
            return {"success": True, "message": f"Set 3D Cursor location to {location}", "cursor_location": list(cursor.location)}

        # Object actions
        if not object_name:
            active = bpy.context.active_object
            if not active:
                return {"success": False, "message": "No active object and 'object_name' was not provided"}
            obj = active
        else:
            obj = bpy.data.objects.get(object_name)
            if not obj:
                return {"success": False, "message": f"Object '{object_name}' not found"}

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        if action == "ORIGIN_TO_GEOMETRY":
            bpy.ops.object.origin_set(type="ORIGIN_GEOMETRY", center="MEDIAN")

        elif action == "ORIGIN_TO_CURSOR":
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR")

        elif action == "ORIGIN_TO_CENTER_OF_MASS":
            bpy.ops.object.origin_set(type="ORIGIN_CENTER_OF_MASS")

        elif action == "CURSOR_TO_SELECTED":
            cursor.location = obj.location

        elif action == "ORIGIN_TO_BOTTOM":
            # Compute lowest Z in local bounding box and shift origin
            bbox = [Vector(b) for b in obj.bound_box]
            min_z = min(b.z for b in bbox)
            center_x = sum(b.x for b in bbox) / 8.0
            center_y = sum(b.y for b in bbox) / 8.0

            cursor_orig = cursor.location.copy()
            # Move cursor to bottom center in world coordinates
            bottom_world = obj.matrix_world @ Vector((center_x, center_y, min_z))
            cursor.location = bottom_world
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
            cursor.location = cursor_orig

        elif action == "SET_ORIGIN_LOCATION":
            if not location:
                return {"success": False, "message": "'location' is required for SET_ORIGIN_LOCATION"}
            cursor_orig = cursor.location.copy()
            cursor.location = tuple(location)
            bpy.ops.object.origin_set(type="ORIGIN_CURSOR")
            cursor.location = cursor_orig

        else:
            return {"success": False, "message": f"Unknown action '{action}'"}

        return {
            "success": True,
            "message": f"Executed '{action}' on '{obj.name}'",
            "object_name": obj.name,
            "new_origin_location": list(obj.location),
            "cursor_location": list(cursor.location),
        }
