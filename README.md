# mcp-blender-pakkio (v0.9.0)

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

## Tool Catalog (103 Tools across 17 Specialized Domains)

### 1. Batch Execution & Pipeline Optimization (New in v0.9.0)
- **`execute_batch`**: Executes multiple MCP commands in a single network roundtrip with automatic rollback/stop-on-error, real-time viewport progress updates, and per-step output logging.
- **`update_progress_hud`**: Displays a non-modal floating glass HUD card in Blender's 3D Viewport with live task progress percentage ($0-100\%$), step counters, and detailed operation logs without blocking the user.
- **`clear_progress_hud`**: Hides and resets the non-modal status HUD.

### 2. Vision-in-the-Loop AI Feedback & Inspection
- **`capture_multiview_audit`**: Renders a 4-view isometric/front/top/side contact sheet with bounding box metrics, polygon budgets, and returns an inline Base64 data URI for vision models.
- **`inspect_focus_shot`**: Automates macro close-up framing ($35\text{mm}$ to $200\text{mm}$) on any mesh region or detail.

### 3. Viewport Compositor & NPR Cel-Shading
- **`configure_compositor_effects`**: Controls real-time GPU Viewport Compositing, Bloom/Glare, and Lens Distortion (Chromatic Aberration).
- **`create_toon_shader`**: Procedural anime cel shader with multi-stepped ColorRamps and highlight clamping.

### 4. Physics Simulations & Dynamics
- **`setup_rigid_body_simulation`**: Rigid body physics with automated `settle_simulation` natural drop settling.
- **`setup_cloth_simulation`**: Configures cloth presets (SILK, COTTON, LEATHER, DENIM, RUBBER) and structural stiffness.
- **`add_force_field`**: Adds WIND, VORTEX, FORCE, TURBULENCE, and HARMONIC dynamics.

### 5. Studio Lighting Rigs & Light Linking
- **`create_lighting_rig`**: Spawns studio rigs (`THREE_POINT_STUDIO`, `PRODUCT_SOFTBOX`, `CYBERPUNK_NEON`, `FILM_NOIR`, `WARM_GOLDEN_HOUR`).
- **`configure_light_linking`**: Blender 4.0+/5.x object-specific light linking and shadow linking receivers.

### 6. Grease Pencil v3 Real-Time Line Art
- **`setup_line_art_contour`**: GPv3 silhouette cartoon ink outlines from scene/collection geometry with color tinting and stroke smoothing.

### 7. Render Effects & Material Transparency
- **`configure_render_effects`**: Viewport Ambient Occlusion, EEVEE Next Raytracing/Screen Space Reflections, Depth of Field, and Film Transparent alpha.
- **`configure_material_transparency`**: Transmission weight, IOR, and blend modes for glass, water, crystals, and acrylics.

### 8. Advanced Mesh Surgery & Cursor / Origin Manipulation
- **`advanced_mesh_edit`**: Bisect plane cuts with cap fill, bridge edge loops with lofting curves, extrude along normals, and edge creasing.
- **`manipulate_origin_cursor`**: Sets object origin (`ORIGIN_TO_BOTTOM` for ground alignment, `ORIGIN_TO_CURSOR`, `ORIGIN_TO_GEOMETRY`) and 3D cursor placement.
- **`align_distribute_objects`**: Snaps objects to ground ($Z=0$), aligns along axes, and distributes along grids.

### 9. Geometry Nodes Studio & Shader Graph Control
- **`create_geometry_nodes`**: Procedural node graphs (`SCATTER_ON_SURFACE`, `EXTRUDE_FACES`, `SUBDIVIDE_AND_NOISE`).
- **`edit_geometry_nodes`**: Add nodes, connect sockets, update parameters, and inspect full node graphs.
- **`bake_geometry_nodes`**: Converts procedural geometry into permanent editable mesh geometry.
- **`edit_material_nodes`**: Complete low-level shader graph inspection and node wiring.
- **`manage_color_attributes`**: Vertex color attributes with procedural height/normal gradients.

### 10. 3D Typography & Motion Graphics
- **`create_3d_text`**: Create 3D title text with custom fonts, extrude depth, bevel resolution, tracking, leading, alignment (`LEFT`, `CENTER`, `RIGHT`, `JUSTIFY`), and optional convert-to-mesh.
- **`deform_text_along_curve`**: Curve-guide text wrapping for circular logos, signage, and ribbon banners.
- **`set_text_properties`**: Modify text content, font size, tracking, extrude, and bevel on existing text objects.

