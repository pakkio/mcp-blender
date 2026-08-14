from .addon_management_ops import InspectAddonTool, ManageAddonsTool
from .advanced_bake_ops import BakeAdvancedTool, ConfigureLightProbeTool
from .advanced_material_ops import EditMaterialNodesTool, ManageColorAttributesTool
from .advanced_mesh_edit_ops import AdvancedMeshEditTool, ManipulateOriginCursorTool
from .animation_ops import DeleteKeyframeTool, SetKeyframeTool, SetTimelineRangeTool
from .apply_transform import ApplyTransformTool
from .asset_browser_ops import (
    GenerateAssetPreviewTool,
    ImportAssetLibraryTool,
    ManageAssetBrowserTool,
)
from .boolean_ops import BooleanOperationTool
from .camera_ops import CameraLookAtTool, ConfigureCameraTool, FrameObjectsTool
from .collection_ops import ManageCollectionTool
from .compositor_effects_ops import (
    ConfigureCompositorEffectsTool,
    CreateToonShaderTool,
)
from .constraint_ops import AddConstraintTool, AnimateCameraTurntableTool
from .create_object import CreateObjectTool
from .curve_wire_ops import (
    ConvertMeshToCurveTool,
    CreateCurveCableTool,
    EditCurvePointsTool,
)
from .delete_object import DeleteObjectTool
from .duplicate_object import DuplicateObjectTool
from .execute_python import ExecuteBlenderPythonTool
from .geometry_nodes_ops import (
    BakeGeometryNodesTool,
    CreateGeometryNodesTool,
    EditGeometryNodesTool,
)
from .get_object_info import GetObjectInfoTool
from .get_scene_info import GetSceneInfoTool
from .grease_pencil_ops import SetupLineArtContourTool
from .io_ops import ExportSceneTool, ImportFileTool
from .lattice_deform_ops import (
    CreateLatticeDeformTool,
    DeformLatticePointsTool,
)
from .light_ops import ConfigureLightTool
from .material_ops import (
    AssignMaterialTool,
    CreateMaterialTool,
    GetMaterialInfoTool,
    SetMaterialPropertiesTool,
)
from .mesh_operation import MeshOperationTool
from .modifier_ops import (
    AddModifierTool,
    ApplyModifierTool,
    RemoveModifierTool,
    SetModifierPropertiesTool,
)
from .parent_ops import ParentObjectsTool, UnparentObjectsTool
from .pbr_bake_ops import (
    BakeTexturesTool,
    CreateProceduralMaterialTool,
    SetupPBRMaterialsTool,
)
from .physics_simulation_ops import (
    AddForceFieldTool,
    SetupClothSimulationTool,
    SetupRigidBodySimulationTool,
)
from .pipeline_export_ops import ExportUnityFBXTool, GenerateLODsTool
from .preference_ops import ConfigurePreferencesTool, GetSystemInfoTool
from .remesh_decimate_ops import DecimateMeshTool, RemeshMeshTool
from .render_effects_ops import (
    ConfigureMaterialTransparencyTool,
    ConfigureRenderEffectsTool,
)
from .render_ops import (
    GetViewportScreenshotTool,
    RenderSceneTool,
    SetRenderSettingsTool,
)
from .rigging_ops import CreateArmatureTool, PoseBoneTool
from .sculpt_ops import (
    ApplySculptFilterTool,
    ConfigureSculptModeTool,
    SculptMaskFaceSetsTool,
)
from .select_objects import SelectObjectsTool
from .sequencer_vse_ops import (
    ConfigureSequencerAudioTool,
    ManageSequencerStripsTool,
)
from .set_object_properties import SetObjectPropertiesTool
from .set_object_transform import SetObjectTransformTool
from .shape_key_ops import ManageShapeKeysTool
from .studio_lighting_ops import (
    ConfigureLightLinkingTool,
    CreateLightingRigTool,
)
from .text_typography_ops import (
    Create3DTextTool,
    DeformTextAlongCurveTool,
    SetTextPropertiesTool,
)
from .texture_image_ops import ImportImageAsPlaneTool, ProjectImageTextureTool
from .uv_ops import UVUnwrapTool
from .viewport_scene_advanced_ops import (
    AlignDistributeObjectsTool,
    ConfigureViewportDisplayTool,
    PurgeOrphansAndCleanupTool,
)
from .vision_feedback_ops import (
    CaptureMultiviewAuditTool,
    InspectFocusShotTool,
)
from .volumetric_vdb_ops import (
    BakeFluidDomainTool,
    ConfigureVolumeShaderTool,
    CreateVolumeVDBTool,
)
from .world_environment_ops import (
    ConfigureScenePhysicsTool,
    ConfigureWorldEnvironmentTool,
    SwitchWorkspaceTool,
)

