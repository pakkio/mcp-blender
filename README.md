# mcp-blender-pakkio (v0.5.0)

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

## Tool Catalog (74 Tools)

### 1. Render Effects, AO, Raytracing & Material Transparency
- **`configure_render_effects`**: Ambient Occlusion (distance/factor), EEVEE Next Raytracing & Screen Space Reflections, Refractions, Motion Blur, Depth of Field, Volumetrics, and Film Transparency (Alpha channel rendering).
- **`configure_material_transparency`**: Advanced glass, liquid, acrylic, and transparent shader properties (Transmission weight, Index of Refraction / IOR, Alpha blend modes, screen refraction, backface culling, roughness).

### 2. Advanced Mesh Editing & Origin Manipulation
- **`advanced_mesh_edit`**: Bisect plane cuts with cap fill, Bridge Edge Loops, Extrude along normals / individual faces, Edge Crease, Bevel Weights, Separate by loose parts/materials, and Join meshes.
- **`manipulate_origin_cursor`**: 3D Cursor & origin transformation (Origin to Geometry, Origin to Cursor, Origin to Bottom bounding box for ground snapping, Origin to Center of Mass, Cursor to Selected, Set Cursor/Origin Location).
- **`align_distribute_objects`**: Align objects along X/Y/Z axes, distribute across linear or 3D grid patterns, or snap lowest vertices to ground level (Z=0).

### 3. Viewport Display, Overlays & Data Purging
- **`configure_viewport_display`**: 3D Viewport shading mode (SOLID, MATERIAL, RENDERED, WIREFRAME), studio lighting/matcaps, cavity/shadows, and overlays (face orientation normal check, wireframe, scene statistics).
- **`purge_orphans_and_cleanup`**: Multi-pass purge of unused orphan datablocks (materials, meshes, textures, node groups, actions) and pack/unpack external file resources.

### 4. Geometry Nodes Studio
- **`create_geometry_nodes`**: Create Geometry Nodes modifiers with production presets (`EMPTY`, `SCATTER_ON_SURFACE`, `EXTRUDE_FACES`, `SUBDIVIDE_AND_NOISE`, `CURVE_TO_TUBE`, `WIREFRAME_LATTICE`, `PROCEDURAL_GRID_ARRAY`).
- **`edit_geometry_nodes`**: Inspect full graph structure, add/remove geometry nodes, connect sockets, and set exposed modifier parameters.
- **`bake_geometry_nodes`**: Bake procedural geometry trees into real mesh geometry, auto-realizing instanced points.

### 5. Advanced Light & Texture Baking Pipeline
- **`bake_advanced`**: High-to-low poly baking, multi-pass baking (`NORMAL`, `COMBINED`, `DIFFUSE`, `ROUGHNESS`, `AO`, `SHADOW`, `EMISSION`), cage objects/extrusion ray distance, and direct baking to vertex color attributes.
- **`configure_light_probe`**: Create EEVEE Light Probes (`VOLUME` / `GRID` Irradiance Volumes, `SPHERE` Reflection Probes, `PLANE` Reflection Planes) and trigger lighting cache bakes.

### 6. Add-on & Extension Discovery & Control
- **`manage_addons`**: List, discover, enable, disable, and configure preferences for built-in and community add-ons/extensions (Rigify, Node Wrangler, LoopTools, Archimesh, glTF, FBX, etc.).
- **`inspect_addon`**: Query complete add-on metadata: author, version, documentation links, enabled status, file path, and preference property keys.

### 7. Advanced Shader Node Trees & Color Attributes
- **`edit_material_nodes`**: Full low-level control over shader node graphs: create custom shader nodes, connect/disconnect sockets, set socket values, and inspect material node trees.
- **`manage_color_attributes`**: Create vertex color layers, fill solid colors, or generate procedural height/coordinate color gradients.

### 8. Sculpting & Organic Modeling
- **`configure_sculpt_mode`**: Enter/exit Sculpt Mode, select active brushes (Draw, Clay, Clay Strips, Crease, Smooth, Flatten, Grab, Snake Hook, Elastic Deform, Pinch, Cloth, Scrape), configure brush radius, strength, XYZ symmetry, and Dynamic Topology (Dyntopo).
- **`apply_sculpt_filter`**: Full-mesh sculpt deformation filters (SMOOTH, SCALE, INFLATE, SPHERE, RANDOM, RELAX, RELAX_FACE_SETS, SURFACE_SMOOTH, SHARPEN, ENHANCE_DETAILS) with customizable axis and strength.
- **`sculpt_mask_facesets`**: Manage sculpt masks (clear, invert, smooth) and initialize Face Sets (by loose parts, materials, or mask selection).

