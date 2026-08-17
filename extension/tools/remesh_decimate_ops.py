import math
import bpy

from .base import ToolBase


class DecimateMeshTool(ToolBase):
    name = "decimate_mesh"
    description = "Decimate/reduce polygon count of a mesh using COLLAPSE (ratio), UNSUBDIVIDE (iterations), or PLANAR (angle limit) algorithms."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        mode = params.get("mode", "COLLAPSE").upper()
        ratio = float(params.get("ratio", 0.5))
        iterations = int(params.get("iterations", 2))
        angle_limit = float(params.get("angle_limit", 5.0))
        use_symmetry = bool(params.get("use_symmetry", False))
        symmetry_axis = params.get("symmetry_axis", "X").upper()
        apply_immediately = bool(params.get("apply_immediately", True))

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        orig_verts = len(obj.data.vertices)
        orig_faces = len(obj.data.polygons)

        mod = obj.modifiers.new(name="Decimate_Auto", type="DECIMATE")
        mod.decimate_type = mode

        if mode == "COLLAPSE":
            mod.ratio = max(0.0001, min(1.0, ratio))
            mod.use_symmetry = use_symmetry
            if hasattr(mod, "symmetry_axis"):
                mod.symmetry_axis = symmetry_axis
        elif mode == "UNSUBDIV":
            mod.iterations = max(1, iterations)
        elif mode == "PLANAR":
            mod.angle_limit = math.radians(angle_limit)

        if apply_immediately:
            bpy.context.view_layer.objects.active = obj
            # Blender refuses to apply a modifier to a mesh that carries shape
            # keys (a common situation on imported rigged/character assets).
            # Drop them on the decimated result -- morph targets are generally
            # meaningless on a collapsed mesh anyway.
            if obj.data.shape_keys:
                obj.shape_key_clear()
            bpy.ops.object.modifier_apply(modifier=mod.name)

        new_verts = len(obj.data.vertices) if apply_immediately else None
        new_faces = len(obj.data.polygons) if apply_immediately else None

        return {
            "success": True,
            "message": f"Decimated '{object_name}' using {mode} mode",
            "object_name": object_name,
            "mode": mode,
            "applied": apply_immediately,
            "original_vertices": orig_verts,
            "original_faces": orig_faces,
            "result_vertices": new_verts,
            "result_faces": new_faces,
        }


class RemeshMeshTool(ToolBase):
    name = "remesh_mesh"
    description = "Remesh geometry using modern VOXEL remesher or modifier-based remeshing (SHARP, SMOOTH, BLOCKS)."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        mode = params.get("mode", "VOXEL").upper()
        voxel_size = float(params.get("voxel_size", 0.05))
        adaptivity = float(params.get("adaptivity", 0.0))
        octree_depth = int(params.get("octree_depth", 4))
        scale = float(params.get("scale", 0.9))
        smooth_shading = bool(params.get("smooth_shading", True))
        apply_immediately = bool(params.get("apply_immediately", True))

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        orig_verts = len(obj.data.vertices)
        orig_faces = len(obj.data.polygons)

        bpy.context.view_layer.objects.active = obj

        if mode == "VOXEL":
            # Use Blender's native mesh voxel remesh
            if hasattr(obj.data, "remesh_voxel_size"):
                obj.data.remesh_voxel_size = max(0.001, voxel_size)
            if hasattr(obj.data, "remesh_voxel_adaptivity"):
                obj.data.remesh_voxel_adaptivity = max(0.0, adaptivity)
            if hasattr(obj.data, "use_remesh_smooth_normals"):
                obj.data.use_remesh_smooth_normals = smooth_shading
            bpy.ops.object.voxel_remesh()
            if smooth_shading:
                try:
                    bpy.ops.object.shade_smooth()
                except Exception:
                    pass
        else:
            # Modifier remesh (SHARP, SMOOTH, BLOCKS)
            mod = obj.modifiers.new(name="Remesh_Auto", type="REMESH")
            mod.mode = mode
            if hasattr(mod, "octree_depth"):
                mod.octree_depth = octree_depth
            if hasattr(mod, "scale"):
                mod.scale = scale
            if hasattr(mod, "use_smooth_shade"):
                mod.use_smooth_shade = smooth_shading

            if apply_immediately:
                if obj.data.shape_keys:
                    obj.shape_key_clear()
                bpy.ops.object.modifier_apply(modifier=mod.name)

        new_verts = len(obj.data.vertices)
        new_faces = len(obj.data.polygons)

        return {
            "success": True,
            "message": f"Remeshed '{object_name}' using {mode} mode",
            "object_name": object_name,
            "mode": mode,
            "original_vertices": orig_verts,
            "original_faces": orig_faces,
            "result_vertices": new_verts,
            "result_faces": new_faces,
        }
