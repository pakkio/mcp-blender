import base64
import math
import os
import tempfile
from pathlib import Path
import bpy
from mathutils import Vector

from .base import ToolBase


class CaptureMultiviewAuditTool(ToolBase):
    name = "capture_multiview_audit"
    description = "Capture a 4-angle visual inspection contact sheet (Front, Right Side, Top, and 3/4 Perspective) of the scene or target object for multimodal AI vision analysis."

    def execute(self, params: dict) -> dict:
        target_name = params.get("target_object")
        output_filepath = params.get("output_filepath")
        include_base64 = bool(params.get("include_base64", False))
        resolution = int(params.get("resolution", 1024))
        shading = params.get("shading_mode", "SOLID").upper()

        scene = bpy.context.scene

        # Compute focus center & bounding radius
        if target_name:
            target_obj = bpy.data.objects.get(target_name)
            if not target_obj:
                return {"success": False, "message": f"Target object '{target_name}' not found"}
            bbox = [target_obj.matrix_world @ Vector(b) for b in target_obj.bound_box]
            center = sum(bbox, Vector((0, 0, 0))) / 8.0
            radius = max((b - center).length for b in bbox) or 2.0
        else:
            center = Vector((0, 0, 0))
            radius = 3.0

        dist = radius * 2.8

        # Create temporary audit camera
        audit_cam_data = bpy.data.cameras.new("AuditCamData")
        audit_cam = bpy.data.objects.new("AuditCamObj", audit_cam_data)
        scene.collection.objects.link(audit_cam)
        orig_cam = scene.camera
        scene.camera = audit_cam

        # View configs: (Name, Position Offset)
        views = [
            ("Perspective", Vector((dist * 0.8, -dist * 0.8, dist * 0.6))),
            ("Front", Vector((0, -dist, 0))),
            ("Right", Vector((dist, 0, 0))),
            ("Top", Vector((0, 0, dist))),
        ]

        temp_dir = tempfile.gettempdir()
        rendered_images = []

        # half*2 (rather than the raw `resolution`) is what the composite
        # canvas is sized to below, so it always exactly matches the pixel
        # dimensions of the 4 captured quadrants even when `resolution` is
        # odd. resolution_percentage is pinned to 100 for the same reason:
        # otherwise the actual rendered-out PNG dimensions silently diverge
        # from resolution_x/y and the quadrant pixel-copy loop reads the
        # wrong offsets.
        half = resolution // 2
        composite_size = half * 2

        orig_res_x = scene.render.resolution_x
        orig_res_y = scene.render.resolution_y
        orig_res_pct = scene.render.resolution_percentage
        orig_filepath = scene.render.filepath
        scene.render.resolution_x = half
        scene.render.resolution_y = half
        scene.render.resolution_percentage = 100

        try:
            for view_name, offset in views:
                cam_pos = center + offset
                audit_cam.location = cam_pos

                # Look at target center
                direction = center - cam_pos
                rot_quat = direction.to_track_quat("-Z", "Y")
                audit_cam.rotation_euler = rot_quat.to_euler()

                frame_path = os.path.join(temp_dir, f"mcp_audit_{view_name.lower()}.png")
                scene.render.filepath = frame_path

                if shading == "RENDERED":
                    bpy.ops.render.render(write_still=True)
                else:
                    bpy.ops.render.opengl(write_still=True)

                if os.path.isfile(frame_path):
                    rendered_images.append((view_name, frame_path))

            # Stitch 2x2 grid in Blender or save primary
            final_out = output_filepath or os.path.join(temp_dir, "mcp_multiview_audit.png")
            final_out = os.path.abspath(os.path.expanduser(final_out))

            # Load captured images and compose into 2x2 grid image
            composite_img = bpy.data.images.new(
                "AuditComposite",
                width=composite_size,
                height=composite_size,
                alpha=True,
            )

            # Read pixels from the 4 rendered quadrants
            pixels = [0.0] * (composite_size * composite_size * 4)

            # Positions in 2x2: (0: Top-Left=Persp, 1: Top-Right=Front, 2: Bottom-Left=Right, 3: Bottom-Right=Top)
            quadrant_offsets = [(0, half), (half, half), (0, 0), (half, 0)]

            for idx, (_, img_path) in enumerate(rendered_images):
                if idx >= 4:
                    break
                sub_img = bpy.data.images.load(img_path)
                sub_px = list(sub_img.pixels)
                # Read the source's actual dimensions rather than assuming
                # `half` -- with resolution_percentage pinned to 100 above
                # they now always match, but this keeps the copy from
                # silently misaligning rows if that ever stops being true.
                src_w, src_h = sub_img.size
                qx, qy = quadrant_offsets[idx]
                copy_w = min(src_w, half)
                copy_h = min(src_h, half)

                for y in range(copy_h):
                    for x in range(copy_w):
                        src_idx = (y * src_w + x) * 4
                        dst_x = qx + x
                        dst_y = qy + y
                        dst_idx = (dst_y * composite_size + dst_x) * 4
                        if src_idx + 3 < len(sub_px) and dst_idx + 3 < len(pixels):
                            pixels[dst_idx : dst_idx + 4] = sub_px[src_idx : src_idx + 4]

                bpy.data.images.remove(sub_img)

            composite_img.pixels = pixels
            composite_img.filepath_raw = final_out
            composite_img.file_format = "PNG"
            composite_img.save()
            bpy.data.images.remove(composite_img)

            b64_data = None
            if include_base64 and os.path.isfile(final_out):
                with open(final_out, "rb") as f:
                    b64_data = "data:image/png;base64," + base64.b64encode(f.read()).decode("utf-8")

            return {
                "success": True,
                "message": f"Generated 4-view visual audit contact sheet: '{final_out}'",
                "output_filepath": final_out,
                "resolution": [composite_size, composite_size],
                "views": [v[0] for v in rendered_images],
                "base64_data_uri": b64_data,
            }
        finally:
            for _, img_path in rendered_images:
                try:
                    if os.path.isfile(img_path):
                        os.remove(img_path)
                except OSError:
                    pass

            scene.render.resolution_x = orig_res_x
            scene.render.resolution_y = orig_res_y
            scene.render.resolution_percentage = orig_res_pct
            scene.render.filepath = orig_filepath
            scene.camera = orig_cam
            if audit_cam:
                bpy.data.objects.remove(audit_cam)
            if audit_cam_data:
                bpy.data.cameras.remove(audit_cam_data)


