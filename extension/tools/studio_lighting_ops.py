import math
import bpy
from mathutils import Vector

from .base import ToolBase


class CreateLightingRigTool(ToolBase):
    name = "create_lighting_rig"
    description = (
        "Instantly build production lighting setups (THREE_POINT_STUDIO, PRODUCT_SOFTBOX, "
        "CYBERPUNK_NEON, FILM_NOIR, WARM_GOLDEN_HOUR) with automatic target tracking. "
        "Aim it with target_object (name, tracked via constraint) or target_location "
        "([x,y,z], aimed once at build time); default is the world origin. distance sets "
        "the rig radius in metres (default 5.0), rescaling the rig about the aim point "
        "while preserving its shape. energy_multiplier scales every lamp's power."
    )

    # The per-rig offsets below are authored around a nominal radius of this many
    # metres. A caller-supplied `distance` rescales them proportionally, so the
    # rig keeps its designed shape (key nearer, rim further back) instead of
    # collapsing every lamp onto one sphere.
    NOMINAL_RIG_RADIUS = 5.0

    def execute(self, params: dict) -> dict:
        rig_type = params.get("rig_type", "THREE_POINT_STUDIO").upper()
        target_name = params.get("target_object")
        energy_scale = float(params.get("energy_multiplier", 1.0))

        # Aim point: an object by name, or explicit coordinates. `target_location`
        # matters when the subject is not centred on an object origin (or has no
        # object at all) -- previously the rig silently fell back to the world
        # origin, which put the lights nowhere near an off-origin subject.
        raw_loc = params.get("target_location")
        target_obj = bpy.data.objects.get(target_name) if target_name else None

        if target_obj:
            target_loc = Vector(target_obj.location)
        elif raw_loc is not None:
            try:
                target_loc = Vector((float(raw_loc[0]), float(raw_loc[1]), float(raw_loc[2])))
            except (TypeError, ValueError, IndexError):
                return {
                    "success": False,
                    "message": "'target_location' must be [x, y, z] numeric coordinates",
                }
        else:
            target_loc = Vector((0, 0, 0))

        raw_dist = params.get("distance")
        if raw_dist is None:
            offset_scale = 1.0
        else:
            try:
                offset_scale = float(raw_dist) / self.NOMINAL_RIG_RADIUS
            except (TypeError, ValueError):
                return {"success": False, "message": "'distance' must be a number"}
            if offset_scale <= 0:
                return {"success": False, "message": "'distance' must be greater than 0"}

        created_lights = []

        def add_light(name, ltype, loc, color, power, size=1.0):
            ldata = bpy.data.lights.new(name=name, type=ltype)
            ldata.color = color
            ldata.energy = power * energy_scale
            if ltype == "AREA" and hasattr(ldata, "size"):
                ldata.size = size
            elif ltype == "SPOT" and hasattr(ldata, "spot_size"):
                ldata.spot_size = math.radians(45.0)

            lobj = bpy.data.objects.new(name=name, object_data=ldata)
            # Scale the authored offset about the aim point, not about the world origin.
            lobj.location = target_loc + (Vector(loc) - target_loc) * offset_scale
            bpy.context.scene.collection.objects.link(lobj)

            if target_obj:
                # Constraint keeps the lamp aimed even if the subject is moved later.
                con = lobj.constraints.new(type="TRACK_TO")
                con.target = target_obj
                con.track_axis = "TRACK_NEGATIVE_Z"
                con.up_axis = "UP_Y"
            else:
                # No object to track: aim the lamp explicitly. Without this a rig
                # built from coordinates (or with no target at all) kept its default
                # rotation and pointed straight down, lighting nothing.
                direction = target_loc - lobj.location
                if direction.length > 1e-6:
                    lobj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

            created_lights.append(lobj.name)
            return lobj

        tl = target_loc
        if rig_type == "THREE_POINT_STUDIO":
            add_light("Key_Light", "AREA", (tl.x + 3.5, tl.y - 3.5, tl.z + 3.0), (1.0, 0.98, 0.95), 400.0, 1.5)
            add_light("Fill_Light", "AREA", (tl.x - 3.5, tl.y - 2.5, tl.z + 1.5), (0.9, 0.95, 1.0), 180.0, 2.0)
            add_light("Rim_Light", "SPOT", (tl.x - 2.0, tl.y + 4.0, tl.z + 3.5), (1.0, 1.0, 1.0), 550.0)

        elif rig_type == "PRODUCT_SOFTBOX":
            add_light("Top_Softbox", "AREA", (tl.x, tl.y, tl.z + 4.0), (1.0, 1.0, 1.0), 500.0, 3.0)
            add_light("Left_Strip", "AREA", (tl.x - 3.0, tl.y - 1.0, tl.z + 1.5), (0.95, 0.95, 1.0), 250.0, 0.5)
            add_light("Right_Strip", "AREA", (tl.x + 3.0, tl.y - 1.0, tl.z + 1.5), (1.0, 0.95, 0.95), 250.0, 0.5)

        elif rig_type == "CYBERPUNK_NEON":
            add_light("Cyan_Key", "AREA", (tl.x + 3.0, tl.y - 2.5, tl.z + 2.0), (0.0, 0.85, 1.0), 450.0, 1.5)
            add_light("Magenta_Rim", "AREA", (tl.x - 3.0, tl.y + 2.5, tl.z + 2.5), (1.0, 0.05, 0.6), 550.0, 1.5)
            add_light("Ground_Glow", "POINT", (tl.x, tl.y, tl.z + 0.2), (0.2, 0.0, 0.8), 100.0)

        elif rig_type == "FILM_NOIR":
            add_light("Harsh_Key", "SPOT", (tl.x + 4.0, tl.y - 3.0, tl.z + 4.0), (1.0, 0.95, 0.85), 800.0)
            add_light("Kicker_Rim", "SPOT", (tl.x - 3.0, tl.y + 4.0, tl.z + 2.0), (1.0, 1.0, 1.0), 600.0)

        elif rig_type == "WARM_GOLDEN_HOUR":
            add_light("Golden_Sun", "SUN", (tl.x + 5.0, tl.y - 5.0, tl.z + 3.0), (1.0, 0.7, 0.35), 8.0)
            add_light("Sky_Fill", "AREA", (tl.x - 2.0, tl.y, tl.z + 4.0), (0.5, 0.75, 1.0), 120.0, 4.0)

        return {
            "success": True,
            "message": f"Created '{rig_type}' lighting rig ({len(created_lights)} lights)",
            "rig_type": rig_type,
            "lights": created_lights,
            # Echo the resolved aim/scale so a caller can see when a named target
            # was not found and the rig fell back to the world origin.
            "target_location": [round(c, 4) for c in target_loc],
            "target_object": target_obj.name if target_obj else None,
            "target_object_found": bool(target_obj) if target_name else None,
            "distance": round(self.NOMINAL_RIG_RADIUS * offset_scale, 4),
        }


class ConfigureLightLinkingTool(ToolBase):
    name = "configure_light_linking"
    description = "Configure per-object light linking and shadow linking (link lights to illuminate specific objects or exclude shadows)."

    def execute(self, params: dict) -> dict:
        light_name = params.get("light_name")
        target_collection = params.get("collection_name")

        if not light_name:
            return {"success": False, "message": "'light_name' is required"}

        lobj = bpy.data.objects.get(light_name)
        if not lobj or lobj.type != "LIGHT":
            return {"success": False, "message": f"Light object '{light_name}' not found"}

        # Light linking in Blender 4.0+
        if hasattr(lobj, "light_linking"):
            ll = lobj.light_linking
            if target_collection:
                col = bpy.data.collections.get(target_collection)
                if col and hasattr(ll, "receiver_collection"):
                    ll.receiver_collection = col

            return {
                "success": True,
                "message": f"Configured light linking for '{light_name}'",
                "light_name": light_name,
                "receiver_collection": target_collection,
            }

        return {
            "success": True,
            "message": f"Light linking not supported in this Blender version for '{light_name}'",
            "light_name": light_name,
        }
