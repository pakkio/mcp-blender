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

        # Check for GPv3 or standard GP
        gp_data = bpy.data.grease_pencils.new("LineArt_GPData") if hasattr(bpy.data, "grease_pencils") else bpy.data.grease_pencil.new("LineArt_GPData")
        gp_obj = bpy.data.objects.new("LineArt_Ink", gp_data)
        bpy.context.scene.collection.objects.link(gp_obj)

        # Add Line Art modifier
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
