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
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_DEFAULT_MODEL = "google/gemini-2.5-flash"


def _call_openrouter_json(system_prompt: str, user_content: str) -> dict:
    """POST a system/user prompt pair to OpenRouter and parse a JSON object out
    of the response. Shared by _call_llm_rename and _call_llm_classify.

    Uses OPENROUTER_API_KEY (with optional OPENROUTER_VISION_MODEL override) --
    the same provider/key convention as mcp_server's vlm.generate_text() and
    every other LLM-backed tool in this addon, and the only LLM key
    .env.example actually documents. This function replaces per-caller
    ANTHROPIC_API_KEY/OPENAI_API_KEY checks that this project's setup never
    tells users to set, which meant classification silently never fired and
    callers always fell through to the much cruder heuristic fallback.
    """
    import os
    import json
    import urllib.request
    from ..config import load_env_vars

    load_env_vars()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return {}

    model = os.environ.get("OPENROUTER_VISION_MODEL") or OPENROUTER_DEFAULT_MODEL
    payload = {
        "model": model,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ],
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        req = urllib.request.Request(
            OPENROUTER_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))

        content_text = response_data["choices"][0]["message"]["content"]
        # Look for a JSON block in case the model wrapped it in markdown
        match = re.search(r"\{.*\}", content_text, re.DOTALL)
        return json.loads(match.group(0)) if match else json.loads(content_text)
    except Exception as e:
        print(f"[MCP Bridge] OpenRouter LLM request failed: {e}")
        return {}


_REORG_LEVEL_RENAME_NOTE = {
    "LIGHT": (
        "Level: LIGHT -- be conservative. Only rename names that are clearly generic, garbled, or "
        "exporter-mangled (hashes, GUIDs, 'Cube.003', 'mesh_7'). Leave names alone if they already look "
        "intentional or descriptive."
    ),
    "STANDARD": "",
    "DEEP": (
        "Level: DEEP -- be thorough. Rename as many names as you reasonably can into clean, specific, "
        "semantic terms, even ones that already look partially reasonable, so the whole hierarchy reads "
        "consistently."
    ),
}


def _call_llm_rename(
    objects_info: list[dict], lang: str, custom_prompt: str = "", reorg_level: str = "STANDARD"
) -> dict[str, str]:
    """Semantically translate/organize object names via OpenRouter."""
    import json

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
    level_note = _REORG_LEVEL_RENAME_NOTE.get(reorg_level, "")
    if level_note:
        system_prompt += " " + level_note

    user_content = f"Here is the list of objects in the hierarchy:\n{json.dumps(objects_info, indent=2)}"
    if custom_prompt.strip():
        user_content += (
            "\n\nAdditional instructions from the user (follow these carefully, they take priority over "
            f"the generic guidance above): {custom_prompt.strip()}"
        )
    return _call_openrouter_json(system_prompt, user_content)



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


