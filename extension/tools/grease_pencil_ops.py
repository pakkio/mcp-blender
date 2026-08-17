import bpy
from .base import ToolBase


class SetupLineArtContourTool(ToolBase):
    name = "setup_line_art_contour"
    description = "Add cartoon / anime Line Art contour ink outlines around 3D objects or scene collections using Grease Pencil Line Art."

    def execute(self, params: dict) -> dict:
        source_type = params.get("source_type", "SCENE").upper()
        target_object = params.get("target_object")
        thickness = int(params.get("thickness", 3))
        use_crease = bool(params.get("use_crease", True))

        gp_data = bpy.data.grease_pencils.new("LineArt_GPData") if hasattr(bpy.data, "grease_pencils") else bpy.data.grease_pencil.new("LineArt_GPData")
        gp_obj = bpy.data.objects.new("LineArt_Ink", gp_data)
        bpy.context.scene.collection.objects.link(gp_obj)

        mod = gp_obj.modifiers.new(name="LineArt", type="LINEART")
        if hasattr(mod, "thickness"):
            mod.thickness = thickness
        if hasattr(mod, "radius"):
            mod.radius = float(thickness) * 0.005
        if hasattr(mod, "use_crease"):
            mod.use_crease = use_crease

        if source_type == "OBJECT" and target_object:
            src_obj = bpy.data.objects.get(target_object)
            if src_obj:
                mod.source_type = "OBJECT"
                mod.source_object = src_obj
        else:
            mod.source_type = "SCENE"

        return {
            "success": True,
            "message": f"Created Line Art contour outlines ('{gp_obj.name}') for {source_type}",
            "gp_object": gp_obj.name,
            "thickness": thickness,
            "source_type": source_type,
        }


class CreateGreasePencilLayerTool(ToolBase):
    name = "create_grease_pencil_layer"
    description = "Create or configure a Grease Pencil / GPv3 drawing layer with color, line thickness, and blending properties."

    def execute(self, params: dict) -> dict:
        gp_object = params.get("gp_object")
        layer_name = params.get("layer_name", "Lines")
        color = params.get("color", [0.0, 0.0, 0.0, 1.0])
        use_lights = bool(params.get("use_lights", False))

        gp_obj = None
        if gp_object:
            gp_obj = bpy.data.objects.get(gp_object)

        if not gp_obj:
            gp_data = bpy.data.grease_pencils.new(f"{layer_name}_GPData") if hasattr(bpy.data, "grease_pencils") else bpy.data.grease_pencil.new(f"{layer_name}_GPData")
            gp_obj = bpy.data.objects.new(gp_object or "Grease_Pencil", gp_data)
            bpy.context.scene.collection.objects.link(gp_obj)

        gp_data = gp_obj.data
        layer = None

        if hasattr(gp_data, "layers"):
            layer = gp_data.layers.get(layer_name) or gp_data.layers.new(layer_name)
            if hasattr(layer, "use_lights"):
                layer.use_lights = use_lights

        # Create or assign GP material
        mat = bpy.data.materials.new(name=f"GP_{layer_name}_Mat")
        if hasattr(bpy.data.materials, "create_gpencil_data"):
            bpy.data.materials.create_gpencil_data(mat)
            if hasattr(mat, "grease_pencil"):
                mat.grease_pencil.color = tuple(color)
        gp_obj.data.materials.append(mat)

        return {
            "success": True,
            "message": f"Grease pencil layer '{layer_name}' created on '{gp_obj.name}'",
            "gp_object": gp_obj.name,
            "layer_name": layer_name,
            "material": mat.name,
        }


class DrawGreasePencilStrokesTool(ToolBase):
    name = "draw_grease_pencil_strokes"
    description = "Draw procedural 2D/3D strokes into a Grease Pencil frame with point coordinates, pressure, and strength."

    def execute(self, params: dict) -> dict:
        gp_object = params.get("gp_object")
        layer_name = params.get("layer_name", "Lines")
        strokes_spec = params.get("strokes", [])
        frame_number = int(params.get("frame", 1))

        if not gp_object:
            return {"success": False, "message": "'gp_object' is required"}
        if not strokes_spec:
            return {"success": False, "message": "'strokes' list is required"}

        gp_obj = bpy.data.objects.get(gp_object)
        if not gp_obj or gp_obj.type != "GPENCIL":
            # In Blender 4.3+ GPv3 type might be GREASEPENCIL
            if not gp_obj or not (hasattr(gp_obj, "type") and "PENCIL" in gp_obj.type):
                return {"success": False, "message": f"Grease pencil object '{gp_object}' not found"}

        gp_data = gp_obj.data
        if not hasattr(gp_data, "layers"):
            return {"success": False, "message": "Grease pencil layers not accessible"}

        layer = gp_data.layers.get(layer_name) or gp_data.layers.new(layer_name)
        frame = layer.frames.get(frame_number) if hasattr(layer, "frames") and hasattr(layer.frames, "get") else None
        if not frame and hasattr(layer, "frames"):
            try:
                frame = layer.frames.new(frame_number)
            except Exception:
                frame = layer.frames[0] if len(layer.frames) > 0 else None

        strokes_created = 0
        if frame and hasattr(frame, "strokes"):
            for s_spec in strokes_spec:
                points = s_spec.get("points", [])
                if not points:
                    continue
                stroke = frame.strokes.new()
                stroke.points.add(len(points))
                pressures = s_spec.get("pressure", [1.0] * len(points))

                for i, pt in enumerate(points):
                    stroke.points[i].co = tuple(pt[:3])
                    if hasattr(stroke.points[i], "pressure") and i < len(pressures):
                        stroke.points[i].pressure = float(pressures[i])

                strokes_created += 1

        return {
            "success": True,
            "message": f"Drew {strokes_created} stroke(s) on frame {frame_number} of '{gp_obj.name}'",
            "gp_object": gp_obj.name,
            "layer_name": layer_name,
            "frame": frame_number,
            "strokes_count": strokes_created,
        }
