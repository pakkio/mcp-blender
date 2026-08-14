# mcp-blender-pakkio (v0.5.1)

Exposes Blender to MCP clients (Claude Code, Claude Desktop, Antigravity, and others) through a
two-process bridge, mirroring [mcp-unity](https://github.com/claudiopacchiega/mcp-unity)'s
architecture but built in pure Python for Blender's native runtime:

```
MCP client (Claude) <--stdio--> mcp_server (pip package) <--WebSocket--> extension (Blender addon)
```

- **`extension/`** -- a Blender 4.2+ & 5.x Extension (`blender_manifest.toml`). Runs a
  localhost WebSocket server inside Blender and executes tool calls safely on Blender's
  main thread.
- **`mcp_server/`** -- a pip-installable Python package that is the actual MCP
  server (stdio transport, via the `mcp` SDK's `FastMCP`). It's also a WebSocket
  *client* to the extension.

---

## Tool Catalog (84 Tools)

### 1. Vision-in-the-Loop AI Feedback & Inspection
- **`capture_multiview_audit`**: Automatically renders and stitches a 4-angle visual inspection contact sheet (Front, Right Side, Top, and 3/4 Perspective) with optional base64 data URI payload for multimodal AI models (Claude 3.5/3.7, Gemini 2.0).
- **`inspect_focus_shot`**: Frames a tight cinematic close-up camera shot directly on a specific object or vertex selection with customizable focal length (e.g. 50mm, 85mm portrait/macro).

### 2. Viewport Compositor, Post-Processing & Cel Shading
- **`configure_compositor_effects`**: Full scene Compositor post-processing pipeline: real-time GPU Viewport Compositing, Glare/Bloom (Fog Glow, Streaks, Ghosting), Lens Distortion & Chromatic Aberration, and Color Grading.
- **`create_toon_shader`**: Procedural anime / Non-Photorealistic (NPR) cel-shading material with stepped ColorRamp shadow bands and rim lighting.

### 3. Physics Simulations & Dynamics
- **`setup_rigid_body_simulation`**: Active/Passive rigid body dynamics (Mass, Friction, Bounciness, Collision Shapes) with `settle_simulation` to naturally drop props onto surfaces.
- **`setup_cloth_simulation`**: Fabric simulation presets (SILK, COTTON, LEATHER, DENIM, RUBBER) with pinning vertex groups and internal pressure (inflatables).
- **`add_force_field`**: 3D physics force fields (WIND, VORTEX, TURBULENCE, FORCE, MAGNETIC) with customizable strength and flow.

### 4. Cinematic Studio Lighting & Light Linking
- **`create_lighting_rig`**: One-call studio lighting setups (`THREE_POINT_STUDIO`, `PRODUCT_SOFTBOX`, `CYBERPUNK_NEON`, `FILM_NOIR`, `WARM_GOLDEN_HOUR`) with automatic target tracking.
- **`configure_light_linking`**: Per-object light linking and shadow linking (Blender 4.0+/5.x) to illuminate specific assets without affecting the background.

### 5. Grease Pencil & Line Art NPR
- **`setup_line_art_contour`**: Real-time cartoon ink outlines and crease edge detection using Grease Pencil Line Art modifiers.

### 6. Render Effects, AO, Raytracing & Material Transparency
- **`configure_render_effects`**: Ambient Occlusion (distance/factor), EEVEE Next Raytracing & Screen Space Reflections, Refractions, Motion Blur, Depth of Field, Volumetrics, and Film Transparency (Alpha channel rendering).
- **`configure_material_transparency`**: Advanced glass, liquid, acrylic, and transparent shader properties (Transmission weight, Index of Refraction / IOR, Alpha blend modes, screen refraction, backface culling, roughness).

### 7. Advanced Mesh Editing & Origin Manipulation
- **`advanced_mesh_edit`**: Bisect plane cuts with cap fill, Bridge Edge Loops, Extrude along normals / individual faces, Edge Crease, Bevel Weights, Separate by loose parts/materials, and Join meshes.
- **`manipulate_origin_cursor`**: 3D Cursor & origin transformation (Origin to Geometry, Origin to Cursor, Origin to Bottom bounding box for ground snapping, Origin to Center of Mass, Cursor to Selected, Set Cursor/Origin Location).
- **`align_distribute_objects`**: Align objects along X/Y/Z axes, distribute across linear or 3D grid patterns, or snap lowest vertices to ground level (Z=0).

### 8. Viewport Display, Overlays & Data Purging
- **`configure_viewport_display`**: 3D Viewport shading mode (SOLID, MATERIAL, RENDERED, WIREFRAME), studio lighting/matcaps, cavity/shadows, and overlays (face orientation normal check, wireframe, scene statistics).
- **`purge_orphans_and_cleanup`**: Multi-pass purge of unused orphan datablocks (materials, meshes, textures, node groups, actions) and pack/unpack external file resources.

### 9. Geometry Nodes Studio
- **`create_geometry_nodes`**: Create Geometry Nodes modifiers with production presets (`EMPTY`, `SCATTER_ON_SURFACE`, `EXTRUDE_FACES`, `SUBDIVIDE_AND_NOISE`, `CURVE_TO_TUBE`, `WIREFRAME_LATTICE`, `PROCEDURAL_GRID_ARRAY`).
- **`edit_geometry_nodes`**: Inspect full graph structure, add/remove geometry nodes, connect sockets, and set exposed modifier parameters.
- **`bake_geometry_nodes`**: Bake procedural geometry trees into real mesh geometry, auto-realizing instanced points.

### 10. Advanced Light & Texture Baking Pipeline
- **`bake_advanced`**: High-to-low poly baking, multi-pass baking (`NORMAL`, `COMBINED`, `DIFFUSE`, `ROUGHNESS`, `AO`, `SHADOW`, `EMISSION`), cage objects/extrusion ray distance, and direct baking to vertex color attributes.
- **`configure_light_probe`**: Create EEVEE Light Probes (`VOLUME` / `GRID` Irradiance Volumes, `SPHERE` Reflection Probes, `PLANE` Reflection Planes) and trigger lighting cache bakes.

### 11. Add-on & Extension Discovery & Control
- **`manage_addons`**: List, discover, enable, disable, and configure preferences for built-in and community add-ons/extensions (Rigify, Node Wrangler, LoopTools, Archimesh, glTF, FBX, etc.).
- **`inspect_addon`**: Query complete add-on metadata: author, version, documentation links, enabled status, file path, and preference property keys.

### 12. Advanced Shader Node Trees & Color Attributes
- **`edit_material_nodes`**: Full low-level control over shader node graphs: create custom shader nodes, connect/disconnect sockets, set socket values, and inspect material node trees.
- **`manage_color_attributes`**: Create vertex color layers, fill solid colors, or generate procedural height/coordinate color gradients.
- **`setup_rigid_body_simulation`**: Rigid body physics with automated `settle_simulation` natural drop settling.
- **`setup_cloth_simulation`**: Configures cloth presets (SILK, COTTON, LEATHER, DENIM, RUBBER) and structural stiffness.
- **`add_force_field`**: Adds WIND, VORTEX, FORCE, TURBULENCE, and HARMONIC dynamics.

### 4. Studio Lighting Rigs & Light Linking
- **`create_lighting_rig`**: Spawns studio rigs (`THREE_POINT_STUDIO`, `PRODUCT_SOFTBOX`, `CYBERPUNK_NEON`, `FILM_NOIR`, `WARM_GOLDEN_HOUR`).
- **`configure_light_linking`**: Blender 4.0+/5.x object-specific light linking and shadow linking receivers.

### 5. Grease Pencil v3 Real-Time Line Art
- **`setup_line_art_contour`**: GPv3 silhouette cartoon ink outlines from scene/collection geometry with color tinting and stroke smoothing.

### 6. Render Effects & Material Transparency
- **`configure_render_effects`**: Viewport Ambient Occlusion, EEVEE Next Raytracing/Screen Space Reflections, Depth of Field, and Film Transparent alpha.
- **`configure_material_transparency`**: Transmission weight, IOR, and blend modes for glass, water, crystals, and acrylics.

### 7. Advanced Mesh Surgery & Cursor / Origin Manipulation
- **`advanced_mesh_edit`**: Bisect plane cuts with cap fill, bridge edge loops with lofting curves, extrude along normals, and edge creasing.
- **`manipulate_origin_cursor`**: Sets object origin (`ORIGIN_TO_BOTTOM` for ground alignment, `ORIGIN_TO_CURSOR`, `ORIGIN_TO_GEOMETRY`) and 3D cursor placement.
- **`align_distribute_objects`**: Snaps objects to ground ($Z=0$), aligns along axes, and distributes along grids.

### 8. Geometry Nodes Studio & Shader Graph Control
- **`create_geometry_nodes`**: Procedural node graphs (`SCATTER_ON_SURFACE`, `EXTRUDE_FACES`, `SUBDIVIDE_AND_NOISE`).
- **`edit_geometry_nodes`**: Add nodes, connect sockets, update parameters, and inspect full node graphs.
- **`bake_geometry_nodes`**: Converts procedural geometry into permanent editable mesh geometry.
- **`edit_material_nodes`**: Complete low-level shader graph inspection and node wiring.
- **`manage_color_attributes`**: Vertex color attributes with procedural height/normal gradients.

### 9. 3D Typography & Motion Graphics (New in v0.5.2)
- **`create_3d_text`**: Create 3D title text with custom fonts, extrude depth, bevel resolution, tracking, leading, alignment (`LEFT`, `CENTER`, `RIGHT`, `JUSTIFY`), and optional convert-to-mesh.
- **`deform_text_along_curve`**: Curve-guide text wrapping for circular logos, signage, and ribbon banners.
- **`set_text_properties`**: Modify text content, font size, tracking, extrude, and bevel on existing text objects.

### 10. Curves, Cables, Pipes & Wire Generation (New in v0.5.2)
- **`create_curve_cable`**: Procedurally route realistic sagging cables, electrical wires, neon tubes, or plumbing pipes between 3D points with bevel depth and gravity sag.
- **`convert_mesh_to_curve`**: Convert mesh boundary edges into curves for neon wireframes and railings.
- **`edit_curve_points`**: Add or modify control points, handles, radius, and tilt on Bezier and Poly splines.

### 11. Asset Browser & Library Management (New in v0.5.2)
- **`manage_asset_browser`**: Mark objects, materials, Geometry Nodes, or skeletal poses as **Blender Assets** (`ASSET_MARK`, `ASSET_CLEAR`), assign catalog tags, authors, and descriptions.
- **`generate_asset_preview`**: Automatically render and assign a custom thumbnail preview to an asset.
- **`import_asset_library`**: Link or append approved assets from external `.blend` asset libraries.

### 12. Lattice & Squash/Stretch Deformers (New in v0.5.2)
- **`create_lattice_deform`**: Automatically fit a 3D lattice cage around any complex model with configurable $U \times V \times W$ resolution and bind with Lattice Modifiers for cartoon squash & stretch.
- **`deform_lattice_points`**: Procedurally apply `SQUASH_AND_STRETCH`, `BEND`, `TAPER`, or move control points.

### 13. Volumetrics, Clouds & OpenVDB (New in v0.5.2)
- **`create_volume_vdb`**: Import OpenVDB cloud/smoke files or create procedural volumetric fog domains.
- **`configure_volume_shader`**: Setup Principled Volume shader graphs (Density, Absorption, Color, Emission, Blackbody).
- **`bake_fluid_domain`**: Configure Mantaflow smoke, fire, or liquid simulation domains and trigger cache baking.

### 14. Video Sequence Editor & Timeline Audio (New in v0.5.2)
- **`manage_sequencer_strips`**: Load background music, audio sound effects, video clips, or color strips directly into the VSE timeline.
- **`configure_sequencer_audio`**: Adjust volume, pan, pitch, and sync audio with 3D animation keyframes.

### 15. Hard-Surface Modeling & Modifiers
- **`boolean_operation`**: UNION, DIFFERENCE, INTERSECT with dynamic solver resolution (`FLOAT`, `EXACT`, `MANIFOLD`).
- **`decimate_mesh`**, **`remesh_mesh`**, **`mesh_operation`**, **`create_object`**, **`add_modifier`**, **`set_modifier_properties`**, **`apply_modifier`**, **`remove_modifier`**, **`apply_transform`**.

### 16. UV, Rigging, Animation, Engine Exports & Scene Management
- **`uv_unwrap`**, **`import_image_as_plane`**, **`project_image_texture`**, **`setup_pbr_materials`**, **`create_procedural_material`**, **`bake_textures`**, **`create_armature`**, **`pose_bone`**, **`manage_shape_keys`**, **`add_constraint`**, **`animate_camera_turntable`**, **`export_unity_fbx`**, **`export_scene`**, **`generate_lods`**, **`import_file`**, **`manage_addons`**, **`inspect_addon`**, **`bake_advanced`**, **`configure_light_probe`**, **`purge_orphans_and_cleanup`**, **`set_keyframe`**, **`delete_keyframe`**, **`set_timeline_range`**, **`configure_preferences`**, **`get_system_info`**, **`configure_world_environment`**, **`configure_scene_physics`**, **`switch_workspace`**, **`get_scene_info`**, **`get_object_info`**, **`select_objects`**, **`delete_object`**, **`duplicate_object`**, **`parent_objects`**, **`unparent_objects`**, **`manage_collection`**, **`configure_camera`**, **`camera_look_at`**, **`frame_objects`**, **`configure_light`**, **`render_scene`**, **`get_viewport_screenshot`**, **`set_render_settings`**, **`execute_blender_python`**.

---

## Install & Setup

### 1. Build and install the Blender extension

```bash
python scripts/build_extension.py              # packages dist/mcp_bridge_pakkio-0.5.2.zip
```

In Blender: **Edit > Preferences > Get Extensions > (dropdown) > Install from Disk**,
select `dist/mcp_bridge_pakkio-0.5.2.zip`, and enable it.

### 2. Install the MCP server

```bash
cd mcp_server
pip install -e .
```

### 3. Add to MCP Client Config

For Claude Code / Claude Desktop / Antigravity:

```json
{
  "mcpServers": {
    "blender": {
      "command": "mcp-blender-pakkio"
    }
  }
}
```

## License

MIT -- see `LICENSE`..
