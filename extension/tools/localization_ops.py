"""Localized (re)naming of structural nodes (collections, Empties, objects, meshes)
into a target language's vocabulary, plus alphabetical sorting and re-linking.

Both long-running tools here (regen_element_names, separate_logical_areas)
report phased progress to the viewport HUD with plain-language explanations,
the same pattern simplify_geometry_ops.py uses: each phase pushes through
push_hud_update(force_redraw=True) -- a plain tag_redraw() never paints while
a blocking Operator.execute() holds the event loop -- throttled so the forced
redraws don't themselves become a cost, with elapsed seconds and a
cursor-following "% - what" badge for wherever the user is actually looking.
"""

import re
import time
from typing import Any

import bpy

from .base import ToolBase
from ..bridge.jobs import drive_to_completion

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
        # "plane" is defined once, in Primitives below, as the Blender plane
        # primitive ("Piano") -- far more common in part names than "Aereo".
        "tree": "Albero",
        "trees": "Alberi",
        "plant": "Pianta",
        "plants": "Piante",
        "flower": "Fiore",
        "grass": "Erba",
        "bush": "Cespuglio",
        "rock": "Roccia",
        "rocks": "Rocce",
        "box": "Scatola",
        "boxes": "Scatole",
        "crate": "Cassa",
        "barrel": "Barile",
        "bottle": "Bottiglia",
        "cup": "Tazza",
        # "glass" is defined once, in Materials below, as "Vetro" -- the
        # material sense dominates in 3D part names over the drinking vessel.
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
        # NOTE: bare "back" is defined once, below, as the directional
        # "posteriore". The furniture sense lives on "backrest" -- defining
        # "back": "Schienale" here too would be silently shadowed by the later
        # key and never fire.
        "backrest": "Schienale",
        "arm": "Braccio",
        "armrest": "Bracciolo",
        "armrests": "Braccioli",
        "leg": "Gamba",
        "legs": "Gambe",
        "base": "Base",
        # "top" is defined once, below, as the directional "superiore".
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
# Mirrors mcp_server's localization_ops.LANG_DISPLAY_NAMES -- only used to
# turn a lang code into a display name for the vision prompt.
LANG_DISPLAY_NAMES = {"it": "Italian", "en": "English"}

_HUD_MIN_INTERVAL_S = 0.2


# Phase status -> plain-language hint for the cursor badge and the Status
# line. Matched by prefix (statuses embed live numbers), first hit wins;
# unknown statuses pass through untouched. Same idea as simplify_geometry's
# _HUMAN_HINTS: the user watches a "% - what" pill, not a technical log.
_RENAME_HINTS = (
    ("Collecting", "Finding everything that needs renaming"),
    ("Renaming", "Translating names into clean vocabulary"),
    ("Asking LLM", "Asking the AI to organize the names"),
    ("Applying LLM", "Applying the AI's naming suggestions"),
    ("Naming", "Looking at each part to name it by its role"),
    ("Vision", "Looking at each part to name it by its role"),
    ("Done:", "Wrapping up"),
)

_SEPARATE_HINTS = (
    ("Duplicating", "Copying the mesh so the original stays safe"),
    ("Splitting", "Cutting the mesh into separate parts"),
    ("Split into", "Cutting done - measuring the parts"),
    ("Reading", "Measuring where each part sits"),
    ("Asking LLM", "Asking the AI to group parts into assemblies"),
    ("Grouped", "Sorting parts into sub-assembly groups"),
    ("Placing", "Sorting parts into sub-assembly groups"),
    ("Naming", "Looking at each part to name it by its role"),
    ("Vision", "Looking at each part to name it by its role"),
    ("Done:", "Wrapping up"),
)


def _human_hint(status, hints):
    for prefix, hint in hints:
        if status.startswith(prefix):
            return hint
    if status.startswith("Done:"):
        return status
    return status


class _OpProgress:
    """Phase-by-phase HUD feedback for the rename/split runs.

    Same contract as simplify_geometry_ops._Progress, scoped to what these
    tools need: phase() records every call into history (even when throttled
    or headless), pushes title/status/% + last-4-details + cursor badge with
    a forced redraw so the bar actually moves mid-execute, and carries
    elapsed seconds so even a long blocking step visibly ticks. base/span
    map a sub-pass (e.g. the vision loop) onto its slice of an outer run's
    bar instead of fighting it for 0-100%.
    """

    def __init__(self, title, base=0.0, span=100.0, enabled=True, hints=()):
        self.enabled = bool(enabled) and not bpy.app.background
        self.title = title
        self.base = float(base)
        self.span = float(span)
        self.hints = hints
        self.started = time.perf_counter()
        self._last_push = 0.0
        self._log: list = []
        # Every phase() call lands here with timing, even when the HUD push
        # is throttled or disabled (background mode). Each entry: {step,
        # status, elapsed_s, dt_s, progress_pct, extra}.
        self.history: list = []
        self._last_step_t = self.started

    def phase(self, status, fraction, force=False, extra=None):
        now = time.perf_counter()
        elapsed = now - self.started
        dt = now - self._last_step_t
        self._last_step_t = now
        percent = self.base + self.span * max(0.0, min(1.0, fraction))
        entry = {
            "step": len(self.history) + 1,
            "status": str(status),
            "elapsed_s": round(elapsed, 3),
            "dt_s": round(dt, 3),
            "progress_pct": round(percent, 1),
        }
        if isinstance(extra, dict) and extra:
            try:
                entry["extra"] = {k: extra[k] for k in extra}
            except Exception:
                entry["extra"] = {}
        self.history.append(entry)
        self._log.append(status)
        if not self.enabled:
            return entry
        wall_now = time.time()
        if not force and wall_now - self._last_push < _HUD_MIN_INTERVAL_S:
            return entry
        self._last_push = wall_now
        try:
            from .progress_hud_ops import push_hud_update

            hint = _human_hint(status, self.hints)
            push_hud_update(
                title=self.title,
                status=f"{hint}  [{elapsed:.0f}s]",
                progress_percent=percent,
                details=self._log[-4:],
                force_redraw=True,
                cursor_badge=True,
                badge_text=hint,
            )
        except Exception:
            self.enabled = False
        return entry

    def total_seconds(self):
        return round(time.perf_counter() - self.started, 3)

    def history_payload(self):
        return {"total_seconds": self.total_seconds(), "steps": list(self.history)}


