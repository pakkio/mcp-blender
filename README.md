# mcp-blender-pakkio (v1.0.7)

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

## 🌟 Why `mcp-blender-pakkio` is Fundamentally Different & Superior

Existing open-source Blender MCP implementations (e.g. `RFingAdam/mcp-blender`, `ahujasid/blender-mcp`) are typically minimal proofs-of-concept providing only 5 to 15 basic tools and rely heavily on raw `exec(python_code)` strings. 

`mcp-blender-pakkio` was engineered from the ground up as a **complete 3D production pipeline suite**:

| Capability | Generic Blender MCPs | `mcp-blender-pakkio` (v1.0.7) |
| :--- | :--- | :--- |
| **Total Tool Count** | ~5 to 15 basic tools | **137 Native Structured FastMCP Tools** |
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

## 🛠️ Complete Tool Catalog (121 Tools across 19 Domains)

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
- **`decimate_mesh`**, **`remesh_mesh`**, **`mesh_operation`**, **`create_object`**, **`add_modifier`**, **`set_modifier_properties`**, **`apply_modifier`**, **`remove_modifier`**, **`apply_transform`**.

### 17. UV, Rigging & PBR Texturing
- **`uv_unwrap`**, **`import_image_as_plane`**, **`project_image_texture`**, **`setup_pbr_materials`**, **`create_procedural_material`**, **`bake_textures`**, **`create_armature`**, **`pose_bone`**, **`manage_shape_keys`**, **`add_constraint`**.

### 18. Game Engine Pipelines & System Management
- **`export_unity_fbx`**, **`export_scene`**, **`generate_lods`**, **`import_file`**, **`manage_addons`**, **`inspect_addon`**, **`bake_advanced`**, **`configure_light_probe`**, **`purge_orphans_and_cleanup`**, **`manipulate_origin_cursor`**, **`align_distribute_objects`**, **`configure_preferences`**, **`get_system_info`**, **`configure_world_environment`**, **`configure_scene_physics`**, **`switch_workspace`**, **`get_scene_info`**, **`get_object_info`**, **`select_objects`**, **`delete_object`**, **`duplicate_object`**, **`parent_objects`**, **`unparent_objects`**, **`manage_collection`**, **`configure_camera`**, **`camera_look_at`**, **`frame_objects`**, **`configure_light`**, **`render_scene`**, **`get_viewport_screenshot`**, **`set_render_settings`**, **`execute_blender_python`**.

### 19. Online Asset Sourcing, Semantic Grouping & Vision Fallback
- **`search_online_assets`**: Search free/CC0 asset libraries -- Poly Haven and ambientCG need no API key; Sketchfab search is keyless too (download needs a token). Use before hand-modelling any recognisable real-world object.
- **`import_online_asset`**: Download a found asset, import it via the existing pipeline, auto-decimate to a polygon budget, place it, and file it under a nested collection in one call.
- **`organize_scene_hierarchy`**: Build a multi-level semantic grouping in one call -- nested collections plus an empty-parent hierarchy over a set of objects, with nested child groups.
- **`evaluate_scene_visually`**: Cheap-VLM (OpenRouter) critique of a render, for hosts that cannot see the image content returned by `capture_multiview_audit`/`get_viewport_screenshot`/`render_scene` directly.

---

## 🚀 Quickstart Installation

### 1. Build and install the Blender extension

```bash
python scripts/build_extension.py              # packages dist/mcp_bridge_pakkio-1.0.7.zip
```

In Blender: **Edit > Preferences > Get Extensions > (top-right dropdown) > Install from Disk**,
select `dist/mcp_bridge_pakkio-1.0.7.zip`, and enable **MCP Bridge Pakkio**.

### 2. Install the MCP Server

```bash
cd mcp_server
pip install -e .
```

### 3. (Optional) Configure API keys

```bash
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
      "command": "mcp-blender-pakkio"
    }
  }
}
```

---

## 🧪 Testing & Verification

The project includes a two-tier test suite:

### 1. FastMCP & Mock Bridge Unit Tests (151 Tests)
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

## 📜 License

MIT License -- see `LICENSE`.

