import math
import os
import bpy
from mathutils import Vector

from .base import ToolBase


class Create3DTextTool(ToolBase):
    name = "create_3d_text"
    description = "Create a 3D Text object with custom font size, extrude depth, bevel resolution, alignment (LEFT, CENTER, RIGHT, JUSTIFY), tracking, and optional mesh conversion."

    def execute(self, params: dict) -> dict:
        text_content = params.get("text", "Hello 3D")
        name = params.get("name", "Text3D")
        location = params.get("location", [0, 0, 0])
        rotation = params.get("rotation", [0, 0, 0])
        scale = params.get("scale", [1, 1, 1])
        extrude = float(params.get("extrude", 0.1))
        bevel_depth = float(params.get("bevel_depth", 0.02))
        bevel_resolution = int(params.get("bevel_resolution", 3))
        align_x = params.get("align_x", "CENTER").upper()
        align_y = params.get("align_y", "CENTER").upper()
        character_spacing = float(params.get("character_spacing", 1.0))
        convert_to_mesh = bool(params.get("convert_to_mesh", False))

        font_curve = bpy.data.curves.new(name=f"{name}_Data", type="FONT")
        font_curve.body = text_content
        font_curve.extrude = extrude
        font_curve.bevel_depth = bevel_depth
        font_curve.bevel_resolution = bevel_resolution
        font_curve.space_character = character_spacing

        if align_x in ("LEFT", "CENTER", "RIGHT", "JUSTIFY", "FLUSH"):
            font_curve.align_x = align_x
        if align_y in ("TOP_BASELINE", "TOP", "CENTER", "BOTTOM", "BOTTOM_BASELINE"):
            font_curve.align_y = align_y

        text_obj = bpy.data.objects.new(name, font_curve)
        text_obj.location = location
        text_obj.rotation_euler = tuple(math.radians(r) for r in rotation)
        text_obj.scale = scale
        bpy.context.scene.collection.objects.link(text_obj)

        if convert_to_mesh:
            bpy.context.view_layer.objects.active = text_obj
            text_obj.select_set(True)
            bpy.ops.object.convert(target="MESH")

        return {
            "success": True,
            "message": f"Created 3D text '{text_obj.name}' with body '{text_content}'",
            "name": text_obj.name,
            "text": text_content,
            "is_mesh": convert_to_mesh,
        }


class DeformTextAlongCurveTool(ToolBase):
    name = "deform_text_along_curve"
    description = "Deform and wrap 3D text along a Bezier curve or circular path for logos, circular signage, and ribbons."

    def execute(self, params: dict) -> dict:
        text_name = params.get("text_name")
        curve_name = params.get("curve_name")
        create_circle_curve = bool(params.get("create_circle_curve", False))
        circle_radius = float(params.get("circle_radius", 3.0))

        if not text_name:
            return {"success": False, "message": "'text_name' is required"}

        text_obj = bpy.data.objects.get(text_name)
        if not text_obj:
            return {"success": False, "message": f"Text object '{text_name}' not found"}

        if create_circle_curve or not curve_name:
            bpy.ops.curve.primitive_bezier_circle_add(radius=circle_radius, location=text_obj.location)
            curve_obj = bpy.context.active_object
            curve_obj.name = f"{text_name}_Path"
        else:
            curve_obj = bpy.data.objects.get(curve_name)
            if not curve_obj or curve_obj.type != "CURVE":
                return {"success": False, "message": f"Curve object '{curve_name}' not found or not a CURVE"}

        if text_obj.type == "FONT":
            text_obj.data.follow_curve = curve_obj
        else:
            # Curve modifier for mesh converted text
            mod = text_obj.modifiers.new(name="CurveDeform", type="CURVE")
            mod.object = curve_obj

        return {
            "success": True,
            "message": f"Bound text '{text_name}' along curve path '{curve_obj.name}'",
            "text_name": text_name,
            "curve_name": curve_obj.name,
        }


class SetTextPropertiesTool(ToolBase):
    name = "set_text_properties"
    description = "Update body content, font size, extrude depth, bevel, and letter spacing on existing 3D text."

    def execute(self, params: dict) -> dict:
        text_name = params.get("text_name") or params.get("name")
        text_content = params.get("text")
        extrude = params.get("extrude")
        bevel_depth = params.get("bevel_depth")
        size = params.get("size")
        character_spacing = params.get("character_spacing")

        if not text_name:
            return {"success": False, "message": "'text_name' is required"}

        text_obj = bpy.data.objects.get(text_name)
        if not text_obj or text_obj.type != "FONT":
            return {"success": False, "message": f"3D Text object '{text_name}' not found or not a FONT object"}

        curve = text_obj.data
        if text_content is not None:
            curve.body = str(text_content)
        if extrude is not None:
            curve.extrude = float(extrude)
        if bevel_depth is not None:
            curve.bevel_depth = float(bevel_depth)
        if size is not None:
            curve.size = float(size)
        if character_spacing is not None:
            curve.space_character = float(character_spacing)

        return {
            "success": True,
            "message": f"Updated text properties on '{text_name}'",
            "text_name": text_name,
            "body": curve.body,
        }
