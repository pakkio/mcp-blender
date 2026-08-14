import bpy

from .base import ToolBase


class BooleanOperationTool(ToolBase):
    name = "boolean_operation"
    description = "Perform boolean operations (UNION, DIFFERENCE, INTERSECT, SLICE) between mesh objects using FAST or EXACT solvers."

    def execute(self, params: dict) -> dict:
        target_name = params.get("target_object")
        operand_name = params.get("operand_object")
        operation = params.get("operation", "UNION").upper()
        solver = params.get("solver", "EXACT").upper()
        apply_immediately = params.get("apply_immediately", True)
        delete_operand = params.get("delete_operand", False)

        if not target_name:
            return {"success": False, "message": "'target_object' is required"}
        if not operand_name:
            return {"success": False, "message": "'operand_object' is required"}

        target_obj = bpy.data.objects.get(target_name)
        if not target_obj or target_obj.type != "MESH":
            return {"success": False, "message": f"Target object '{target_name}' not found or not a MESH"}

        operand_obj = bpy.data.objects.get(operand_name)
        if not operand_obj or operand_obj.type != "MESH":
            return {"success": False, "message": f"Operand object '{operand_name}' not found or not a MESH"}

        if operation not in ("UNION", "DIFFERENCE", "INTERSECT", "SLICE"):
            return {
                "success": False,
                "message": f"Invalid operation '{operation}'. Must be UNION, DIFFERENCE, INTERSECT, or SLICE",
            }

        # Resolve solver compatibility across Blender versions
        try:
            valid_solvers = [
                item.identifier
                for item in bpy.types.BooleanModifier.bl_rna.properties["solver"].enum_items
            ]
            if solver not in valid_solvers:
                if solver == "FAST":
                    solver = "FLOAT" if "FLOAT" in valid_solvers else ("MANIFOLD" if "MANIFOLD" in valid_solvers else "EXACT")
                elif solver in ("FLOAT", "MANIFOLD"):
                    solver = "FAST" if "FAST" in valid_solvers else "EXACT"
                else:
                    solver = valid_solvers[0]
        except Exception:
            solver = "EXACT"

        # Handle SLICE as Difference on target + Intersect duplicate
        if operation == "SLICE":
            # Duplicate target for slice piece
            slice_obj = target_obj.copy()
            slice_obj.data = target_obj.data.copy()
            slice_obj.name = f"{target_name}_Slice"
            for col in target_obj.users_collection:
                col.objects.link(slice_obj)

            # Target gets DIFFERENCE
            mod_diff = target_obj.modifiers.new(name="Bool_Slice_Diff", type="BOOLEAN")
            mod_diff.operation = "DIFFERENCE"
            mod_diff.solver = solver
            mod_diff.object = operand_obj

            # Slice piece gets INTERSECT
            mod_int = slice_obj.modifiers.new(name="Bool_Slice_Int", type="BOOLEAN")
            mod_int.operation = "INTERSECT"
            mod_int.solver = solver
            mod_int.object = operand_obj

            if apply_immediately:
                bpy.context.view_layer.objects.active = target_obj
                bpy.ops.object.modifier_apply(modifier=mod_diff.name)
                bpy.context.view_layer.objects.active = slice_obj
                bpy.ops.object.modifier_apply(modifier=mod_int.name)

            if delete_operand:
                bpy.data.objects.remove(operand_obj, do_unlink=True)

            return {
                "success": True,
                "message": f"Sliced '{target_name}' with '{operand_name}' into '{target_name}' and '{slice_obj.name}'",
                "target_object": target_name,
                "slice_object": slice_obj.name,
                "operation": "SLICE",
                "applied": apply_immediately,
            }

        # Standard boolean (UNION, DIFFERENCE, INTERSECT)
        mod_name = f"Bool_{operation.title()}"
        mod = target_obj.modifiers.new(name=mod_name, type="BOOLEAN")
        mod.operation = operation
        mod.solver = solver
        mod.object = operand_obj

        if apply_immediately:
            bpy.context.view_layer.objects.active = target_obj
            bpy.ops.object.modifier_apply(modifier=mod.name)

        if delete_operand:
            bpy.data.objects.remove(operand_obj, do_unlink=True)

        return {
            "success": True,
            "message": f"Successfully performed {operation} on '{target_name}' with operand '{operand_name}' (solver: {solver})",
            "target_object": target_name,
            "operand_object": operand_name if not delete_operand else None,
            "operation": operation,
            "solver": solver,
            "applied": apply_immediately,
        }
