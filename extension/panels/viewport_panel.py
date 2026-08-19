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
        "Rename selected objects/hierarchy, active collection, or scene into clean localized vocabulary "
        "and re-link children/objects in alphabetical order"
    )
    bl_options = {"REGISTER", "UNDO"}

    scope: bpy.props.EnumProperty(
        name="Scope",
        description="Target elements to rename",
        items=[
            ("SELECTED", "Selected Object(s) & Hierarchy", "Rename selected objects and their children parts", "RESTRICT_SELECT_OFF", 0),
            ("ACTIVE_COLLECTION", "Active Collection", "Rename active collection and its contents", "GROUP", 1),
            ("SCENE", "Entire Scene", "Rename all scene collections and objects", "WORLD", 2),
        ],
        default="SELECTED",
    )

    lang: bpy.props.EnumProperty(
        name="Language",
        description="Target language vocabulary",
        items=[
            ("it", "Italian (Italiano)", "Localize into Italian names (e.g. Sedia, Ruota, Tavolo, Schienale)", "WORLD", 0),
            ("en", "English (Cleanup)", "De-clutter technical suffixes and translate foreign exporter tags into clean English", "FONT_DATA", 1),
        ],
        default="it",
    )

    rename_meshes: bpy.props.BoolProperty(
        name="Rename Mesh Data",
        description="Keep underlying mesh data blocks synchronized with object names",
        default=True,
    )

    def invoke(self, context, event):
        # Default scope intelligently based on active viewport selection
        if context.selected_objects:
            self.scope = "SELECTED"
        elif context.collection and context.collection != context.scene.collection:
            self.scope = "ACTIVE_COLLECTION"
        else:
            self.scope = "SCENE"
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Regenerate & Localize Names", icon="WORLD")
        box.prop(self, "scope")
        box.prop(self, "lang")

        if self.scope == "SELECTED":
            count = len(context.selected_objects)
            if count > 0:
                names_preview = ", ".join([o.name for o in context.selected_objects[:3]])
                if count > 3:
                    names_preview += f"... (+{count - 3} more)"
                box.label(text=f"Selected ({count}): {names_preview}", icon="OBJECT_DATA")
            else:
                box.label(text="No objects selected! (Select in 3D View)", icon="ERROR")

        elif self.scope == "ACTIVE_COLLECTION":
            active_col = context.collection.name if context.collection else "None"
            box.label(text=f"Active Collection: {active_col}", icon="GROUP")

        layout.separator()
        box_opt = layout.box()
        box_opt.prop(self, "rename_meshes")

    def execute(self, context):
        params = {"lang": self.lang, "rename_meshes": self.rename_meshes}

        if self.scope == "SELECTED":
            selected = [obj.name for obj in context.selected_objects]
            if not selected:
                if context.active_object:
                    selected = [context.active_object.name]
                else:
                    self.report({"WARNING"}, "No objects selected in viewport")
                    return {"CANCELLED"}
            params["objects"] = selected

        elif self.scope == "ACTIVE_COLLECTION":
            if context.collection:
                params["element"] = context.collection.name
            else:
                params["element"] = None
        else:
            params["element"] = None

        result = TOOL_REGISTRY["regen_element_names"].execute(params)
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


import bpy.utils.previews

from ..tools import TOOL_REGISTRY
from .preferences import status_text_and_icon

_preview_collections: dict = {}