class InspectFocusShotTool(ToolBase):
    name = "inspect_focus_shot"
    description = "Frame a cinematic close-up camera shot directly on a target object with custom focal length (e.g. 50mm, 85mm macro) and capture an inspection snapshot."

    def execute(self, params: dict) -> dict:
        target_name = params.get("target_object")
        focal_length = float(params.get("focal_length", 50.0))
        angle_elevation = float(params.get("angle_elevation", 20.0))
        angle_azimuth = float(params.get("angle_azimuth", 45.0))
        output_filepath = params.get("output_filepath")
        include_base64 = bool(params.get("include_base64", False))

        if not target_name:
            return {"success": False, "message": "'target_object' is required"}

        obj = bpy.data.objects.get(target_name)
        if not obj:
            return {"success": False, "message": f"Target object '{target_name}' not found"}

        scene = bpy.context.scene
        cam_data = bpy.data.cameras.new(f"InspectCam_{target_name}")
        cam_data.lens = focal_length
        cam_obj = bpy.data.objects.new(f"InspectCamObj_{target_name}", cam_data)
        scene.collection.objects.link(cam_obj)

        orig_cam = scene.camera
        orig_filepath = scene.render.filepath
        scene.camera = cam_obj

        try:
            bbox = [obj.matrix_world @ Vector(b) for b in obj.bound_box]
            center = sum(bbox, Vector((0, 0, 0))) / 8.0
            radius = max((b - center).length for b in bbox) or 1.5

            dist = radius * (focal_length / 24.0) * 1.4

            el_rad = math.radians(angle_elevation)
            az_rad = math.radians(angle_azimuth)

            cam_x = center.x + dist * math.cos(el_rad) * math.sin(az_rad)
            cam_y = center.y - dist * math.cos(el_rad) * math.cos(az_rad)
            cam_z = center.z + dist * math.sin(el_rad)

            cam_obj.location = (cam_x, cam_y, cam_z)
            direction = center - cam_obj.location
            rot_quat = direction.to_track_quat("-Z", "Y")
            cam_obj.rotation_euler = rot_quat.to_euler()

            final_out = output_filepath or os.path.join(tempfile.gettempdir(), f"mcp_focus_{target_name}.png")
            final_out = os.path.abspath(os.path.expanduser(final_out))

            scene.render.filepath = final_out
            bpy.ops.render.opengl(write_still=True)

            b64_data = None
            if include_base64 and os.path.isfile(final_out):
                with open(final_out, "rb") as f:
                    b64_data = base64.b64encode(f.read()).decode("utf-8")

            result = {
                "success": True,
                "message": f"Captured focus shot for '{target_name}' at {focal_length}mm -> '{final_out}'",
                "target_object": target_name,
                "focal_length": focal_length,
                "output_filepath": final_out,
            }
            if b64_data:
                result["image_base64"] = b64_data
            return result
        finally:
            scene.camera = orig_cam
            scene.render.filepath = orig_filepath
            bpy.data.objects.remove(cam_obj)
            bpy.data.cameras.remove(cam_data)