def _collect_renamed_pairs(report: dict) -> list[dict]:
    """Flatten a _regen_collection report tree into a flat old->new list,
    for a UI that wants a simple confirmation list rather than the nested
    collection/object tree."""
    pairs = []
    if report.get("renamed"):
        pairs.append({"old": report["old_name"], "new": report["new_name"]})
    for obj_rep in report.get("objects", []):
        if obj_rep.get("renamed"):
            pairs.append({"old": obj_rep["old_name"], "new": obj_rep["new_name"]})
    for child in report.get("children", []):
        pairs.extend(_collect_renamed_pairs(child))
    return pairs


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
        custom_prompt = str(params.get("custom_prompt") or "")
        reorg_level = str(params.get("reorg_level") or "STANDARD").strip().upper()

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
                mapping = _call_llm_rename(objects_info, lang, custom_prompt=custom_prompt, reorg_level=reorg_level)
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

                    obj_pairs = [
                        {"old": r["old_name"], "new": r["new_name"]} for r in renamed_objs if r["renamed"]
                    ]

                    if not is_selection and not is_single_obj and root_col:
                        report = _regen_collection(root_col, vocab, rename_objects=False)
                        return {
                            "success": True,
                            "message": f"Regenerated names using LLM for '{report['new_name']}' hierarchy (lang={lang})",
                            "lang": lang,
                            "objects": renamed_objs,
                            "root": report,
                            "renamed_pairs": obj_pairs + _collect_renamed_pairs(report),
                        }
                    else:
                        msg = "selected object(s)" if is_selection else f"object hierarchy '{objects_to_rename[0].name}'"
                        total_renamed = sum(1 for r in renamed_objs if r["renamed"])
                        return {
                            "success": True,
                            "message": f"Regenerated names using LLM for {msg} ({total_renamed} changed, lang={lang})",
                            "lang": lang,
                            "objects": renamed_objs,
                            "renamed_pairs": obj_pairs,
                        }

        # Fallback to local dictionary translation
        prompt_note = ""
        if custom_prompt.strip() and not llm_success:
            prompt_note = (
                " (custom_prompt ignored -- enable Use LLM Semantics)" if not use_llm
                else " (custom_prompt ignored -- LLM call unavailable/failed, check OPENROUTER_API_KEY)"
            )

        if is_selection or is_single_obj:
            renamed_objs = []
            for obj in objects_to_rename:
                rep = _regen_object(obj, vocab, rename_mesh=rename_meshes)
                renamed_objs.append(rep)
            total_renamed = sum(1 for r in renamed_objs if r["renamed"])
            msg = "selected object(s)" if is_selection else f"object hierarchy '{objects_to_rename[0].name}'"
            return {
                "success": True,
                "message": f"Regenerated names for {msg} ({total_renamed} changed, lang={lang}){prompt_note}",
                "lang": lang,
                "objects": renamed_objs,
                "renamed_pairs": [
                    {"old": r["old_name"], "new": r["new_name"]} for r in renamed_objs if r["renamed"]
                ],
            }

        report = _regen_collection(root_col, vocab, rename_objects=True)
        return {
            "success": True,
            "message": f"Regenerated names for '{report['new_name']}' hierarchy (lang={lang}){prompt_note}",
            "lang": lang,
            "root": report,
            "renamed_pairs": _collect_renamed_pairs(report),
        }


_REORG_LEVEL_CLASSIFY_NOTE = {
    "LIGHT": (
        "Level: LIGHT -- keep the breakdown coarse. Prefer fewer, larger sub-assemblies (aim for roughly "
        "2-4 groups total) over lots of small ones."
    ),
    "STANDARD": "",
    "DEEP": (
        "Level: DEEP -- break the assembly down as finely as reasonable. Prefer more, smaller, more "
        "specific sub-assemblies rather than a few broad ones."
    ),
}