def _get_search_items_callback(self, context):
    if "main" not in _preview_collections:
        try:
            _preview_collections["main"] = bpy.utils.previews.new()
        except Exception:
            pass

    pcoll = _preview_collections.get("main")
    query = getattr(self, "search_query", "").strip()
    provider = getattr(self, "search_provider", "ALL")

    from ..tools.super_import_ops import download_thumbnail, search_all_online_models

    hits = search_all_online_models(query, provider=provider, limit=15)
    if not hits:
        return [("NONE", f"No models found for '{query}'", "Try searching for another keyword or change provider", "ERROR", 0)]

    items = []
    for i, hit in enumerate(hits):
        raw_id = hit["id"]
        prov = hit.get("provider", "online").lower()
        full_key = f"{prov}:{raw_id}"
        icon_id = 0
        if pcoll is not None and hit.get("thumbnail_url"):
            if raw_id not in pcoll:
                thumb_path = download_thumbnail(raw_id, hit["thumbnail_url"])
                if thumb_path:
                    try:
                        pcoll.load(raw_id, thumb_path, "IMAGE")
                    except Exception:
                        pass
            if raw_id in pcoll:
                icon_id = pcoll[raw_id].icon_id

        prov_tag = prov.upper()
        poly_str = f"{hit['polycount']:,} verts" if hit.get("polycount") else "PBR asset"
        label = f"[{prov_tag}] {hit['name']} ({poly_str})"
        desc = f"{hit['credits']} | {hit['downloads']:,} downloads"
        items.append((full_key, label, desc, icon_id or "OBJECT_DATA", i))

    return items


