import os
import bpy

from .base import ToolBase


class ExportSceneTool(ToolBase):
    name = "export_scene"
    description = "Export the scene or selected objects to 3D file formats (GLTF, GLB, FBX, OBJ, STL, USD)."

    def execute(self, params: dict) -> dict:
        filepath = params.get("filepath")
        if not filepath:
            return {"success": False, "message": "'filepath' is required"}

        file_format = (params.get("file_format") or "GLB").upper()
        selected_only = params.get("selected_only", False)

        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)

        try:
            if file_format in ("GLTF", "GLB"):
                export_format = "GLB" if file_format == "GLB" or filepath.lower().endswith(".glb") else "GLTF_EMBEDDED"
                gltf_kwargs = {
                    "filepath": filepath,
                    "export_format": export_format,
                    "use_selection": selected_only,
                    "export_apply": bool(params.get("apply_modifiers", True)),
                    "export_animations": bool(params.get("export_animations", True)),
                    "export_materials": "EXPORT" if params.get("export_materials", True) else "NONE",
                }
                if params.get("draco_compression", False):
                    gltf_kwargs["export_draco_mesh_compression_enable"] = True
                    if "draco_compression_level" in params:
                        gltf_kwargs["export_draco_mesh_compression_level"] = int(params["draco_compression_level"])

                if hasattr(bpy.ops.export_scene, "gltf"):
                    bpy.ops.export_scene.gltf(**gltf_kwargs)
            elif file_format == "FBX":
                bpy.ops.export_scene.fbx(
                    filepath=filepath,
                    use_selection=selected_only,
                    use_mesh_modifiers=bool(params.get("apply_modifiers", True)),
                    bake_anim=bool(params.get("export_animations", True)),
                )
            elif file_format == "OBJ":
                if hasattr(bpy.ops.wm, "obj_export"):
                    bpy.ops.wm.obj_export(filepath=filepath, export_selected_objects=selected_only)
                else:
                    bpy.ops.export_scene.obj(filepath=filepath, use_selection=selected_only)
            elif file_format == "STL":
                if hasattr(bpy.ops.wm, "stl_export"):
                    bpy.ops.wm.stl_export(filepath=filepath, export_selected_objects=selected_only)
                else:
                    bpy.ops.export_mesh.stl(filepath=filepath, use_selection=selected_only)
            elif file_format == "USD":
                bpy.ops.wm.usd_export(filepath=filepath, selected_objects_only=selected_only)
            else:
                return {"success": False, "message": f"Unsupported file format '{file_format}'"}
        except Exception as exc:
            return {"success": False, "message": f"Export failed: {exc}"}

        file_size_bytes = os.path.getsize(filepath) if os.path.exists(filepath) else 0

        return {
            "success": True,
            "message": f"Exported scene to '{filepath}' ({file_size_bytes} bytes)",
            "filepath": filepath,
            "file_format": file_format,
            "file_size_bytes": file_size_bytes,
        }


class ImportFileTool(ToolBase):
    name = "import_file"
    description = "Import 3D model files (GLTF, GLB, FBX, OBJ, STL, USD, BLEND) into Blender."

    def execute(self, params: dict) -> dict:
        filepath = params.get("filepath")
        if not filepath or not os.path.exists(filepath):
            return {"success": False, "message": f"File not found: '{filepath}'"}

        file_format = params.get("file_format")
        if not file_format:
            ext = os.path.splitext(filepath)[1].lower().lstrip(".")
            file_format = ext.upper()
        else:
            file_format = file_format.upper()

        prev_objects = set(bpy.data.objects.keys())

        try:
            if file_format in ("GLTF", "GLB"):
                bpy.ops.import_scene.gltf(filepath=filepath)
            elif file_format == "FBX":
                bpy.ops.import_scene.fbx(filepath=filepath)
            elif file_format == "OBJ":
                if hasattr(bpy.ops.wm, "obj_import"):
                    bpy.ops.wm.obj_import(filepath=filepath)
                else:
                    bpy.ops.import_scene.obj(filepath=filepath)
            elif file_format == "STL":
                if hasattr(bpy.ops.wm, "stl_import"):
                    bpy.ops.wm.stl_import(filepath=filepath)
                else:
                    bpy.ops.import_mesh.stl(filepath=filepath)
            elif file_format == "USD":
                bpy.ops.wm.usd_import(filepath=filepath)
            elif file_format == "BLEND":
                with bpy.data.libraries.load(filepath) as (data_from, data_to):
                    data_to.objects = data_from.objects
                for obj in data_to.objects:
                    if obj:
                        bpy.context.scene.collection.objects.link(obj)
            else:
                return {"success": False, "message": f"Unsupported import format '{file_format}'"}
        except Exception as exc:
            return {"success": False, "message": f"Import failed: {exc}"}

        new_objects = list(set(bpy.data.objects.keys()) - prev_objects)

        return {
            "success": True,
            "message": f"Imported {len(new_objects)} object(s) from '{filepath}'",
            "imported_objects": new_objects,
            "filepath": filepath,
        }
