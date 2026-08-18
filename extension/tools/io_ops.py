import os
import bpy

from . import axis_utils
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
    description = (
        "Import 3D model files (GLTF, GLB, FBX, OBJ, STL, USD, BLEND) into Blender, "
        "with optional source axis conversion so Y-up files don't land on their side."
    )

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

        forward_axis, up_axis, axis_error = axis_utils.resolve_axes(
            params.get("forward_axis"), params.get("up_axis")
        )
        if axis_error:
            return {"success": False, "message": axis_error}

        # Nothing to do when the request is exactly the importer's own default.
        if forward_axis and axis_utils.is_format_default(file_format, forward_axis, up_axis):
            forward_axis = up_axis = None

        # Axes handled by the operator itself, or by rotating what came out?
        want_native = bool(forward_axis) and axis_utils.has_native_axis_args(file_format)
        native_applied = False

        prev_objects = set(bpy.data.objects.keys())

        try:
            if file_format in ("GLTF", "GLB"):
                bpy.ops.import_scene.gltf(filepath=filepath)
            elif file_format == "FBX":
                native_applied = self._call_import(
                    bpy.ops.import_scene.fbx, filepath, forward_axis, up_axis, want_native
                )
            elif file_format == "OBJ":
                op = bpy.ops.wm.obj_import if hasattr(bpy.ops.wm, "obj_import") else bpy.ops.import_scene.obj
                native_applied = self._call_import(op, filepath, forward_axis, up_axis, want_native)
            elif file_format == "STL":
                op = bpy.ops.wm.stl_import if hasattr(bpy.ops.wm, "stl_import") else bpy.ops.import_mesh.stl
                native_applied = self._call_import(op, filepath, forward_axis, up_axis, want_native)
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

        new_names = list(set(bpy.data.objects.keys()) - prev_objects)

        new_objects = [bpy.data.objects[name] for name in new_names]

        axis_conversion = None
        if forward_axis and not native_applied:
            try:
                roots = axis_utils.apply_conversion(new_objects, forward_axis, up_axis)
            except Exception as exc:
                return {"success": False, "message": f"Axis conversion failed: {exc}"}
            axis_conversion = f"rotated {roots} root object(s) from {forward_axis} forward / {up_axis} up"
        elif forward_axis:
            axis_conversion = f"importer converted from {forward_axis} forward / {up_axis} up"

        message = f"Imported {len(new_names)} object(s) from '{filepath}'"
        if axis_conversion:
            message += f" ({axis_conversion})"

        # Always look at the result: axis metadata can be right and the model
        # still be authored upside down.
        check_requested = params.get("check_orientation", True)
        auto_orient = bool(params.get("auto_orient", False))
        orientation = None
        if check_requested or auto_orient:
            try:
                orientation = axis_utils.analyze_orientation(new_objects)
            except Exception as exc:
                orientation = {"verdict": "unknown", "reason": f"orientation check failed: {exc}"}

            verdict = orientation.get("verdict")
            if auto_orient and verdict in ("suspect_upside_down", "suspect_lying_down"):
                roots = axis_utils.apply_fix(
                    new_objects, orientation["fix_axis"], orientation["fix_degrees"]
                )
                orientation["corrected"] = (
                    f"rotated {roots} root object(s) {orientation['fix_degrees']}° "
                    f"about {orientation['fix_axis']}"
                )
                orientation["verdict_after_fix"] = axis_utils.analyze_orientation(new_objects).get("verdict")
                message += f" — {orientation['corrected']}"
            elif verdict in ("suspect_upside_down", "suspect_lying_down"):
                message += (
                    f" — WARNING: {verdict.replace('suspect_', '').replace('_', ' ')} "
                    f"({orientation.get('reason')}); re-import with auto_orient=true, or with "
                    f"up_axis set to the file's real up axis"
                )

        return {
            "success": True,
            "message": message,
            "imported_objects": new_names,
            "filepath": filepath,
            "forward_axis": forward_axis,
            "up_axis": up_axis,
            "orientation": orientation,
        }

    @staticmethod
    def _call_import(operator, filepath, forward_axis, up_axis, want_native) -> bool:
        """Run an import operator, passing axis kwargs when asked for.

        Returns True when the operator itself did the conversion. Blender
        renamed these properties between the legacy Python importers and the
        current C++ ones, so if the kwargs are rejected we import plainly and
        let the caller rotate the result instead of silently ignoring the axes.
        """
        if not want_native:
            operator(filepath=filepath)
            return False
        try:
            operator(filepath=filepath, **axis_utils.native_axis_kwargs(operator, forward_axis, up_axis))
            return True
        except TypeError:
            operator(filepath=filepath)
            return False
