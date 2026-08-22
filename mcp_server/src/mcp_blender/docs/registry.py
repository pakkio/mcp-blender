"""Curated documentation, multi-step 3D workflow recipes, and action parameter specs.
Allows LLMs and human users to query exact parameters, best practices, and recipes
on demand without bloating the global prompt context.
"""

from typing import Any, Optional


RECIPES: dict[str, dict[str, Any]] = {
    "ai_asset_generation": {
        "title": "Text-to-3D AI Asset Generation & Optimization",
        "description": "Generate a 3D model using Meshy AI / Tripo3D / Trellis, import it into Blender, auto-decimate to budget, and frame it.",
        "steps": [
            {
                "step": 1,
                "tool": "blender_scene",
                "action": "checkpoint_create",
                "params": {"name": "pre_asset_gen", "description": "Snapshot before importing new generated model"},
            },
            {
                "step": 2,
                "tool": "blender_assets",
                "action": "search_online",
                "params": {"query": "medieval treasure chest", "providers": ["meshy", "sketchfab"], "limit": 5},
            },
            {
                "step": 3,
                "tool": "blender_assets",
                "action": "import_online",
                "params": {
                    "provider": "meshy",
                    "asset_id": "<asset_id_from_search>",
                    "target_poly_budget": 25000,
                    "collection_path": "Props/Chests",
                    "location": [0.0, 0.0, 0.0],
                },
            },
            {
                "step": 4,
                "tool": "blender_camera_lighting",
                "action": "frame_objects",
                "params": {"target_objects": ["<imported_object_name>"], "margin": 1.3},
            },
            {
                "step": 5,
                "tool": "blender_camera_lighting",
                "action": "screenshot",
                "params": {},
            },
        ],
        "gotchas": "Generative models often arrive with high polycounts (>1M). Always supply target_poly_budget or use blender_mesh(action='decimate', ratio=0.01..0.05).",
    },
    "cloth_simulation": {
        "title": "Cloth Physics Simulation & Pinning",
        "description": "Create a subdivided plane, add cloth physics, setup collisions, and add wind force field.",
        "steps": [
            {
                "step": 1,
                "tool": "blender_mesh",
                "action": "create",
                "params": {"type": "PLANE", "name": "FlagCloth", "location": [0.0, 0.0, 3.0], "scale": [2.0, 1.5, 1.0]},
            },
            {
                "step": 2,
                "tool": "blender_mesh",
                "action": "mesh_op",
                "params": {"object_name": "FlagCloth", "operation": "SUBDIVIDE", "cuts": 15},
            },
            {
                "step": 3,
                "tool": "blender_physics_sim",
                "action": "setup_cloth",
                "params": {"object_name": "FlagCloth", "preset": "SILK", "quality_steps": 5, "enable_pressure": False},
            },
            {
                "step": 4,
                "tool": "blender_physics_sim",
                "action": "add_force_field",
                "params": {"type": "WIND", "strength": 40.0, "location": [-3.0, 0.0, 3.0], "rotation": [0.0, 1.57, 0.0]},
            },
        ],
        "gotchas": "Cloth requires sufficient geometric vertices to deform. Always subdivide before applying cloth modifier.",
    },
    "character_rigging_hair": {
        "title": "Humanoid Character Rigging & Hair Curves",
        "description": "Set up a humanoid armature, configure IK constraints, and add modern Blender 4.2+ hair curves.",
        "steps": [
            {
                "step": 1,
                "tool": "blender_rigging_anim",
                "action": "setup_humanoid_rig",
                "params": {"target_mesh": "CharacterBody", "rig_preset": "BASIC_BIPED"},
            },
            {
                "step": 2,
                "tool": "blender_rigging_anim",
                "action": "setup_ik",
                "params": {"armature_name": "CharacterBody_Rig", "bone_name": "Hand.L", "target_name": "IK_Target.L", "chain_length": 2},
            },
            {
                "step": 3,
                "tool": "blender_rigging_anim",
                "action": "create_hair_curves",
                "params": {"surface_object": "CharacterBody", "density": 50.0, "length": 0.25, "name": "CharacterHair"},
            },
            {
                "step": 4,
                "tool": "blender_rigging_anim",
                "action": "apply_hair_groom",
                "params": {"curves_object": "CharacterHair", "modifier_type": "CLUMP", "strength": 0.7},
            },
        ],
        "gotchas": "Blender 4.2+ uses modern Hair Curves geometry nodes rather than legacy particle hair.",
    },
    "pbr_material_baking": {
        "title": "PBR Material Setup & Texture Map Baking",
        "description": "Create PBR procedural materials and bake them to image texture maps (Diffuse, Normal, Roughness).",
        "steps": [
            {
                "step": 1,
                "tool": "blender_material",
                "action": "pbr_setup",
                "params": {"object_name": "ModelProp", "base_color": [0.8, 0.6, 0.2, 1.0], "metallic": 0.9, "roughness": 0.25},
            },
            {
                "step": 2,
                "tool": "blender_mesh",
                "action": "uv_unwrap",
                "params": {"object_name": "ModelProp", "method": "SMART_PROJECT", "island_margin": 0.02},
            },
            {
                "step": 3,
                "tool": "blender_render_pipeline",
                "action": "bake_textures",
                "params": {"object_name": "ModelProp", "pass_type": "COMBINED", "resolution": 2048, "margin": 16},
            },
        ],
        "gotchas": "Cycles render engine is required for GPU/CPU texture baking.",
    },
    "game_engine_export": {
        "title": "Unity / Unreal Engine Game-Ready Export Pipeline",
        "description": "Generate Level of Detail (LOD) hierarchies and export clean FBX with axis orientation fixes.",
        "steps": [
            {
                "step": 1,
                "tool": "blender_render_pipeline",
                "action": "generate_lods",
                "params": {"object_name": "HeroProp", "ratios": [1.0, 0.5, 0.25, 0.1], "group_name": "HeroProp_LODGroup"},
            },
            {
                "step": 2,
                "tool": "blender_render_pipeline",
                "action": "export_unity_fbx",
                "params": {"filepath": "exports/HeroProp.fbx", "apply_modifiers": True, "bake_anim": True, "embed_textures": True},
            },
        ],
        "gotchas": "export_unity_fbx automatically fixes the -90 degree X rotation bug between Blender Z-up and Unity Y-up.",
    },
    "mesh_logical_segmentation": {
        "title": "Segment an Imported Mesh into Named Sub-Assemblies",
        "description": "Split a single-blob imported mesh (a whole building, vehicle, or prop with no useful part boundaries) into an LLM-classified macro/medium/micro hierarchy of named parts, then localize any leftover generic names.",
        "steps": [
            {
                "step": 1,
                "tool": "blender_scene",
                "action": "checkpoint_create",
                "params": {"name": "pre_segmentation", "description": "Snapshot before destructive mesh separation"},
            },
            {
                "step": 2,
                "tool": "blender_mesh",
                "action": "separate_logical_areas",
                "params": {"objects": ["<imported_mesh_object_name>"], "lang": "it", "reorg_level": "STANDARD"},
            },
            {
                "step": 3,
                "tool": "regen_names",
                "params": {"element": "<root_object_from_step_2>", "use_vision": True, "vision_only_generic": True},
            },
        ],
        "gotchas": "separate_logical_areas selects the given objects internally, combining multiple into one mesh first -- pass every source object you want merged+split in a single 'objects' list rather than calling it once per object. The original source is renamed with a '.bak' suffix and hidden, not deleted, so it's recoverable without restoring the checkpoint. use_vision on either tool requires OPENROUTER_API_KEY; without it, only the LLM-text/heuristic classification pass runs.",
    },
}