### 9. Modeling & Hard-Surface Geometry
- **`boolean_operation`**: UNION, DIFFERENCE, INTERSECT, SLICE with FAST or EXACT solvers and operand cleanup.
- **`decimate_mesh`**: High-speed polygon reduction (COLLAPSE with ratio/symmetry, UNSUBDIVIDE iterations, PLANAR angle limits).
- **`remesh_mesh`**: Native VOXEL remesher with adaptivity and modifier-based SHARP/SMOOTH/BLOCKS remeshing.
- **`mesh_operation`**: Subdivision, triangulation, normals recalculation, merge vertices, bevel, inset individual faces, symmetrize, convex hull, dissolve degenerate.
- **`create_object`**: Create primitives (CUBE, UV_SPHERE, ICO_SPHERE, CYLINDER, CONE, PLANE, TORUS, GRID, MONKEY, EMPTY, CAMERA, LIGHT, TEXT, CURVE).
- **`add_modifier`**, **`set_modifier_properties`**, **`apply_modifier`**, **`remove_modifier`**: Full modifier stack lifecycle.
- **`apply_transform`**: Permanently bake location, rotation, and scale transforms into mesh geometry.

### 10. UV Mapping, Texturing & PBR Shaders
- **`uv_unwrap`**: Complete unwrapping suite (SMART_PROJECT, LIGHTMAP_PACK, CUBE_PROJECT, SPHERE_PROJECT, CYLINDER_PROJECT, PROJECT_FROM_VIEW, UNWRAP, PACK_ISLANDS).
- **`import_image_as_plane`**: Instant textured 3D plane generation matching image aspect ratio with alpha transparency handling.
- **`project_image_texture`**: Project decals or textures using camera projection or empty-driven mapping.
- **`setup_pbr_materials`**: Automated multi-map PBR shader graph setup (Albedo, Normal, Roughness, Metallic, Height, Emission, AO) with automated color spaces.
- **`create_procedural_material`**: Procedural shaders (NOISE, VORONOI, WAVE, BRICK, CHECKER, GRADIENT) with ColorRamps and bump mapping.
- **`bake_textures`**: Cycles texture baking (DIFFUSE, NORMAL, ROUGHNESS, AO, COMBINED) to target image maps.
- **`create_material`**, **`assign_material`**, **`get_material_info`**, **`set_material_properties`**: Principled BSDF shader control.

### 11. Animation, Rigging & Pipeline Exports
- **`create_armature`**: Generate single-bone or multi-bone hierarchical skeletal rigs, bind meshes with automatic vertex weights.
- **`pose_bone`**: Pose bones in Pose Mode (location, rotation, scale) and insert skeletal keyframes.
- **`manage_shape_keys`**: Create Basis and morph target shape keys, set weights (0.0 to 1.0), and keyframe morph animations.
- **`add_constraint`**: Add object/bone constraints (TRACK_TO, DAMPED_TRACK, FOLLOW_PATH, COPY_TRANSFORMS, COPY_LOCATION, COPY_ROTATION, LIMIT_DISTANCE, CHILD_OF, IK).
- **`animate_camera_turntable`**: Auto-generate smooth 360-degree orbital camera turntable animations.
- **`export_unity_fbx`**: Unity-tailored FBX export (fixes Unity -90° X rotation axis bug, strips dummy leaf bones, bakes animations, embeds textures).
- **`export_scene`**: Advanced GLTF/GLB export with Draco mesh compression, animation baking, material export, FBX, OBJ, STL, USD.
- **`generate_lods`**: Multi-level LOD generation (LOD0..LODn) with decimation ratios and LOD Group empty hierarchy.
- **`import_file`**: Import GLTF, GLB, FBX, OBJ, STL, USD, and BLEND files.
- **`set_keyframe`**, **`delete_keyframe`**, **`set_timeline_range`**, **`configure_preferences`**, **`get_system_info`**, **`configure_world_environment`**, **`configure_scene_physics`**, **`switch_workspace`**, **`get_scene_info`**, **`get_object_info`**, **`select_objects`**, **`delete_object`**, **`duplicate_object`**, **`parent_objects`**, **`unparent_objects`**, **`manage_collection`**, **`configure_camera`**, **`camera_look_at`**, **`frame_objects`**, **`configure_light`**, **`render_scene`**, **`get_viewport_screenshot`**, **`set_render_settings`**, **`execute_blender_python`**.

---

## Install & Setup

### 1. Build and install the Blender extension

```bash
python scripts/build_extension.py              # packages dist/mcp_bridge_pakkio-0.5.0.zip
```

In Blender: **Edit > Preferences > Get Extensions > (dropdown) > Install from Disk**,
select `dist/mcp_bridge_pakkio-0.5.0.zip`, and enable it.

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

