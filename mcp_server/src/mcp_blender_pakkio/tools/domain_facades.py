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
from ..docs.registry import search_docs
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


class BlenderMeshParams(BaseModel):
    action: Literal[
        "create",
        "delete",
        "duplicate",
        "transform",
        "apply_transform",
        "boolean",
        "decimate",
        "remesh",
        "uv_unwrap",
        "mesh_op",
        "modifier",
        "origin_cursor",
    ] = Field(description="Action to perform on mesh geometry")
    params: dict[str, Any] = Field(default_factory=dict, description="Action arguments (e.g. type='CUBE', object_name='Cube', ratio=0.1)")


class BlenderMaterialParams(BaseModel):
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
    ] = Field(description="Action to perform on materials/shaders")
    params: dict[str, Any] = Field(default_factory=dict, description="Action arguments (e.g. material_name='Gold', base_color=[0.8, 0.6, 0.2, 1.0])")


class BlenderAssetsParams(BaseModel):
    action: Literal[
        "search_online",
        "import_online",
        "meshy_generate",
        "tripo_generate",
        "asset_browser",
    ] = Field(description="Asset action (search, AI text-to-3d generation, import)")
    params: dict[str, Any] = Field(default_factory=dict, description="Action arguments (e.g. query='snake', provider='meshy', prompt='a sword', target_poly_budget=25000)")


class BlenderSceneParams(BaseModel):
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
    ] = Field(description="Scene-level inspection, hierarchy, snapshot checkpoints, and background job operations")
    params: dict[str, Any] = Field(default_factory=dict, description="Action arguments (e.g. include_hierarchy=True, name='pre_sim', job_id='job_1')")


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

async def _dispatch_bridge(bridge: BlenderBridge, method: str, params: dict, timeout: Optional[float] = None) -> dict:
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
        return search_docs(query, category)

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
            "params up_axis (the file's real up axis, usually 'Y') or auto_orient=true."
        ),
    )
    async def blender_assets(
        action: Literal[
            "search_online",
            "import_online",
            "meshy_generate",
            "tripo_generate",
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
        elif action == "meshy_generate":
            prompt = p.get("prompt", p.get("query", ""))
            return await import_tool(
                asset_id=f"meshy_prompt_{prompt.replace(' ', '_')[:30]}",
                provider="meshy",
                target_poly_budget=p.get("target_poly_budget", 30000),
                collection_path=p.get("collection_path", "Generated/Meshy"),
                location=p.get("location"),
                forward_axis=p.get("forward_axis"),
                up_axis=p.get("up_axis"),
                auto_orient=p.get("auto_orient", False),
            )
        elif action == "tripo_generate":
            prompt = p.get("prompt", p.get("query", ""))
            return await import_tool(
                asset_id=f"tripo_{prompt.replace(' ', '_')[:30]}",
                provider="tripo",
                target_poly_budget=p.get("target_poly_budget", 25000),
                collection_path=p.get("collection_path", "Generated/Tripo"),
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
        return await _dispatch_bridge(bridge, method, p)

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