def _call_llm_classify(
    parts_info: list[dict], lang: str, macro_name: str, custom_prompt: str = "", reorg_level: str = "STANDARD"
) -> dict:
    """Classify mesh loose parts into a macro/medium/micro grouping via OpenRouter.

    macro_name is the whole assembly being separated (e.g. 'Door') -- already
    the root Empty's name outside this call. This asks the LLM only for the
    medium tier (logical sub-assemblies, e.g. 'Frame', 'Panel', 'Hardware')
    and the micro tier (a clean name per individual part within its group).
    """
    import json

    system_prompt = (
        "You are an expert 3D model semantic analyzer. "
        "Given a list of separated mesh parts belonging to a single assembly "
        f"called '{macro_name}' (each part has an 'index', 'name', 'center' coordinates [X, Y, Z], and "
        "'materials' list), organize them into a two-level breakdown: "
        "medium-level functional sub-assemblies (intermediate groups), each containing "
        "micro-level individual parts. "
        "Use spatial position (nearby centers likely belong to the same sub-assembly) and material "
        "as strong signals, not just material alone -- e.g. for a door, group into sub-assemblies like "
        "'Telaio' (Frame), 'Pannello' (Panel), 'Ferramenta' (Hardware/hinges/handle), not one giant group "
        "per material. "
        f"For a car: 'Ruote' (Wheels), 'Portiere' (Doors), 'Vetri' (Glass), 'Scocca' (Chassis), 'Interni' (Interior). "
        f"For a human body: 'Testa' (Head), 'Braccio Sinistro' (Left Arm), 'Braccio Destro' (Right Arm), 'Gambe' (Legs), 'Busto' (Torso). "
        f"Translate every group and part name into '{lang}'. "
        "Every part index in the input MUST appear in exactly one group in the output -- never drop or "
        "duplicate an index, and avoid a single group swallowing more than half the parts unless the "
        "geometry genuinely has only one distinct area. "
        "Propose: "
        "1. A mapping of medium-level group names (e.g. 'Telaio', 'Ferramenta') to the list of part indices that belong to them. "
        "2. A mapping of each part index to a clean, specific micro-level name (e.g. 'Cerniera Superiore', 'Maniglia'). "
        "You MUST return ONLY a JSON object of this structure (no markdown wrapper, just raw JSON):\n"
        "{\n"
        "  \"groups\": {\n"
        "    \"GroupName1\": [0, 2, 4],\n"
        "    \"GroupName2\": [1, 3]\n"
        "  },\n"
        "  \"names\": {\n"
        "    \"0\": \"SemanticNameFor0\",\n"
        "    \"1\": \"SemanticNameFor1\",\n"
        "    \"2\": \"SemanticNameFor2\",\n"
        "    \"3\": \"SemanticNameFor3\",\n"
        "    \"4\": \"SemanticNameFor4\"\n"
        "  }\n"
        "}"
    )
    level_note = _REORG_LEVEL_CLASSIFY_NOTE.get(reorg_level, "")
    if level_note:
        system_prompt += " " + level_note

    user_content = f"Here is the list of parts to classify:\n{json.dumps(parts_info, indent=2)}"
    if custom_prompt.strip():
        user_content += (
            "\n\nAdditional instructions from the user (follow these carefully, they take priority over "
            f"the generic guidance above): {custom_prompt.strip()}"
        )
    return _call_openrouter_json(system_prompt, user_content)


def _duplicate_and_combine(target_objs: list, anchor_obj, original_name: str):
    """Duplicate every target object and, when more than one was selected,
    join the duplicates into a single working mesh.

    "Separate logical areas" on a multi-object selection (e.g. several
    already-separate door parts) should treat the whole selection as one
    assembly to break down, not silently process only whichever object
    happened to be active and ignore the rest.
    """
    bpy.ops.object.select_all(action='DESELECT')
    for o in target_objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = anchor_obj
    bpy.ops.object.duplicate()
    if len(target_objs) > 1:
        bpy.ops.object.join()
    dup_obj = bpy.context.active_object
    dup_obj.name = f"{original_name}_separate_temp"
    return dup_obj


def _cluster_by_proximity(parts_info: list[dict], threshold_ratio: float = 0.18) -> list[list[int]]:
    """Union-find spatial clustering of part centers, used by the no-LLM
    heuristic fallback. Grouping purely by material (the old fallback) dumps
    every part sharing a material -- e.g. every wooden part across an entire
    door -- into one meaningless blob; clustering by proximity first at
    least approximates distinct physical sub-assemblies."""
    import math

    n = len(parts_info)
    if n == 0:
        return []
    centers = [tuple(p["center"]) for p in parts_info]
    xs, ys, zs = (c[0] for c in centers), (c[1] for c in centers), (c[2] for c in centers)
    diag = math.dist((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))
    threshold = max(diag * threshold_ratio, 1e-6)

    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for i in range(n):
        for j in range(i + 1, n):
            if math.dist(centers[i], centers[j]) <= threshold:
                union(i, j)

    clusters: dict[int, list[int]] = {}
    for i in range(n):
        clusters.setdefault(find(i), []).append(i)
    return list(clusters.values())


