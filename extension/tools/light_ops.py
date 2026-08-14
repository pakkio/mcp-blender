import bpy

from .base import ToolBase


class ConfigureLightTool(ToolBase):
    name = "configure_light"
    description = "Configure properties of a light object (energy/power, color, light type, spot size, area size, shadow soft size)."

    def execute(self, params: dict) -> dict:
        name = params.get("name")
        if not name:
            return {"success": False, "message": "'name' is required"}

        obj = bpy.data.objects.get(name)
        if not obj:
            return {"success": False, "message": f"Object '{name}' not found"}

        if obj.type != "LIGHT" or not obj.data:
            return {"success": False, "message": f"Object '{name}' is not a light"}

        light = obj.data

        if params.get("light_type"):
            light.type = params["light_type"].upper()

        if params.get("energy") is not None:
            light.energy = float(params["energy"])

        if params.get("color") is not None:
            light.color = tuple(params["color"])

        if params.get("spot_size") is not None and hasattr(light, "spot_size"):
            light.spot_size = float(params["spot_size"])

        if params.get("spot_blend") is not None and hasattr(light, "spot_blend"):
            light.spot_blend = float(params["spot_blend"])

        if params.get("shadow_soft_size") is not None and hasattr(light, "shadow_soft_size"):
            light.shadow_soft_size = float(params["shadow_soft_size"])

        if params.get("size") is not None and hasattr(light, "size"):
            light.size = float(params["size"])

        if params.get("size_y") is not None and hasattr(light, "size_y"):
            light.size_y = float(params["size_y"])

        return {
            "success": True,
            "message": f"Configured light '{obj.name}'",
            "name": obj.name,
            "light_type": light.type,
            "energy": light.energy,
            "color": [round(c, 4) for c in light.color],
        }
