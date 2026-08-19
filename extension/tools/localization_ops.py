"""Localized (re)naming of structural nodes (collections, Empties, objects, meshes)
into a target language's vocabulary, plus alphabetical sorting and re-linking.
"""

import re
from typing import Any

import bpy

from .base import ToolBase

CATEGORY_TRANSLATIONS = {
    "it": {
        # Categories / Collections
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
        "collection": "Collezione",
        "master": "Principale",
        "assets": "Risorse",
        "materials": "Materiali",
        "textures": "Texture",
        # Major Objects
        "chair": "Sedia",
        "chairs": "Sedie",
        "armchair": "Poltrona",
        "armchairs": "Poltrone",
        "stool": "Sgabello",
        "sofa": "Divano",
        "couch": "Divano",
        "table": "Tavolo",
        "tables": "Tavoli",
        "desk": "Scrivania",
        "shelf": "Scaffale",
        "cabinet": "Mobile",
        "closet": "Armadio",
        "bed": "Letto",
        "lamp": "Lampada",
        "lamps": "Lampade",
        "light": "Luce",
        "bulb": "Lampadina",
        "spotlight": "Faretto",
        "camera": "Fotocamera",
        "car": "Auto",
        "cars": "Auto",
        "vehicle": "Veicolo",
        "truck": "Camion",
        "boat": "Barca",
        "plane": "Aereo",
        "tree": "Albero",
        "trees": "Alberi",
        "plant": "Pianta",
        "plants": "Piante",
        "flower": "Fiore",
        "grass": "Erba",
        "bush": "Cespuglio",
        "rock": "Roccia",
        "rocks": "Rocce",
        "stone": "Pietra",
        "box": "Scatola",
        "boxes": "Scatole",
        "crate": "Cassa",
        "barrel": "Barile",
        "bottle": "Bottiglia",
        "cup": "Tazza",
        "glass": "Bicchiere",
        "plate": "Piatto",
        "door": "Porta",
        "doors": "Porte",
        "window": "Finestra",
        "windows": "Finestre",
        "wall": "Parete",
        "walls": "Pareti",
        "floor": "Pavimento",
        "roof": "Tetto",
        "ceiling": "Soffitto",
        "pillar": "Pilastro",
        "column": "Colonna",
        "stairs": "Scale",
        "sword": "Spada",
        "shield": "Scudo",
        "gun": "Pistola",
        "wheel": "Ruota",
        "wheels": "Ruote",
        # Subparts
        "tire": "Pneumatico",
        "tires": "Pneumatici",
        "rim": "Cerchione",
        "rims": "Cerchioni",
        "hood": "Cofano",
        "trunk_car": "Baule",
        "windshield": "Parabrezza",
        "bumper": "Paraurti",
        "exhaust": "Scappamento",
        "mirror": "Specchietto",
        "seat": "Sedile",
        "seats": "Sedili",
        "back": "Schienale",
        "backrest": "Schienale",
        "arm": "Braccio",
        "armrest": "Bracciolo",
        "armrests": "Braccioli",
        "leg": "Gamba",
        "legs": "Gambe",
        "base": "Base",
        "top": "Piano",
        "frame": "Telaio",
        "handle": "Maniglia",
        "handles": "Maniglie",
        "cover": "Copertura",
        "cushion": "Cuscino",
        "cushions": "Cuscini",
        "screw": "Vite",
        "screws": "Viti",
        "bolt": "Bullone",
        "bolts": "Bulloni",
        "pedal": "Pedale",
        "chain": "Catena",
        "mesh": "Mesh",
        "root": "Radice",
        "body": "Corpo",
        "head": "Testa",
        # Directional and relative terms
        "left": "sinistro",
        "right": "destro",
        "front": "anteriore",
        "back": "posteriore",
        "rear": "posteriore",
        "top": "superiore",
        "bottom": "inferiore",
        "inside": "interno",
        "outside": "esterno",
        # Materials
        "wood": "Legno",
        "metal": "Metallo",
        "plastic": "Plastica",
        "glass": "Vetro",
        "leather": "Pelle",
        "fabric": "Tessuto",
        "gold": "Oro",
        "silver": "Argento",
        "bronze": "Bronzo",
        "chrome": "Cromo",
        "brass": "Ottone",
        "steel": "Acciaio",
        "copper": "Rame",
        "iron": "Ferro",
        "rubber": "Gomma",
        "stone": "Pietra",
        "concrete": "Cemento",
        "marble": "Marmo",
        # Sketchfab & 3D Exporter Transliterations
        "nogi": "Gambe",
        "noga": "Gamba",
        "spinka": "Schienale",
        "sidenie": "Sedile",
        "obod": "Bordo",
        "obruch": "Cerchio",
        "perekladina": "Traversa",
        "perekladini": "Traverse",
        "setka": "Rete",
        "bolti": "Bulloni",
        "bolt": "Bullone",
        "fixator": "Fissaggio",
        "koleso": "Ruota",
        "kolesa": "Ruote",
        "kuzov": "Carrozzeria",
        "fara": "Faro",
        "fary": "Fari",
        "rul": "Volante",
        "ruchka": "Maniglia",
        "dver": "Porta",
        # Primitives
        "cube": "Cubo",
        "cylinder": "Cilindro",
        "sphere": "Sfera",
        "icosphere": "Icosfera",
        "plane": "Piano",
        "cone": "Cono",
        "torus": "Toro",
        "suzanne": "Scimmia",
        "monkey": "Scimmia",
        "empty": "Vuoto",
    },
    "en": {
        # Cleanup dictionary (Russian / non-English terms to clean English)
        "nogi": "Legs",
        "noga": "Leg",
        "spinka": "Backrest",
        "sidenie": "Seat",
        "obod": "Rim",
        "obruch": "Ring",
        "perekladina": "Crossbar",
        "perekladini": "Crossbars",
        "setka": "Mesh_Grid",
        "bolti": "Bolts",
        "fixator": "Fixator",
        "koleso": "Wheel",
        "kolesa": "Wheels",
        "kuzov": "Car_Body",
        "fara": "Headlight",
        "fary": "Headlights",
        "rul": "Steering_Wheel",
        "ruchka": "Handle",
        "dver": "Door",
        "left": "Left",
        "right": "Right",
        "front": "Front",
        "back": "Back",
        "rear": "Rear",
        "top": "Top",
        "bottom": "Bottom",
    },
}


