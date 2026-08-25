

[2026-08-22] Query: image-to-3D generation + panel paste + Meshy 404 fix
Result: Success
Note: Endpoint guessing caused a 404; docs verification added to workflow.

[2026-08-22] Query: image preview not visible in AI Generate dialog
Result: Success
Note: bpy.data writes are forbidden inside draw(); use bpy.app.timers for deferred loads.

[2026-08-25] Query: add sample_render_pixels + raycast_from_camera diagnostic tools
Result: Success
Note: New tool must be wired into domain_facades.py, not just FULL-mode registration -- AGGREGATED is the default. Live-test run caught Render Result reading 0x0 in headless mode; fixed by tracking last render's saved file path instead.
