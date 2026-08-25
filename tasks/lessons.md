
[2026-08-22] Query: image-to-3D feature (MCP + panel + clipboard paste)
Result: Success after 3 user-reported defects
Note: Lessons: (1) cover BOTH integration surfaces (MCP path AND Blender panel) when the project has parallel UIs; (2) never guess AI-provider endpoint URLs -- verify against official docs first (Meshy image-to-3d is /openapi/v1, not /v2); (3) props-dialog operators aren't findable via window.modal_operators -- use a WindowManager custom-property hand-off; (4) silent failure paths must return diagnostics.

[2026-08-25] Query: add render/occlusion diagnostic tools (sample_render_pixels, raycast_from_camera)
Result: Success
Note: (1) resolve_tool_mode() defaults to AGGREGATED, so any new bridge tool that isn't also wired into domain_facades.py (and ideally docs/registry.py) is unreachable for most users -- FULL-mode registration alone is not enough. (2) Don't trust bpy.data.images["Render Result"] in headless/background Blender -- .size reads 0x0 there right after a real render since no window holds its pixel buffer; prefer tracking the last file a render actually wrote and reading that. (3) Live bpy tests (scripts/run_live_bpy_tests.py against a real installed Blender) caught this immediately where a plain code read would have missed it -- run them for any change touching render/image/pixel code.