class MCP_OT_super_import(bpy.types.Operator):
    bl_idname = "mcp_bridge_pakkio.super_import"
    bl_label = "Super Import"
    bl_description = (
        "Search online models across Poly Haven, Sketchfab, and ambientCG with previews, "
        "vertex counts, and credits, or import local files with automatic mesh simplification"
    )
    bl_options = {"REGISTER", "UNDO"}

    source_type: bpy.props.EnumProperty(
        name="Source",
        description="Asset acquisition source",
        items=[
            ("SEARCH", "Search Online (Poly Haven, Sketchfab, ambientCG)", "Search online 3D models with previews and polycount ranking", "VIEWZOOM", 0),
            ("FILE", "Local File", "Pick a 3D model file (.glb, .gltf, .fbx, .obj, .stl, .usd, .zip) from disk", "FILE_FOLDER", 1),
            ("URL", "Direct URL / AI Model", "Direct download from HTTP/HTTPS link (Meshy, Tripo, Trellis, GLB link)", "SHADERFX", 2),
        ],
        default="SEARCH",
    )

    search_provider: bpy.props.EnumProperty(
        name="Provider",
        description="Online library provider to search",
        items=[
            ("ALL", "All Providers (Poly Haven, Sketchfab, ambientCG)", "Search across all supported online libraries", "WORLD", 0),
            ("POLYHAVEN", "Poly Haven (CC0 3D Models)", "Search Poly Haven CC0 library", "IMAGE", 1),
            ("SKETCHFAB", "Sketchfab (Models Catalog)", "Search Sketchfab downloadable models", "COMMUNITY", 2),
            ("AMBIENTCG", "ambientCG (CC0 PBR Assets)", "Search ambientCG materials & models", "FILE_IMAGE", 3),
        ],
        default="ALL",
    )

    search_query: bpy.props.StringProperty(
        name="Search Query",
        description="Keyword to search online models (e.g. chair, table, car, plant, bottle, sword)",
        default="chair",
    )

    selected_asset: bpy.props.EnumProperty(
        name="Matching Models",
        description="Select a model ordered by importance and popularity",
        items=_get_search_items_callback,
    )

    filepath: bpy.props.StringProperty(
        name="File Path",
        description="Path to local 3D file or archive",
        subtype="FILE_PATH",
        default="",
    )

    direct_url: bpy.props.StringProperty(
        name="Direct URL",
        description="HTTP/HTTPS download link to .glb / .gltf / .zip",
        default="",
    )

    simplifier_tool: bpy.props.EnumProperty(
        name="Simplifier",
        description="Mesh reduction method applied after import",
        items=[
            ("SIMPLIFY", "Simplify Geometry (Preserve Form)", "Form-preserving repair, curvature decimation & rollback quality gate", "MOD_DECIM", 0),
            ("DECIMATE", "Decimate (Ratio/Collapse)", "Standard ratio decimation modifier", "MOD_SIMPLIFY", 1),
            ("REMESH", "Voxel Remesh", "Uniform voxel reconstruction (destroys UVs)", "MOD_REMESH", 2),
            ("NONE", "None (Keep Original)", "Do not reduce mesh geometry", "RESTRICT_RENDER_OFF", 3),
        ],
        default="SIMPLIFY",
    )

    target_vertices: bpy.props.IntProperty(
        name="Target Vertices",
        description="Target vertex count budget per mesh object",
        default=10000,
        min=10,
        max=10000000,
    )

    auto_orient: bpy.props.BoolProperty(
        name="Auto Orient",
        description="Automatically detect and correct upside-down or lying-down models",
        default=True,
    )

    normalize_scale: bpy.props.BoolProperty(
        name="Normalize Size & Ground",
        description="Auto-rescale model to real-world target dimension (e.g. 2.0m) and align base to ground Z=0",
        default=True,
    )

    target_size: bpy.props.FloatProperty(
        name="Target Size (m)",
        description="Target maximum dimension in meters (e.g. 1.0m chair, 2.0m vehicle/person, 0.5m prop)",
        default=2.0,
        min=0.01,
        max=1000.0,
    )

    ground_to_floor: bpy.props.BoolProperty(
        name="Ground at Z=0",
        description="Align the bottom base of the model flush on the ground plane (Z=0)",
        default=True,
    )

    center_xy: bpy.props.BoolProperty(
        name="Center at (0, 0)",
        description="Center model horizontally at origin",
        default=True,
    )

    collection_name: bpy.props.StringProperty(
        name="Collection",
        description="Target collection name (leave blank for active scene collection)",
        default="",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "source_type", expand=True)

        if self.source_type == "SEARCH":
            box_search = layout.box()
            box_search.label(text="Search Online 3D Libraries", icon="WORLD")
            box_search.prop(self, "search_provider")
            box_search.prop(self, "search_query", text="Keyword", icon="VIEWZOOM")

            box_search.separator()
            box_search.label(text="Found Models (Ordered by Relevance & Popularity):", icon="SORT_DESC")
            box_search.template_icon_view(self, "selected_asset", show_labels=True)
            box_search.prop(self, "selected_asset", text="")

        elif self.source_type == "FILE":
            box_file = layout.box()
            box_file.label(text="Local 3D File", icon="FILE_FOLDER")
            box_file.prop(self, "filepath")
            box_file.label(text="Supports: .glb, .gltf, .fbx, .obj, .stl, .usd, .blend, .zip", icon="INFO")

        elif self.source_type == "URL":
            box_url = layout.box()
            box_url.label(text="Direct Model URL", icon="SHADERFX")
            box_url.prop(self, "direct_url")
            box_url.label(text="Supports direct link to .glb, .gltf, or AI model outputs", icon="INFO")

        layout.separator()
        box_norm = layout.box()
        box_norm.label(text="Real-World Size & Grounding", icon="ORIENTATION_GIMBAL")
        box_norm.prop(self, "normalize_scale")
        if self.normalize_scale:
            row_s = box_norm.row()
            row_s.prop(self, "target_size")
            row_g = box_norm.row()
            row_g.prop(self, "ground_to_floor")
            row_g.prop(self, "center_xy")

        layout.separator()
        box_sim = layout.box()
        box_sim.label(text="Mesh Reduction & Vertex Budget", icon="MOD_DECIM")
        box_sim.prop(self, "simplifier_tool")
        if self.simplifier_tool != "NONE":
            box_sim.prop(self, "target_vertices")

        layout.separator()
        box_opt = layout.box()
        box_opt.label(text="Placement Options", icon="TOOL_SETTINGS")
        box_opt.prop(self, "auto_orient")
        box_opt.prop(self, "collection_name")

    def execute(self, context):
        if self.source_type == "SEARCH":
            if not self.selected_asset or self.selected_asset == "NONE":
                self.report({"ERROR"}, "No valid model selected from search results")
                return {"CANCELLED"}
            selected = self.selected_asset
            if ":" in selected:
                provider, asset_id = selected.split(":", 1)
            else:
                provider = self.search_provider
                asset_id = selected
            filepath = ""
            url = ""
        elif self.source_type == "FILE":
            if not self.filepath:
                self.report({"ERROR"}, "Please choose a file to import")
                return {"CANCELLED"}
            asset_id = ""
            filepath = self.filepath
            url = ""
            provider = "FILE"
        else:  # URL
            if not self.direct_url:
                self.report({"ERROR"}, "Please enter a model URL")
                return {"CANCELLED"}
            asset_id = ""
            filepath = ""
            url = self.direct_url
            provider = "URL"

        params = {
            "source_type": self.source_type,
            "provider": provider,
            "asset_id": asset_id,
            "filepath": filepath,
            "url": url,
            "simplifier_tool": self.simplifier_tool,
            "target_vertices": self.target_vertices,
            "auto_orient": self.auto_orient,
            "normalize_scale": self.normalize_scale,
            "target_size": self.target_size,
            "ground_to_floor": self.ground_to_floor,
            "center_xy": self.center_xy,
            "collection_name": self.collection_name,
        }

        result = TOOL_REGISTRY["super_import"].execute(params)
        if not result.get("success"):
            self.report({"ERROR"}, result.get("message", "Super import failed"))
            return {"CANCELLED"}

        self.report({"INFO"}, result["message"])
        return {"FINISHED"}