def _format_history_for_hud(history):
    """One short line per step for the HUD card details list."""
    lines = []
    for e in history:
        try:
            lines.append(f"{e['elapsed_s']:.1f}s (+{e['dt_s']:.1f}s) [{e['progress_pct']:.0f}%] {e['status']}"[:96])
        except Exception:
            continue
    return lines


def _save_history_card(progress, status, completed_summary, next_steps=None):
    """Persist the run's history card to the viewport HUD.

    The live HUD only shows the last 4 details lines, but HUD_STATE keeps
    the full list, so pass the whole formatted history -- the card becomes
    the on-screen record of time data + each step.
    """
    try:
        from .progress_hud_ops import push_hud_update

        push_hud_update(
            title=progress.title,
            status=status,
            progress_percent=100.0,
            details=_format_history_for_hud(progress.history),
            completed_summary=completed_summary,
            next_steps=next_steps or [],
            force_redraw=True,
            cursor_badge=False,
        )
    except Exception:
        pass


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


def _call_openrouter_vision(question: str, png_bytes: bytes, model: str = None) -> str:
    """POST an image + question to OpenRouter's vision endpoint and return the
    raw text reply, or None on any failure.

    Reimplements mcp_server's vlm.critique_image with urllib so the "Regenerate
    Names" button can run the vision-assisted mesh-naming pass entirely
    in-process, without round-tripping through the separate mcp_server process
    (which the panel button never talks to -- it calls TOOL_REGISTRY directly).
    """
    import os
    import json
    import base64
    import urllib.request
    from ..config import load_env_vars

    load_env_vars()
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        return None

    resolved_model = model or os.environ.get("OPENROUTER_VISION_MODEL") or OPENROUTER_DEFAULT_MODEL
    data_uri = "data:image/png;base64," + base64.b64encode(png_bytes).decode("utf-8")
    payload = {
        "model": resolved_model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url", "image_url": {"url": data_uri}},
                ],
            }
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
        with urllib.request.urlopen(req, timeout=60) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
        return response_data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"[MCP Bridge] OpenRouter vision request failed: {e}")
        return None


def _sanitize_vision_name(text: str) -> str:
    # Vision models sometimes wrap the answer in a sentence or quotes despite
    # instructions -- take the first line, strip quoting/trailing punctuation,
    # and cap length so a rambling answer can't produce an unusable name.
    if not text:
        return ""
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    return first_line.strip(" .\"'“”").strip()[:40]


def _collect_mesh_leaves(node: dict) -> list:
    """Flatten a _regen_collection report tree into every MESH leaf, each
    carrying its category (immediate parent collection's new_name) for
    vision-prompt context, and whether the structural/LLM pass already
    renamed it (used to filter down to still-generic leaves)."""
    found = []
    for obj in node.get("objects", []):
        if obj.get("type") == "MESH":
            found.append({
                "name": obj["new_name"],
                "category": node.get("new_name"),
                "renamed": bool(obj.get("renamed", False)),
            })
    for child in node.get("children", []):
        found.extend(_collect_mesh_leaves(child))
    return found


def _mesh_candidates_from_result(result: dict) -> list:
    """MESH leaves to offer the vision pass, from either result shape
    RegenElementNamesTool.execute() can return: a "root" collection tree, or
    a flat "objects" list (selection/single-object scope)."""
    root = result.get("root")
    if root:
        return _collect_mesh_leaves(root)
    return [
        {"name": o["new_name"], "category": None, "renamed": bool(o.get("renamed", False))}
        for o in result.get("objects", [])
        if o.get("type") == "MESH"
    ]