### 11. Curves, Cables, Pipes & Wire Generation
- **`create_curve_cable`**: Procedurally route realistic sagging cables, electrical wires, neon tubes, or plumbing pipes between 3D points with bevel depth and gravity sag.
- **`convert_mesh_to_curve`**: Convert mesh boundary edges into curves for neon wireframes and railings.
- **`edit_curve_points`**: Add or modify control points, handles, radius, and tilt on Bezier and Poly splines.

### 12. Asset Browser & Library Management
- **`manage_asset_browser`**: Mark objects, materials, Geometry Nodes, or skeletal poses as **Blender Assets** (`ASSET_MARK`, `ASSET_CLEAR`), assign catalog tags, authors, and descriptions.
- **`generate_asset_preview`**: Automatically render and assign a custom thumbnail preview to an asset.
- **`import_asset_library`**: Link or append approved assets from external `.blend` asset libraries.

### 13. Lattice & Squash/Stretch Deformers
- **`create_lattice_deform`**: Automatically fit a 3D lattice cage around any complex model with configurable $U \times V \times W$ resolution and bind with Lattice Modifiers for cartoon squash & stretch.
- **`deform_lattice_points`**: Procedurally apply `SQUASH_AND_STRETCH`, `BEND`, `TAPER`, or move control points.

### 14. Volumetrics, Clouds & OpenVDB
- **`create_volume_vdb`**: Import OpenVDB cloud/smoke files or create procedural volumetric fog domains.
- **`configure_volume_shader`**: Setup Principled Volume shader graphs (Density, Absorption, Color, Emission, Blackbody).
- **`bake_fluid_domain`**: Configure Mantaflow smoke, fire, or liquid simulation domains and trigger cache baking.

### 15. Video Sequence Editor & Timeline Audio
- **`manage_sequencer_strips`**: Load background music, audio sound effects, video clips, or color strips directly into the VSE timeline.
- **`configure_sequencer_audio`**: Adjust volume, pan, pitch, and sync audio with 3D animation keyframes.

### 16. Hard-Surface Modeling & Modifiers
- **`boolean_operation`**: UNION, DIFFERENCE, INTERSECT with dynamic solver resolution (`FLOAT`, `EXACT`, `MANIFOLD`).
- **`decimate_mesh`**, **`remesh_mesh`**, **`mesh_operation`**, **`create_object`**, **`add_modifier`**, **`set_modifier_properties`**, **`apply_modifier`**, **`remove_modifier`**, **`apply_transform`**.

### 17. UV, Rigging, Animation, Engine Exports & Scene Management
- **`uv_unwrap`**, **`import_image_as_plane`**, **`project_image_texture`**, **`setup_pbr_materials`**, **`create_procedural_material`**, **`bake_textures`**, **`create_armature`**, **`pose_bone`**, **`manage_shape_keys`**, **`add_constraint`**, **`animate_camera_turntable`**, **`export_unity_fbx`**, **`export_scene`**, **`generate_lods`**, **`import_file`**, **`manage_addons`**, **`inspect_addon`**, **`bake_advanced`**, **`configure_light_probe`**, **`purge_orphans_and_cleanup`**, **`set_keyframe`**, **`delete_keyframe`**, **`set_timeline_range`**, **`configure_preferences`**, **`get_system_info`**, **`configure_world_environment`**, **`configure_scene_physics`**, **`switch_workspace`**, **`get_scene_info`**, **`get_object_info`**, **`select_objects`**, **`delete_object`**, **`duplicate_object`**, **`parent_objects`**, **`unparent_objects`**, **`manage_collection`**, **`configure_camera`**, **`camera_look_at`**, **`frame_objects`**, **`configure_light`**, **`render_scene`**, **`get_viewport_screenshot`**, **`set_render_settings`**, **`execute_blender_python`**.

---

## Install & Setup

### 1. Build and install the Blender extension

```bash
python scripts/build_extension.py              # packages dist/mcp_bridge_pakkio-0.9.0.zip
```

In Blender: **Edit > Preferences > Get Extensions > (dropdown) > Install from Disk**,
select `dist/mcp_bridge_pakkio-0.9.0.zip`, and enable it.

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

MIT -- see `LICENSE`.