class MCP_OT_normalize_model(bpy.types.Operator):
    bl_idname = "mcp_bridge_pakkio.normalize_model"
    bl_label = "Normalize Scale & Ground"
    bl_description = "Rescale selected objects to real-world dimensions (e.g. 2.0m) and place base flush on ground Z=0"
    bl_options = {"REGISTER", "UNDO"}

    target_size: bpy.props.FloatProperty(
        name="Target Size (m)",
        description="Target maximum dimension in meters",
        default=2.0,
        min=0.01,
        max=1000.0,
    )

    ground: bpy.props.BoolProperty(
        name="Place on Ground (Z=0)",
        description="Align bottom base of model flush on ground grid",
        default=True,
    )

    center_xy: bpy.props.BoolProperty(
        name="Center at Origin",
        description="Center model horizontally at (0, 0)",
        default=True,
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=340)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Normalize Scale & Grounding", icon="ORIENTATION_GIMBAL")
        box.prop(self, "target_size")
        box.prop(self, "ground")
        box.prop(self, "center_xy")

        count = len(context.selected_objects)
        if count > 0:
            box.label(text=f"Selected: {count} object(s)", icon="OBJECT_DATA")
        else:
            box.label(text="All scene objects will be normalized", icon="INFO")

    def execute(self, context):
        selected = [obj.name for obj in context.selected_objects]
        params = {
            "target_size": self.target_size,
            "ground": self.ground,
            "center_xy": self.center_xy,
            "objects": selected if selected else None,
        }
        result = TOOL_REGISTRY["normalize_model"].execute(params)
        if not result.get("success"):
            self.report({"ERROR"}, result.get("message", "Normalization failed"))
            return {"CANCELLED"}

        self.report({"INFO"}, result["message"])
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
        layout.operator(MCP_OT_super_import.bl_idname, icon="IMPORT")
        layout.operator(MCP_OT_normalize_model.bl_idname, icon="ORIENTATION_GIMBAL")
        layout.separator()
        layout.operator(MCP_OT_create_checkpoint.bl_idname, icon="FILE_TICK")
        layout.operator(MCP_OT_regen_names.bl_idname, icon="WORLD")
        layout.separator()
        layout.operator(MCP_OT_verify_tools.bl_idname, icon="TOOL_SETTINGS")


CLASSES = (
    MCP_OT_super_import,
    MCP_OT_normalize_model,
    MCP_OT_create_checkpoint,
    MCP_OT_regen_names,
    MCP_OT_verify_tools,
    VIEW3D_PT_mcp_bridge,
)