def _iter_vision_pass(
    result: dict,
    use_vision: bool,
    max_vision_renames: int,
    vision_model: str,
    lang: str,
    rename_meshes: bool,
    vision_only_generic: bool = False,
    _hud: dict | None = None,
    ctx=None,
):
    """Second pass after the structural/LLM rename: name mesh leaves the
    keyword vocabulary can't cover (e.g. 'Chair_Mesh') by capturing a close-up
    render of each and asking a vision model for its semantic role. Mutates
    and returns `result` so the panel's rename-result dialog picks up the
    extra pairs for free via the shared "renamed_pairs" list.

    vision_only_generic restricts the vision pass to leaves the structural/LLM
    pass left untouched ("renamed": False) -- both truly generic exporter
    names (Cube.003) and vocabulary gaps (Chair_Mesh) -- instead of spending a
    render+API call re-naming parts that already got a decent name.

    _hud optionally maps this loop onto a slice of an outer run's bar
    ({"base": .., "span": .., "enabled": ..}, same convention as
    simplify_geometry's _hud): the caller owns 0-100% and this pass fills
    only its share instead of resetting the bar.

    Step generator (see ToolBase.iter_steps): yields once per candidate so
    the bridge scheduler can interleave other requests between parts, and
    returns the mutated result. ctx (a bridge.jobs.JobCtx) mirrors each
    chunk into the job record; None on the synchronous path.
    """
    result["vision_used"] = False
    result["vision_renames"] = []
    result["vision_note"] = None

    if not use_vision:
        return result

    import os
    import base64
    from ..config import load_env_vars

    load_env_vars()
    if not os.environ.get("OPENROUTER_API_KEY"):
        result["vision_note"] = "Use Vision was requested but OPENROUTER_API_KEY is not set -- structural pass only."
        return result

    candidates = _mesh_candidates_from_result(result)
    if vision_only_generic:
        candidates = [c for c in candidates if not c.get("renamed")]
    candidates = candidates[: max(0, int(max_vision_renames))]
    if not candidates:
        return result

    from .vision_feedback_ops import InspectFocusShotTool
    from .progress_hud_ops import push_hud_update

    hud = _hud or {}
    base = float(hud.get("base", 0.0))
    span = float(hud.get("span", 100.0))
    hud_enabled = bool(hud.get("enabled", True)) and not bpy.app.background

    def _vision_pct(i, total):
        return base + span * ((i - 1) / total if total else 1.0)

    focus_tool = InspectFocusShotTool()
    lang_name = LANG_DISPLAY_NAMES.get(lang, lang)
    vision_renames = []
    renamed_pairs = result.setdefault("renamed_pairs", [])
    total = len(candidates)
    details: list = []
    started = time.perf_counter()

    for i, candidate in enumerate(candidates, 1):
        obj_name = candidate["name"]
        if ctx is not None:
            # Chunk boundary BEFORE the slow part (close-up render + HTTP
            # round-trip): the scheduler yields here so other bridge
            # requests interleave between candidates.
            ctx.report(
                (base + span * ((i - 1) / total if total else 1.0)) / 100.0,
                f"Naming '{obj_name}' via vision ({i}/{total})...",
            )
        yield
        obj = bpy.data.objects.get(obj_name)
        if obj is None:
            continue
        # force_redraw=True: this loop runs entirely inside one Operator.execute()
        # call (the "Regenerate Names" button), so a plain tag_redraw() would
        # never actually paint until the whole pass is done -- see
        # push_hud_update's docstring. Without this the UI just looks frozen
        # for the whole vision pass (one render + one API round-trip per part).
        if hud_enabled:
            elapsed = time.perf_counter() - started
            hint = f"Looking at part {i} of {total} to name it by role"
            details.append(f"Naming '{obj_name}' ({i}/{total})")
            push_hud_update(
                title="Regenerate Names: Vision Pass",
                status=f"{hint}  [{elapsed:.0f}s]",
                progress_percent=_vision_pct(i, total),
                step_current=i,
                step_total=total,
                details=details[-4:],
                force_redraw=True,
                cursor_badge=True,
                badge_text=hint,
            )
        try:
            capture = focus_tool.execute({"target_object": obj_name, "include_base64": True})
            if not capture.get("success"):
                continue
            b64 = capture.get("image_base64")
            if not b64:
                continue
            png_bytes = base64.b64decode(b64)

            category = candidate.get("category")
            context = f" It belongs to the '{category}' group." if category else ""
            question = (
                f"This 3D model part is currently named '{obj_name}'.{context} In one or two "
                f"words, name it by its SEMANTIC ROLE or FUNCTION within the whole object "
                f"(e.g. 'leg', 'seat', 'wheel', 'handle', 'blade') -- NOT its geometric shape "
                f"(never answer 'cube', 'cylinder', 'sphere', 'cone', or similar). Reply in "
                f"{lang_name} with ONLY that name, capitalized, no punctuation."
            )
            answer = _call_openrouter_vision(question, png_bytes, vision_model)
            new_name = _sanitize_vision_name(answer)
            if not new_name:
                continue

            old_name = obj.name
            obj.name = new_name
            if rename_meshes and obj.data and hasattr(obj.data, "name") and obj.data.name == old_name:
                try:
                    obj.data.name = obj.name
                except Exception:
                    pass

            vision_renames.append({"old_name": old_name, "new_name": obj.name})
            renamed_pairs.append({"old": old_name, "new": obj.name})
        except Exception as e:
            print(f"[MCP Bridge] Vision rename failed for '{obj_name}': {e}")
            continue

    standalone = not _hud or (base <= 0.0 and span >= 100.0)
    if hud_enabled or standalone:
        try:
            push_hud_update(
                title="Regenerate Names: Vision Pass",
                status=f"Done: {len(vision_renames)}/{total} part(s) renamed via vision",
                progress_percent=(base + span) if not standalone else 100.0,
                step_current=total,
                step_total=total,
                completed_summary=(
                    f"Vision named {len(vision_renames)}/{total} part(s)"
                ) if standalone else "",
                next_steps=(
                    ["Review names in the Rename Result dialog"] if standalone and vision_renames else []
                ),
                auto_hide_seconds=6.0 if standalone else 0.0,
                force_redraw=True,
                cursor_badge=False,
            )
        except Exception:
            pass

    result["vision_used"] = True
    result["vision_renames"] = vision_renames
    return result


def _apply_vision_pass(
    result: dict,
    use_vision: bool,
    max_vision_renames: int,
    vision_model: str,
    lang: str,
    rename_meshes: bool,
    vision_only_generic: bool = False,
    _hud: dict | None = None,
) -> dict:
    """Synchronous driver for _iter_vision_pass (panel button path): same
    chunks, same HUD pushes, just no yield to the event loop between parts."""
    return drive_to_completion(
        _iter_vision_pass(
            result, use_vision, max_vision_renames, vision_model, lang,
            rename_meshes, vision_only_generic, _hud=_hud, ctx=None,
        )
    )


