import bpy
from mathutils import Vector

from .base import ToolBase


class SetupRigidBodySimulationTool(ToolBase):
    name = "setup_rigid_body_simulation"
    description = "Configure rigid body physics (Active/Passive, mass, friction, bounciness, collision shapes) with optional 'settle_simulation' to naturally drop and rest props onto surfaces."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        body_type = params.get("body_type", "ACTIVE").upper()
        mass = float(params.get("mass", 1.0))
        friction = float(params.get("friction", 0.5))
        bounciness = float(params.get("bounciness", 0.1))
        collision_shape = params.get("collision_shape", "CONVEX_HULL").upper()
        settle_simulation = bool(params.get("settle_simulation", False))
        settle_frames = int(params.get("settle_frames", 40))

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

        # Add or configure rigid body
        if not obj.rigid_body:
            bpy.ops.rigidbody.object_add()

        rb = obj.rigid_body
        rb.type = body_type
        rb.mass = mass
        rb.friction = friction
        rb.restitution = bounciness
        rb.collision_shape = collision_shape

        if settle_simulation and body_type == "ACTIVE":
            # Ensure rigid body world exists in scene
            if not bpy.context.scene.rigidbody_world:
                bpy.ops.rigidbody.world_add()

            # Advance scene timeline to settle objects
            scene = bpy.context.scene
            orig_frame = scene.frame_current
            scene.frame_set(orig_frame + settle_frames)

            # Apply current visual transform
            bpy.ops.object.visual_transform_apply()

            # Remove rigid body or switch to passive
            bpy.ops.rigidbody.object_remove()
            scene.frame_set(orig_frame)

            return {
                "success": True,
                "message": f"Simulated and settled '{obj.name}' at location {list(obj.location)}",
                "object_name": obj.name,
                "settled_location": list(obj.location),
                "settled_rotation": list(obj.rotation_euler),
            }

        return {
            "success": True,
            "message": f"Configured {body_type} rigid body on '{obj.name}' (Shape: {collision_shape}, Mass: {mass}kg)",
            "object_name": obj.name,
            "body_type": body_type,
            "mass": mass,
            "collision_shape": collision_shape,
        }


class SetupClothSimulationTool(ToolBase):
    name = "setup_cloth_simulation"
    description = "Add and configure Cloth physics simulations with fabric presets (SILK, COTTON, LEATHER, DENIM, RUBBER), pinning groups, and internal pressure."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        preset = params.get("preset", "COTTON").upper()
        pin_group = params.get("pin_vertex_group")
        use_pressure = bool(params.get("use_pressure", False))
        pressure = float(params.get("pressure", 1.0))

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        # Add Cloth modifier
        mod = obj.modifiers.get("Cloth")
        if not mod:
            mod = obj.modifiers.new(name="Cloth", type="CLOTH")

        cs = mod.settings
        if preset == "SILK":
            cs.mass = 0.05
            cs.tension_stiffness = 5.0
            cs.bending_stiffness = 0.05
        elif preset == "COTTON":
            cs.mass = 0.3
            cs.tension_stiffness = 15.0
            cs.bending_stiffness = 0.5
        elif preset == "LEATHER":
            cs.mass = 0.8
            cs.tension_stiffness = 80.0
            cs.bending_stiffness = 25.0
        elif preset == "DENIM":
            cs.mass = 0.5
            cs.tension_stiffness = 40.0
            cs.bending_stiffness = 10.0
        elif preset == "RUBBER":
            cs.mass = 1.0
            cs.tension_stiffness = 15.0
            cs.bending_stiffness = 25.0

        if pin_group:
            cs.vertex_group_mass = pin_group

        if use_pressure and hasattr(cs, "use_pressure"):
            cs.use_pressure = True
            cs.uniform_pressure_force = pressure

        return {
            "success": True,
            "message": f"Configured Cloth simulation ('{preset}' preset) on '{obj.name}'",
            "object_name": obj.name,
            "preset": preset,
            "has_pressure": use_pressure,
        }


class AddForceFieldTool(ToolBase):
    name = "add_force_field"
    description = "Add a 3D Physics Force Field (WIND, VORTEX, TURBULENCE, FORCE, MAGNETIC) with strength and direction."

    def execute(self, params: dict) -> dict:
        field_type = params.get("field_type", "WIND").upper()
        strength = float(params.get("strength", 10.0))
        flow = float(params.get("flow", 1.0))
        location = params.get("location", [0, 0, 0])
        rotation = params.get("rotation", [0, 0, 0])

        bpy.ops.object.effector_add(type=field_type, location=location, rotation=rotation)
        field_obj = bpy.context.active_object
        field_obj.name = f"Field_{field_type.title()}"

        if field_obj.field:
            field_obj.field.strength = strength
            field_obj.field.flow = flow

        return {
            "success": True,
            "message": f"Created {field_type} force field at {location} (Strength: {strength})",
            "field_name": field_obj.name,
            "field_type": field_type,
            "location": location,
            "strength": strength,
        }
