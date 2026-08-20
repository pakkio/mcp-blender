"""Unified Domain Facades for Blender MCP.
Consolidates ~138 micro-tools into 10 high-utility domain controllers (plus 4 tools kept
standalone: search_online_assets, import_online_asset, evaluate_scene_visually,
simplify_geometry), cutting schema context overhead by ~90% while maintaining full
underlying capabilities.
"""

from typing import Any, Literal, Optional
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field

from ..bridge import HEAVY_REQUEST_TIMEOUT_S, BlenderBridge
from ..docs.registry import search_docs, DOMAIN_DOCS
from ..vlm import is_configured, generate_text
import json
from ..errors import BridgeError, ErrorType
from .asset_source_ops import register_asset_source_tools
from .bridge_status_ops import register_bridge_status_tools
from .execute_python import register_execute_blender_python_tool
from .localization_ops import register_localization_tools
from .simplify_geometry_ops import register_simplify_geometry_tools
from .vision_eval_ops import register_vision_eval_tools


# --- Facade Parameter Models ---

class BlenderDocsParams(BaseModel):
    query: str = Field(description="Search term (e.g. 'cloth simulation', 'pbr materials', 'decimate', 'rigging')")
    category: Optional[str] = Field(default=None, description="Optional filter category ('RECIPE', 'MESH', 'MATERIAL', 'ASSETS', 'SCENE', 'RIGGING', 'LIGHTING', 'PHYSICS', 'RENDER', 'ALL')")


class BlenderRiggingAnimParams(BaseModel):
    action: Literal[
        "create_armature",
        "pose_bone",
        "setup_ik",
        "setup_humanoid_rig",
        "create_hair_curves",
        "apply_hair_groom",
        "set_keyframe",
        "turntable",
        "timeline_range",
    ] = Field(description="Rigging, bone posing, hair curves, and animation action")
    params: dict[str, Any] = Field(default_factory=dict, description="Action arguments (e.g. target_mesh='Character', density=50.0, frames=120)")


class BlenderCameraLightingParams(BaseModel):
    action: Literal[
        "camera_setup",
        "look_at",
        "frame_objects",
        "light_setup",
        "studio_lighting",
        "sun_sky_rig",
        "screenshot",
        "evaluate_scene",
        "compositor_effects",
    ] = Field(description="Camera positioning, studio/sun lighting rigs, and viewport screenshot capture")
    params: dict[str, Any] = Field(default_factory=dict, description="Action arguments (e.g. target_objects=['Cube'], margin=1.3, energy=1000.0)")


class BlenderPhysicsSimParams(BaseModel):
    action: Literal[
        "setup_rigid_body",
        "setup_cloth",
        "add_force_field",
        "bake_fluid",
        "configure_physics",
    ] = Field(description="Physics simulation setup (rigid body, cloth, wind, fluid bake)")
    params: dict[str, Any] = Field(default_factory=dict, description="Action arguments (e.g. object_name='Cloth', preset='SILK', strength=40.0)")


class BlenderRenderPipelineParams(BaseModel):
    action: Literal[
        "render_image",
        "render_anim",
        "bake_textures",
        "export_unity_fbx",
        "generate_lods",
        "vfx_tracking",
        "vfx_shadow_catcher",
    ] = Field(description="Render, texture baking, game engine export, and VFX tracking operations")
    params: dict[str, Any] = Field(default_factory=dict, description="Action arguments (e.g. output_path='render.png', resolution=2048, ratios=[1.0, 0.5])")


# --- Dispatch Helper ---

# --- Facade parameter hygiene ---
#
# The facades forward `params` verbatim and the Blender-side tools read the keys
# they know via params.get(...). A misnamed key is therefore dropped in SILENCE:
# the call returns success while doing nothing, which is far worse than an error
# (e.g. create_material with `color=` reported success and produced a default
# grey material; create_lighting_rig with `target=`/`distance=` reported success
# and built the rig at the world origin).
#
# _PARAM_SPECS records the accepted parameter names per bridge method, plus
# aliases for the names callers intuitively reach for. Methods absent from this
# table keep the previous permissive pass-through, so this is additive.
_PARAM_SPECS: dict[str, dict[str, Any]] = {
    "create_material": {
        "accepted": {
            "name", "base_color", "metallic", "roughness", "specular", "ior",
            "transmission", "emission_color", "emission_strength", "alpha",
            "assign_to_object",
        },
        "aliases": {
            "color": "base_color",
            "diffuse_color": "base_color",
            "object_name": "assign_to_object",
            "assign_to": "assign_to_object",
            "material_name": "name",
        },
    },
    "assign_material": {
        "accepted": {"object_name", "material_name", "slot_index"},
        "aliases": {"object": "object_name", "material": "material_name", "slot": "slot_index"},
    },
    "create_lighting_rig": {
        "accepted": {
            "rig_type", "target_object", "target_location", "distance",
            "energy_multiplier",
        },
        "aliases": {"energy": "energy_multiplier", "radius": "distance"},
    },
}


