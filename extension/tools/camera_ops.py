import math
import bpy
import mathutils

from .base import ToolBase


class ConfigureCameraTool(ToolBase):
    name = "configure_camera"
    description = "Configure camera parameters (focal length/lens, clip start/end, sensor, dof, ortho scale, active status)."

    def execute(self, params: dict) -> dict:
        name = params.get("name")
        if not name:
            return {"success": False, "message": "'name' is required"}

        obj = bpy.data.objects.get(name)
        if not obj:
            return {"success": False, "message": f"Object '{name}' not found"}

        if obj.type != "CAMERA" or not obj.data:
            return {"success": False, "message": f"Object '{name}' is not a camera"}

        cam = obj.data

        if params.get("lens") is not None:
            cam.lens = float(params["lens"])

        if params.get("camera_type"):
            cam.type = params["camera_type"].upper()

        if params.get("ortho_scale") is not None:
            cam.ortho_scale = float(params["ortho_scale"])

        if params.get("clip_start") is not None:
            cam.clip_start = float(params["clip_start"])

        if params.get("clip_end") is not None:
            cam.clip_end = float(params["clip_end"])

        if params.get("sensor_width") is not None:
            cam.sensor_width = float(params["sensor_width"])

        if params.get("dof_focus_object"):
            focus_obj = bpy.data.objects.get(params["dof_focus_object"])
            if focus_obj:
                cam.dof.use_dof = True
                cam.dof.focus_object = focus_obj

        if params.get("dof_fstop") is not None:
            cam.dof.use_dof = True
            cam.dof.aperture_fstop = float(params["dof_fstop"])

        if params.get("set_as_active_camera", False):
            bpy.context.scene.camera = obj

        return {
            "success": True,
            "message": f"Configured camera '{obj.name}'",
            "name": obj.name,
            "lens": cam.lens,
            "clip_start": cam.clip_start,
            "clip_end": cam.clip_end,
            "is_active_camera": (bpy.context.scene.camera == obj),
        }


class CameraLookAtTool(ToolBase):
    name = "camera_look_at"
    description = "Point a camera (or any object) directly at a target 3D coordinate or target object."

    def execute(self, params: dict) -> dict:
        camera_name = params.get("camera_name")
        if not camera_name:
            return {"success": False, "message": "'camera_name' is required"}

        obj = bpy.data.objects.get(camera_name)
        if not obj:
            return {"success": False, "message": f"Object '{camera_name}' not found"}

        target_pos = None
        target_obj_name = params.get("target_object")
        if target_obj_name:
            target_obj = bpy.data.objects.get(target_obj_name)
            if target_obj:
                target_pos = target_obj.matrix_world.translation

        if target_pos is None and params.get("target_location") is not None:
            target_pos = mathutils.Vector(params["target_location"])

        if target_pos is None:
            return {"success": False, "message": "Either 'target_location' or 'target_object' must be provided"}

        add_constraint = params.get("add_constraint", False)
        if add_constraint and target_obj_name and bpy.data.objects.get(target_obj_name):
            # Check or create Track To constraint
            constraint = None
            for c in obj.constraints:
                if c.type == "TRACK_TO":
                    constraint = c
                    break
            if not constraint:
                constraint = obj.constraints.new(type="TRACK_TO")
            constraint.target = bpy.data.objects.get(target_obj_name)
            constraint.track_axis = "TRACK_NEGATIVE_Z"
            constraint.up_axis = "UP_Y"
        else:
            direction = target_pos - obj.matrix_world.translation
            if direction.length > 0.0001:
                # Camera looks along -Z with +Y up
                rot_quat = direction.to_track_quat("-Z", "Y")
                obj.rotation_euler = rot_quat.to_euler()

        return {
            "success": True,
            "message": f"Pointed '{obj.name}' at target",
            "camera_name": obj.name,
            "location": [round(v, 4) for v in obj.location],
            "rotation_euler": [round(v, 4) for v in obj.rotation_euler],
        }


