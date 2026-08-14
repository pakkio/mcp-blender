import math
import bpy

from .base import ToolBase


class AddConstraintTool(ToolBase):
    name = "add_constraint"
    description = "Add constraints to an object or bone (TRACK_TO, DAMPED_TRACK, FOLLOW_PATH, COPY_TRANSFORMS, COPY_LOCATION, COPY_ROTATION, LIMIT_DISTANCE, CHILD_OF, IK)."

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        constraint_type = params.get("constraint_type", "TRACK_TO").upper()
        target_name = params.get("target_object")
        subtarget = params.get("subtarget")
        name = params.get("name")
        properties = params.get("properties", {})

        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj:
            return {"success": False, "message": f"Object '{object_name}' not found"}

        con_name = name or f"{constraint_type.title()}_Auto"
        con = obj.constraints.new(type=constraint_type)
        con.name = con_name

        if target_name:
            target_obj = bpy.data.objects.get(target_name)
            if target_obj and hasattr(con, "target"):
                con.target = target_obj
                if subtarget and hasattr(con, "subtarget"):
                    con.subtarget = subtarget

        # Apply specific properties
        if properties:
            for k, v in properties.items():
                if hasattr(con, k):
                    setattr(con, k, v)

        return {
            "success": True,
            "message": f"Added constraint '{con.name}' ({constraint_type}) to '{object_name}'",
            "object_name": object_name,
            "constraint_name": con.name,
            "constraint_type": constraint_type,
            "target_object": target_name,
        }


class AnimateCameraTurntableTool(ToolBase):
    name = "animate_camera_turntable"
    description = "Create a smooth 360-degree turntable camera animation around a target object or location over a specified duration."

    def execute(self, params: dict) -> dict:
        camera_name = params.get("camera_name", "Camera")
        target_name = params.get("target_object")
        target_loc = params.get("target_location", [0, 0, 0])
        radius = float(params.get("radius", 10.0))
        height = float(params.get("height", 5.0))
        duration_frames = int(params.get("duration_frames", 120))
        start_frame = int(params.get("start_frame", 1))

        cam = bpy.data.objects.get(camera_name)
        if not cam or cam.type != "CAMERA":
            return {"success": False, "message": f"Camera '{camera_name}' not found or not a CAMERA"}

        # Target center
        center_x, center_y, center_z = target_loc
        if target_name:
            target_obj = bpy.data.objects.get(target_name)
            if target_obj:
                center_x, center_y, center_z = target_obj.location

        # Insert circular orbit keyframes
        steps = 12
        frames_per_step = duration_frames / steps

        for i in range(steps + 1):
            angle = (2.0 * math.pi * i) / steps
            f = int(start_frame + i * frames_per_step)

            cam_x = center_x + radius * math.sin(angle)
            cam_y = center_y - radius * math.cos(angle)
            cam_z = center_z + height

            cam.location = (cam_x, cam_y, cam_z)
            cam.keyframe_insert(data_path="location", frame=f)

        # Set Track To constraint if not present
        track_con = next((c for c in cam.constraints if c.type in ("TRACK_TO", "DAMPED_TRACK")), None)
        if not track_con:
            # Create tracking empty at center if target object not specified
            track_target = bpy.data.objects.get(target_name) if target_name else None
            if not track_target:
                bpy.ops.object.empty_add(type="PLAIN_AXES", location=(center_x, center_y, center_z))
                track_target = bpy.context.active_object
                track_target.name = f"Turntable_Center_{camera_name}"

            track_con = cam.constraints.new(type="TRACK_TO")
            track_con.target = track_target
            track_con.track_axis = "TRACK_NEGATIVE_Z"
            track_con.up_axis = "UP_Y"

        bpy.context.scene.frame_start = start_frame
        bpy.context.scene.frame_end = start_frame + duration_frames

        return {
            "success": True,
            "message": f"Configured 360-degree turntable animation for '{camera_name}' ({duration_frames} frames)",
            "camera_name": camera_name,
            "frame_range": [start_frame, start_frame + duration_frames],
            "radius": radius,
            "height": height,
        }