_REORG_LEVEL_THRESHOLD_RATIO = {
    "LIGHT": 0.32,      # bigger clusters -> fewer, coarser groups
    "STANDARD": 0.18,
    "DEEP": 0.08,       # smaller clusters -> more, finer-grained groups
}


def _heuristic_classify(parts_info: list[dict], original_name: str, reorg_level: str = "STANDARD") -> dict:
    """No-LLM fallback (OPENROUTER_API_KEY not set): cluster parts spatially
    into medium-level groups first, then label each group by its dominant
    material for at least some semantic signal, and give each part a
    group-scoped name instead of a bare running index. reorg_level tunes the
    clustering threshold since it's the only lever that still works without
    an LLM -- custom_prompt has no effect here."""
    threshold_ratio = _REORG_LEVEL_THRESHOLD_RATIO.get(reorg_level, _REORG_LEVEL_THRESHOLD_RATIO["STANDARD"])
    clusters = _cluster_by_proximity(parts_info, threshold_ratio=threshold_ratio)
    groups: dict[str, list[int]] = {}
    names: dict[str, str] = {}
    for c_idx, indices in enumerate(sorted(clusters, key=len, reverse=True), start=1):
        mats = [parts_info[i]["materials"][0] for i in indices if parts_info[i]["materials"]]
        label = mats[0] if mats else "Area"
        group_name = f"{original_name}_{label}_{c_idx}"
        groups[group_name] = indices
        for local_idx, i in enumerate(indices, start=1):
            names[str(i)] = f"{group_name}_Part{local_idx}"
    return {"groups": groups, "names": names}