class FrameObjectsTool(ToolBase):
    name = "frame_objects"
    description = "Position and orient a camera to frame specified objects (or all visible objects) cleanly."

    def execute(self, params: dict) -> dict:
        camera_name = params.get("camera_name")
        cam_obj = bpy.data.objects.get(camera_name) if camera_name else bpy.context.scene.camera
        if not cam_obj or cam_obj.type != "CAMERA":
            return {"success": False, "message": "Valid camera object not found"}

        target_names = params.get("target_objects") or []
        if target_names:
            targets = [bpy.data.objects.get(n) for n in target_names if bpy.data.objects.get(n)]
        else:
            targets = [o for o in bpy.context.scene.objects if o.type not in ("CAMERA", "LIGHT") and not o.hide_get()]

        if not targets:
            return {"success": False, "message": "No target objects to frame"}

        # Calculate bounding box encompassing all targets
        min_co = mathutils.Vector((float("inf"), float("inf"), float("inf")))
        max_co = mathutils.Vector((float("-inf"), float("-inf"), float("-inf")))

        for obj in targets:
            for corner in obj.bound_box:
                world_corner = obj.matrix_world @ mathutils.Vector(corner)
                for i in range(3):
                    min_co[i] = min(min_co[i], world_corner[i])
                    max_co[i] = max(max_co[i], world_corner[i])

        center = (min_co + max_co) / 2.0
        radius = (max_co - min_co).length / 2.0
        margin = params.get("margin", 1.5)

        cam_data = cam_obj.data
        fov = 2.0 * math.atan((cam_data.sensor_width / 2.0) / cam_data.lens)
        distance = (radius * margin) / math.sin(fov / 2.0) if fov > 0 else 5.0
        distance = max(distance, 1.0)

        # Retain camera view direction or default to 45 degree isometric angle
        direction = cam_obj.location - center
        if direction.length < 0.1:
            direction = mathutils.Vector((1.0, -1.0, 0.8))
        direction.normalize()

        cam_obj.location = center + direction * distance

        # Look at center
        look_dir = center - cam_obj.location
        rot_quat = look_dir.to_track_quat("-Z", "Y")
        cam_obj.rotation_euler = rot_quat.to_euler()

        return {
            "success": True,
            "message": f"Framed {len(targets)} object(s) with camera '{cam_obj.name}'",
            "camera_name": cam_obj.name,
            "location": [round(v, 4) for v in cam_obj.location],
            "rotation_euler": [round(v, 4) for v in cam_obj.rotation_euler],
            "target_center": [round(v, 4) for v in center],
            "distance": round(distance, 4),
        }


class RaycastFromCameraTool(ToolBase):
    name = "raycast_from_camera"
    description = (
        "Cast a ray from a camera toward a target point/object (or straight ahead "
        "down the camera's view direction) and list every object hit along the "
        "way, in order, with distances -- answers 'what's actually between the "
        "camera and my target' in one call instead of a hide/render/diff loop."
    )

    def execute(self, params: dict) -> dict:
        camera_name = params.get("camera_name")
        cam_obj = bpy.data.objects.get(camera_name) if camera_name else bpy.context.scene.camera
        if not cam_obj or cam_obj.type != "CAMERA":
            return {
                "success": False,
                "message": "Valid camera not found (pass camera_name, or set an active scene camera).",
            }

        origin = cam_obj.matrix_world.translation.copy()

        target_pos = None
        target_object_name = params.get("target_object")
        if target_object_name:
            target_obj = bpy.data.objects.get(target_object_name)
            if not target_obj:
                return {"success": False, "message": f"Object '{target_object_name}' not found"}
            target_pos = target_obj.matrix_world.translation.copy()
        elif params.get("target_location") is not None:
            target_pos = mathutils.Vector(params["target_location"])

        max_distance_param = params.get("max_distance")

        if target_pos is not None:
            direction = target_pos - origin
            dist_to_target = direction.length
            if dist_to_target < 1e-6:
                return {"success": False, "message": "Target location coincides with the camera origin."}
            direction.normalize()
            max_distance = float(max_distance_param) if max_distance_param is not None else dist_to_target + 1e-4
        else:
            direction = (cam_obj.matrix_world.to_3x3() @ mathutils.Vector((0.0, 0.0, -1.0))).normalized()
            max_distance = float(max_distance_param) if max_distance_param is not None else 1000.0

        max_hits = int(params.get("max_hits", 10))
        depsgraph = bpy.context.evaluated_depsgraph_get()

        hits = []
        current_origin = origin
        traveled = 0.0
        epsilon = 1e-4
        for _ in range(max_hits):
            remaining = max_distance - traveled
            if remaining <= 0:
                break
            success, location, normal, index, hit_obj, matrix = bpy.context.scene.ray_cast(
                depsgraph, current_origin, direction, distance=remaining
            )
            if not success:
                break
            distance = (location - origin).length
            hits.append(
                {
                    "name": hit_obj.name,
                    "distance": round(distance, 4),
                    "location": [round(v, 4) for v in location],
                }
            )
            current_origin = location + direction * epsilon
            traveled = distance + epsilon

        return {
            "success": True,
            "camera_name": cam_obj.name,
            "origin": [round(v, 4) for v in origin],
            "direction": [round(v, 4) for v in direction],
            "hits": hits,
            "hit_count": len(hits),
        }
