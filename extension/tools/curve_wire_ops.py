import math
import bpy
from mathutils import Vector

from .base import ToolBase


class CreateCurveCableTool(ToolBase):
    name = "create_curve_cable"
    description = "Procedurally create electrical cables, wires, pipes, or neon tubes between two points with gravity sag, bevel depth, and resolution."

    def execute(self, params: dict) -> dict:
        name = params.get("name", "CableWire")
        start_point = params.get("start_point", [-2.0, 0.0, 3.0])
        end_point = params.get("end_point", [2.0, 0.0, 3.0])
        sag = float(params.get("sag", 0.8))
        radius = float(params.get("radius", 0.04))
        resolution = int(params.get("resolution", 12))
        curve_type = params.get("curve_type", "BEZIER").upper()

        p0 = Vector(start_point)
        p1 = Vector(end_point)
        mid = (p0 + p1) / 2.0
        mid.z -= sag

        curve_data = bpy.data.curves.new(name=f"{name}_Data", type="CURVE")
        curve_data.dimensions = "3D"
        curve_data.bevel_depth = radius
        curve_data.bevel_resolution = 4
        curve_data.resolution_u = resolution

        spline = curve_data.splines.new(type="BEZIER")
        spline.bezier_points.add(2)  # 3 points total: start, mid, end

        # Start point
        bp0 = spline.bezier_points[0]
        bp0.co = p0
        bp0.handle_left = p0 + Vector((0, 0, -sag * 0.5))
        bp0.handle_right = p0 + (mid - p0) * 0.5

        # Mid point
        bp1 = spline.bezier_points[1]
        bp1.co = mid
        bp1.handle_left = mid - (p1 - p0) * 0.25
        bp1.handle_right = mid + (p1 - p0) * 0.25

        # End point
        bp2 = spline.bezier_points[2]
        bp2.co = p1
        bp2.handle_left = p1 - (p1 - mid) * 0.5
        bp2.handle_right = p1 + Vector((0, 0, -sag * 0.5))

        curve_obj = bpy.data.objects.new(name, curve_data)
        bpy.context.scene.collection.objects.link(curve_obj)

        return {
            "success": True,
            "message": f"Created procedural cable '{curve_obj.name}' between {start_point} and {end_point} (sag: {sag}m)",
            "name": curve_obj.name,
            "radius": radius,
            "sag": sag,
        }


class ConvertMeshToCurveTool(ToolBase):
    name = "convert_mesh_to_curve"
    description = "Convert mesh edges into 3D curves with automatic bevel depth for neon tubing, railings, or wireframes."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name") or params.get("name")
        bevel_depth = float(params.get("bevel_depth", 0.03))
        extrude = float(params.get("extrude", 0.0))

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.convert(target="CURVE")

        if obj.type == "CURVE":
            obj.data.dimensions = "3D"
            obj.data.bevel_depth = bevel_depth
            obj.data.extrude = extrude

        return {
            "success": True,
            "message": f"Converted mesh '{object_name}' to 3D Curve (Bevel: {bevel_depth})",
            "name": obj.name,
            "bevel_depth": bevel_depth,
        }


class EditCurvePointsTool(ToolBase):
    name = "edit_curve_points"
    description = "Add or modify control points, handles, radius, and tilt on Bezier and Poly splines."

    def execute(self, params: dict) -> dict:
        curve_name = params.get("curve_name") or params.get("name")
        points = params.get("points", [])
        bevel_depth = params.get("bevel_depth")

        if not curve_name:
            return {"success": False, "message": "'curve_name' is required"}

        obj = bpy.data.objects.get(curve_name)
        if not obj or obj.type != "CURVE":
            return {"success": False, "message": f"Curve object '{curve_name}' not found"}

        curve_data = obj.data
        if bevel_depth is not None:
            curve_data.bevel_depth = float(bevel_depth)

        if points:
            curve_data.splines.clear()
            spline = curve_data.splines.new(type="BEZIER")
            spline.bezier_points.add(len(points) - 1)
            for idx, pt in enumerate(points):
                bp = spline.bezier_points[idx]
                co = pt.get("co", [0, 0, 0])
                bp.co = tuple(co)
                bp.handle_left = tuple(pt.get("handle_left", [co[0] - 0.5, co[1], co[2]]))
                bp.handle_right = tuple(pt.get("handle_right", [co[0] + 0.5, co[1], co[2]]))
                if "radius" in pt:
                    bp.radius = float(pt["radius"])
                if "tilt" in pt:
                    bp.tilt = float(pt["tilt"])

        return {
            "success": True,
            "message": f"Updated curve '{curve_name}' points and splines",
            "curve_name": curve_name,
            "points_count": len(points) if points else len(curve_data.splines[0].bezier_points) if curve_data.splines else 0,
        }
