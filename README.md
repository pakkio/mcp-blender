# mcp-blender (v2.0.26)

Exposes Blender to MCP clients (Claude Code, Claude Desktop, Antigravity, and others) through a
high-performance two-process bridge, mirroring [mcp-unity](https://github.com/claudiopacchiega/mcp-unity)'s
architecture but built in pure Python for Blender's native runtime:

```
MCP client (Claude / Gemini / GPT-4) <--stdio--> mcp_server (pip package) <--WebSocket--> extension (Blender 4.2+ / 5.x)
```

- **`extension/`** -- a Blender 4.2+ & 5.x Native Extension (`blender_manifest.toml`). Runs a
  localhost WebSocket server inside Blender and executes tool calls safely on Blender's
  main thread with non-modal viewport HUD rendering.
- **`mcp_server/`** -- a pip-installable Python package that is the actual MCP
  server (stdio transport, via FastMCP). It communicates over WebSockets directly to Blender.

---

## 🌟 Why `mcp-blender` is Fundamentally Different & Superior

Existing open-source Blender MCP implementations (e.g. `RFingAdam/mcp-blender`, `ahujasid/blender-mcp`) are typically minimal proofs-of-concept providing only 5 to 15 basic tools and rely heavily on raw `exec(python_code)` strings. 

`mcp-blender` was engineered from the ground up as a **complete 3D production pipeline suite**:

| Capability | Generic Blender MCPs | `mcp-blender` (v2.0.26) |
| :--- | :--- | :--- |
| **Total Tool Count** | ~5 to 15 basic tools | **138 Native Tools / 10 Unified Low-Context Domain Facades** |
| **Context Overhead** | Heavy per-tool bloat | **Ultra-Low Context Mode (90% token reduction) with on-demand `blender_docs`** |
| **Architecture** | Legacy Blender 2.8/3.x zip addons | **Blender 4.2+ & 5.2+ Native Extension System** |
| **Transactional Safety** | ❌ None (scene corrupts on fail) | **`execute_batch` (with automatic snapshot rollback on failure)** + **`create_scene_checkpoint`** / **`restore_scene_checkpoint`** |
| **Async Background Jobs** | ❌ UI freezes indefinitely | **`get_job_status`**, **`cancel_job`**, **`list_jobs`** |
| **Multimodal Vision Feedback** | ❌ None (blind execution) | **`capture_multiview_audit`** (4-angle contact sheets returned as real MCP image content) + **`inspect_focus_shot`** + **`evaluate_scene_visually`** (Gemini 2.5 Flash VLM fallback) |
| **Online & AI 3D Sourcing** | ❌ None | **Poly Haven, Sketchfab, ambientCG, Meshy AI, Tripo3D, Trellis 3D** |
| **IK Rigging & Metarigs** | ❌ Basic single bone only | **`setup_humanoid_rig_preset`** (biped metarig), **`setup_ik_constraint`** (pole targets/angles), **`setup_spline_ik_constraint`** |
| **Blender 4.2+ Hair Curves** | ❌ Legacy particle only | **`create_hair_curves`**, **`apply_hair_groom_modifier`** (Frizz, Clump, Noise, Braid), **`convert_legacy_hair_to_curves`** |
| **Grease Pencil & VFX Matchmoving** | ❌ None | **GPv3 layers & strokes**, **`setup_camera_tracking`**, **`setup_vfx_shadow_catcher`** |
| **Batch Latency Optimization** | ❌ Slow roundtrips (1 tool/turn) | **`execute_batch`** (Executes 50+ actions in a single roundtrip with stop-on-error/optional-step control and per-step reporting) |
| **Non-Modal Progress HUD** | ❌ None / Freezes UI | **`update_progress_hud`** (Real-time GPU 2D floating glass card with progress % and live task logs) |
| **Geometry Nodes Studio** | ❌ None | **Procedural graphs, Point scattering, Curve profiling, VDB volume remeshing, Proximity effectors** |
| **Shader & Material Studio** | ❌ Flat single colors | **Procedural edge-wear grunge masks, Triplanar box mapping, Auto-PBR texture folder loader, Specialty shaders** |
| **Game Engine Pipelines** | ❌ Raw unoptimized exports | **`export_unity_fbx`** (fixes Unity $-90^\circ$ X-axis bug), **`generate_lods`** (LOD0..LODn), Draco GLTF/GLB, Animation Keyframe Baking |

---

## ⚡ Low-Context Unified Domain Controllers (`MCP_BLENDER_TOOL_MODE=AGGREGATED`)

By default, `mcp-blender` exposes **10 unified domain facade tools** that cut LLM context consumption by **90%** while retaining 100% of underlying pipeline features:

1. **`blender_docs`**: Query multi-step 3D workflow recipes (e.g. cloth sim, character rigging & hair, PBR baking, game engine export), parameters, and best practices on demand.
2. **`blender_mesh`**: 3D modeling, transforms, boolean CSG, decimation (<10k poly budget), voxel remesh, UV unwrap, and modifiers.
3. **`blender_material`**: PBR shading, procedural grunge masks, toon shaders, alpha transparency, triplanar mapping, and material slots.
4. **`blender_assets`**: Online asset search (Poly Haven/Sketchfab) & AI text-to-3D generation (Meshy/Tripo/Trellis).
5. **`blender_scene`**: Scene inspection, semantic hierarchy organization, snapshot checkpoints for safe rollback, orphan purging, and background jobs.
6. **`blender_rigging_anim`**: Armatures, bone posing, IK rigs, Blender 4.2+ hair curves creation & grooming, animation keyframes, and turntable camera animations.
7. **`blender_camera_lighting`**: Studio 3-point & Nishita sun/sky lighting rigs, camera tracking/framing, viewport screenshots, and AI visual critique.
8. **`blender_physics_sim`**: Rigid body physics, cloth simulation, wind/vortex forces, fluid domain baking, and scene physics settings.
9. **`blender_render_pipeline`**: Still/animation rendering, PBR texture map baking, Unity FBX export with axis correction, and LOD chain generation.
10. **`execute_blender_python`**: Direct raw Python execution.

Four tools stay standalone even in this low-context mode rather than folding into a facade, since they're already single-purpose, high-stakes entry points worth their own full parameter schema: `search_online_assets`, `import_online_asset` (both also reachable via `blender_assets`), `evaluate_scene_visually` (also reachable via `blender_camera_lighting`), and `simplify_geometry` (also reachable via `blender_mesh(action="simplify_geometry")`) -- so aggregated mode exposes 14 tools total, not 10.

*(Note: Set `MCP_BLENDER_TOOL_MODE=FULL` in your `.env` if you prefer exposing all 138 individual micro-tools separately).*

---

## 🎯 What Can It Be Used For?

1. **Autonomous 3D Game Asset Generation**:
   - Create fully modeled, voxel-remeshed, UV unwrapped, PBR-textured 3D props and environments ready for Unity or Unreal Engine with automated LOD generation and coordinate correction.
2. **AI-Assisted Architectural & Product Visualization**:
   - Generate parametric buildings, procedural spiral staircases, realistic sagging powerlines, studio lighting rigs (`CYBERPUNK_NEON`, `WARM_GOLDEN_HOUR`, `PRODUCT_SOFTBOX`), and physical Nishita atmosphere sky models.
3. **Procedural Motion Graphics & Geometry Nodes Design**:
   - Construct radial starburst arrays, sci-fi energy matrices, 3D text typography deformed along circular curves, and reactive proximity deformers.
4. **Automated Scene Diagnostics & QA Auditing**:
   - Inspect polycounts, detect non-manifold vertices, run visual 4-view AI audits, and render entire animation sequences or video clips with synchronized audio in the Video Sequence Editor (VSE).

---

## 🛠️ Complete Tool Catalog (138 Tools across 21 Domains)

### 1. Batch Execution & Non-Modal Progress HUD
- **`execute_batch`**: Single-roundtrip multi-tool pipeline execution with stop-on-error/optional-step control and per-step output logging.
- **`update_progress_hud`**: Floating 2D glass HUD card in 3D Viewport displaying live progress percentage ($0-100\%$), step counters, and detailed task history without blocking the user.
- **`clear_progress_hud`**: Hides and resets the non-modal status HUD.

### 2. Shader Studio & Specialty Shaders
- **`create_procedural_grunge_mask`**: Procedural edge-wear cavity, curvature, pointiness, AO, and noise grunge masks.
- **`setup_triplanar_mapping`**: Seamless UV-free box / triplanar texture projection for organic rock, terrain, and architecture.
- **`setup_specialty_shader`**: Production presets: `CAR_PAINT` (metallic flakes + clearcoat), `SKIN_SSS` (subsurface scattering), `IRIDESCENT_PEARL` (thin-film sheen), `HOLOGRAM_GLOW`, and `GLASS_DISPERSION`.
- **`manage_shader_node_group`**: Reusable Shader Node Groups with custom inputs, outputs, and internal sub-networks.

### 3. Advanced Geometry Nodes Studio
- **`setup_geometry_proximity_interaction`**: Dynamic proximity deformation/scaling networks reacting to moving effector objects.
- **`curve_to_profile_mesh`**: Sweep custom curve profiles (Star, Circle, Quadrilateral) along paths with automatic caps.
- **`volume_mesh_booleans_gn`**: Procedural OpenVDB volume meshing and organic blending inside Geometry Nodes.
- **`create_geometry_nodes`**, **`edit_geometry_nodes`**, **`bake_geometry_nodes`**.

### 4. Advanced Material Slots & Auto-PBR Loader
- **`auto_load_pbr_texture_set`**: Automatically detects PBR maps from disk (Albedo, Roughness, Metallic, Normal, Height/Displacement, AO) and wires the complete Principled BSDF node graph.
- **`manage_material_slots`**: Multi-material slot management and per-face polygon index material assignments.
- **`project_decal_material`**: Floating alpha decal projection planes parented and shrinkwrapped to target meshes.

### 5. Scene Diagnostics, Sky & Lighting Rig
- **`inspect_scene_performance`**: Audits triangle/vert counts per object, detects non-manifold edges, and monitors polygon budgets.
- **`setup_sky_sun_rig`**: Physically-based atmospheric sky model with synchronized directional Sun light elevation/rotation.
- **`create_lighting_rig`**: Spawns studio rigs (`THREE_POINT_STUDIO`, `PRODUCT_SOFTBOX`, `CYBERPUNK_NEON`, `FILM_NOIR`, `WARM_GOLDEN_HOUR`).
- **`configure_light_linking`**: Blender 4.0+/5.x object-specific light linking and shadow linking receivers.

### 6. Animation, Keyframe Baking & Sequence Rendering
- **`bake_object_animation`**: Bakes constraints, follow-paths, or physics simulations into permanent transform keyframes for game engines.
- **`render_animation_sequence`**: Renders an entire animation frame sequence or video (MP4/H.264, PNG sequence, OpenEXR) with resolution controls.
- **`set_keyframe`**, **`delete_keyframe`**, **`set_timeline_range`**, **`animate_camera_turntable`**.

### 7. Vision-in-the-Loop AI Feedback & Inspection
- **`capture_multiview_audit`**: Renders a 4-view isometric/front/top/side contact sheet with bounding box metrics and inline Base64 data URI for vision models.
- **`inspect_focus_shot`**: Automates macro close-up framing ($35\text{mm}$ to $200\text{mm}$) on any mesh region or detail.

### 8. Viewport Compositor & NPR Cel-Shading
- **`configure_compositor_effects`**: Controls real-time GPU Viewport Compositing, Bloom/Glare, and Lens Distortion (Chromatic Aberration).
- **`create_toon_shader`**: Procedural anime cel shader with multi-stepped ColorRamps and highlight clamping.
- **`setup_line_art_contour`**: GPv3 silhouette cartoon ink outlines from scene geometry.

### 9. Physics Simulations & Dynamics
- **`setup_rigid_body_simulation`**: Rigid body physics with automated `settle_simulation` natural drop settling.
- **`setup_cloth_simulation`**: Configures cloth presets (SILK, COTTON, LEATHER, DENIM, RUBBER) and structural stiffness.
- **`add_force_field`**: Adds WIND, VORTEX, FORCE, TURBULENCE, and HARMONIC dynamics.

### 10. 3D Typography & Motion Graphics
- **`create_3d_text`**: 3D title text with custom fonts, extrude depth, bevel resolution, tracking, and alignment.
- **`deform_text_along_curve`**: Curve-guide text wrapping for circular logos, signage, and ribbon banners.
- **`set_text_properties`**: Modify text content, font size, tracking, extrude, and bevel on existing text objects.

### 11. Curves, Cables, Pipes & Wire Generation
- **`create_curve_cable`**: Procedurally route realistic sagging cables, electrical wires, or plumbing pipes between 3D points with gravity sag.
- **`convert_mesh_to_curve`**: Convert mesh boundary edges into curves for neon wireframes and railings.
- **`edit_curve_points`**: Add or modify control points, handles, radius, and tilt on Bezier splines.

### 12. Asset Browser & Library Management
- **`manage_asset_browser`**: Mark objects, materials, Geometry Nodes, or skeletal poses as **Blender Assets**, assign catalog tags, authors, and descriptions.
- **`generate_asset_preview`**: Automatically render and assign a custom thumbnail preview to an asset.
- **`import_asset_library`**: Link or append approved assets from external `.blend` asset libraries.

### 13. Lattice & Squash/Stretch Deformers
- **`create_lattice_deform`**: Automatically fit a 3D lattice cage around any model and bind with Lattice Modifiers for squash & stretch.
- **`deform_lattice_points`**: Procedurally apply `SQUASH_AND_STRETCH`, `BEND`, `TAPER`, or move control points.

### 14. Volumetrics, Clouds & OpenVDB
- **`create_volume_vdb`**: Import OpenVDB cloud/smoke files or create procedural volumetric fog domains.
- **`configure_volume_shader`**: Setup Principled Volume shader graphs (Density, Absorption, Color, Emission).
- **`bake_fluid_domain`**: Configure Mantaflow smoke, fire, or liquid simulation domains and trigger cache baking.

### 15. Video Sequence Editor & Timeline Audio
- **`manage_sequencer_strips`**: Load background music, audio sound effects, video clips, or color strips directly into the VSE timeline.
- **`configure_sequencer_audio`**: Adjust volume, pan, pitch, and sync audio with 3D animation keyframes.

### 16. Hard-Surface Modeling & Mesh Surgery
- **`boolean_operation`**: UNION, DIFFERENCE, INTERSECT with dynamic solver resolution (`FLOAT`, `EXACT`, `MANIFOLD`).
- **`advanced_mesh_edit`**: Bisect plane cuts with cap fill, bridge edge loops with lofting curves, extrude along normals, and edge creasing.
- **`decimate_mesh`**, **`remesh_mesh`**, **`simplify_geometry`**, **`mesh_operation`**, **`create_object`**, **`add_modifier`**, **`set_modifier_properties`**, **`apply_modifier`**, **`remove_modifier`**, **`apply_transform`**.

### 17. UV, Rigging & PBR Texturing
- **`uv_unwrap`**, **`import_image_as_plane`**, **`project_image_texture`**, **`setup_pbr_materials`**, **`create_procedural_material`**, **`bake_textures`**, **`create_armature`**, **`pose_bone`**, **`manage_shape_keys`**, **`add_constraint`**.

### 18. Game Engine Pipelines & System Management
- **`export_unity_fbx`**, **`export_scene`**, **`generate_lods`**, **`import_file`**, **`manage_addons`**, **`inspect_addon`**, **`bake_advanced`**, **`configure_light_probe`**, **`purge_orphans_and_cleanup`**, **`manipulate_origin_cursor`**, **`align_distribute_objects`**, **`configure_preferences`**, **`get_system_info`**, **`configure_world_environment`**, **`configure_scene_physics`**, **`switch_workspace`**, **`get_scene_info`**, **`get_object_info`**, **`select_objects`**, **`delete_object`**, **`duplicate_object`**, **`parent_objects`**, **`unparent_objects`**, **`manage_collection`**, **`configure_camera`**, **`camera_look_at`**, **`frame_objects`**, **`configure_light`**, **`render_scene`**, **`get_viewport_screenshot`**, **`set_render_settings`**, **`execute_blender_python`**.

### 19. Online Asset Sourcing, Semantic Grouping & Vision Fallback
- **`search_online_assets`**: Search free/CC0 asset libraries -- Poly Haven and ambientCG need no API key; Sketchfab search is keyless too (download needs a token). Use before hand-modelling any recognisable real-world object.
- **`import_online_asset`**: Download a found asset, import it via the existing pipeline, auto-reduce to a polygon budget via `simplify_geometry` (falls back to a plain decimate if its quality gate rejects the result), place it, and file it under a nested collection in one call.
- **`organize_scene_hierarchy`**: Build a multi-level semantic grouping in one call -- nested collections plus an empty-parent hierarchy over a set of objects, with nested child groups.
- **`evaluate_scene_visually`**: Cheap-VLM (OpenRouter) critique of a render, for hosts that cannot see the image content returned by `capture_multiview_audit`/`get_viewport_screenshot`/`render_scene` directly.

### 20. Import Orientation (v2.0.2)
Blender is Z-up; glTF, FBX, USD, Maya/Unity/3ds Max exports and most STL files are not, which is why an imported model's "up" often ends up horizontal.

- **Axis conversion**: `import_file` (and `import_online_asset` / `blender_assets`) take `forward_axis` + `up_axis` describing the **source file's** convention. Passing only one fills in the conventional partner, so `up_axis="Y"` is usually the whole fix. FBX/OBJ/STL use the importer's own axis arguments; glTF/USD/BLEND have none, so the conversion is applied to the imported roots instead. STL is the common offender — the format carries no axis metadata, so Blender does no conversion at all.
- **Orientation check**: every import returns an `orientation` report measured from the geometry (cross-section-weighted volume centroid, base-vs-top footprint, bounding dimensions) with a verdict of `ok`, `unknown`, `suspect_upside_down` or `suspect_lying_down` plus the corrective rotation. It only flags a model that has nothing to stand on, so upright-but-top-heavy shapes (tables, lamps) and deliberately flat ones (rugs, ground planes) are left alone.
- **`auto_orient=true`**: applies that corrective rotation (180° or 90° about X, pivoted on the bounds) to the imported roots and re-runs the check.

### 21. Mesh Simplification (v2.0.3)
`decimate_mesh` assumes a welded, manifold mesh. Imported glTF/FBX/OBJ/STL geometry usually isn't one: exporters split vertices at every UV seam, sharp edge and material boundary, so what looks like one surface is disconnected shells that only happen to touch. Running Collapse decimate on that pulls the shells apart independently — the holes and wrecked topology a flat decimate produces on real assets. `remesh_mesh` avoids that by rebuilding the surface from scratch, but that destroys UVs and spends resolution uniformly rather than where the shape actually needs it.

- **`simplify_geometry`**: reduces a mesh to a vertex budget (`target` + `target_unit`, or `preset`: `BACKGROUND`=10k / `HERO`=30k / `MAX`=100k) while preserving its form and UVs. Repairs first (welds coincident vertices, drops loose geometry, closes pinhole gaps — this is what actually fixes the "decimate makes holes" failure), then spends the budget on flat/dense regions first via limited dissolve, then curvature-weighted Collapse so thin features and boundaries survive.
- **Measures what it produced**: every call reports two-sided surface deviation (`mathutils.bvhtree`, both directions — catches a deleted feature that a one-sided check would miss) and new-hole count, against a quality gate (`max_deviation_pct`, default 2%; `allow_new_holes`, default 0).
- **Rolls back on failure**: a failed gate restores the mesh from an in-memory copy rather than handing back a broken result, and returns `suggested_retry_target`. Set `dry_run=true` to see the analysis and estimated ratio without changing anything.
- Use `decimate_mesh` only on a mesh you already know is clean (hand-modelled, or already repaired); use `simplify_geometry` on anything imported or downloaded.
- **v2.0.4 fix**: `simplify_geometry` on a large mesh (weld + dissolve + iterative collapse solve + deviation sampling) can run past 15s, but the Blender-side bridge wasn't in its long-timeout allowlist -- it would report "Blender did not respond in time" after 15s while the tool kept running, silently dropping the eventual result. Fixed in `extension/bridge/server.py`'s `HEAVY_METHODS`, with a regression test (`test_heavy_timeout_consistency.py`) checking every mcp_server-side heavy call has a matching entry there.

> **Version note**: v2.0.9 -- v2.0.12 and v2.0.20 -- v2.0.22 were never released; the
> series jumps 2.0.8 → 2.0.13 → 2.0.19 → 2.0.23 → 2.0.24. Section headings below cite the release a
> change actually shipped in, so those gaps are expected rather than missing entries.

### 22. Paginated Asset Search (v2.0.13)
`search_online_assets` pages through provider results instead of returning only the first batch. Cursor handling was fixed -- earlier calls passed the cursor incorrectly and silently re-returned page one -- and each result now carries a browser-openable URL so a candidate can be inspected online before importing.

### 23. Semantic Renaming (v2.0.14 → v2.0.17)
`regen_names` turns exporter-mangled object names into readable, meaningful ones. It landed incrementally:

- **v2.0.14**: fixed translation of dot-suffixed and trailing-digit names (`Sedia.001`, `Tavolo2`), and expanded the Italian directional/material vocabulary.
- **v2.0.15**: purely generic primitive names (`Cube.001`, `obj_01`, `Mesh_3`) are left alone rather than "translated" into nonsense, since they carry no semantic content to preserve.
- **v2.0.16**: hexadecimal exporter hashes are stripped from generic names (e.g. `mesh_a3f91c` → `mesh`).
- **v2.0.17**: renaming became **LLM-based**, with the local dictionary kept as an offline fallback when no model is reachable. This release also introduced a **unified `.env` loader** shared by every component that needs credentials.

### 24. `separate_logical_areas` -- AI Mesh Segmentation (v2.0.18)
Splits a single mesh into semantically meaningful sub-objects (a chair into seat / back / legs) using AI-driven segmentation, rather than by connected components or material boundaries.

### 25. Unified `ai_generate` (v2.0.19)
Text-to-3D generation is a single call with an explicit provider and an explicit post-generation vertex budget.

| Param | Values | Notes |
| :--- | :--- | :--- |
| `prompt` | string | **required** |
| `provider` | `meshy` (default), `tripo` | |
| `target_vertices` | int, default `30000` | post-generation vertex budget |
| `reduction_method` | `simplify` (default) | form-preserving weld + dissolve + iterative collapse; higher quality, but can run for **minutes** on a dense generated mesh |
| | `decimate` | plain ratio decimate -- much faster; use for quick iteration, or if `simplify` is timing out |
| | `remesh` | voxel remesh; **destroys UVs** -- avoid, generated models are textured |
| | `none` | skip reduction entirely; fastest, keeps the raw generated mesh |

**Meshy results are always textured.** Meshy has no single-call textured mode: the provider runs a fast untextured `preview` geometry pass, then automatically a slower `refine` pass that bakes PBR textures onto it. There is no untextured-only mode via `ai_generate`.

Also in v2.0.19: checkpoint restore is deferred via timers so it cannot fire mid-operation, and the VLM path auto-falls-back when a model rejects an image.

### 26. VLM Fallback Hardening (post-v2.0.19)
Some vision-incompatible models answer with **HTTP 200** and an error body rather than a non-2xx status, which defeated the original fallback. `evaluate_scene_visually` now detects that case and falls back to a working model instead of surfacing a confusing success-shaped failure.

### 27. In-Blender AI Generation + Progress HUD (v2.0.23)
Generation can be driven from **inside Blender**, not only from the MCP server:

- `generate_ai_model_job(provider, prompt)` in `extension/tools/super_import_ops.py` implements both providers Blender-side -- Meshy (`preview` → `refine`) and Tripo (`text_to_model`) -- each polling its task until a terminal state.
- The viewport panel gained a **modal operator with a background worker and live status callbacks**, so a multi-minute generation reports progress in the viewport instead of blocking the UI.
- mcp_server's Meshy provider gained a `texture: bool = True` flag on `download()`: `texture=False` skips the `refine` stage for a faster untextured result, and caches under a distinct `_untextured` id so the two variants don't collide.

### 28. Facade Parameter Validation & Rig Aiming (v2.0.24)
The domain facades used to forward `params` straight through to the Blender side, where each tool reads the keys it knows via `params.get(...)`. A misnamed key was therefore dropped **in silence**: the call returned `success` while doing nothing. Two real cases: `blender_material(action='create', params={'color': ...})` reported success and produced a default grey material, and `blender_camera_lighting(action='studio_lighting', params={'target': ..., 'distance': ...})` reported success and built the rig at the world origin.

- **Unknown parameters now raise** a `validation_error` naming the offending key and listing the accepted ones, instead of being discarded. Methods without a declared spec keep the previous pass-through, so this is additive.
- **Intuitive aliases are accepted**: `color` → `base_color`, `object_name` → `assign_to_object`, `material`/`object` → `material_name`/`object_name`, `radius` → `distance`. For `create_lighting_rig`, `target` resolves by type -- coordinates become `target_location`, a string becomes `target_object`.
- **`create_lighting_rig` gained real aiming**: `target_location` ([x,y,z]) positions a rig around a subject that isn't on an object origin, and `distance` (metres, default 5.0) rescales the rig about the aim point while preserving its designed shape. Previously a rig built without a `target_object` got **no aiming at all** -- the lamps kept their default rotation and pointed straight down. The response now echoes the resolved `target_location`, `target_object_found` and `distance`, so a fallback to the origin is visible rather than silent.

### 29. LLM-Powered Custom Workflow Recipes (v2.0.26)
Earlier versions of `blender_docs` only searched a static dictionary of hardcoded workflow recipes. 

- **Custom AI Recipes**: If an `OPENROUTER_API_KEY` is configured in your `.env`, `blender_docs` now automatically calls OpenRouter/Gemini to generate a customized, step-by-step 3D workflow recipe tailored exactly to your query.
- **Accurate Action Schemas**: The system compiles the complete action descriptions, tool names, and parameter specifications for all 10 domain facades and feeds them to the LLM, ensuring the generated steps use valid tools and parameters.

### Required credentials
The unified `.env` loader (v2.0.17) reads these. Each is only needed for the provider you actually use:

| Key | Used by |
| :--- | :--- |
| `MESHY_API_KEY` | `ai_generate` / import with `provider=meshy` |
| `TRIPO_API_KEY` | `ai_generate` / import with `provider=tripo` |
| `OPENROUTER_API_KEY` + `OPENROUTER_VISION_MODEL` | `evaluate_scene_visually`, LLM-based renaming |
| `SKETCHFAB_API_TOKEN` | Sketchfab asset search / import |
| `HF_TOKEN`, `TRELLIS_API_KEY` | HuggingFace-hosted generation (Trellis) |

---

## 🚀 Quickstart Installation

### 1. Build and install the Blender extension

```bash
python scripts/build_extension.py              # packages dist/mcp_bridge-2.0.26.zip
```

3. In Blender 4.2+, open **Preferences > Get Extensions > Install from Disk...**,
   select `dist/mcp_bridge-2.0.26.zip`, and enable **MCP Bridge**.

### 2. Install the MCP Server

```bash
cd mcp_server
pip install -e .
```

### 3. (Optional) Configure API keys

You can place your `.env` file in either of these locations:
* **Globally (Recommended):** At `~/.mcp-blender/.env` (shared automatically by both the addon and the server).
* **Locally:** In the current working directory from which you run the server.

```bash
# Example for local setup:
cp .env.example .env
```

Fill in `SKETCHFAB_API_TOKEN` (free account, needed only to *download* Sketchfab models --
search works without it) and/or `OPENROUTER_API_KEY` (powers `evaluate_scene_visually`, a
cheap-VLM scene critique for hosts that can't see image content directly). Both are optional;
tools that need a missing key degrade to an actionable message instead of failing.

### 4. Add to your MCP Client Configuration

For Claude Code, Claude Desktop, Antigravity, or Cursor:

```json
{
  "mcpServers": {
    "blender": {
      "command": "mcp-blender"
    }
  }
}
```

---

## 🧪 Testing & Verification

The project includes a two-tier test suite:

### 1. FastMCP & Mock Bridge Unit Tests (207 Tests)
Validates tool registration, schema definitions, Pydantic argument parsing, and WebSocket protocol handling:

```bash
cd mcp_server
pytest
```

### 2. Live In-Blender (`bpy`) Integration Tests
Executes real Blender tool operations (`execute()`) directly inside a live headless Blender runtime across all domains (modeling, shaders, geometry nodes, camera, lighting, physics, and bridge dispatch queues):

```bash
python scripts/run_live_bpy_tests.py
```

*Note: Automatically detects your local Blender installation (or respects the `BLENDER_BIN` environment variable / `--blender-bin` argument).*

---

## 🖥️ Standalone CLI (`tools/mcp-blender-pp-cli/`)

An experimental Go CLI, generated with [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press) from the 14 aggregated-mode MCP tools, that talks directly to the Blender WebSocket bridge (`ws://127.0.0.1:9876`) without going through the MCP server:

```bash
cd tools/mcp-blender-pp-cli
./mcp-blender-pp-cli doctor
echo '{"object_type":"CONE","name":"MyCone"}' | ./mcp-blender-pp-cli mesh create --stdin
```

The generator's default HTTP client was replaced with a real WebSocket transport (`internal/wsbridge/`, `internal/client/wsbridge_map.go`) since this project has no REST API. See `.printing-press-patches/0001-websocket-transport.md` in that directory for what was hand-patched, why, and its known limitations (`search-online-assets` / `import-online-asset` / `ai_generate` / `evaluate-scene-visually` / `scene regen` are not wired -- their logic lives in the Python `mcp_server` process, not the Blender bridge).

---

## 📜 License

MIT License -- see `LICENSE`.

