# Render/occlusion diagnostic tools

## Plan
- [ ] Blender-side `sample_render_pixels` tool (render_ops.py): read RGBA from a
      region of the last render (or a saved PNG), to confirm a material's
      color actually reached the output without round-tripping full base64 images.
- [ ] Blender-side `raycast_from_camera` tool (camera_ops.py): list every object
      hit along the camera->target ray, in order, with distances -- answers
      "what's actually between camera and object" in one call instead of
      hide/render/diff loops.
- [ ] Wire both into mcp_server (render_ops.py / camera_ops.py) as pydantic tools.
- [ ] Wire both into domain_facades.py (AGGREGATED mode is the default; tools
      not facaded are unreachable for most users).
- [ ] Unit tests mirroring existing test_tool_render_ops.py / test_tool_camera_ops.py patterns.
- [ ] Run mcp_server pytest suite.

## Review
- Added `sample_render_pixels` (render_ops.py, both sides) and `raycast_from_camera`
  (camera_ops.py, both sides), registered in FULL mode's tool list and wired into
  the AGGREGATED-mode facades (blender_render_pipeline/sample_pixels,
  blender_camera_lighting/raycast) plus docs/registry.py -- AGGREGATED is the
  default resolve_tool_mode(), so skipping the facade wiring would have shipped
  tools nobody could reach.
- Real bug caught by live testing (not guessed): sample_render_pixels' first
  cut read `bpy.data.images["Render Result"]`, whose `.size` comes back 0x0 in
  headless/background Blender even right after a successful render -- exactly
  the execution mode this bridge itself runs under. Fixed by having
  render_scene record its last written output path and defaulting to loading
  that file instead of the flaky in-memory buffer.
- Also fixed while implementing: used `check_existing=True` on the loaded-image
  path initially, which would have (a) returned stale cached pixels for a path
  rendered to more than once, and (b) let the tool's cleanup `bpy.data.images.remove()`
  a datablock it didn't create. Switched to `check_existing=False`.
- 281 mcp_server pytest tests pass (9 new), 90/90 live Blender tests pass
  (8 new, run against real Blender 5.0.1 headless, not just imported).
