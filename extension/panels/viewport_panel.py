"""3D Viewport sidebar panel: real clickable buttons for the two actions
worth triggering without going through an MCP client -- creating a scene
checkpoint and regenerating localized structural names. Both operators call
the exact same ToolBase.execute() the MCP bridge itself dispatches to (via
TOOL_REGISTRY), so there is no second implementation of either to drift out
of sync with the MCP-facing one.
"""

import bpy

from ..tools import TOOL_REGISTRY
from .preferences import status_text_and_icon


class MCP_OT_create_checkpoint(bpy.types.Operator):
    bl_idname = "mcp_bridge_pakkio.create_checkpoint"
    bl_label = "Create Scene Checkpoint"
    bl_description = "Save a full scene snapshot to disk that can be restored later"
    bl_options = {"REGISTER", "UNDO"}

    name: bpy.props.StringProperty(
        name="Name", description="Optional checkpoint name (auto-generated if empty)", default=""
    )

    def execute(self, context):
        result = TOOL_REGISTRY["create_scene_checkpoint"].execute({"name": self.name or None})
        if not result.get("success"):
            self.report({"ERROR"}, result.get("message", "Checkpoint failed"))
            return {"CANCELLED"}
        self.report({"INFO"}, result["message"])
        return {"FINISHED"}


class MCP_OT_regen_names(bpy.types.Operator):
    bl_idname = "mcp_bridge_pakkio.regen_names"
    bl_label = "Regenerate Names"
    bl_description = (
        "Rename category collections/Empties into the target language's vocabulary and "
        "re-link every collection's children/objects alphabetically"
    )
    bl_options = {"REGISTER", "UNDO"}

    lang: bpy.props.StringProperty(
        name="Language", description="Target language code (e.g. 'it')", default="it"
    )
    element: bpy.props.StringProperty(
        name="Element",
        description="Limit to one collection/root-Empty name (empty = whole scene)",
        default="",
    )

    def execute(self, context):
        result = TOOL_REGISTRY["regen_element_names"].execute(
            {"lang": self.lang, "element": self.element or None}
        )
        if not result.get("success"):
            self.report({"ERROR"}, result.get("message", "Regen failed"))
            return {"CANCELLED"}
        self.report({"INFO"}, result["message"])
        return {"FINISHED"}


# Skipped by default by the invoke-smoke-test in MCP_OT_verify_tools:
# render/bake/batch/fluid tools can legitimately take real time even with no
# target object, so blindly calling them from a health check would make
# "Verify Tools" itself slow and unpredictable. Everything else is expected
# (see ToolBase's own docstring contract) to validate required params and
# return a clean {"success": False, ...} before doing any real work -- so
# calling them with {} is a safe way to catch a tool that raises instead of
# validating. include_heavy opts into running these too, behind an explicit
# warning dialog (see draw()) since the user may want full coverage anyway.
_VERIFY_SKIP_KEYWORDS = ("render", "bake", "batch", "fluid")


class MCP_OT_verify_tools(bpy.types.Operator):
    bl_idname = "mcp_bridge_pakkio.verify_tools"
    bl_label = "Verify Tools"
    bl_description = (
        "Health-check every registered tool: confirms it's well-formed, then calls execute({}) "
        "in an isolated temporary scene (never your actual scene) to catch tools that raise an "
        "unhandled exception instead of cleanly validating missing input. Skips render/bake/"
        "batch/fluid tools by default -- opt in via the dialog to include them too"
    )
    bl_options = {"REGISTER"}

    include_heavy: bpy.props.BoolProperty(
        name="Include Heavy Tools (render/bake/batch/fluid)",
        description="Also run render/bake/batch/fluid tools -- can take noticeably longer",
        default=False,
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "include_heavy")
        if self.include_heavy:
            col = layout.column()
            col.alert = True
            col.label(text="Warning: render/bake/batch/fluid tools will run for real,", icon="ERROR")
            col.label(text="in the isolated temp scene -- this can take noticeably longer.")

    def execute(self, context):
        malformed = []
        for name, tool in TOOL_REGISTRY.items():
            if not getattr(tool, "name", None) or not getattr(tool, "description", None):
                malformed.append(name)
            elif not callable(getattr(tool, "execute", None)):
                malformed.append(name)

        original_scene = context.window.scene
        tmp_scene = bpy.data.scenes.new("mcp_verify_tmp")
        context.window.scene = tmp_scene

        crashed = []
        validated = 0
        ran_clean = 0
        skipped = 0
        try:
            for name, tool in TOOL_REGISTRY.items():
                if not self.include_heavy and any(k in name for k in _VERIFY_SKIP_KEYWORDS):
                    skipped += 1
                    continue
                try:
                    result = tool.execute({})
                    if isinstance(result, dict) and result.get("success") is False:
                        validated += 1
                    else:
                        ran_clean += 1
                except Exception as exc:  # noqa: BLE001 -- collecting failures is the point
                    crashed.append((name, str(exc)))
        finally:
            context.window.scene = original_scene
            bpy.data.scenes.remove(tmp_scene)
            for _ in range(3):
                bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)

        total = len(TOOL_REGISTRY)
        summary = (
            f"{total} tools: {validated} validated cleanly, {ran_clean} ran with no params, "
            f"{skipped} skipped (heavy), {len(crashed)} raised an exception"
        )
        if malformed:
            summary += f"; {len(malformed)} malformed registration(s)"

        if crashed or malformed:
            for name, err in crashed:
                print(f"[MCP Bridge Pakkio] '{name}'.execute({{}}) raised: {err}")
            for name in malformed:
                print(f"[MCP Bridge Pakkio] '{name}' is malformed in TOOL_REGISTRY")
            self.report({"WARNING"}, summary + " -- see System Console for details")
            return {"CANCELLED"}

        self.report({"INFO"}, summary)
        return {"FINISHED"}


class VIEW3D_PT_mcp_bridge(bpy.types.Panel):
    bl_label = "MCP Bridge"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "MCP Bridge"

    def draw(self, context):
        layout = self.layout
        text, icon = status_text_and_icon()
        layout.label(text=text, icon=icon)

        layout.separator()
        layout.operator(MCP_OT_create_checkpoint.bl_idname, icon="FILE_TICK")
        layout.operator(MCP_OT_regen_names.bl_idname, icon="WORLD")
        layout.separator()
        layout.operator(MCP_OT_verify_tools.bl_idname, icon="TOOL_SETTINGS")


CLASSES = (MCP_OT_create_checkpoint, MCP_OT_regen_names, MCP_OT_verify_tools, VIEW3D_PT_mcp_bridge)
