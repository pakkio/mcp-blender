import bpy
from mathutils import Vector

from .base import ToolBase


def _get_or_create_collection_path(path: str) -> "bpy.types.Collection":
    """Create (or reuse) each segment of a '/'-separated nested collection path.

    Reuse is scoped to "already a child of this exact parent" -- a global
    name lookup would find and silently relink an unrelated same-named
    collection from elsewhere in the file (e.g. a repeated leaf segment like
    "Details" under two different parents), corrupting whatever hierarchy it
    was previously part of. If the name collides globally but isn't already
    positioned here, bpy.data.collections.new() auto-suffixes it instead.
    """
    parent = bpy.context.scene.collection
    col = parent
    for segment in path.split("/"):
        segment = segment.strip()
        if not segment:
            continue
        existing = next((c for c in parent.children if c.name == segment), None)
        if existing is None:
            existing = bpy.data.collections.new(segment)
            parent.children.link(existing)
        col = existing
        parent = col
    return col


def _relink_to_collection(obj: "bpy.types.Object", collection: "bpy.types.Collection") -> None:
    for existing in list(obj.users_collection):
        existing.objects.unlink(obj)
    collection.objects.link(obj)


def _build_group(spec: dict, keep_transform: bool, rename_members: bool) -> dict:
    name = spec.get("name")
    object_names = spec.get("objects") or []
    if not name:
        return {"success": False, "message": "each group requires a 'name'"}

    objects = []
    missing = []
    for obj_name in object_names:
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            missing.append(obj_name)
        else:
            objects.append(obj)
    if missing:
        return {"success": False, "message": f"Object(s) not found: {', '.join(missing)}"}

    collection_path = spec.get("collection_path")
    collection = _get_or_create_collection_path(collection_path) if collection_path else None
    if collection is not None:
        for obj in objects:
            _relink_to_collection(obj, collection)

    root_empty = None
    if spec.get("root_empty", True) and objects:
        median = sum((obj.matrix_world.translation for obj in objects), Vector()) / len(objects)
        empty_data = bpy.data.objects.new(name, None)
        empty_data.empty_display_type = "PLAIN_AXES"
        empty_data.location = median
        (collection or bpy.context.scene.collection).objects.link(empty_data)
        root_empty = empty_data

        for obj in objects:
            if keep_transform:
                world = obj.matrix_world.copy()
            obj.parent = root_empty
            if keep_transform:
                obj.matrix_world = world
            else:
                obj.matrix_parent_inverse = root_empty.matrix_world.inverted()

    if rename_members and root_empty is not None:
        for i, obj in enumerate(objects):
            obj.name = f"{name}_part{i:02d}"

    child_results = []
    for child_spec in spec.get("children") or []:
        child_result = _build_group(child_spec, keep_transform, rename_members)
        child_results.append(child_result)
        if child_result.get("success") and root_empty is not None:
            child_empty_name = child_result.get("root_empty")
            child_empty = bpy.data.objects.get(child_empty_name) if child_empty_name else None
            if child_empty is not None:
                if keep_transform:
                    world = child_empty.matrix_world.copy()
                child_empty.parent = root_empty
                if keep_transform:
                    child_empty.matrix_world = world
                else:
                    child_empty.matrix_parent_inverse = root_empty.matrix_world.inverted()

    return {
        "success": True,
        "name": name,
        "collection": collection.name if collection else None,
        "root_empty": root_empty.name if root_empty else None,
        "objects": [obj.name for obj in objects],
        "children": child_results,
    }


class OrganizeSceneHierarchyTool(ToolBase):
    name = "organize_scene_hierarchy"
    description = (
        "Build a multi-level semantic grouping in one call: nested collections plus an empty-parent "
        "hierarchy over a set of objects. Use after any multi-part build so parts aren't left loose at scene root."
    )

    def execute(self, params: dict) -> dict:
        groups = params.get("groups")
        if not groups or not isinstance(groups, list):
            return {"success": False, "message": "'groups' (non-empty list) is required"}

        keep_transform = bool(params.get("keep_transform", True))
        rename_members = bool(params.get("rename_members", False))

        results = []
        for spec in groups:
            results.append(_build_group(spec, keep_transform, rename_members))

        failed = [r for r in results if not r.get("success")]
        if failed:
            return {
                "success": False,
                "message": "; ".join(r["message"] for r in failed),
                "groups": results,
            }

        return {
            "success": True,
            "message": f"Organized {len(results)} top-level group(s)",
            "groups": results,
        }