GENERIC_NAMES = {
    "cube", "cylinder", "sphere", "icosphere", "plane", "cone", "torus",
    "suzanne", "monkey", "empty", "obj", "mesh", "object", "default",
    "node", "primitive", "submesh", "part", "element"
}
def _call_llm_rename(objects_info: list[dict], lang: str) -> dict[str, str]:
    """Call OpenAI or Anthropic LLM to semantically translate and organize names."""
    import os
    import json
    import urllib.request
    import urllib.parse
    from pathlib import Path
    from ..config import load_env_vars

    load_env_vars()
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if not anthropic_key and not openai_key:
        return {}

    system_prompt = (
        "You are an expert 3D model semantic organizer and translator. "
        "Your task is to analyze a list of 3D object names from an imported model and translate/rename them "
        f"into a clean, logical semantic hierarchy in '{lang}'. "
        "Remove all random exporter suffixes (like hashes, GUIDs, exporter tags). "
        "Keep generic names (like cube, cylinder, empty, mesh) generic if they have no specific meaning, "
        "but translate specific terms (like wheel, leg, table, door) to proper anatomical/mechanical names "
        f"in the target language '{lang}' (e.g. Ruota, Gamba, Tavolo, Portella). "
        "You MUST return ONLY a JSON object mapping the exact old names to the proposed new names: "
        '{"old_name": "NewName", "another_old_name": "AnotherNewName"}'
    )

    user_content = f"Here is the list of objects in the hierarchy:\n{json.dumps(objects_info, indent=2)}"

    headers = {"Content-Type": "application/json"}
    
    # Try Anthropic Claude first
    if anthropic_key:
        url = "https://api.anthropic.com/v1/messages"
        headers.update({
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01"
        })
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_content}]
        }
    # Fallback to OpenAI GPT-4o
    elif openai_key:
        url = "https://api.openai.com/v1/chat/completions"
        headers.update({
            "Authorization": f"Bearer {openai_key}"
        })
        payload = {
            "model": "gpt-4o",
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
        }
    else:
        return {}

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))

        if anthropic_key:
            content_text = response_data["content"][0]["text"]
        else:
            content_text = response_data["choices"][0]["message"]["content"]

        # Parse JSON output from LLM
        # Look for JSON block in case Claude wrapped it in markdown
        match = re.search(r"\{.*\}", content_text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        return json.loads(content_text)
    except Exception as e:
        print(f"[MCP Bridge] LLM renaming request failed: {e}")
        return {}



def _localize_name(name: str, vocab: dict) -> str:
    """Translate compound keywords, strip exporter suffixes, and preserve indexing."""
    if not name:
        return name

    clean = name
    # Strip Sketchfab / glTF duplicate export suffixes like __0, _primitive0, .fbx, .gltf
    clean = re.sub(r"__\d+$", "", clean)
    clean = re.sub(r"_(primitive|submesh)\d*$", "", clean, flags=re.I)
    clean = re.sub(r"\.(fbx|gltf|glb|obj|blend|dae)$", "", clean, flags=re.I)

    # Strip hex hashes and Sketchfab tags
    clean = re.sub(r"[_\-\s][a-fA-F0-9]{32}\b", "", clean)
    clean = re.sub(r"[_\-\s](?=.*\d)[a-fA-F0-9]{7,12}\b", "", clean)
    clean = re.sub(r"[_\-\s]sketchfab\b", "", clean, flags=re.I)

    # Skip renaming if the name is purely generic (e.g. Cube.001, obj_01, Mesh_3)
    clean_lower = clean.lower().strip()
    clean_base = re.sub(r"[\d\.]+$", "", clean_lower).strip("_-. ")
    if clean_base in GENERIC_NAMES:
        return clean

    # Normalize technical root names
    if clean.lower() in ("rootnode", "sketchfab_model", "root_empty", "node"):
        clean = "Modello" if vocab.get("scene") == "Scena" else "Model"

    parts = re.split(r"([_\-\s\.]+|\d+)", clean)
    translated = []
    for p in parts:
        if not p:
            continue
        if re.match(r"^[_\-\s\.]+$", p) or p.isdigit():
            translated.append(p)
        else:
            word_key = p.lower().strip()
            trans = vocab.get(word_key, p)
            if p.isupper() and len(p) <= 3:
                translated.append(trans.upper())
            elif p and p[0].isupper():
                translated.append(trans.capitalize())
            else:
                translated.append(trans)

    result = "".join(translated)
    return result if result else name


def _relink_sorted(collection: bpy.types.Collection) -> None:
    """Alphabetically re-link children and objects in a collection."""
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


def _regen_object(obj: bpy.types.Object, vocab: dict, rename_mesh: bool = True) -> dict:
    """Localize object name and its underlying mesh data block."""
    old_name = obj.name
    new_name = _localize_name(old_name, vocab)
    renamed = False

    if new_name != old_name:
        try:
            obj.name = new_name
            renamed = True
        except Exception:
            pass

    # Rename underlying mesh data if it was matching or has exporter suffix
    if rename_mesh and obj.data and hasattr(obj.data, "name"):
        old_mesh_name = obj.data.name
        if (
            old_mesh_name == old_name
            or "__" in old_mesh_name
            or any(k in old_mesh_name.lower() for k in vocab)
        ):
            new_mesh_name = _localize_name(old_mesh_name, vocab)
            if new_mesh_name != old_mesh_name:
                try:
                    obj.data.name = new_mesh_name
                except Exception:
                    pass

    return {
        "old_name": old_name,
        "new_name": obj.name,
        "type": obj.type,
        "renamed": renamed,
        "parent": obj.parent.name if obj.parent else None,
    }


def _regen_collection(collection: bpy.types.Collection, vocab: dict, rename_objects: bool = True) -> dict:
    """Recursively localize collection names and member objects."""
    old_name = collection.name
    new_name = _localize_name(old_name, vocab)
    renamed = False
    if new_name != old_name:
        try:
            collection.name = new_name
            renamed = True
        except AttributeError:
            new_name = old_name

    if renamed:
        wrapper = bpy.data.objects.get(old_name)
        if wrapper is not None and wrapper.type == "EMPTY":
            wrapper.name = collection.name

    objects_reports = []
    if rename_objects:
        for obj in list(collection.objects):
            objects_reports.append(_regen_object(obj, vocab))

    children_reports = [
        _regen_collection(child, vocab, rename_objects=rename_objects)
        for child in collection.children
    ]
    _relink_sorted(collection)

    return {
        "old_name": old_name,
        "new_name": collection.name,
        "renamed": renamed,
        "objects_count": len(collection.objects),
        "objects": objects_reports,
        "children": children_reports,
    }


class RegenElementNamesTool(ToolBase):
    name = "regen_element_names"
    description = (
        "Rename scene elements (collections, Empties, selected objects, meshes, parts) into "
        "the target language's vocabulary (default Italian 'it', or 'en'), and re-link "
        "collection children and objects in alphabetical order."
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
        target_objects = params.get("objects")
        rename_meshes = bool(params.get("rename_meshes", True))
        use_llm = bool(params.get("use_llm", False))

        # Collect target objects
        objects_to_rename = []
        is_selection = False
        is_single_obj = False
        root_col = None

        if target_objects and isinstance(target_objects, list):
            is_selection = True
            for obj_id in target_objects:
                obj = obj_id if isinstance(obj_id, bpy.types.Object) else bpy.data.objects.get(str(obj_id))
                if obj:
                    if obj not in objects_to_rename:
                        objects_to_rename.append(obj)
                    for child in obj.children_recursive:
                        if child not in objects_to_rename:
                            objects_to_rename.append(child)
        elif element:
            obj = bpy.data.objects.get(element)
            col = bpy.data.collections.get(element)
            if obj is not None and col is None:
                is_single_obj = True
                objects_to_rename = [obj] + list(obj.children_recursive)
            else:
                root_col = col
                if root_col is None and obj is not None and obj.type == "EMPTY":
                    root_col = bpy.data.collections.get(obj.name)
                if root_col is None:
                    return {"success": False, "message": f"No collection or Object named '{element}' found"}
        else:
            root_col = bpy.context.scene.collection

        # If LLM is requested, try to use it
        llm_success = False
        if use_llm:
            if not objects_to_rename and root_col:
                def collect_recursive(c):
                    for o in c.objects:
                        if o not in objects_to_rename:
                            objects_to_rename.append(o)
                    for child_col in c.children:
                        collect_recursive(child_col)
                collect_recursive(root_col)

            objects_info = []
            for obj in objects_to_rename:
                objects_info.append({
                    "name": obj.name,
                    "type": obj.type,
                    "parent": obj.parent.name if obj.parent else None
                })

            if objects_info:
                mapping = _call_llm_rename(objects_info, lang)
                if mapping:
                    llm_success = True
                    renamed_objs = []
                    for obj in objects_to_rename:
                        old_name = obj.name
                        new_name = mapping.get(old_name)
                        renamed = False
                        if new_name and new_name != old_name:
                            try:
                                obj.name = new_name
                                renamed = True
                            except Exception:
                                pass
                        
                        if rename_meshes and obj.data and hasattr(obj.data, "name"):
                            if obj.data.name == old_name:
                                try:
                                    obj.data.name = obj.name
                                except Exception:
                                    pass

                        renamed_objs.append({
                            "old_name": old_name,
                            "new_name": obj.name,
                            "type": obj.type,
                            "renamed": renamed,
                            "parent": obj.parent.name if obj.parent else None,
                        })

                    if not is_selection and not is_single_obj and root_col:
                        report = _regen_collection(root_col, vocab, rename_objects=False)
                        return {
                            "success": True,
                            "message": f"Regenerated names using LLM for '{report['new_name']}' hierarchy (lang={lang})",
                            "lang": lang,
                            "objects": renamed_objs,
                            "root": report,
                        }
                    else:
                        msg = "selected object(s)" if is_selection else f"object hierarchy '{objects_to_rename[0].name}'"
                        total_renamed = sum(1 for r in renamed_objs if r["renamed"])
                        return {
                            "success": True,
                            "message": f"Regenerated names using LLM for {msg} ({total_renamed} changed, lang={lang})",
                            "lang": lang,
                            "objects": renamed_objs,
                        }

        # Fallback to local dictionary translation
        if is_selection or is_single_obj:
            renamed_objs = []
            for obj in objects_to_rename:
                rep = _regen_object(obj, vocab, rename_mesh=rename_meshes)
                renamed_objs.append(rep)
            total_renamed = sum(1 for r in renamed_objs if r["renamed"])
            msg = "selected object(s)" if is_selection else f"object hierarchy '{objects_to_rename[0].name}'"
            return {
                "success": True,
                "message": f"Regenerated names for {msg} ({total_renamed} changed, lang={lang})",
                "lang": lang,
                "objects": renamed_objs,
            }

        report = _regen_collection(root_col, vocab, rename_objects=True)
        return {
            "success": True,
            "message": f"Regenerated names for '{report['new_name']}' hierarchy (lang={lang})",
            "lang": lang,
            "root": report,
        }