DOMAIN_DOCS: dict[str, dict[str, Any]] = {
    "blender_mesh": {
        "description": "3D modeling, mesh manipulation, geometry transforms, booleans, decimation, remeshing, and UVs.",
        "actions": {
            "create": "Create 3D primitives (CUBE, UV_SPHERE, ICO_SPHERE, CYLINDER, CONE, TORUS, PLANE, GRID, MONKEY, CIRCLE, EMPTY, CAMERA, LIGHT, TEXT, CURVE_BEZIER, CURVE_CIRCLE). Params: object_type (not 'type' -- unrecognized keys are silently ignored and default to CUBE), name, location, rotation_euler, scale, radius, size, collection.",
            "delete": "Delete one or more objects by name. Params: name or names.",
            "duplicate": "Duplicate an object with optional transform offset. Params: object_name, location_offset, linked.",
            "transform": "Set absolute/relative location, rotation_euler, or scale on an object. Params: name, location, rotation_euler, scale, relative.",
            "apply_transform": "Bake/apply location, rotation, and scale deltas into the raw mesh vertices. Params: name, apply_location, apply_rotation, apply_scale.",
            "boolean": "Perform CSG Boolean operations (UNION, DIFFERENCE, INTERSECT, SLICE). Params: target_object, operand_object, operation, solver.",
            "decimate": "Reduce polygon/vertex count using COLLAPSE, UNSUBDIV, or PLANAR. Params: object_name, ratio (e.g. 0.1 for 10%), mode. Assumes an already-welded, manifold mesh -- on a raw imported asset use simplify_geometry instead, or holes/torn topology are likely.",
            "remesh": "Voxel or Quad remesh geometry for clean manifold topology. Params: object_name, mode ('VOXEL'), voxel_size. Rebuilds the surface from scratch (destroys UVs) rather than reducing the existing one -- use simplify_geometry when the asset needs to keep its UVs/textures.",
            "simplify_geometry": "Reduce a mesh to a vertex budget while preserving its form: repairs the mesh (welds seams, drops loose geometry, closes pinhole gaps), then removes vertices from flat/dense regions first via limited dissolve and curvature-weighted decimation, protecting thin features/boundaries. Measures the result and rolls back on a failed quality gate instead of returning a broken mesh. Params: object_name, target or preset ('BACKGROUND'=10k, 'HERO'=30k, 'MAX'=100k), preserve_uv, max_deviation_pct, dry_run.",
            "uv_unwrap": "Unwrap UV coordinates using SMART_PROJECT, CUBE, SPHERE, or LIGHTMAP. Params: object_name, method, island_margin.",
            "mesh_op": "Edit-mode operations: SUBDIVIDE, EXTRUDE, BEVEL, INSET, MERGE_BY_DISTANCE, RECALCULATE_NORMALS. Params: object_name, operation.",
            "modifier": "Add, configure, or apply modifiers (SUBSURF, BEVEL, SOLIDIFY, ARRAY, MIRROR, DISPLACE). Params: object_name, modifier_type, properties, apply_immediately.",
            "separate_logical_areas": "Combine the given mesh object(s) into one working mesh, separate it into logical parts (by connectivity or materials), classify+rename them via LLM into medium-level sub-assemblies and micro-level parts, and organize them under parent Empties in a macro/medium/micro hierarchy. Every separated part stays visible; the original source object(s) are renamed with a '.bak' suffix and hidden instead of deleted. Params: objects (required list of mesh object names -- multiple are combined first), lang (default 'it'), reorg_level (default 'STANDARD'), custom_prompt, use_vision (bool, names parts by close-up render via a vision model -- requires OPENROUTER_API_KEY), max_vision_renames (default 9999), vision_model, vision_only_generic (restrict vision pass to parts that fell back to a generic 'Part_N' name).",
        },
    },
    "blender_material": {
        "description": "PBR shading, procedural node groups, toon/NPR materials, transparency, and texture mapping.",
        "actions": {
            "create": "Create a new named material. Params: name, use_nodes.",
            "assign": "Assign material to an object or specific slot index. Params: object_name, material_name, slot_index.",
            "pbr_setup": "Configure Principled BSDF PBR properties. Params: object_name, material_name, base_color, metallic, roughness, specular, emission.",
            "procedural_grunge": "Add procedural grunge/wear mask (triplanar noise/musgrave) to material nodes. Params: material_name, roughness_scale, wear_amount.",
            "toon_shader": "Create NPR/Anime toon shader with color ramp and outline. Params: material_name, base_color, shadow_color, steps.",
            "transparency": "Configure alpha blend mode (OPAQUE, CLIP, HASHED, BLEND) and refraction. Params: material_name, blend_mode, ior.",
            "triplanar": "Setup box/triplanar projection mapping without manual UV seams. Params: material_name, image_path, blend.",
            "slots": "Manage material slots: ADD, REMOVE, ASSIGN_POLYGONS. Params: object_name, action, material_name, polygon_indices.",
        },
    },
    "blender_assets": {
        "description": "Search and import from online catalogs (Poly Haven, ambientCG, Sketchfab) or generate 3D models with AI (Meshy, Tripo3D, Trellis).",
        "actions": {
            "search_online": "Search 3D models, textures, or HDRIs. Params: query, asset_type ('MODEL'|'TEXTURE'|'HDRI'), providers (['polyhaven','sketchfab','meshy','tripo','trellis']), limit, free_only.",
            "import_online": "Download and import online/generated asset into scene. Params: provider, asset_id, target_poly_budget, reduction_method ('simplify'|'decimate'|'remesh', default auto simplify-with-decimate-fallback), collection_path, location, scale_to_size, include_preview (default true). Result carries vertices_count (final), preview_base64 (PNG of the placed asset), and credits (license + attribution combined).",
            "meshy_generate": "Direct shortcut to generate 3D model via Meshy AI text-to-3d. Params: prompt, art_style ('realistic'|'sculpture'), target_poly_budget, collection_path.",
            "tripo_generate": "Direct shortcut to generate 3D model via Tripo3D AI. Params: prompt, target_poly_budget, collection_path.",
            "asset_browser": "Import or catalog assets with Blender's native Asset Browser. Params: action ('IMPORT'|'MARK'|'CLEAR'), asset_name, library_name.",
        },
    },
    "blender_scene": {
        "description": "Scene inspection, collection hierarchy, transactional checkpoints/undo, orphan cleanup, and async background jobs.",
        "actions": {
            "info": "Comprehensive scene metadata (objects, collections, materials, render engine, active camera). Params: include_hierarchy (bool).",
            "hierarchy": "Auto-organize loose scene objects into clean semantic collections (e.g. Architecture, Props, Characters). Params: create_missing_collections (bool).",
            "collection": "Create, delete, rename, or link objects to collections. Params: action ('CREATE'|'DELETE'|'LINK'|'UNLINK'), name, object_names, parent_collection.",
            "checkpoint_create": "Save a non-destructive full scene snapshot before risky/destructive operations. Params: name, description.",
            "checkpoint_restore": "Rollback the scene to a previously saved checkpoint snapshot. Params: name.",
            "checkpoint_list": "List all active scene checkpoints.",
            "purge_orphans": "Purge unused datablocks (unused meshes, materials, images, textures) to free memory. Params: recursive (bool).",
            "job_status": "Check status of background async job. Params: job_id.",
            "job_list": "List all running and finished background jobs.",
            "job_cancel": "Cancel a running background job. Params: job_id.",
            "busy": "Non-blocking check for whether Blender's main thread is still busy with a previous heavy command (e.g. checkpoint_create, render, bake). Always answers instantly, even mid-operation. Response includes current.description (e.g. \"create_scene_checkpoint({\\\"name\\\":\\\"before_boolean\\\"}) — running for 12.3s\"), current.running_for_s, current.method, and queue_depth for anything else waiting behind it -- poll this instead of re-sending or waiting out a slow request's own timeout. No params.",
            "regen": "Rename a scene element's category collections/Empties into a target language (default 'it'/Italian) via a keyword vocabulary, keep+report zero-object nodes instead of skipping them, and re-link every collection alphabetically. Params: lang (default 'it'), element (scope to one collection/root-Empty, default whole scene), use_vision (bool, also names mesh leaves like 'Chair_Mesh' by semantic role via a vision model -- requires OPENROUTER_API_KEY), max_vision_renames (default 9999), vision_model, vision_only_generic (restrict vision pass to leaves the structural pass left untouched).",
        },
    },
    "blender_rigging_anim": {
        "description": "Character armatures, bone posing, IK/Spline constraints, modern hair curves grooming, and animation keyframes.",
        "actions": {
            "create_armature": "Create a new armature rig. Params: name, bone_names, parent_chain.",
            "pose_bone": "Pose an individual bone. Params: armature_name, bone_name, location, rotation_euler, rotation_quaternion.",
            "setup_ik": "Add an Inverse Kinematics constraint to a bone chain. Params: armature_name, bone_name, target_name, pole_target_name, chain_length.",
            "setup_humanoid_rig": "Generate a standard humanoid biped or quadruped rig preset. Params: target_mesh, rig_preset ('BASIC_BIPED'|'HUMAN'|'QUADRUPED').",
            "create_hair_curves": "Create Blender 4.2+ Hair Curves on a surface mesh. Params: surface_object, density, length, name.",
            "apply_hair_groom": "Apply grooming modifiers (CLUMP, NOISE, FRIZZ, BRAID, CURL, TRIM) to hair curves. Params: curves_object, modifier_type, strength.",
            "set_keyframe": "Insert animation keyframe. Params: object_name, data_path ('location'|'rotation_euler'|'scale'), frame, index.",
            "turntable": "Generate a 360-degree turntable camera animation. Params: target_object, frames (e.g. 120), radius, height.",
        },
    },
    "blender_camera_lighting": {
        "description": "Camera setup, 3-point studio lighting, sun/sky rigs, light linking, light probes, and visual auditing.",
        "actions": {
            "camera_setup": "Configure camera lens, focal length, sensor, depth of field, clip start/end. Params: name, lens, fstop, focus_object.",
            "look_at": "Point camera or light to track a target object or 3D coordinate. Params: object_name, target_name, target_location.",
            "frame_objects": "Auto-position and frame camera cleanly on specified objects. Params: target_objects, margin (e.g. 1.3), camera_name.",
            "light_setup": "Create or configure light source (POINT, SUN, SPOT, AREA). Params: name, type, energy (Watts), color, size.",
            "studio_lighting": "Generate a classic 3-point studio lighting rig (Key, Fill, Rim). Params: target_object, key_energy, fill_ratio, rim_energy.",
            "sun_sky_rig": "Create a physical Nishita sun/sky environment atmosphere. Params: sun_elevation, sun_rotation, turbidity, sky_type.",
            "screenshot": "Capture an OpenGL viewport screenshot returned as real image content. Params: output_path.",
            "evaluate_scene": "Run cheap VLM visual critique on scene composition, lighting, and materials. Params: custom_prompt.",
        },
    },
    "blender_physics_sim": {
        "description": "Rigid body physics, cloth simulation, force fields, fluid domain baking, and physics scene settings.",
        "actions": {
            "setup_rigid_body": "Add rigid body physics (ACTIVE or PASSIVE). Params: object_name, type ('ACTIVE'|'PASSIVE'), mass, collision_shape ('CONVEX_HULL'|'MESH'|'BOX').",
            "setup_cloth": "Add cloth physics modifier. Params: object_name, preset ('SILK'|'COTTON'|'LEATHER'|'DENIM'|'RUBBER'), quality_steps, enable_pressure.",
            "add_force_field": "Add physics force field (WIND, VORTEX, TURBULENCE, GRAVITY, HARMONIC). Params: type, strength, location, rotation.",
            "bake_fluid": "Bake fluid simulation domain (GAS/SMOKE or LIQUID). Params: domain_object, frame_start, frame_end, resolution.",
            "configure_physics": "Set scene gravity, simulation sub-steps, and time scale. Params: gravity, time_scale, solver_iterations.",
        },
    },
    "blender_render_pipeline": {
        "description": "Render scenes/animations, bake PBR texture maps, export Unity FBX/LODs, and setup VFX tracking.",
        "actions": {
            "render_image": "Render still frame to file. Params: output_path, resolution_x, resolution_y, render_engine ('BLENDER_EEVEE'|'CYCLES'), samples.",
            "render_anim": "Render animation sequence over timeline. Params: output_path, frame_start, frame_end, file_format ('FFMPEG'|'PNG').",
            "bake_textures": "Bake combined, normal, roughness, or AO maps to image files. Params: object_name, pass_type ('COMBINED'|'NORMAL'|'ROUGHNESS'|'AO'), resolution.",
            "export_unity_fbx": "Export FBX specifically tailored for Unity with axis orientation fixes and baked anims. Params: filepath, selected_only, bake_anim, embed_textures.",
            "generate_lods": "Auto-generate LOD0..LODn reduction chain. Params: object_name, ratios ([1.0, 0.5, 0.25, 0.1]), group_name.",
            "vfx_tracking": "Configure movie clip camera tracking and shadow catcher planes for live VFX composite. Params: clip_path, plane_name.",
        },
    },
}


