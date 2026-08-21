package client

// bridgeMethodByPath maps this CLI's synthetic REST paths (from spec.yaml)
// back to the real Blender-bridge method name expected by
// extension/bridge/server.py, mirroring the method_map dicts in
// mcp_server/src/mcp_blender/tools/domain_facades.py. Paths not listed here
// have no direct bridge equivalent: search_online_assets / import_online_asset
// / ai_generate do their HTTP fetching inside the Python mcp_server process
// (not over the Blender bridge), evaluate_scene_visually additionally calls
// out to a VLM, and scene regen calls an LLM -- none of that is replicated by
// this WebSocket transport.
var bridgeMethodByPath = map[string]string{
	// mesh
	"/blender_mesh/create":            "create_object",
	"/blender_mesh/delete":            "delete_object",
	"/blender_mesh/duplicate":         "duplicate_object",
	"/blender_mesh/transform":         "set_object_transform",
	"/blender_mesh/apply_transform":   "apply_transform",
	"/blender_mesh/boolean":           "boolean_operation",
	"/blender_mesh/decimate":          "decimate_mesh",
	"/blender_mesh/remesh":            "remesh_mesh",
	"/blender_mesh/simplify_geometry": "simplify_geometry",
	"/blender_mesh/uv_unwrap":         "uv_unwrap",
	"/blender_mesh/mesh_op":           "mesh_operation",
	"/blender_mesh/modifier":          "add_modifier",
	"/blender_mesh/origin_cursor":     "manipulate_origin_cursor",

	// material
	"/blender_material/create":            "create_material",
	"/blender_material/assign":            "assign_material",
	"/blender_material/pbr_setup":         "setup_pbr_materials",
	"/blender_material/procedural_grunge": "create_procedural_grunge_mask",
	"/blender_material/toon_shader":       "create_toon_shader",
	"/blender_material/transparency":      "configure_material_transparency",
	"/blender_material/triplanar":         "setup_triplanar_mapping",
	"/blender_material/slots":             "manage_material_slots",
	"/blender_material/edit_nodes":        "edit_material_nodes",

	// rigging & animation
	"/blender_rigging_anim/create_armature":    "create_armature",
	"/blender_rigging_anim/pose_bone":          "pose_bone",
	"/blender_rigging_anim/setup_ik":           "setup_ik_constraint",
	"/blender_rigging_anim/setup_humanoid_rig": "setup_humanoid_rig_preset",
	"/blender_rigging_anim/create_hair_curves": "create_hair_curves",
	"/blender_rigging_anim/apply_hair_groom":   "apply_hair_groom_modifier",
	"/blender_rigging_anim/set_keyframe":       "set_keyframe",
	"/blender_rigging_anim/turntable":          "animate_camera_turntable",
	"/blender_rigging_anim/timeline_range":     "set_timeline_range",

	// camera & lighting (evaluate_scene excluded -- VLM call, not a bridge method)
	"/blender_camera_lighting/camera_setup":       "configure_camera",
	"/blender_camera_lighting/look_at":            "camera_look_at",
	"/blender_camera_lighting/frame_objects":      "frame_objects",
	"/blender_camera_lighting/light_setup":        "configure_light",
	"/blender_camera_lighting/studio_lighting":    "create_lighting_rig",
	"/blender_camera_lighting/sun_sky_rig":        "setup_sky_sun_rig",
	"/blender_camera_lighting/screenshot":         "get_viewport_screenshot",
	"/blender_camera_lighting/compositor_effects": "configure_compositor_effects",

	// physics & simulation
	"/blender_physics_sim/setup_rigid_body":  "setup_rigid_body_simulation",
	"/blender_physics_sim/setup_cloth":       "setup_cloth_simulation",
	"/blender_physics_sim/add_force_field":   "add_force_field",
	"/blender_physics_sim/bake_fluid":        "bake_fluid_domain",
	"/blender_physics_sim/configure_physics": "configure_scene_physics",

	// render & pipeline export
	"/blender_render_pipeline/render_image":       "render_scene",
	"/blender_render_pipeline/render_anim":        "render_animation_sequence",
	"/blender_render_pipeline/bake_textures":      "bake_textures",
	"/blender_render_pipeline/export_unity_fbx":   "export_unity_fbx",
	"/blender_render_pipeline/generate_lods":      "generate_lods",
	"/blender_render_pipeline/vfx_tracking":       "setup_camera_tracking",
	"/blender_render_pipeline/vfx_shadow_catcher": "setup_vfx_shadow_catcher",

	// scene (regen excluded -- LLM call, not a bridge method)
	"/blender_scene/info":               "get_scene_info",
	"/blender_scene/hierarchy":          "organize_scene_hierarchy",
	"/blender_scene/collection":         "manage_collection",
	"/blender_scene/checkpoint_create":  "create_scene_checkpoint",
	"/blender_scene/checkpoint_restore": "restore_scene_checkpoint",
	"/blender_scene/checkpoint_list":    "list_scene_checkpoints",
	"/blender_scene/purge_orphans":      "purge_orphans_and_cleanup",
	"/blender_scene/job_status":         "get_job_status",
	"/blender_scene/job_list":           "list_jobs",
	"/blender_scene/job_cancel":         "cancel_job",
	"/blender_scene/performance":        "inspect_scene_performance",
	"/blender_scene/busy":               "bridge_status",

	// direct Python execution
	"/execute_blender_python": "execute_blender_python",

	// standalone high-stakes tool also reachable via blender_mesh(action=simplify_geometry)
	"/simplify_geometry": "simplify_geometry",

	// doctor's reachability probe (client.Get(ctx, "/", nil)) maps to the one
	// bridge method explicitly documented to answer instantly off the
	// websocket thread regardless of what else is running (see
	// domain_facades.go's "busy" action / bridge_status.go), making it the
	// right connectivity check.
	"/": "bridge_status",
}

// heavyBridgePaths get a longer round-trip timeout (matches
// HEAVY_REQUEST_TIMEOUT_S = 600s in mcp_server/src/mcp_blender/bridge.py):
// bakes, renders, and iterative mesh reduction can legitimately run minutes.
var heavyBridgePaths = map[string]bool{
	"/blender_mesh/boolean":                     true,
	"/blender_mesh/decimate":                    true,
	"/blender_mesh/remesh":                      true,
	"/blender_mesh/simplify_geometry":           true,
	"/simplify_geometry":                        true,
	"/blender_scene/checkpoint_create":          true,
	"/blender_scene/checkpoint_restore":         true,
	"/blender_camera_lighting/screenshot":       true,
	"/blender_physics_sim/bake_fluid":           true,
	"/blender_render_pipeline/render_image":     true,
	"/blender_render_pipeline/render_anim":      true,
	"/blender_render_pipeline/bake_textures":    true,
	"/blender_render_pipeline/export_unity_fbx": true,
	"/blender_render_pipeline/generate_lods":    true,
}