def _vision_rename_piece(obj: bpy.types.Object, category: str, lang: str, vision_model: str = None) -> str:
    """Capture a close-up render of a separated part and ask a vision model to
    name it by semantic role within its sub-assembly. Returns the sanitized
    new name, or None if the capture or the model call failed. Shared by
    SeparateLogicalAreasTool's group and leftover/misc assignment loops."""
    import base64
    from .vision_feedback_ops import InspectFocusShotTool

    capture = InspectFocusShotTool().execute({"target_object": obj.name, "include_base64": True})
    if not capture.get("success"):
        return None
    b64 = capture.get("image_base64")
    if not b64:
        return None
    png_bytes = base64.b64decode(b64)

    lang_name = LANG_DISPLAY_NAMES.get(lang, lang)
    context = f" It belongs to the '{category}' sub-assembly." if category else ""
    question = (
        f"This 3D model part is currently named '{obj.name}'.{context} In one or two words, name it by "
        f"its SEMANTIC ROLE or FUNCTION within the whole object (e.g. 'hinge', 'panel', 'handle', "
        f"'bracket', 'frame') -- NOT its geometric shape (never answer 'cube', 'cylinder', 'sphere', "
        f"'cone', or similar). Reply in {lang_name} with ONLY that name, capitalized, no punctuation."
    )
    answer = _call_openrouter_vision(question, png_bytes, vision_model)
    return _sanitize_vision_name(answer)


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
        "the target language's vocabulary (default Italian 'it', or 'en'), re-link collection "
        "children and objects in alphabetical order, and optionally (use_vision=true) run a "
        "vision-assisted pass afterward to name mesh leaves the vocabulary can't cover, capped "
        "at max_vision_renames (default 9999) objects to bound cost/time. Pass "
        "vision_only_generic=true to restrict that pass to leaves the structural/LLM pass left "
        "untouched instead of re-naming every mesh. Reports phased progress with plain-language "
        "explanations to the viewport HUD and returns a 'history' card with per-step timings."
    )

    def execute(self, params: dict) -> dict:
        from ..bridge.jobs import NULL_CTX

        return drive_to_completion(self.iter_steps(params, NULL_CTX))

    def iter_steps(self, params: dict, ctx):
        """Chunked run: structural/LLM chunk, then one chunk per vision
        candidate, then the history card. The synchronous execute() drives
        this to completion in one go; the bridge scheduler drives one chunk
        per timer tick so other requests interleave."""
        lang = (params.get("lang") or "it").strip().lower()
        use_vision = bool(params.get("use_vision", False))
        max_vision_renames = int(params.get("max_vision_renames", 9999))
        vision_model = params.get("vision_model")
        vision_only_generic = bool(params.get("vision_only_generic", False))
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

        lang_name = LANG_DISPLAY_NAMES.get(lang, lang)
        if is_selection or is_single_obj:
            scope_label = f"{len(objects_to_rename)} object(s)"
        elif element:
            scope_label = f"'{element}'"
        else:
            scope_label = "entire scene"
        progress = _OpProgress(f"Regenerate Names ({lang_name})", hints=_RENAME_HINTS)
        progress.phase(f"Collecting targets in {scope_label}...", 0.02, force=True)
        if ctx is not None:
            ctx.report(0.02, f"Collecting targets in {scope_label}...")
        yield
        progress.phase(f"Renaming {scope_label}...", 0.08)

        # Pre-vision result: set by the LLM branch on success, else by the
        # dictionary fallback below. The shared tail (vision slice + history
        # card) runs once for all four shapes.
        result = None

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
                progress.phase(f"Asking LLM to organize {len(objects_info)} name(s)...", 0.15, force=True)
                if ctx is not None:
                    ctx.report(0.15, f"Asking LLM to organize {len(objects_info)} name(s)...")
                yield
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
                    progress.phase(f"Applying LLM names ({len(obj_pairs)} changed)...", 0.5)
                    if ctx is not None:
                        ctx.report(0.5, f"Applying LLM names ({len(obj_pairs)} changed)...")
                    yield

                    if not is_selection and not is_single_obj and root_col:
                        report = _regen_collection(root_col, vocab, rename_objects=False)
                        result = {
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
                        result = {
                            "success": True,
                            "message": f"Regenerated names using LLM for {msg} ({total_renamed} changed, lang={lang})",
                            "lang": lang,
                            "objects": renamed_objs,
                            "renamed_pairs": obj_pairs,
                        }

        # Fallback to local dictionary translation (skipped when the LLM
        # branch above already produced a result).
        prompt_note = ""
        if custom_prompt.strip() and not llm_success:
            prompt_note = (
                " (custom_prompt ignored -- enable Use LLM Semantics)" if not use_llm
                else " (custom_prompt ignored -- LLM call unavailable/failed, check OPENROUTER_API_KEY)"
            )
        if result is None:
            progress.phase("Renaming with local vocabulary...", 0.2, force=True)

        if result is None and (is_selection or is_single_obj):
            renamed_objs = []
            for obj in objects_to_rename:
                rep = _regen_object(obj, vocab, rename_mesh=rename_meshes)
                renamed_objs.append(rep)
            total_renamed = sum(1 for r in renamed_objs if r["renamed"])
            progress.phase(f"Renamed {total_renamed}/{len(renamed_objs)} object(s)...", 0.5)
            if ctx is not None:
                ctx.report(0.5, f"Renamed {total_renamed}/{len(renamed_objs)} object(s)...")
            yield
            msg = "selected object(s)" if is_selection else f"object hierarchy '{objects_to_rename[0].name}'"
            result = {
                "success": True,
                "message": f"Regenerated names for {msg} ({total_renamed} changed, lang={lang}){prompt_note}",
                "lang": lang,
                "objects": renamed_objs,
                "renamed_pairs": [
                    {"old": r["old_name"], "new": r["new_name"]} for r in renamed_objs if r["renamed"]
                ],
            }

        if result is None:
            progress.phase("Renaming collections and objects...", 0.25, force=True)
            report = _regen_collection(root_col, vocab, rename_objects=True)
            renamed_now = len(_collect_renamed_pairs(report))
            progress.phase(f"Renamed {renamed_now} name(s)...", 0.5)
            if ctx is not None:
                ctx.report(0.5, f"Renamed {renamed_now} name(s)...")
            yield
            result = {
                "success": True,
                "message": f"Regenerated names for '{report['new_name']}' hierarchy (lang={lang}){prompt_note}",
                "lang": lang,
                "root": report,
                "renamed_pairs": _collect_renamed_pairs(report),
            }

        # Shared tail: vision slice (55-100% of the bar) if asked, then the
        # final history card and per-step timings.
        staged = len(result.get("renamed_pairs", []))
        progress.phase(f"Checking vision pass ({staged} renamed so far)...", 0.55)
        if ctx is not None:
            ctx.report(0.55, f"Checking vision pass ({staged} renamed so far)...")
        yield
        out = yield from _iter_vision_pass(
            result, use_vision, max_vision_renames, vision_model, lang,
            rename_meshes, vision_only_generic,
            _hud={"base": 55.0, "span": 45.0},
            ctx=ctx,
        )
        changed = len(out.get("renamed_pairs", [])) + len(out.get("vision_renames", []))
        progress.phase(f"Done: {changed} name(s) changed", 1.0, force=True)
        if ctx is not None:
            ctx.report(1.0, f"Done: {changed} name(s) changed")
        history = progress.history_payload()
        _save_history_card(
            progress,
            status=f"Done {changed} renamed in {history['total_seconds']:.1f}s",
            completed_summary=f"Renamed {changed} name(s) in {history['total_seconds']:.1f}s",
            next_steps=["Review names in the Rename Result dialog"],
        )
        out["history"] = history
        return out


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


def _relink_to_collection(obj, target_collection) -> None:
    """Ensure obj lives only in target_collection.

    bpy.ops.object.empty_add() links the new object into whatever the
    *active* collection happens to be, which is not necessarily the scene
    root or original_collection -- the old code only ever checked and
    unlinked from bpy.context.scene.collection, so an empty created while a
    third collection was active stayed double-linked (visible in two places
    in the outliner). Unlink from everywhere except the intended target.
    """
    if target_collection not in obj.users_collection:
        target_collection.objects.link(obj)
    for col in list(obj.users_collection):
        if col != target_collection:
            try:
                col.objects.unlink(obj)
            except Exception:
                pass


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


def _bbox_diagonal_world(obj) -> float:
    """World-space bounding-box diagonal, used to scale the weld threshold to
    this mesh's actual size instead of a fixed absolute distance."""
    import math
    from mathutils import Vector

    if not obj.data or not obj.data.vertices:
        return 0.0
    mw = obj.matrix_world
    corners = [mw @ Vector(c) for c in obj.bound_box]
    xs = [c.x for c in corners]
    ys = [c.y for c in corners]
    zs = [c.z for c in corners]
    return math.dist((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))


def _piece_center(obj) -> list[float]:
    """World-space center of a separated piece's actual geometry.

    bpy.ops.mesh.separate() does NOT recompute object origins -- every piece
    inherits the source object's transform, so obj.location is byte-identical
    across all of them. Using it as the part "center" fed the classifier a
    constant, which collapsed _cluster_by_proximity into a single group and
    stripped the LLM of the spatial signal its prompt says to rely on. Derive
    the center from the bounding box instead, which is genuinely per-piece.
    """
    from mathutils import Vector

    if not obj.data or not obj.data.vertices:
        return [round(c, 3) for c in obj.location]
    mw = obj.matrix_world
    corners = [mw @ Vector(c) for c in obj.bound_box]
    return [
        round(sum(c[axis] for c in corners) / len(corners), 3)
        for axis in range(3)
    ]


def _piece_materials(obj) -> list[str]:
    """Materials actually used by this piece's faces.

    separate() copies the whole material slot list onto every piece, so
    obj.data.materials is identical for all of them -- another constant the
    classifier was being asked to discriminate on. Resolve the slots the
    polygons genuinely reference instead.
    """
    mesh = obj.data
    if not mesh or not mesh.materials:
        return []
    used_slots = {p.material_index for p in mesh.polygons}
    names = []
    for slot_idx in sorted(used_slots):
        if 0 <= slot_idx < len(mesh.materials):
            mat = mesh.materials[slot_idx]
            if mat and mat.name not in names:
                names.append(mat.name)
    return names


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
    # Materialize as lists: generators here would be exhausted by the min()
    # calls, making the following max() calls raise ValueError on every run.
    xs = [c[0] for c in centers]
    ys = [c[1] for c in centers]
    zs = [c[2] for c in centers]
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

    # A raw OBJ import commonly loose-separates into thousands of pieces, and
    # the naive all-pairs comparison below is O(n^2) -- ~4.5M math.dist calls
    # at n=3000, freezing the UI on the main thread. Bucket centers into a grid
    # sized to the threshold first so only points in the same or adjacent
    # cells (guaranteed to cover every pair within `threshold`) are ever
    # compared, which is near-linear for realistically distributed geometry.
    cell = max(threshold, 1e-6)
    grid: dict[tuple[int, int, int], list[int]] = {}
    for i, c in enumerate(centers):
        key = (int(c[0] // cell), int(c[1] // cell), int(c[2] // cell))
        grid.setdefault(key, []).append(i)

    for (cx, cy, cz), idxs in grid.items():
        neighbor_idxs = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    neighbor_idxs.extend(grid.get((cx + dx, cy + dy, cz + dz), []))
        for i in idxs:
            for j in neighbor_idxs:
                if j > i and math.dist(centers[i], centers[j]) <= threshold:
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
        "macro (whole assembly) / medium (sub-assembly) / micro (part) hierarchy. Every separated part is "
        "left visible; the original source object(s) are renamed with a '.bak' suffix and hidden instead "
        "of deleted. Pass use_vision=true to also run a vision-assisted pass afterward, capping at "
        "max_vision_renames (default 9999) objects to bound cost/time; vision_only_generic=true restricts "
        "it to parts that fell back to a generic 'Part_N' name instead of re-naming every part. "
        "Reports phased progress with plain-language explanations to the viewport HUD and returns a "
        "'history' card with per-step timings."
    )

    def execute(self, params: dict) -> dict:
        from ..bridge.jobs import NULL_CTX

        return drive_to_completion(self.iter_steps(params, NULL_CTX))

    def iter_steps(self, params: dict, ctx):
        """Chunked run: duplicate, split, gather, classify, organize (one
        chunk per group), then one chunk per vision candidate, then the
        history card. The synchronous execute() drives this to completion in
        one go; the bridge scheduler drives one chunk per timer tick so
        other requests interleave -- in particular between vision candidates
        (one close-up render + one API round-trip each), the long pole.

        Vision is deferred until every part is placed (same attempt order
        and budget rules as the old inline loop): the report is built from
        the live objects at the end, so it still carries post-vision names.
        """
        lang = (params.get("lang") or "it").strip().lower()
        vocab = CATEGORY_TRANSLATIONS.get(lang)
        if vocab is None:
            vocab = CATEGORY_TRANSLATIONS["it"]

        custom_prompt = str(params.get("custom_prompt") or "")
        reorg_level = str(params.get("reorg_level") or "STANDARD").strip().upper()
        use_vision = bool(params.get("use_vision", False))
        max_vision_renames = int(params.get("max_vision_renames", 9999))
        vision_model = params.get("vision_model")
        vision_only_generic = bool(params.get("vision_only_generic", False))

        vision_note = None
        vision_renames: list[dict] = []
        vision_budget = max(0, max_vision_renames)
        if use_vision:
            import os
            from ..config import load_env_vars

            load_env_vars()
            if not os.environ.get("OPENROUTER_API_KEY"):
                vision_note = "Use Vision was requested but OPENROUTER_API_KEY is not set -- classification pass only."
                use_vision = False

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

        progress = _OpProgress(f"Separate '{original_name}'", hints=_SEPARATE_HINTS)

        # Step 1: Duplicate (and combine, if more than one object selected)
        progress.phase(f"Duplicating {combined_count} object(s) (original stays as hidden backup)...", 0.02, force=True)
        if ctx is not None:
            ctx.report(0.02, f"Duplicating {combined_count} object(s)...")
        yield
        existing_objs = set(bpy.data.objects.keys())
        dup_obj = _duplicate_and_combine(target_objs, anchor_obj, original_name)

        # Step 2: Try separating by loose parts first. The separate() calls
        # below block Blender's main thread with no cancellation -- the phase
        # push just before them (force_redraw) is what keeps the viewport from
        # looking hung, and the elapsed timer ticks even through the block.
        progress.phase("Splitting mesh into parts (Blender is busy, cannot cancel)...", 0.10, force=True)
        if ctx is not None:
            ctx.report(0.10, "Splitting mesh into parts...")
        yield
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        # Weld coincident-but-unshared vertices (e.g. UV seams on the face/hands/ears
        # in a raw OBJ import) before separating -- otherwise mesh.separate(LOOSE)
        # treats every seam as a real disconnection and chops off stray pieces of an
        # otherwise-continuous body alongside genuinely separate meshes like clothes.
        # A fixed absolute threshold breaks across scales -- a no-op on mm-scale
        # imports, over-merging on huge ones -- so derive it from this mesh's own
        # bbox diagonal instead, matching simplify_geometry_ops.py's _bbox_diagonal
        # pattern. Kept tiny (1e-5 of the diagonal): the goal is only to close
        # exact-duplicate UV-seam verts, not to fuse distinct touching parts.
        weld_dist = max(1e-6, _bbox_diagonal_world(dup_obj) * 1e-5)
        bpy.ops.mesh.remove_doubles(threshold=weld_dist)
        bpy.ops.mesh.separate(type='LOOSE')
        bpy.ops.object.mode_set(mode='OBJECT')

        separated_pieces = [obj for name, obj in bpy.data.objects.items() if name not in existing_objs]
        progress.phase(f"Split into {len(separated_pieces)} piece(s)...", 0.30)
        if ctx is not None:
            ctx.report(0.30, f"Split into {len(separated_pieces)} piece(s)...")
        yield

        # If only 1 piece is returned, try separating by material!
        if len(separated_pieces) <= 1:
            for obj in separated_pieces:
                bpy.data.objects.remove(obj, do_unlink=True)

            progress.phase("Loose split gave 1 piece, retrying by material...", 0.20, force=True)
            if ctx is not None:
                ctx.report(0.20, "Loose split gave 1 piece, retrying by material...")
            yield
            existing_objs = set(bpy.data.objects.keys())
            dup_obj = _duplicate_and_combine(target_objs, anchor_obj, original_name)

            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='MATERIAL')
            bpy.ops.object.mode_set(mode='OBJECT')

            separated_pieces = [obj for name, obj in bpy.data.objects.items() if name not in existing_objs]
            progress.phase(f"Split into {len(separated_pieces)} piece(s)...", 0.30, force=True)
            if ctx is not None:
                ctx.report(0.30, f"Split into {len(separated_pieces)} piece(s)...")
            yield

        if not separated_pieces:
            progress.phase("Failed: mesh did not separate into parts", 1.0, force=True)
            return {
                "success": False,
                "message": "Failed to separate the mesh into parts.",
                "history": progress.history_payload(),
            }

        # Step 3: Gather parts metadata
        progress.phase(f"Reading {len(separated_pieces)} part(s) (position, materials)...", 0.32, force=True)
        if ctx is not None:
            ctx.report(0.32, f"Reading {len(separated_pieces)} part(s)...")
        yield
        parts_info = []
        for idx, obj in enumerate(separated_pieces):
            parts_info.append({
                "index": idx,
                "name": obj.name,
                "center": _piece_center(obj),
                "materials": _piece_materials(obj),
            })
            if (idx + 1) % 200 == 0 or idx + 1 == len(separated_pieces):
                frac = 0.32 + 0.06 * (idx + 1) / max(1, len(separated_pieces))
                progress.phase(
                    f"Reading part {idx + 1}/{len(separated_pieces)}...",
                    frac,
                )
                if ctx is not None:
                    ctx.report(frac, f"Reading part {idx + 1}/{len(separated_pieces)}...")
                yield

        # Step 4: Call LLM to classify into medium groups + micro names.
        # The HTTP round-trip blocks with no intermediate ticks -- bookend it
        # so the bar explains the wait instead of freezing mid-gather.
        progress.phase(f"Asking LLM to group {len(parts_info)} part(s)...", 0.42, force=True)
        if ctx is not None:
            ctx.report(0.42, f"Asking LLM to group {len(parts_info)} part(s)...")
        yield
        classification = _call_llm_classify(
            parts_info, lang, original_name, custom_prompt=custom_prompt, reorg_level=reorg_level
        )
        # `used_llm` used to only check the two keys exist. An LLM will still
        # deviate from the requested shape (a list instead of a dict for
        # "groups" is a common one -- only json_object mode constrains the
        # top level, not nested types), which crashed groups.items() below
        # *after* the scene had already been mutated -- debris plus a
        # traceback. An empty-but-well-shaped response also used to count as
        # "used_llm", silently skipping the heuristic and dumping every part
        # into the orphan/misc group while still reporting "classified via LLM".
        used_llm = bool(
            classification
            and isinstance(classification.get("groups"), dict)
            and isinstance(classification.get("names"), dict)
            and classification["groups"]
        )

        # Fallback if LLM classification is empty/unavailable (no OPENROUTER_API_KEY)
        if not used_llm:
            classification = _heuristic_classify(parts_info, original_name, reorg_level=reorg_level)
        how = "LLM" if used_llm else "heuristic clustering"
        progress.phase(
            f"Grouped into {len(classification.get('groups', {}))} group(s) via {how}...",
            0.55,
            force=True,
            extra={"groups": len(classification.get("groups", {})), "used_llm": used_llm},
        )
        if ctx is not None:
            ctx.report(0.55, f"Grouped into {len(classification.get('groups', {}))} group(s) via {how}...")
        yield

        # Step 5: Rename and organize under a root Empty (macro tier)
        progress.phase("Creating sub-assembly groups...", 0.58, force=True)
        if ctx is not None:
            ctx.report(0.58, "Creating sub-assembly groups...")
        yield
        bpy.ops.object.select_all(action='DESELECT')

        root_empty_name = f"{original_name}_Organizzato" if lang == "it" else f"{original_name}_Organized"
        bpy.ops.object.empty_add(type='PLAIN_AXES', location=anchor_obj.location)
        root_empty = bpy.context.active_object
        root_empty.name = root_empty_name
        _relink_to_collection(root_empty, original_collection)

        groups = classification.get("groups", {})
        names = classification.get("names", {})

        def _make_group_empty(group_name: str):
            bpy.ops.object.empty_add(type='PLAIN_AXES', location=anchor_obj.location)
            group_empty = bpy.context.active_object
            group_empty.name = group_name
            group_empty.parent = root_empty
            # Keep the child's world-space transform stable under its parent --
            # both empties are created at anchor_obj.location, and without this
            # every piece inherits the anchor's transform *again* on top of its
            # own, so the organized hierarchy visibly jumps away from the
            # source mesh (it only looked right when the source origin sat at
            # world (0,0,0)). Matches the pattern already used for root-empty
            # parenting in hierarchy_ops.py.
            group_empty.matrix_parent_inverse = root_empty.matrix_world.inverted()
            _relink_to_collection(group_empty, original_collection)
            return group_empty

        # The classifier is told every index must appear in exactly one group,
        # but an LLM will still drop or double-assign some. Track what actually
        # got placed: an unassigned piece would otherwise be left unparented,
        # still named "<name>_separate_temp.NNN" and visible in the scene as
        # stray debris, while a double-assigned one would be reported under two
        # groups despite only ever living under the last one to claim it.
        assigned: set[int] = set()

        def _attach_piece(piece_obj, group_empty):
            piece_obj.parent = group_empty
            # Same world-space-stability reasoning as the group empty above.
            piece_obj.matrix_parent_inverse = group_empty.matrix_world.inverted()

        # Precompute how many parts the vision pass will actually attempt, so
        # the HUD can show real "i/total" progress instead of an unbounded
        # counter -- both `names` and `separated_pieces` are already final by
        # this point.
        vision_total = 0
        if use_vision:
            eligible = range(len(separated_pieces))
            if vision_only_generic:
                eligible = [i for i in eligible if not names.get(str(i))]
            vision_total = min(len(list(eligible)), vision_budget)
        vision_done = 0

        # Organize-loop progress rides on placed parts (0.58 -> 0.85), so the
        # bar moves monotonically whether or not the vision pass runs inside
        # it -- vision attempts reuse the current fraction and only change
        # the status text.
        placed = 0
        placed_total = len(separated_pieces)

        def _organize_pct():
            return 0.58 + 0.27 * placed / max(1, placed_total)

        # Vision candidates are collected during placement but attempted
        # afterwards, one chunk each: each is a close-up render plus an API
        # round-trip, the long pole of this tool. Same order and budget rules
        # as the old inline loop (group order, then leftovers; budget spent
        # only on successes), so sync results are unchanged.
        vision_queue: list = []

        def _queue_vision(piece_obj, category_name: str, was_generic: bool):
            if not use_vision or (vision_only_generic and not was_generic):
                return
            vision_queue.append((piece_obj, category_name))

        report_order: list = []  # (group display name, [member objects])

        report_groups = []
        group_items = list(groups.items())
        for gi, (group_name, indices) in enumerate(group_items, 1):
            # Medium tier: one Empty per logical sub-assembly
            group_empty = _make_group_empty(group_name)

            members = []
            if isinstance(indices, (list, tuple)):
                for idx in indices:
                    try:
                        obj_idx = int(idx)
                    except (ValueError, TypeError):
                        continue
                    if not (0 <= obj_idx < len(separated_pieces)) or obj_idx in assigned:
                        continue
                    # Micro tier: the individual named part
                    piece_obj = separated_pieces[obj_idx]
                    was_generic = not names.get(str(obj_idx))
                    new_name = names.get(str(obj_idx)) or f"Part_{obj_idx}"
                    piece_obj.name = new_name
                    if piece_obj.data:
                        piece_obj.data.name = new_name
                    _attach_piece(piece_obj, group_empty)
                    assigned.add(obj_idx)
                    placed += 1
                    members.append(piece_obj)
                    _queue_vision(piece_obj, group_empty.name, was_generic)
            # Read the name back from the object rather than echoing group_name:
            # Blender auto-suffixes (".001") on a collision with an existing
            # object, so the report would otherwise claim a group name that
            # isn't actually what got created.
            report_order.append((group_empty.name, members))
            frac = _organize_pct()
            progress.phase(
                f"Placing group '{group_empty.name}' ({gi}/{len(group_items)}, {placed}/{placed_total} parts)...",
                frac,
            )
            if ctx is not None:
                ctx.report(frac, f"Placing group '{group_empty.name}' ({gi}/{len(group_items)})...")
            yield

        leftovers = [i for i in range(len(separated_pieces)) if i not in assigned]
        if leftovers:
            misc_name = f"{original_name}_Varie" if lang == "it" else f"{original_name}_Misc"
            misc_empty = _make_group_empty(misc_name)
            members = []
            for obj_idx in leftovers:
                piece_obj = separated_pieces[obj_idx]
                was_generic = not names.get(str(obj_idx))
                new_name = names.get(str(obj_idx)) or f"Part_{obj_idx}"
                piece_obj.name = new_name
                if piece_obj.data:
                    piece_obj.data.name = new_name
                _attach_piece(piece_obj, misc_empty)
                placed += 1
                members.append(piece_obj)
                _queue_vision(piece_obj, misc_empty.name, was_generic)
            report_order.append((misc_empty.name, members))
            frac = _organize_pct()
            progress.phase(
                f"Placing leftovers in '{misc_empty.name}' ({placed}/{placed_total} parts)...",
                frac,
            )
            if ctx is not None:
                ctx.report(frac, f"Placing leftovers in '{misc_empty.name}'...")
            yield

        # Deferred vision pass: one chunk per candidate (render + API call).
        for piece_obj, category_name in vision_queue:
            if vision_budget <= 0:
                break
            vision_done += 1
            frac = 0.85 + 0.13 * (vision_done - 1) / max(1, vision_total)
            progress.phase(
                f"Naming '{piece_obj.name}' via vision ({vision_done}/{vision_total})...",
                frac,
                force=True,
            )
            if ctx is not None:
                ctx.report(frac, f"Naming '{piece_obj.name}' via vision ({vision_done}/{vision_total})...")
            yield
            try:
                vname = _vision_rename_piece(piece_obj, category_name, lang, vision_model)
                if vname:
                    old_vname = piece_obj.name
                    piece_obj.name = vname
                    if piece_obj.data:
                        piece_obj.data.name = piece_obj.name
                    vision_renames.append({"old_name": old_vname, "new_name": piece_obj.name})
                    vision_budget -= 1
            except Exception as e:
                print(f"[MCP Bridge] Vision rename failed for '{piece_obj.name}': {e}")

        # The report reads names back from the live objects, so it carries
        # post-vision names exactly like the old inline loop did.
        report_groups = [
            {"group": gname, "parts": [o.name for o in members]}
            for gname, members in report_order
        ]

        if use_vision and vision_total > 0:
            progress.phase(
                f"Vision pass done: {len(vision_renames)}/{vision_total} part(s) renamed",
                0.98,
                force=True,
            )
            if ctx is not None:
                ctx.report(0.98, f"Vision pass done: {len(vision_renames)}/{vision_total} renamed")

        # Every separated piece must land visible -- separate()/duplicate()
        # can otherwise inherit a hidden state from the source object (e.g.
        # re-running on a previously-processed ".bak" source), which would
        # silently bury working parts instead of surfacing them.
        for piece_obj in separated_pieces:
            piece_obj.hide_viewport = False
            piece_obj.hide_render = False

        # Keep the original(s) as a hidden backup rather than deleting them --
        # renamed with a ".bak" suffix so they read unambiguously as inert
        # source geometry rather than a live duplicate part in the outliner.
        for obj in target_objs:
            obj.hide_viewport = True
            obj.hide_render = True
            if not obj.name.endswith(".bak"):
                obj.name = f"{obj.name}.bak"

        combined_note = f" (combined from {combined_count} selected objects)" if combined_count > 1 else ""
        classifier_note = "LLM" if used_llm else "heuristic spatial clustering (set OPENROUTER_API_KEY for smarter classification)"
        prompt_note = ""
        if custom_prompt.strip() and not used_llm:
            prompt_note = " Custom instructions were ignored -- they only apply when OPENROUTER_API_KEY is configured."
        vision_note_suffix = ""
        if vision_note:
            vision_note_suffix = f" {vision_note}"
        elif vision_renames:
            vision_note_suffix = f" +{len(vision_renames)} vision-assisted part rename(s)."
        progress.phase(
            f"Done: {len(separated_pieces)} part(s) in {len(report_groups)} group(s)",
            1.0,
            force=True,
        )
        if ctx is not None:
            ctx.report(1.0, f"Done: {len(separated_pieces)} part(s) in {len(report_groups)} group(s)")
        history = progress.history_payload()
        _save_history_card(
            progress,
            status=f"Done {len(separated_pieces)} parts in {history['total_seconds']:.1f}s",
            completed_summary=(
                f"Split into {len(separated_pieces)} parts / {len(report_groups)} groups "
                f"in {history['total_seconds']:.1f}s"
            ),
            next_steps=["Review groups in the Separation Result dialog"],
        )
        return {
            "success": True,
            "message": (
                f"Successfully separated '{original_name}'{combined_note} into {len(separated_pieces)} parts "
                f"across {len(report_groups)} logical groups (classified via {classifier_note})."
                f"{prompt_note}{vision_note_suffix}"
            ),
            "root_object": root_empty.name,
            "used_llm": used_llm,
            "groups": report_groups,
            "vision_used": use_vision,
            "vision_renames": vision_renames,
            "vision_note": vision_note,
            "history": history,
        }