def search_docs(query: str, category: Optional[str] = None) -> dict[str, Any]:
    """Search docs for relevant recipes, domains, and action parameter guides."""
    query_lower = query.lower().strip()
    results = {
        "query": query,
        "matched_recipes": [],
        "matched_domains": [],
    }

    # Search Recipes
    for key, recipe in RECIPES.items():
        if category and category.lower() not in ("all", "recipe", "recipes"):
            continue
        text_corpus = f"{key} {recipe['title']} {recipe['description']} {recipe['gotchas']}".lower()
        if any(term in text_corpus for term in query_lower.split()):
            results["matched_recipes"].append({
                "recipe_key": key,
                "title": recipe["title"],
                "description": recipe["description"],
                "steps": recipe["steps"],
                "gotchas": recipe["gotchas"],
            })

    # Search Domains & Actions
    for domain_name, domain in DOMAIN_DOCS.items():
        if category and category.lower() not in ("all", "domain", "tools", domain_name.lower()):
            continue
        domain_matched = any(term in f"{domain_name} {domain['description']}".lower() for term in query_lower.split())
        action_matches = {}
        for action_name, action_desc in domain["actions"].items():
            if any(term in f"{action_name} {action_desc}".lower() for term in query_lower.split()) or domain_matched:
                action_matches[action_name] = action_desc

        if action_matches:
            results["matched_domains"].append({
                "domain_tool": domain_name,
                "description": domain["description"],
                "matching_actions": action_matches,
            })

    return results


def get_recipe(recipe_name: str) -> Optional[dict[str, Any]]:
    return RECIPES.get(recipe_name)


def list_domains_summary() -> dict[str, str]:
    return {name: doc["description"] for name, doc in DOMAIN_DOCS.items()}
