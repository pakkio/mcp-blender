import bpy

from .base import ToolBase


class CreateObjectTool(ToolBase):
    name = "create_object"
    description = "Create mesh primitives, empty, camera, light, text, or curve objects in the scene."

    def execute(self, params: dict) -> dict:
        # blender_mesh's params dict has no schema, so a caller guessing the
        # wrong key name (e.g. "type" or "shape" instead of "object_type")
        # would otherwise silently fall through to CUBE while "name" still
        # applies -- accept the common near-misses instead of guessing wrong.
        object_type = (
            params.get("object_type") or params.get("type") or params.get("shape") or "CUBE"
        ).upper()
        location = tuple(params.get("location") or (0.0, 0.0, 0.0))
        radius = params.get("radius")
        size = params.get("size")

        # Ensure we are in object mode before adding objects
        if bpy.context.mode != "OBJECT":
            try:
                bpy.ops.object.mode_set(mode="OBJECT")
            except Exception:
                pass

        if object_type == "EMPTY":
            bpy.ops.object.empty_add(location=location)
        elif object_type == "CUBE":
            kw = {"location": location}
            if size is not None:
                kw["size"] = size
            bpy.ops.mesh.primitive_cube_add(**kw)
        elif object_type in ("UV_SPHERE", "SPHERE"):
            kw = {"location": location}
            if radius is not None:
                kw["radius"] = radius
            bpy.ops.mesh.primitive_uv_sphere_add(**kw)
        elif object_type == "ICO_SPHERE":
            kw = {"location": location}
            if radius is not None:
                kw["radius"] = radius
            bpy.ops.mesh.primitive_ico_sphere_add(**kw)
        elif object_type == "CYLINDER":
            kw = {"location": location}
            if radius is not None:
                kw["radius"] = radius
            bpy.ops.mesh.primitive_cylinder_add(**kw)
        elif object_type == "CONE":
            kw = {"location": location}
            if radius is not None:
                kw["radius1"] = radius
            bpy.ops.mesh.primitive_cone_add(**kw)
        elif object_type == "PLANE":
            kw = {"location": location}
            if size is not None:
                kw["size"] = size
            bpy.ops.mesh.primitive_plane_add(**kw)
        elif object_type == "TORUS":
            kw = {"location": location}
            if radius is not None:
                kw["major_radius"] = radius
            bpy.ops.mesh.primitive_torus_add(**kw)
        elif object_type == "GRID":
            kw = {"location": location}
            if size is not None:
                kw["size"] = size
            bpy.ops.mesh.primitive_grid_add(**kw)
        elif object_type == "MONKEY" or object_type == "SUZANNE":
            kw = {"location": location}
            if size is not None:
                kw["size"] = size
            bpy.ops.mesh.primitive_monkey_add(**kw)
        elif object_type == "CIRCLE":
            kw = {"location": location}
            if radius is not None:
                kw["radius"] = radius
            bpy.ops.mesh.primitive_circle_add(**kw)
        elif object_type == "CAMERA":
            bpy.ops.object.camera_add(location=location)
        elif object_type == "LIGHT":
            light_type = (params.get("light_type") or "POINT").upper()
            bpy.ops.object.light_add(type=light_type, location=location)
            obj = bpy.context.active_object
            if obj and obj.data:
                if params.get("light_energy") is not None:
                    obj.data.energy = float(params["light_energy"])
                if params.get("light_color") is not None:
                    obj.data.color = tuple(params["light_color"])
        elif object_type == "TEXT":
            bpy.ops.object.text_add(location=location)
            obj = bpy.context.active_object
            if obj and obj.data:
                if params.get("text_body"):
                    obj.data.body = str(params["text_body"])
                if params.get("text_extrude") is not None:
                    obj.data.extrude = float(params["text_extrude"])
                if size is not None:
                    obj.data.size = float(size)
        elif object_type == "CURVE_BEZIER":
            bpy.ops.curve.primitive_bezier_curve_add(location=location)
        elif object_type == "CURVE_CIRCLE":
            bpy.ops.curve.primitive_bezier_circle_add(location=location)
        else:
            return {
                "success": False,
                "message": f"Unknown object_type '{object_type}'",
            }

        obj = bpy.context.active_object
        if obj is None:
            return {"success": False, "message": "Failed to create object"}

        if params.get("name"):
            obj.name = params["name"]

        rotation_euler = params.get("rotation_euler") or params.get("rotation")
        if rotation_euler:
            obj.rotation_euler = tuple(rotation_euler)

        if params.get("scale"):
            obj.scale = tuple(params["scale"])

        collection_name = params.get("collection")
        if collection_name:
            target = bpy.data.collections.get(collection_name)
            if target is not None:
                for existing in list(obj.users_collection):
                    existing.objects.unlink(obj)
                target.objects.link(obj)

        return {
            "success": True,
            "message": f"Created object '{obj.name}'",
            "name": obj.name,
            "type": obj.type,
            "location": [round(v, 4) for v in obj.location],
            "rotation_euler": [round(v, 4) for v in obj.rotation_euler],
            "scale": [round(v, 4) for v in obj.scale],
        }
