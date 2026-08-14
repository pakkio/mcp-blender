import bpy

from .base import ToolBase


class SetObjectTransformTool(ToolBase):
    name = "set_object_transform"
    description = "Set location/rotation/scale on an existing object (absolute or relative/delta update)."

    def execute(self, params: dict) -> dict:
        name = params.get("name")
        obj = bpy.data.objects.get(name) if name else None
        if obj is None:
            return {"success": False, "message": f"Object '{name}' not found"}

        # Absolute transform
        if params.get("location") is not None:
            obj.location = tuple(params["location"])
        if params.get("rotation_euler") is not None:
            obj.rotation_euler = tuple(params["rotation_euler"])
        if params.get("scale") is not None:
            obj.scale = tuple(params["scale"])

        # Delta / relative transform
        if params.get("delta_location") is not None:
            d = params["delta_location"]
            obj.location = (obj.location.x + d[0], obj.location.y + d[1], obj.location.z + d[2])
        if params.get("delta_rotation_euler") is not None:
            d = params["delta_rotation_euler"]
            obj.rotation_euler = (
                obj.rotation_euler.x + d[0],
                obj.rotation_euler.y + d[1],
                obj.rotation_euler.z + d[2],
            )
        if params.get("delta_scale") is not None:
            d = params["delta_scale"]
            obj.scale = (obj.scale.x * d[0], obj.scale.y * d[1], obj.scale.z * d[2])

        return {
            "success": True,
            "message": f"Updated transform for '{obj.name}'",
            "name": obj.name,
            "location": [round(v, 4) for v in obj.location],
            "rotation_euler": [round(v, 4) for v in obj.rotation_euler],
            "scale": [round(v, 4) for v in obj.scale],
        }
