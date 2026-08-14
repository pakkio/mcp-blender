from mcp.server.fastmcp import FastMCP

from ..bridge import BlenderBridge
from .addon_management_ops import register_addon_management_tools
from .advanced_bake_ops import register_advanced_bake_tools
from .advanced_geom_nodes_studio_ops import register_advanced_geom_nodes_studio_tools
from .advanced_material_ops import register_advanced_material_tools
from .advanced_material_slot_ops import register_advanced_material_slot_tools
from .advanced_mesh_edit_ops import register_advanced_mesh_edit_tools
from .animation_ops import register_animation_tools
from .apply_transform import register_apply_transform_tool
from .asset_browser_ops import register_asset_browser_tools
from .batch_execution_ops import register_batch_execution_tools
from .boolean_ops import register_boolean_tools
from .camera_ops import register_camera_tools
from .collection_ops import register_collection_tools
from .compositor_effects_ops import register_compositor_effects_tools
from .constraint_ops import register_constraint_tools
from .create_object import register_create_object_tool
from .curve_wire_ops import register_curve_wire_tools
from .delete_object import register_delete_object_tool
from .duplicate_object import register_duplicate_object_tool
from .execute_python import register_execute_blender_python_tool
from .geometry_nodes_ops import register_geometry_nodes_tools
from .get_object_info import register_get_object_info_tool
from .get_scene_info import register_get_scene_info_tool
from .grease_pencil_ops import register_grease_pencil_tools
from .io_ops import register_io_tools
from .lattice_deform_ops import register_lattice_deform_tools
from .light_ops import register_light_tools
from .material_ops import register_material_tools
from .mesh_operation import register_mesh_operation_tool
from .modifier_ops import register_modifier_tools
from .parent_ops import register_parent_tools
from .pbr_bake_ops import register_pbr_bake_tools
from .physics_simulation_ops import register_physics_simulation_tools
from .pipeline_export_ops import register_pipeline_export_tools
from .preference_ops import register_preference_tools
from .progress_hud_ops import register_progress_hud_tools
from .remesh_decimate_ops import register_remesh_decimate_tools
from .render_effects_ops import register_render_effects_tools
from .render_ops import register_render_tools
from .rigging_ops import register_rigging_tools
from .sculpt_ops import register_sculpt_tools
from .select_objects import register_select_objects_tool
from .sequencer_vse_ops import register_sequencer_vse_tools
from .set_object_properties import register_set_object_properties_tool
from .set_object_transform import register_set_object_transform_tool
from .shader_studio_ops import register_shader_studio_tools
from .shape_key_ops import register_shape_key_tools
from .studio_lighting_ops import register_studio_lighting_tools
from .text_typography_ops import register_text_typography_tools
from .texture_image_ops import register_texture_image_tools
from .uv_ops import register_uv_tools
from .viewport_scene_advanced_ops import register_viewport_scene_advanced_tools
from .vision_feedback_ops import register_vision_feedback_tools
from .volumetric_vdb_ops import register_volumetric_vdb_tools
from .world_environment_ops import register_world_environment_tools

REGISTER_FUNCS = (
    register_get_scene_info_tool,
    register_get_object_info_tool,
    register_select_objects_tool,
    register_create_object_tool,
    register_delete_object_tool,
    register_duplicate_object_tool,
    register_parent_tools,
    register_set_object_transform_tool,
    register_apply_transform_tool,
    register_set_object_properties_tool,
    register_mesh_operation_tool,
    register_modifier_tools,
    register_material_tools,
    register_light_tools,
    register_camera_tools,
    register_animation_tools,
    register_render_tools,
    register_collection_tools,
    register_io_tools,
    register_execute_blender_python_tool,
    # --- 0.2.0 Additions ---
    register_boolean_tools,
    register_remesh_decimate_tools,
    register_uv_tools,
    register_texture_image_tools,
    register_pbr_bake_tools,
    register_rigging_tools,
    register_shape_key_tools,
    register_constraint_tools,
    register_pipeline_export_tools,
    # --- Sculpting, Preferences & Environment ---
    register_sculpt_tools,
    register_preference_tools,
    register_world_environment_tools,
    # --- Baking, Addons, Geometry Nodes & Shader Graphs ---
    register_advanced_bake_tools,
    register_addon_management_tools,
    register_geometry_nodes_tools,
    register_advanced_material_tools,
    # --- Render Effects, Mesh Surgery, Viewport & Cleanup ---
    register_render_effects_tools,
    register_advanced_mesh_edit_tools,
    register_viewport_scene_advanced_tools,
    # --- Vision, Compositor, Physics, Studio Lighting & NPR ---
    register_vision_feedback_tools,
    register_compositor_effects_tools,
    register_physics_simulation_tools,
    register_studio_lighting_tools,
    register_grease_pencil_tools,
    # --- 0.5.2 Additions: 3D Typography, Curves/Cables, Assets, Lattice, Volumetrics, Sequencer (100 Tools) ---
    register_text_typography_tools,
    register_curve_wire_tools,
    register_asset_browser_tools,
    register_lattice_deform_tools,
    register_volumetric_vdb_tools,
    register_sequencer_vse_tools,
    # --- 0.9.0 Additions: Batch Execution & Non-Modal Progress HUD (103 Tools) ---
    register_batch_execution_tools,
    register_progress_hud_tools,
    # --- 1.0.0 Additions: Shader Studio, Advanced GN & Material Slot Pipelines (113 Tools) ---
    register_shader_studio_tools,
    register_advanced_geom_nodes_studio_tools,
    register_advanced_material_slot_tools,
)


def register_all_tools(mcp: FastMCP, bridge: BlenderBridge) -> None:
    for register_func in REGISTER_FUNCS:
        register_func(mcp, bridge)