def _normalise_params(method: str, params: dict) -> dict:
    """Resolve aliases and reject unknown keys for methods with a known spec."""
    spec = _PARAM_SPECS.get(method)
    if not spec:
        return params

    accepted: set[str] = spec["accepted"]
    aliases: dict[str, str] = spec.get("aliases", {})
    out: dict[str, Any] = {}
    unknown: list[str] = []

    for key, value in params.items():
        # `target` is type-dependent: coordinates aim the rig at a point, a
        # string names an object to track.
        if method == "create_lighting_rig" and key == "target":
            canonical = "target_location" if isinstance(value, (list, tuple)) else "target_object"
        else:
            canonical = aliases.get(key, key)

        if canonical not in accepted:
            unknown.append(key)
            continue
        out[canonical] = value

    if unknown:
        raise BridgeError(
            ErrorType.VALIDATION,
            f"Unknown parameter(s) for '{method}': {', '.join(sorted(unknown))}. "
            f"Accepted: {', '.join(sorted(accepted))}.",
        )
    return out


async def _dispatch_bridge(bridge: BlenderBridge, method: str, params: dict, timeout: Optional[float] = None) -> dict:
    params = _normalise_params(method, params)
    result = await bridge.send_request(method, params, timeout=timeout)
    if not result.get("success"):
        raise BridgeError(ErrorType.TOOL_EXECUTION, result.get("message", f"Action '{method}' failed"))
    return result


