import bpy

from .base import ToolBase


class GetObjectInfoTool(ToolBase):
    name = "get_object_info"
    description = "Get detailed information about a specific Blender object."

    def execute(self, params: dict) -> dict:
        name = params.get("name")
        if not name:
            return {"success": False, "message": "'name' parameter is required"}

        obj = bpy.data.objects.get(name)
        if obj is None:
            return {"success": False, "message": f"Object '{name}' not found"}

        active_obj = bpy.context.active_object
        is_active = (active_obj == obj)
        is_selected = obj.select_get()

        info = {
            "success": True,
            "name": obj.name,
            "type": obj.type,
            "location": [round(v, 4) for v in obj.location],
            "rotation_euler": [round(v, 4) for v in obj.rotation_euler],
            "scale": [round(v, 4) for v in obj.scale],
            "dimensions": [round(v, 4) for v in obj.dimensions],
            "hide_viewport": obj.hide_get(),
            "hide_render": obj.hide_render,
            "is_active": is_active,
            "is_selected": is_selected,
            "parent": obj.parent.name if obj.parent else None,
            "children": [child.name for child in obj.children],
            "collections": [c.name for c in obj.users_collection],
        }

        # Bounding box
        if hasattr(obj, "bound_box") and obj.bound_box:
            info["bound_box"] = [[round(coord, 4) for coord in pt] for pt in obj.bound_box]

        # Materials
        materials = []
        for slot_idx, slot in enumerate(obj.material_slots):
            materials.append({
                "slot_index": slot_idx,
                "material_name": slot.material.name if slot.material else None,
            })
        info["materials"] = materials

        # Modifiers
        modifiers = []
        for mod in obj.modifiers:
            mod_data = {
                "name": mod.name,
                "type": mod.type,
                "show_viewport": mod.show_viewport,
                "show_render": mod.show_render,
            }
            # Extract common properties
            for prop in ("levels", "render_levels", "width", "segments", "count", "thickness", "ratio", "operation"):
                if hasattr(mod, prop):
                    val = getattr(mod, prop)
                    mod_data[prop] = val
            modifiers.append(mod_data)
        info["modifiers"] = modifiers

        # Type-specific data
        if obj.type == "MESH" and obj.data:
            mesh = obj.data
            info["mesh_data"] = {
                "vertices_count": len(mesh.vertices),
                "edges_count": len(mesh.edges),
                "polygons_count": len(mesh.polygons),
                "uv_layers": [uv.name for uv in mesh.uv_layers] if hasattr(mesh, "uv_layers") else [],
            }
        elif obj.type == "LIGHT" and obj.data:
            light = obj.data
            info["light_data"] = {
                "type": light.type,
                "energy": light.energy,
                "color": [round(c, 4) for c in light.color],
                "spot_size": getattr(light, "spot_size", None),
                "spot_blend": getattr(light, "spot_blend", None),
            }
        elif obj.type == "CAMERA" and obj.data:
            cam = obj.data
            info["camera_data"] = {
                "type": cam.type,
                "lens": cam.lens,
                "clip_start": cam.clip_start,
                "clip_end": cam.clip_end,
                "sensor_width": cam.sensor_width,
                "dof_focus_object": cam.dof.focus_object.name if (hasattr(cam, "dof") and cam.dof and cam.dof.focus_object) else None,
            }
        elif obj.type == "FONT" and obj.data:
            text_data = obj.data
            info["text_data"] = {
                "body": text_data.body,
                "size": text_data.size,
                "extrude": text_data.extrude,
            }

        # Animation summary
        if obj.animation_data and obj.animation_data.action:
            action = obj.animation_data.action
            curves = []
            if hasattr(action, "fcurves"):
                curves = list(action.fcurves)
            elif hasattr(action, "layers"):
                for layer in action.layers:
                    for strip in layer.strips:
                        if hasattr(strip, "channelbags"):
                            for cb in strip.channelbags:
                                if hasattr(cb, "fcurves"):
                                    curves.extend(cb.fcurves)
                        elif hasattr(strip, "channelbag"):
                            cb = strip.channelbag(obj.animation_data.action_slot) if (hasattr(obj, "animation_data") and hasattr(obj.animation_data, "action_slot")) else None
                            if cb and hasattr(cb, "fcurves"):
                                curves.extend(cb.fcurves)
            info["animation"] = {
                "action_name": action.name,
                "frame_range": [round(f, 1) for f in action.frame_range] if hasattr(action, "frame_range") else [0.0, 0.0],
                "fcurves_count": len(curves),
                "fcurves_paths": list({fc.data_path for fc in curves}),
            }

        # Custom properties
        custom_props = {}
        for key in obj.keys():
            if key not in ("_RNA_UI", "cycles"):
                val = obj[key]
                if isinstance(val, (int, float, str, bool, list)):
                    custom_props[key] = val
        if custom_props:
            info["custom_properties"] = custom_props

        info["message"] = f"Retrieved info for object '{obj.name}' ({obj.type})"
        return info
