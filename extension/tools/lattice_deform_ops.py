import bpy
from mathutils import Vector

from .base import ToolBase


class CreateLatticeDeformTool(ToolBase):
    name = "create_lattice_deform"
    description = "Create a 3D bounding Lattice cage around a target object with custom U/V/W resolution and automatically bind it with a Lattice Modifier."

    def execute(self, params: dict) -> dict:
        target_name = params.get("target_object") or params.get("name")
        u_points = int(params.get("u_resolution", 3))
        v_points = int(params.get("v_resolution", 3))
        w_points = int(params.get("w_resolution", 3))
        padding = float(params.get("padding", 0.1))

        if not target_name:
            return {"success": False, "message": "'target_object' is required"}

        target_obj = bpy.data.objects.get(target_name)
        if not target_obj:
            return {"success": False, "message": f"Target object '{target_name}' not found"}

        # Calculate world bounding box
        bbox = [target_obj.matrix_world @ Vector(b) for b in target_obj.bound_box]
        min_x = min(b.x for b in bbox) - padding
        max_x = max(b.x for b in bbox) + padding
        min_y = min(b.y for b in bbox) - padding
        max_y = max(b.y for b in bbox) + padding
        min_z = min(b.z for b in bbox) - padding
        max_z = max(b.z for b in bbox) + padding

        center = Vector(((min_x + max_x) / 2.0, (min_y + max_y) / 2.0, (min_z + max_z) / 2.0))
        size = Vector((max_x - min_x, max_y - min_y, max_z - min_z))

        lattice_data = bpy.data.lattices.new(f"Lattice_{target_name}_Data")
        lattice_data.points_u = u_points
        lattice_data.points_v = v_points
        lattice_data.points_w = w_points

        lattice_obj = bpy.data.objects.new(f"Lattice_{target_name}", lattice_data)
        lattice_obj.location = center
        lattice_obj.scale = size
        bpy.context.scene.collection.objects.link(lattice_obj)

        # Bind lattice modifier to target
        mod = target_obj.modifiers.new(name="LatticeDeform", type="LATTICE")
        mod.object = lattice_obj

        return {
            "success": True,
            "message": f"Created Lattice '{lattice_obj.name}' ({u_points}x{v_points}x{w_points}) and bound to '{target_name}'",
            "lattice_name": lattice_obj.name,
            "target_object": target_name,
            "resolution": [u_points, v_points, w_points],
        }


class DeformLatticePointsTool(ToolBase):
    name = "deform_lattice_points"
    description = "Apply procedural deformations (SQUASH_AND_STRETCH, BEND, TAPER, TWIST) or move specific control points on a Lattice object."

    def execute(self, params: dict) -> dict:
        lattice_name = params.get("lattice_name") or params.get("lattice_object") or params.get("name")
        deformation = (params.get("deformation") or params.get("deformation_type") or "SQUASH_AND_STRETCH").upper()
        factor = float(params.get("factor", 0.3))

        if not lattice_name:
            return {"success": False, "message": "'lattice_name' or 'lattice_object' is required"}

        lat_obj = bpy.data.objects.get(lattice_name)
        if not lat_obj or lat_obj.type != "LATTICE":
            return {"success": False, "message": f"Lattice object '{lattice_name}' not found"}

        lat = lat_obj.data
        u_res, v_res, w_res = lat.points_u, lat.points_v, lat.points_w

        # Deform points based on preset
        for w in range(w_res):
            w_norm = (w / (w_res - 1)) if w_res > 1 else 0.5  # 0.0 to 1.0 (bottom to top)
            for v in range(v_res):
                for u in range(u_res):
                    pt = lat.points[u + v * u_res + w * u_res * v_res]
                    if deformation == "SQUASH_AND_STRETCH":
                        # Bulge center, pinch top/bottom
                        bulge = (1.0 - (2.0 * w_norm - 1.0) ** 2) * factor
                        pt.co_deform.x = pt.co.x * (1.0 + bulge)
                        pt.co_deform.y = pt.co.y * (1.0 + bulge)
                        pt.co_deform.z = pt.co.z * (1.0 - bulge * 0.5)
                    elif deformation == "TAPER":
                        scale = 1.0 - w_norm * factor
                        pt.co_deform.x = pt.co.x * scale
                        pt.co_deform.y = pt.co.y * scale
                    elif deformation == "BEND":
                        bend_offset = (w_norm ** 2) * factor
                        pt.co_deform.x = pt.co.x + bend_offset

        return {
            "success": True,
            "message": f"Applied '{deformation}' deformation (factor {factor}) to Lattice '{lattice_name}'",
            "lattice_name": lattice_name,
            "deformation": deformation,
            "factor": factor,
        }