def register_domain_facades(mcp: FastMCP, bridge: BlenderBridge) -> None:
    """Register the 10 consolidated domain controllers."""

    # 1. Documentation & Discovery
    @mcp.tool(
        name="blender_docs",
        description="Search documentation, multi-step 3D workflow recipes (e.g. cloth sim, character hair, PBR bake), and action parameter specifications on demand.",
    )
    async def blender_docs(query: str, category: Optional[str] = None) -> dict:
        results = search_docs(query, category)
        
        is_recipe_search = category is None or category.lower() in ("all", "recipe", "recipes")
        if is_recipe_search and is_configured():
            try:
                domains_summary = []
                for tool_name, domain in DOMAIN_DOCS.items():
                    actions_str = "\n".join([f"    - {action_name}: {action_desc}" for action_name, action_desc in domain["actions"].items()])
                    domains_summary.append(f"Tool '{tool_name}' ({domain['description']}):\n{actions_str}")
                domains_summary_str = "\n\n".join(domains_summary)

                system_prompt = (
                    "You are a Blender 3D automation pipeline assistant. Your task is to generate a custom multi-step recipe "
                    "to accomplish the user's goal using ONLY the available MCP tools and actions listed in your instructions.\n\n"
                    "Return ONLY a valid JSON object matching this schema:\n"
                    "{\n"
                    "  \"title\": \"Short descriptive title of the recipe\",\n"
                    "  \"description\": \"What this recipe accomplishes\",\n"
                    "  \"steps\": [\n"
                    "    {\n"
                    "      \"step\": 1,\n"
                    "      \"tool\": \"Name of the tool (must be one of the registered tools, e.g. blender_mesh)\",\n"
                    "      \"action\": \"Name of the action (must be one of the registered actions for this tool)\",\n"
                    "      \"params\": { ... key-value parameters matching the action description ... }\n"
                    "    }\n"
                    "  ],\n"
                    "  \"gotchas\": \"Important tips or caveats (e.g. Cycles render engine requirements, subdivision requirements).\"\n"
                    "}\n\n"
                    "Do not include any markdown fences or conversational prefaces/suffixes. Output only the raw JSON."
                )

                prompt = f"User Goal:\n{query}\n\nAvailable Tools & Action Specs:\n{domains_summary_str}"
                
                raw_json = await generate_text(
                    prompt=prompt,
                    system_prompt=system_prompt,
                    response_format={"type": "json_object"}
                )
                
                custom_recipe = json.loads(raw_json.strip())
                if custom_recipe and "steps" in custom_recipe:
                    custom_recipe["recipe_key"] = f"custom_llm_{query.replace(' ', '_').lower()[:30]}"
                    results["matched_recipes"].insert(0, custom_recipe)
                    results["custom_llm_recipe"] = custom_recipe
            except Exception as e:
                results["custom_llm_recipe_error"] = str(e)

        return results

    # 2. Mesh Modeling & Geometry
    @mcp.tool(
        name="blender_mesh",
        description=(
            "Geometry manipulation: create primitives, delete, duplicate, transform, boolean CSG, decimate "
            "(<10k poly budget), remesh, simplify to a vertex budget while preserving form, UV unwrap, edit "
            "mesh, and modifiers."
        ),
    )
    async def blender_mesh(
        action: Literal[
            "create",
            "delete",
            "duplicate",
            "transform",
            "apply_transform",
            "boolean",
            "decimate",
            "remesh",
            "simplify_geometry",
            "uv_unwrap",
            "mesh_op",
            "modifier",
            "origin_cursor",
        ],
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        p = params or {}
        method_map = {
            "create": "create_object",
            "delete": "delete_object",
            "duplicate": "duplicate_object",
            "transform": "set_object_transform",
            "apply_transform": "apply_transform",
            "boolean": "boolean_operation",
            "decimate": "decimate_mesh",
            "remesh": "remesh_mesh",
            "simplify_geometry": "simplify_geometry",
            "uv_unwrap": "uv_unwrap",
            "mesh_op": "mesh_operation",
            "modifier": "add_modifier",
            "origin_cursor": "manipulate_origin_cursor",
        }
        method = method_map.get(action, action)
        timeout = HEAVY_REQUEST_TIMEOUT_S if action in ("boolean", "decimate", "remesh", "simplify_geometry") else None
        return await _dispatch_bridge(bridge, method, p, timeout=timeout)

    # Kept standalone (also reachable via blender_mesh(action="simplify_geometry")):
    # it's a common, high-stakes operation on its own -- worth a top-level tool with
    # its own full parameter schema and description, not just a hidden import side effect.
    register_simplify_geometry_tools(mcp, bridge)

    # 3. Materials & Shaders
    @mcp.tool(
        name="blender_material",
        description="PBR shading, procedural grunge masks, toon/NPR shaders, alpha transparency, triplanar box mapping, and material slots.",
    )
    async def blender_material(
        action: Literal[
            "create",
            "assign",
            "pbr_setup",
            "procedural_grunge",
            "toon_shader",
            "transparency",
            "triplanar",
            "slots",
            "edit_nodes",
        ],
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        p = params or {}
        method_map = {
            "create": "create_material",
            "assign": "assign_material",
            "pbr_setup": "setup_pbr_materials",
            "procedural_grunge": "create_procedural_grunge_mask",
            "toon_shader": "create_toon_shader",
            "transparency": "configure_material_transparency",
            "triplanar": "setup_triplanar_mapping",
            "slots": "manage_material_slots",
            "edit_nodes": "edit_material_nodes",
        }
        method = method_map.get(action, action)
        return await _dispatch_bridge(bridge, method, p)

    # 4. Assets & AI 3D Generation (Meshy / Tripo / Poly Haven / Sketchfab)
    search_tool, import_tool = register_asset_source_tools(mcp, bridge)

    @mcp.tool(
        name="blender_assets",
        description=(
            "Search free/CC0 3D assets (Poly Haven, ambientCG, Sketchfab) or generate text-to-3D models with AI "
            "(Meshy AI, Tripo3D, Trellis) with auto-decimation & collection sorting. Import results carry an "
            "'orientation' report; when it says the model landed on its side or upside down, retry with "
            "params up_axis (the file's real up axis, usually 'Y') or auto_orient=true.\n\n"
            "ai_generate params: prompt (required), provider ('meshy'|'tripo', default 'meshy'), "
            "target_vertices (post-generation vertex budget, default 30000), reduction_method -- "
            "'simplify' (default, form-preserving weld+dissolve+iterative collapse; higher quality but can run "
            "for minutes on a dense/complex generated mesh), 'decimate' (plain ratio decimate, much faster, use "
            "this for quick iteration or if 'simplify' is timing out), 'remesh' (voxel remesh, destroys UVs -- "
            "avoid, generated models are textured), or 'none' (skip reduction entirely, fastest, keep the raw "
            "generated mesh). Meshy AI results are always textured (a 'preview' untextured pass followed "
            "automatically by a 'refine' texturing pass -- there is no untextured-only mode)."
        ),
    )
    async def blender_assets(
        action: Literal[
            "search_online",
            "import_online",
            "ai_generate",
            "asset_browser",
        ],
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        p = params or {}
        if action == "search_online":
            return await search_tool(
                query=p.get("query", ""),
                asset_type=p.get("asset_type", "MODEL"),
                providers=p.get("providers"),
                limit=p.get("limit", 10),
                free_only=p.get("free_only", True),
            )
        elif action == "import_online":
            return await import_tool(
                asset_id=p.get("asset_id", ""),
                provider=p.get("provider", "sketchfab"),
                target_poly_budget=p.get("target_poly_budget"),
                collection_path=p.get("collection_path"),
                location=p.get("location"),
                scale_to_size=p.get("scale_to_size"),
                forward_axis=p.get("forward_axis"),
                up_axis=p.get("up_axis"),
                auto_orient=p.get("auto_orient", False),
            )
        elif action == "ai_generate":
            prompt = p.get("prompt", p.get("query", ""))
            if not prompt:
                raise BridgeError(ErrorType.VALIDATION, "'prompt' is required for ai_generate")
            provider = (p.get("provider", "meshy") or "meshy").lower()
            reduction = (p.get("reduction_method", "simplify") or "simplify").lower()
            target_verts = int(p.get("target_vertices", 30000))

            asset_id = f"{provider}_prompt_{prompt.replace(' ', '_')[:30]}"
            provider_label = provider.capitalize()
            collection = p.get("collection_path", f"Generated/{provider_label}")

            return await import_tool(
                asset_id=asset_id,
                provider=provider,
                target_poly_budget=target_verts,
                reduction_method=reduction if reduction != "none" else None,
                collection_path=collection,
                location=p.get("location"),
                forward_axis=p.get("forward_axis"),
                up_axis=p.get("up_axis"),
                auto_orient=p.get("auto_orient", False),
            )
        elif action == "asset_browser":
            return await _dispatch_bridge(bridge, "manage_asset_browser", p)
        raise BridgeError(ErrorType.TOOL_EXECUTION, f"Unknown asset action '{action}'")

    # 5. Scene, Hierarchy, Checkpoints & Background Jobs
    @mcp.tool(
        name="blender_scene",
        description="Scene-level control: get scene info, organize semantic collections, create/restore snapshot checkpoints for safe undo, purge orphans, and monitor background jobs.",
    )
    async def blender_scene(
        action: Literal[
            "info",
            "hierarchy",
            "collection",
            "checkpoint_create",
            "checkpoint_restore",
            "checkpoint_list",
            "purge_orphans",
            "job_status",
            "job_list",
            "job_cancel",
            "performance",
            "busy",
            "regen",
        ],
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        p = params or {}
        if action == "regen":
            return await regen_tool(
                lang=p.get("lang", "it"),
                element=p.get("element"),
                use_vision=p.get("use_vision", False),
                max_vision_renames=p.get("max_vision_renames", 15),
                vision_model=p.get("vision_model"),
            )
        method_map = {
            "info": "get_scene_info",
            "hierarchy": "organize_scene_hierarchy",
            "collection": "manage_collection",
            "checkpoint_create": "create_scene_checkpoint",
            "checkpoint_restore": "restore_scene_checkpoint",
            "checkpoint_list": "list_scene_checkpoints",
            "purge_orphans": "purge_orphans_and_cleanup",
            "job_status": "get_job_status",
            "job_list": "list_jobs",
            "job_cancel": "cancel_job",
            "performance": "inspect_scene_performance",
            "busy": "bridge_status",
        }
        method = method_map.get(action, action)
        # "busy" answers instantly straight off the websocket thread (see
        # extension/bridge/server.py) regardless of what's running on the
        # main thread, so it never needs the heavy timeout -- it's the one
        # action explicitly meant to work *while* something else is heavy.
        timeout = HEAVY_REQUEST_TIMEOUT_S if action in ("checkpoint_create", "checkpoint_restore") else None
        return await _dispatch_bridge(bridge, method, p, timeout=timeout)

    # Kept standalone (also reachable via blender_scene(action="busy")): a
    # non-blocking busy check is meant to be reached for quickly while
    # something else may be mid-flight, so it gets its own top-level tool
    # rather than being buried a level down in a params dict.
    register_bridge_status_tools(mcp, bridge)

    # Kept standalone (also reachable via blender_scene(action="regen")): the
    # literal `regen("it")`-style call this was asked for is worth a direct
    # top-level tool, not just a nested action.
    regen_tool = register_localization_tools(mcp, bridge)

    # 6. Rigging, Hair Curves & Animation
    @mcp.tool(
        name="blender_rigging_anim",
        description="Rigging & animation: create armatures, pose bones, IK constraints, humanoid rig presets, Blender 4.2+ hair curves creation/grooming, keyframes, and turntable animation.",
    )
    async def blender_rigging_anim(
        action: Literal[
            "create_armature",
            "pose_bone",
            "setup_ik",
            "setup_humanoid_rig",
            "create_hair_curves",
            "apply_hair_groom",
            "set_keyframe",
            "turntable",
            "timeline_range",
        ],
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        p = params or {}
        method_map = {
            "create_armature": "create_armature",
            "pose_bone": "pose_bone",
            "setup_ik": "setup_ik_constraint",
            "setup_humanoid_rig": "setup_humanoid_rig_preset",
            "create_hair_curves": "create_hair_curves",
            "apply_hair_groom": "apply_hair_groom_modifier",
            "set_keyframe": "set_keyframe",
            "turntable": "animate_camera_turntable",
            "timeline_range": "set_timeline_range",
        }
        method = method_map.get(action, action)
        return await _dispatch_bridge(bridge, method, p)

    # 7. Camera, Lighting & Visual Evaluation
    eval_tool = register_vision_eval_tools(mcp, bridge)

    @mcp.tool(
        name="blender_camera_lighting",
        description="Cameras & lighting: camera lenses, look-at targets, auto-framing, 3-point studio lighting, Nishita sun/sky atmospheres, viewport screenshot capture, and AI visual critique.",
    )
    async def blender_camera_lighting(
        action: Literal[
            "camera_setup",
            "look_at",
            "frame_objects",
            "light_setup",
            "studio_lighting",
            "sun_sky_rig",
            "screenshot",
            "evaluate_scene",
            "compositor_effects",
        ],
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        p = params or {}
        if action == "evaluate_scene":
            return await eval_tool(
                camera_name=p.get("camera_name"),
                prompt=p.get("prompt"),
                resolution=p.get("resolution", (1024, 768)),
            )
        method_map = {
            "camera_setup": "configure_camera",
            "look_at": "camera_look_at",
            "frame_objects": "frame_objects",
            "light_setup": "configure_light",
            "studio_lighting": "create_lighting_rig",
            "sun_sky_rig": "setup_sky_sun_rig",
            "screenshot": "get_viewport_screenshot",
            "compositor_effects": "configure_compositor_effects",
        }
        method = method_map.get(action, action)
        timeout = HEAVY_REQUEST_TIMEOUT_S if action == "screenshot" else None
        return await _dispatch_bridge(bridge, method, p, timeout=timeout)

    # 8. Physics & Simulation
    @mcp.tool(
        name="blender_physics_sim",
        description="Physics simulations: rigid bodies, cloth simulation, wind/vortex force fields, fluid domain baking, and scene gravity/physics parameters.",
    )
    async def blender_physics_sim(
        action: Literal[
            "setup_rigid_body",
            "setup_cloth",
            "add_force_field",
            "bake_fluid",
            "configure_physics",
        ],
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        p = params or {}
        method_map = {
            "setup_rigid_body": "setup_rigid_body_simulation",
            "setup_cloth": "setup_cloth_simulation",
            "add_force_field": "add_force_field",
            "bake_fluid": "bake_fluid_domain",
            "configure_physics": "configure_scene_physics",
        }
        method = method_map.get(action, action)
        timeout = HEAVY_REQUEST_TIMEOUT_S if action == "bake_fluid" else None
        return await _dispatch_bridge(bridge, method, p, timeout=timeout)

    # 9. Render, Bake & Pipeline Export
    @mcp.tool(
        name="blender_render_pipeline",
        description="Rendering & export: still image render, animation render, PBR/AO/normal map baking, Unity FBX game-ready export with axis correction, LOD chain generation, and VFX camera tracking.",
    )
    async def blender_render_pipeline(
        action: Literal[
            "render_image",
            "render_anim",
            "bake_textures",
            "export_unity_fbx",
            "generate_lods",
            "vfx_tracking",
            "vfx_shadow_catcher",
        ],
        params: Optional[dict[str, Any]] = None,
    ) -> dict:
        p = params or {}
        method_map = {
            "render_image": "render_scene",
            "render_anim": "render_animation_sequence",
            "bake_textures": "bake_textures",
            "export_unity_fbx": "export_unity_fbx",
            "generate_lods": "generate_lods",
            "vfx_tracking": "setup_camera_tracking",
            "vfx_shadow_catcher": "setup_vfx_shadow_catcher",
        }
        method = method_map.get(action, action)
        timeout = HEAVY_REQUEST_TIMEOUT_S if action in ("render_image", "render_anim", "bake_textures", "export_unity_fbx", "generate_lods") else None
        return await _dispatch_bridge(bridge, method, p, timeout=timeout)

    # 10. Direct Python execution escape hatch
    register_execute_blender_python_tool(mcp, bridge)