ALL_TOOLS = (
    GetSceneInfoTool(),
    GetObjectInfoTool(),
    SelectObjectsTool(),
    CreateObjectTool(),
    DeleteObjectTool(),
    DuplicateObjectTool(),
    ParentObjectsTool(),
    UnparentObjectsTool(),
    SetObjectTransformTool(),
    ApplyTransformTool(),
    SetObjectPropertiesTool(),
    MeshOperationTool(),
    AddModifierTool(),
    ApplyModifierTool(),
    RemoveModifierTool(),
    SetModifierPropertiesTool(),
    CreateMaterialTool(),
    AssignMaterialTool(),
    GetMaterialInfoTool(),
    SetMaterialPropertiesTool(),
    ConfigureLightTool(),
    ConfigureCameraTool(),
    CameraLookAtTool(),
    FrameObjectsTool(),
    SetKeyframeTool(),
    DeleteKeyframeTool(),
    SetTimelineRangeTool(),
    RenderSceneTool(),
    GetViewportScreenshotTool(),
    SetRenderSettingsTool(),
    ManageCollectionTool(),
    ExportSceneTool(),
    ImportFileTool(),
    ExecuteBlenderPythonTool(),
    # --- 0.2.0 Additions ---
    BooleanOperationTool(),
    DecimateMeshTool(),
    RemeshMeshTool(),
    UVUnwrapTool(),
    ImportImageAsPlaneTool(),
    ProjectImageTextureTool(),
    SetupPBRMaterialsTool(),
    CreateProceduralMaterialTool(),
    BakeTexturesTool(),
    CreateArmatureTool(),
    PoseBoneTool(),
    ManageShapeKeysTool(),
    AddConstraintTool(),
    AnimateCameraTurntableTool(),
    ExportUnityFBXTool(),
    GenerateLODsTool(),
    # --- Sculpting, Preferences & Environment ---
    ConfigureSculptModeTool(),
    ApplySculptFilterTool(),
    SculptMaskFaceSetsTool(),
    ConfigurePreferencesTool(),
    GetSystemInfoTool(),
    ConfigureWorldEnvironmentTool(),
    ConfigureScenePhysicsTool(),
    SwitchWorkspaceTool(),
    # --- Baking, Addons, Geometry Nodes & Shader Graphs ---
    BakeAdvancedTool(),
    ConfigureLightProbeTool(),
    ManageAddonsTool(),
    InspectAddonTool(),
    CreateGeometryNodesTool(),
    EditGeometryNodesTool(),
    BakeGeometryNodesTool(),
    EditMaterialNodesTool(),
    ManageColorAttributesTool(),
    # --- Render Effects, Mesh Surgery, Viewport & Cleanup ---
    ConfigureRenderEffectsTool(),
    ConfigureMaterialTransparencyTool(),
    AdvancedMeshEditTool(),
    ManipulateOriginCursorTool(),
    ConfigureViewportDisplayTool(),
    PurgeOrphansAndCleanupTool(),
    AlignDistributeObjectsTool(),
    # --- Vision, Compositor, Physics, Studio Lighting & NPR ---
    CaptureMultiviewAuditTool(),
    InspectFocusShotTool(),
    ConfigureCompositorEffectsTool(),
    CreateToonShaderTool(),
    SetupRigidBodySimulationTool(),
    SetupClothSimulationTool(),
    AddForceFieldTool(),
    CreateLightingRigTool(),
    ConfigureLightLinkingTool(),
    SetupLineArtContourTool(),
    # --- 0.5.2 Additions: 3D Typography, Curves/Cables, Assets, Lattice, Volumetrics, Sequencer (100 Tools) ---
    Create3DTextTool(),
    DeformTextAlongCurveTool(),
    SetTextPropertiesTool(),
    CreateCurveCableTool(),
    ConvertMeshToCurveTool(),
    EditCurvePointsTool(),
    ManageAssetBrowserTool(),
    GenerateAssetPreviewTool(),
    ImportAssetLibraryTool(),
    CreateLatticeDeformTool(),
    DeformLatticePointsTool(),
    CreateVolumeVDBTool(),
    ConfigureVolumeShaderTool(),
    BakeFluidDomainTool(),
    ManageSequencerStripsTool(),
    ConfigureSequencerAudioTool(),
)

TOOL_REGISTRY = {tool.name: tool for tool in ALL_TOOLS}

__all__ = ["TOOL_REGISTRY", "ALL_TOOLS"]