class SeparateLogicalAreasTool(ToolBase):
    name = "separate_logical_areas"
    description = (
        "Analyze the selected mesh(es) -- combining multiple selected objects into one working mesh "
        "first -- separate it into logical parts (by connectivity or materials), use an LLM to classify "
        "and rename them into medium-level sub-assemblies and micro-level parts (e.g. Frame/Panel/Hardware "
        "for a door, not one giant per-material blob), and organize them under parent Empties in a clean "
        "macro (whole assembly) / medium (sub-assembly) / micro (part) hierarchy."
    )

    def execute(self, params: dict) -> dict:
        lang = (params.get("lang") or "it").strip().lower()
        vocab = CATEGORY_TRANSLATIONS.get(lang)
        if vocab is None:
            vocab = CATEGORY_TRANSLATIONS["it"]

        custom_prompt = str(params.get("custom_prompt") or "")
        reorg_level = str(params.get("reorg_level") or "STANDARD").strip().upper()

        target_objs = [o for o in bpy.context.selected_objects if o.type == "MESH"]
        active_obj = bpy.context.active_object
        if not target_objs:
            if active_obj and active_obj.type == "MESH":
                target_objs = [active_obj]
            else:
                return {"success": False, "message": "Please select at least one MESH object in the 3D viewport first."}

        anchor_obj = active_obj if active_obj in target_objs else target_objs[0]
        original_name = anchor_obj.name
        original_collection = anchor_obj.users_collection[0] if anchor_obj.users_collection else bpy.context.scene.collection
        combined_count = len(target_objs)

        # Step 1: Duplicate (and combine, if more than one object selected)
        existing_objs = set(bpy.data.objects.keys())
        dup_obj = _duplicate_and_combine(target_objs, anchor_obj, original_name)

        # Step 2: Try separating by loose parts first
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')

        separated_pieces = [obj for name, obj in bpy.data.objects.items() if name not in existing_objs]

        # If only 1 piece is returned, try separating by material!
        if len(separated_pieces) <= 1:
            for obj in separated_pieces:
                bpy.data.objects.remove(obj, do_unlink=True)

            existing_objs = set(bpy.data.objects.keys())
            dup_obj = _duplicate_and_combine(target_objs, anchor_obj, original_name)

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='MATERIAL')
            bpy.ops.object.mode_set(mode='OBJECT')

            separated_pieces = [obj for name, obj in bpy.data.objects.items() if name not in existing_objs]

        if not separated_pieces:
            return {"success": False, "message": "Failed to separate the mesh into parts."}

        # Step 3: Gather parts metadata
        parts_info = []
        for idx, obj in enumerate(separated_pieces):
            parts_info.append({
                "index": idx,
                "name": obj.name,
                "center": [round(c, 3) for c in obj.location],
                "materials": [mat.name for mat in obj.data.materials if mat]
            })

        # Step 4: Call LLM to classify into medium groups + micro names
        classification = _call_llm_classify(
            parts_info, lang, original_name, custom_prompt=custom_prompt, reorg_level=reorg_level
        )
        used_llm = bool(classification and "groups" in classification and "names" in classification)

        # Fallback if LLM classification is empty/unavailable (no OPENROUTER_API_KEY)
        if not used_llm:
            classification = _heuristic_classify(parts_info, original_name, reorg_level=reorg_level)

        # Step 5: Rename and organize under a root Empty (macro tier)
        bpy.ops.object.select_all(action='DESELECT')

        root_empty_name = f"{original_name}_Organizzato" if lang == "it" else f"{original_name}_Organized"
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=anchor_obj.location)
        root_empty = bpy.context.active_object
        root_empty.name = root_empty_name

        if root_empty.name not in original_collection.objects:
            original_collection.objects.link(root_empty)
        if original_collection != bpy.context.scene.collection:
            if root_empty.name in bpy.context.scene.collection.objects:
                try:
                    bpy.context.scene.collection.objects.unlink(root_empty)
                except Exception:
                    pass

        groups = classification.get("groups", {})
        names = classification.get("names", {})

        report_groups = []
        for group_name, indices in groups.items():
            # Medium tier: one Empty per logical sub-assembly
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=anchor_obj.location)
            group_empty = bpy.context.active_object
            group_empty.name = group_name
            group_empty.parent = root_empty

            if group_empty.name not in original_collection.objects:
                original_collection.objects.link(group_empty)
            if original_collection != bpy.context.scene.collection:
                if group_empty.name in bpy.context.scene.collection.objects:
                    try:
                        bpy.context.scene.collection.objects.unlink(group_empty)
                    except Exception:
                        pass

            group_pieces = []
            for idx in indices:
                try:
                    obj_idx = int(idx)
                    if 0 <= obj_idx < len(separated_pieces):
                        # Micro tier: the individual named part
                        piece_obj = separated_pieces[obj_idx]
                        new_name = names.get(str(idx), f"Part_{idx}")
                        piece_obj.name = new_name
                        if piece_obj.data:
                            piece_obj.data.name = new_name
                        piece_obj.parent = group_empty
                        group_pieces.append(piece_obj.name)
                except (ValueError, TypeError, IndexError):
                    pass
            report_groups.append({
                "group": group_name,
                "parts": group_pieces
            })

        for obj in target_objs:
            obj.hide_viewport = True
            obj.hide_render = True

        combined_note = f" (combined from {combined_count} selected objects)" if combined_count > 1 else ""
        classifier_note = "LLM" if used_llm else "heuristic spatial clustering (set OPENROUTER_API_KEY for smarter classification)"
        prompt_note = ""
        if custom_prompt.strip() and not used_llm:
            prompt_note = " Custom instructions were ignored -- they only apply when OPENROUTER_API_KEY is configured."
        return {
            "success": True,
            "message": (
                f"Successfully separated '{original_name}'{combined_note} into {len(separated_pieces)} parts "
                f"across {len(groups)} logical groups (classified via {classifier_note})."
                f"{prompt_note}"
            ),
            "root_object": root_empty.name,
            "used_llm": used_llm,
            "groups": report_groups
        }
