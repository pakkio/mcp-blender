"""Localized (re)naming of the structural nodes organize_scene_hierarchy
builds -- category collections and their matching root-Empty wrapper objects
-- plus a real alphabetical re-link of every collection's children and
objects. bpy.data.collections.children/objects order is pure link order
(insertion order), not display order: Blender's Outliner applies its own
sort for display, but the underlying data order is whatever .link() calls
left it in, so "alphabetical structure" has to be enforced by unlinking and
relinking in sorted order.
"""

import bpy

from .base import ToolBase

# Small, explicit, extensible per-language vocabulary for the category labels
# organize_scene_hierarchy's own examples use (Furniture, Characters, Props,
# Architecture...) plus a few more common ones. This is a keyword lookup, not
# machine translation -- names not in the vocabulary are left untouched.
CATEGORY_TRANSLATIONS = {
    "it": {
        "furniture": "Arredamento",
        "characters": "Personaggi",
        "props": "Oggetti",
        "architecture": "Architettura",
        "vehicles": "Veicoli",
        "environment": "Ambiente",
        "lights": "Luci",
        "cameras": "Fotocamere",
        "imports": "Importazioni",
        "generated": "Generati",
        "scene": "Scena",
        "chairs": "Sedie",
        "tables": "Tavoli",
    },
}


def _translate(name: str, vocab: dict) -> str:
    return vocab.get(name.strip().lower(), name)


def _relink_sorted(collection: "bpy.types.Collection") -> None:
    child_cols = sorted(collection.children, key=lambda c: c.name.lower())
    for c in list(child_cols):
        collection.children.unlink(c)
    for c in child_cols:
        collection.children.link(c)

    objs = sorted(collection.objects, key=lambda o: o.name.lower())
    for o in list(objs):
        collection.objects.unlink(o)
    for o in objs:
        collection.objects.link(o)


def _regen_collection(collection: "bpy.types.Collection", vocab: dict) -> dict:
    old_name = collection.name
    new_name = _translate(old_name, vocab)
    renamed = False
    if new_name != old_name:
        try:
            collection.name = new_name  # bpy.data auto-suffixes on collision
            renamed = True
        except AttributeError:
            # The scene's implicit master collection has a read-only name --
            # leave it alone rather than fail the whole operation over it.
            new_name = old_name

    if renamed:
        # Keep any matching root-Empty wrapper (organize_scene_hierarchy
        # creates one with the same name) in sync.
        wrapper = bpy.data.objects.get(old_name)
        if wrapper is not None and wrapper.type == "EMPTY":
            wrapper.name = collection.name

    children_reports = [_regen_collection(child, vocab) for child in collection.children]
    _relink_sorted(collection)

    return {
        "old_name": old_name,
        "new_name": collection.name,
        "renamed": renamed,
        "objects_count": len(collection.objects),
        "is_empty_node": len(collection.objects) == 0 and len(collection.children) == 0,
        # Mesh leaves aren't touched by the keyword vocabulary (it only covers
        # category-level names) -- listed with their parent so a caller doing
        # vision-assisted naming can give the model context about what whole
        # object/category a part belongs to, not just an isolated close-up.
        "objects": [
            {"name": obj.name, "type": obj.type, "parent": obj.parent.name if obj.parent else None}
            for obj in collection.objects
        ],
        "children": children_reports,
    }


class RegenElementNamesTool(ToolBase):
    name = "regen_element_names"
    description = (
        "Rename the structural collection/Empty nodes under a scene element into a target "
        "language's category vocabulary (default Italian, param 'lang'), and re-link every "
        "collection's children and objects in alphabetical order. Nodes with zero objects "
        "(scaffolded but not yet populated) are renamed and kept, never skipped or deleted."
    )

    def execute(self, params: dict) -> dict:
        lang = (params.get("lang") or "it").strip().lower()
        vocab = CATEGORY_TRANSLATIONS.get(lang)
        if vocab is None:
            return {
                "success": False,
                "message": f"Unsupported lang '{lang}'. Supported: {', '.join(sorted(CATEGORY_TRANSLATIONS))}",
            }

        element = params.get("element")
        if element:
            root = bpy.data.collections.get(element)
            if root is None:
                obj = bpy.data.objects.get(element)
                if obj is not None and obj.type == "EMPTY":
                    # An Empty wrapper doesn't own a collection of its own --
                    # fall back to any same-named collection, which is how
                    # organize_scene_hierarchy pairs them.
                    root = bpy.data.collections.get(obj.name)
            if root is None:
                return {"success": False, "message": f"No collection or Empty named '{element}' found"}
        else:
            root = bpy.context.scene.collection

        report = _regen_collection(root, vocab)
        return {
            "success": True,
            "message": f"Regenerated names for '{report['new_name']}' (lang={lang})",
            "lang": lang,
            "root": report,
        }
