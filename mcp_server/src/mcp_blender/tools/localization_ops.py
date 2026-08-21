"""Localized structural renaming: a thin wrapper around the Blender-side
regen_element_names (which handles category collections/Empties via a
keyword vocabulary) plus an optional vision-assisted pass for the mesh
leaves the vocabulary can't cover -- a "Chair_Mesh" or "Cylinder.003" has no
category keyword to match, but a vision model looking at it in context can
name it by semantic role.
"""

from typing import Any, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from .. import client_status
from ..bridge import HEAVY_REQUEST_TIMEOUT_S, BlenderBridge
from ..errors import BridgeError, ErrorType
from ..vlm import VLMError, critique_image, extract_png_bytes, is_configured

# Mirrors extension/tools/localization_ops.py's CATEGORY_TRANSLATIONS keys --
# only used to turn a lang code into a display name for the vision prompt.
LANG_DISPLAY_NAMES = {"it": "Italian", "en": "English"}

_DEFAULT_MAX_VISION_RENAMES = 9999


class RegenNamesParams(BaseModel):
    lang: str = "it"
    element: Optional[str] = None
    use_vision: bool = False
    max_vision_renames: int = Field(default=_DEFAULT_MAX_VISION_RENAMES, ge=0, le=9999)
    vision_model: Optional[str] = None
    vision_only_generic: bool = False


def _collect_mesh_objects(node: dict) -> list[dict]:
    """Flatten the regen_element_names report tree into every MESH leaf, each
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
        found.extend(_collect_mesh_objects(child))
    return found


def _mesh_candidates(structural: dict) -> list[dict]:
    """MESH leaves to offer the vision pass, from either report shape.

    regen_element_names only returns a "root" collection tree when it was
    scoped to a collection/scene; scoping it to a plain object instead
    (element=<object name>) returns a flat "objects" list and no "root" at
    all, so reaching for structural["root"] unconditionally raised KeyError.
    """
    root = structural.get("root")
    if root:
        return _collect_mesh_objects(root)
    return [
        {"name": obj["new_name"], "category": None, "renamed": bool(obj.get("renamed", False))}
        for obj in structural.get("objects", [])
        if obj.get("type") == "MESH"
    ]


def _sanitize_vision_name(text: str) -> str:
    # Vision models sometimes wrap the answer in a sentence or quotes despite
    # instructions -- take the first line, strip quoting/trailing punctuation,
    # and cap length so a rambling answer can't produce an unusable name.
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    return first_line.strip(" .\"'“”").strip()[:40]


def register_localization_tools(mcp: FastMCP, bridge: BlenderBridge):
    @mcp.tool(
        name="regen_names",
        description=(
            "Regenerate the names of a scene element's structure in a target language (default Italian, "
            "'it'). Renames category collections/Empties via a keyword vocabulary (e.g. 'Furniture' -> "
            "'Arredamento'), keeps and reports nodes with zero objects rather than skipping them (they're "
            "scaffolds, not errors), and re-links every collection's children/objects in alphabetical order. "
            "Pass element to scope this to one collection or root-Empty instead of the whole scene. Pass "
            "use_vision=true to also name mesh leaves the vocabulary can't cover (e.g. 'Chair_Mesh') by "
            "looking at each one and asking a vision model for its semantic role within its category -- not "
            "a shape description ('cube', 'cylinder'), a real part name ('seat', 'leg', 'wheel'). Requires "
            "OPENROUTER_API_KEY; without it, use_vision is silently skipped and only the structural pass runs. "
            "Capped at max_vision_renames (default 9999) objects per call to bound cost/time. Pass "
            "vision_only_generic=true to restrict the vision pass to leaves the structural pass left "
            "untouched instead of re-naming every mesh."
        ),
    )
    async def regen_names(
        lang: str = "it",
        element: Optional[str] = None,
        use_vision: bool = False,
        max_vision_renames: int = _DEFAULT_MAX_VISION_RENAMES,
        vision_model: Optional[str] = None,
        vision_only_generic: bool = False,
    ) -> dict:
        params = RegenNamesParams(
            lang=lang,
            element=element,
            use_vision=use_vision,
            max_vision_renames=max_vision_renames,
            vision_model=vision_model,
            vision_only_generic=vision_only_generic,
        )

        structural = await bridge.send_request(
            "regen_element_names",
            {"lang": params.lang, "element": params.element},
            timeout=HEAVY_REQUEST_TIMEOUT_S,
        )
        if not structural.get("success"):
            raise BridgeError(ErrorType.TOOL_EXECUTION, structural.get("message", "regen_element_names failed"))

        vision_renames: list[dict] = []
        vision_note = None
        if params.use_vision:
            if not is_configured():
                vision_note = "use_vision requested but OPENROUTER_API_KEY is not set -- structural pass only."
            else:
                lang_name = LANG_DISPLAY_NAMES.get(params.lang, params.lang)
                candidates = _mesh_candidates(structural)
                if params.vision_only_generic:
                    candidates = [c for c in candidates if not c.get("renamed")]
                candidates = candidates[: params.max_vision_renames]
                async with client_status.track(bridge, f"Naming objects visually ({lang_name})...") as set_status:
                    for i, candidate in enumerate(candidates, 1):
                        obj_name = candidate["name"]
                        await set_status(
                            f"Naming '{obj_name}' via vision ({lang_name})... ({i}/{len(candidates)})"
                        )
                        try:
                            capture = await bridge.send_request(
                                "inspect_focus_shot", {"target_object": obj_name, "include_base64": True}
                            )
                            if not capture.get("success"):
                                continue
                            png_bytes = extract_png_bytes(capture, "image_base64")
                            if not png_bytes:
                                continue

                            category = candidate.get("category")
                            context = f" It belongs to the '{category}' group." if category else ""
                            question = (
                                f"This 3D model part is currently named '{obj_name}'.{context} In one or two "
                                f"words, name it by its SEMANTIC ROLE or FUNCTION within the whole object "
                                f"(e.g. 'leg', 'seat', 'wheel', 'handle', 'blade') -- NOT its geometric shape "
                                f"(never answer 'cube', 'cylinder', 'sphere', 'cone', or similar). Reply in "
                                f"{lang_name} with ONLY that name, capitalized, no punctuation."
                            )
                            verdict = await critique_image(question, png_bytes, params.vision_model)
                            new_name = _sanitize_vision_name(verdict["critique"])
                            if not new_name:
                                continue

                            rename_result = await bridge.send_request(
                                "set_object_properties", {"name": obj_name, "new_name": new_name}
                            )
                            if rename_result.get("success"):
                                vision_renames.append(
                                    {"old_name": obj_name, "new_name": rename_result.get("name")}
                                )
                        except VLMError:
                            continue
                        except Exception:  # noqa: BLE001 -- one bad object must not abort the whole pass
                            continue

        return {
            "success": True,
            "message": structural["message"],
            "lang": params.lang,
            "structural": structural.get("root") or {"objects": structural.get("objects", [])},
            "vision_used": params.use_vision and is_configured(),
            "vision_renames": vision_renames,
            "vision_note": vision_note,
        }

    return regen_names
