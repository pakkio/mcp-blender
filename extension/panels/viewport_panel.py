"""3D Viewport sidebar panel: real clickable buttons for the two actions
worth triggering without going through an MCP client -- creating a scene
checkpoint and regenerating localized structural names. Both operators call
the exact same ToolBase.execute() the MCP bridge itself dispatches to (via
TOOL_REGISTRY), so there is no second implementation of either to drift out
of sync with the MCP-facing one.
"""

import threading

import bpy

from ..tools import TOOL_REGISTRY
from .preferences import status_text_and_icon


class MCP_OT_create_checkpoint(bpy.types.Operator):
    bl_idname = "mcp_bridge.create_checkpoint"
    bl_label = "Create Scene Checkpoint"
    bl_description = "Save a full scene snapshot to disk that can be restored later"
    bl_options = {"REGISTER", "UNDO"}

    name: bpy.props.StringProperty(
        name="Name", description="Optional checkpoint name (auto-generated if empty)", default=""
    )

    def execute(self, context):
        if context.window:
            context.window.cursor_modal_set("WAIT")
        try:
            result = TOOL_REGISTRY["create_scene_checkpoint"].execute({"name": self.name or None})
            if not result.get("success"):
                self.report({"ERROR"}, result.get("message", "Checkpoint failed"))
                return {"CANCELLED"}
            self.report({"INFO"}, result["message"])
            return {"FINISHED"}
        finally:
            if context.window:
                context.window.cursor_modal_restore()


class MCP_OT_show_rename_result(bpy.types.Operator):
    bl_idname = "mcp_bridge.show_rename_result"
    bl_label = "Rename Result"
    bl_description = "Show which names were changed by the last Regenerate Names run"
    bl_options = {"REGISTER"}

    _pairs = None
    _message = ""

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        pairs = MCP_OT_show_rename_result._pairs or []

        if not pairs:
            layout.label(text="Nothing needed renaming -- all names already matched vocabulary.", icon="INFO")
            return

        layout.label(text=f"OK, renamed {len(pairs)} name(s):", icon="CHECKMARK")

        # Literal "old1, old2, ... -> new1, new2, ..." summary, wrapped so it
        # doesn't run off the dialog on hierarchies with many renamed parts.
        box_summary = layout.box()
        chunk = 6
        for i in range(0, len(pairs), chunk):
            group = pairs[i:i + chunk]
            olds = ", ".join(p["old"] for p in group)
            news = ", ".join(p["new"] for p in group)
            box_summary.label(text=f"{olds}  ->  {news}")

        layout.separator()
        box_table = layout.box()
        for p in pairs:
            row = box_table.row()
            row.label(text=p["old"], icon="OUTLINER_OB_MESH")
            row.label(text="->", icon="FORWARD")
            row.label(text=p["new"])

    def execute(self, context):
        return {"FINISHED"}


REORG_LEVEL_ITEMS = [
    ("LIGHT", "Light (minimal changes)", "Only fix clearly generic/garbled names, leave the rest alone -- fewer, coarser groups when separating", "TRIA_DOWN", 0),
    ("STANDARD", "Standard", "Balanced renaming/regrouping", "DOT", 1),
    ("DEEP", "Deep (thorough reorg)", "Rename/reorganize as much as possible -- finer, more granular groups when separating", "TRIA_UP", 2),
]


class MCP_OT_regen_names(bpy.types.Operator):
    bl_idname = "mcp_bridge.regen_names"
    bl_label = "Regenerate Names..."
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

    use_llm: bpy.props.BoolProperty(
        name="Use LLM Semantics",
        description="Call an LLM (via OPENROUTER_API_KEY in .env) to translate and organize hierarchy organically",
        default=True,
    )

    reorg_level: bpy.props.EnumProperty(
        name="Reorg Level",
        description="How aggressively the LLM should rename things (only applies with Use LLM Semantics)",
        items=REORG_LEVEL_ITEMS,
        default="STANDARD",
    )

    custom_prompt: bpy.props.StringProperty(
        name="Custom Instructions",
        description=(
            "Optional free-text instructions passed to the LLM (e.g. 'use nautical terms', "
            "'only rename hardware parts') -- only applies with Use LLM Semantics"
        ),
        default="",
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
        box_opt.prop(self, "use_llm")
        if self.use_llm:
            box_opt.prop(self, "reorg_level")
            box_opt.prop(self, "custom_prompt", icon="TEXT")

    def execute(self, context):
        params = {
            "lang": self.lang,
            "rename_meshes": self.rename_meshes,
            "use_llm": self.use_llm,
            "reorg_level": self.reorg_level,
            "custom_prompt": self.custom_prompt,
        }

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

        if context.window:
            context.window.cursor_modal_set("WAIT")
        try:
            result = TOOL_REGISTRY["regen_element_names"].execute(params)
            if not result.get("success"):
                self.report({"ERROR"}, result.get("message", "Regen failed"))
                return {"CANCELLED"}

            self.report({"INFO"}, result["message"])
            MCP_OT_show_rename_result._pairs = result.get("renamed_pairs", [])
            MCP_OT_show_rename_result._message = result["message"]
            bpy.ops.mcp_bridge.show_rename_result("INVOKE_DEFAULT")
            return {"FINISHED"}
        finally:
            if context.window:
                context.window.cursor_modal_restore()


class MCP_OT_show_separate_result(bpy.types.Operator):
    bl_idname = "mcp_bridge.show_separate_result"
    bl_label = "Separation Result"
    bl_description = "Show the macro/medium/micro breakdown produced by the last Separate in Logical Areas run"
    bl_options = {"REGISTER"}

    _result = None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        result = MCP_OT_show_separate_result._result or {}
        groups = result.get("groups", [])

        if not groups:
            layout.label(text="No groups were produced.", icon="ERROR")
            return

        total_parts = sum(len(g["parts"]) for g in groups)
        classified_by = "LLM" if result.get("used_llm") else "heuristic clustering (no OPENROUTER_API_KEY)"
        layout.label(
            text=f"OK, separated into {len(groups)} group(s) / {total_parts} part(s) via {classified_by}:",
            icon="CHECKMARK",
        )

        for g in groups:
            box = layout.box()
            box.label(text=g["group"], icon="EMPTY_AXIS")
            parts_text = ", ".join(g["parts"]) if g["parts"] else "(no parts)"
            col = box.column()
            col.scale_y = 0.9
            # Wrap long part lists instead of one label running off the dialog
            chunk = 4
            parts = g["parts"] or ["(no parts)"]
            for i in range(0, len(parts), chunk):
                col.label(text=", ".join(parts[i:i + chunk]))

    def execute(self, context):
        return {"FINISHED"}


class MCP_OT_separate_logical_areas(bpy.types.Operator):
    bl_idname = "mcp_bridge.separate_logical_areas"
    bl_label = "Separate in Logical Areas..."
    bl_description = (
        "Analyze the selected mesh(es) -- combining multiple selected objects into one working mesh first -- "
        "separate into logical parts (loose parts or materials), and organize them under parent Empties as "
        "macro/medium/micro areas using semantic classification (LLM via OPENROUTER_API_KEY in .env)"
    )
    bl_options = {"REGISTER", "UNDO"}

    lang: bpy.props.EnumProperty(
        name="Language",
        description="Target language vocabulary",
        items=[
            ("it", "Italian (Italiano)", "Organize and translate names in Italian", "WORLD", 0),
            ("en", "English", "Organize and translate names in English", "FONT_DATA", 1),
        ],
        default="it",
    )

    reorg_level: bpy.props.EnumProperty(
        name="Reorg Level",
        description="How fine-grained the sub-assembly breakdown should be -- applies both to LLM classification and the no-LLM spatial-clustering fallback",
        items=REORG_LEVEL_ITEMS,
        default="STANDARD",
    )

    custom_prompt: bpy.props.StringProperty(
        name="Custom Instructions",
        description=(
            "Optional free-text instructions passed to the LLM (e.g. 'separate hinges and glass into "
            "their own group', 'ignore screws') -- only applies when OPENROUTER_API_KEY is configured"
        ),
        default="",
    )

    def invoke(self, context, event):
        mesh_objs = [o for o in context.selected_objects if o.type == "MESH"]
        if not mesh_objs:
            self.report({"ERROR"}, "Please select at least one MESH object in the 3D viewport first.")
            return {"CANCELLED"}
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Separate Mesh in Logical Areas", icon="MESH_DATA")
        box.prop(self, "lang")

        mesh_objs = [o for o in context.selected_objects if o.type == "MESH"]
        if not mesh_objs and context.active_object and context.active_object.type == "MESH":
            mesh_objs = [context.active_object]

        if mesh_objs:
            count = len(mesh_objs)
            names_preview = ", ".join(o.name for o in mesh_objs[:3])
            if count > 3:
                names_preview += f"... (+{count - 3} more)"
            if count > 1:
                box.label(text=f"Selected ({count}, will be combined): {names_preview}", icon="OBJECT_DATA")
            else:
                box.label(text=f"Selected: {names_preview}", icon="OBJECT_DATA")
        else:
            box.label(text="No mesh selected! (Select in 3D View)", icon="ERROR")

        layout.separator()
        box_opt = layout.box()
        box_opt.prop(self, "reorg_level")
        box_opt.prop(self, "custom_prompt", icon="TEXT")

    def execute(self, context):
        params = {
            "lang": self.lang,
            "reorg_level": self.reorg_level,
            "custom_prompt": self.custom_prompt,
        }

        if context.window:
            context.window.cursor_modal_set("WAIT")
        try:
            result = TOOL_REGISTRY["separate_logical_areas"].execute(params)
            if not result.get("success"):
                self.report({"ERROR"}, result.get("message", "Separation failed"))
                return {"CANCELLED"}

            self.report({"INFO"}, result["message"])
            MCP_OT_show_separate_result._result = result
            bpy.ops.mcp_bridge.show_separate_result("INVOKE_DEFAULT")
            return {"FINISHED"}
        finally:
            if context.window:
                context.window.cursor_modal_restore()


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
    bl_idname = "mcp_bridge.verify_tools"
    bl_label = "Verify Tools..."
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
        if context.window:
            context.window.cursor_modal_set("WAIT")
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
            if context.window:
                context.window.cursor_modal_restore()

        total = len(TOOL_REGISTRY)
        summary = (
            f"{total} tools: {validated} validated cleanly, {ran_clean} ran with no params, "
            f"{skipped} skipped (heavy), {len(crashed)} raised an exception"
        )
        if malformed:
            summary += f"; {len(malformed)} malformed registration(s)"

        if crashed or malformed:
            for name, err in crashed:
                print(f"[MCP Bridge] '{name}'.execute({{}}) raised: {err}")
            for name in malformed:
                print(f"[MCP Bridge] '{name}' is malformed in TOOL_REGISTRY")
            self.report({"WARNING"}, summary + " -- see System Console for details")
            return {"CANCELLED"}

        self.report({"INFO"}, summary)
        return {"FINISHED"}


import bpy.utils.previews

from ..tools import TOOL_REGISTRY
from .preferences import status_text_and_icon

_preview_collections: dict = {}
_search_results_cache: list = []


def _get_search_items_callback(self, context):
    if not _search_results_cache:
        return [("NONE", "Click 'Search Online' to find models", "Enter query and click search", "INFO", 0)]
    return _search_results_cache
def run_online_search(self, context):
    global _search_results_cache
    from ..bridge import dispatch

    query = self.search_query.strip()
    if not query:
        return

    dispatch.set_client_status(f"Searching online for '{query}' (page {self.search_page})...")

    try:
        bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
    except Exception:
        pass

    if context.window:
        context.window.cursor_modal_set("WAIT")
    try:
        if "main" not in _preview_collections:
            try:
                _preview_collections["main"] = bpy.utils.previews.new()
            except Exception:
                pass

        pcoll = _preview_collections.get("main")
        provider = self.search_provider

        from ..tools.super_import_ops import download_thumbnail, search_all_online_models

        limit = 15
        offset = (self.search_page - 1) * limit
        hits = search_all_online_models(query, provider=provider, limit=limit, offset=offset)
        if not hits:
            _search_results_cache = [
                ("NONE", f"No models found for '{query}'", "Try another keyword or change provider", "ERROR", 0)
            ]
        else:
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
            _search_results_cache = items

        default_asset = "NONE"
        if _search_results_cache and _search_results_cache[0][0] != "NONE":
            default_asset = _search_results_cache[0][0]

        self.selected_asset = default_asset

    finally:
        dispatch.set_client_status(None)
        if context.window:
            context.window.cursor_modal_restore()


def _page_prev_callback(self, context):
    if not self.page_prev:
        return
    self.page_prev = False
    if self.search_page > 1:
        self.search_page -= 1
        run_online_search(self, context)


def _page_next_callback(self, context):
    if not self.page_next:
        return
    self.page_next = False
    self.search_page += 1
    run_online_search(self, context)


def _open_url_callback(self, context):
    if not self.open_url:
        return
    self.open_url = False

    selected = self.selected_asset
    if not selected or selected == "NONE":
        return

    if ":" in selected:
        provider, asset_id = selected.split(":", 1)
    else:
        provider = self.search_provider
        asset_id = selected

    import webbrowser
    url = ""
    prov_lower = provider.lower()
    if "polyhaven" in prov_lower:
        url = f"https://polyhaven.com/a/{asset_id}"
    elif "sketchfab" in prov_lower:
        url = f"https://sketchfab.com/3d-models/{asset_id}"
    elif "ambientcg" in prov_lower:
        url = f"https://ambientcg.com/view?id={asset_id}"

    if url:
        webbrowser.open(url)


def _run_search_callback(self, context):
    if not self.trigger_search:
        return
    self.trigger_search = False
    run_online_search(self, context)





class MCP_OT_show_env_info(bpy.types.Operator):
    bl_idname = "mcp_bridge.show_env_info"
    bl_label = ".env"
    bl_description = (
        "Show which .env files this Blender process loaded (with their full paths) and which "
        "API keys/secrets are configured, masked as first3...last3 characters"
    )
    bl_options = {"REGISTER"}

    _info = None

    def invoke(self, context, event):
        MCP_OT_show_env_info._info = TOOL_REGISTRY["get_env_info"].execute({})
        return context.window_manager.invoke_props_dialog(self, width=560)

    def draw(self, context):
        layout = self.layout
        info = MCP_OT_show_env_info._info or {}

        if not info.get("success"):
            layout.label(text=info.get("message", "Failed to read environment info"), icon="ERROR")
            return

        box_files = layout.box()
        box_files.label(text=".env Files", icon="FILE_TEXT")
        for f in info.get("env_files", []):
            row = box_files.row()
            row.label(text=f["path"], icon="CHECKMARK" if f.get("exists") else "X")

        layout.separator()
        box_keys = layout.box()
        box_keys.label(text="Keys", icon="LOCKED")
        keys = info.get("keys", {})
        if not keys:
            box_keys.label(text="No keys found", icon="INFO")
        else:
            header = box_keys.row()
            header.label(text="Key")
            header.label(text="Value")
            header.label(text="Source")
            for name, data in keys.items():
                row = box_keys.row()
                row.label(text=name)
                row.label(text=data.get("masked", ""))
                row.label(text=data.get("source") or "")

        layout.separator()
        py = info.get("python", {})
        layout.label(
            text=f"venv: {py.get('venv_path', '')} (in_venv={py.get('in_venv')}, python {py.get('version', '')})",
            icon="SCRIPTPLUGINS",
        )

    def execute(self, context):
        return {"FINISHED"}


class MCP_OT_super_import(bpy.types.Operator):
    bl_idname = "mcp_bridge.super_import"
    bl_label = "Super Import..."
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
        update=lambda self, context: setattr(self, "search_page", 1),
    )

    search_query: bpy.props.StringProperty(
        name="Search Query",
        description="Keyword to search online models (e.g. chair, table, car, plant, bottle, sword)",
        default="chair",
        update=lambda self, context: setattr(self, "search_page", 1),
    )

    trigger_search: bpy.props.BoolProperty(
        name="Search Online",
        description="Click to search online libraries",
        default=False,
        update=_run_search_callback,
    )

    search_page: bpy.props.IntProperty(
        name="Page",
        description="Current search result page",
        default=1,
        min=1,
    )

    page_prev: bpy.props.BoolProperty(
        name="Previous Page",
        description="Go to previous page of search results",
        default=False,
        update=_page_prev_callback,
    )

    page_next: bpy.props.BoolProperty(
        name="Next Page",
        description="Go to next page of search results",
        default=False,
        update=_page_next_callback,
    )

    open_url: bpy.props.BoolProperty(
        name="View Online",
        description="Open the model page in your web browser",
        default=False,
        update=_open_url_callback,
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
            
            row = box_search.row(align=True)
            row.prop(self, "search_query", text="Keyword", icon="VIEWZOOM")
            row.prop(self, "trigger_search", text="Search Online", icon="VIEWZOOM", toggle=True)

            # Pagination row
            row_page = box_search.row(align=True)
            row_page.prop(self, "page_prev", text="Previous Page", icon="TRIA_LEFT", toggle=True)
            row_page.label(text=f"Page {self.search_page}", icon="FILE_TICK")
            row_page.prop(self, "page_next", text="Next Page", icon="TRIA_RIGHT", toggle=True)

            box_search.separator()
            box_search.label(text="Found Models (Ordered by Relevance & Popularity):", icon="SORT_DESC")
            box_search.template_icon_view(self, "selected_asset", show_labels=True)
            
            row_sel = box_search.row(align=True)
            row_sel.prop(self, "selected_asset", text="")
            if self.selected_asset and self.selected_asset != "NONE":
                row_sel.prop(self, "open_url", text="View Online (3D / Full)", icon="WORLD", toggle=True)

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

        if context.window:
            context.window.cursor_modal_set("WAIT")
        try:
            result = TOOL_REGISTRY["super_import"].execute(params)
            if not result.get("success"):
                self.report({"ERROR"}, result.get("message", "Super import failed"))
                return {"CANCELLED"}

            self.report({"INFO"}, result["message"])
            return {"FINISHED"}
        finally:
            if context.window:
                context.window.cursor_modal_restore()


class MCP_OT_normalize_model(bpy.types.Operator):
    bl_idname = "mcp_bridge.normalize_model"
    bl_label = "Normalize Scale & Ground..."
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
        if context.window:
            context.window.cursor_modal_set("WAIT")
        try:
            result = TOOL_REGISTRY["normalize_model"].execute(params)
            if not result.get("success"):
                self.report({"ERROR"}, result.get("message", "Normalization failed"))
                return {"CANCELLED"}

            self.report({"INFO"}, result["message"])
            return {"FINISHED"}
        finally:
            if context.window:
                context.window.cursor_modal_restore()


class MCP_OT_simplify_mesh(bpy.types.Operator):
    bl_idname = "mcp_bridge.simplify_mesh"
    bl_label = "Simplify Mesh..."
    bl_description = "Reduce vertex budget using decimate, voxel remesh, or form-preserving simplify geometry"
    bl_options = {"REGISTER", "UNDO"}

    simplifier_tool: bpy.props.EnumProperty(
        name="Typology",
        description="Simplification method to apply",
        items=[
            ("SIMPLIFY", "Simplify Geometry (Preserve Form)", "Form-preserving repair, curvature decimation & rollback quality gate", "MOD_DECIM", 0),
            ("DECIMATE", "Decimate (Ratio/Collapse)", "Standard ratio decimation modifier", "MOD_SIMPLIFY", 1),
            ("REMESH", "Voxel Remesh", "Uniform voxel reconstruction (destroys UVs)", "MOD_REMESH", 2),
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

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=380)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Mesh Reduction & Vertex Budget", icon="MOD_DECIM")
        box.prop(self, "simplifier_tool")
        box.prop(self, "target_vertices")

        mesh_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not mesh_objs and context.active_object and context.active_object.type == "MESH":
            mesh_objs = [context.active_object]

        if mesh_objs:
            count = len(mesh_objs)
            names_preview = ", ".join([o.name for o in mesh_objs[:3]])
            if count > 3:
                names_preview += f"... (+{count - 3} more)"
            box.label(text=f"Selected meshes ({count}): {names_preview}", icon="OBJECT_DATA")
            total_verts = sum(len(o.data.vertices) for o in mesh_objs)
            box.label(text=f"Total vertices: {total_verts:,}", icon="INFO")
        else:
            box.label(text="No meshes selected! (Select in 3D View)", icon="ERROR")

    def execute(self, context):
        import math

        mesh_objs = [obj for obj in context.selected_objects if obj.type == "MESH"]
        if not mesh_objs and context.active_object and context.active_object.type == "MESH":
            mesh_objs = [context.active_object]

        if not mesh_objs:
            self.report({"WARNING"}, "No mesh objects selected in viewport")
            return {"CANCELLED"}

        if context.window:
            context.window.cursor_modal_set("WAIT")
        try:
            simplification_log = []
            budget = self.target_vertices
            success_count = 0

            for obj in mesh_objs:
                current_verts = len(obj.data.vertices)
                if current_verts <= budget:
                    simplification_log.append(f"'{obj.name}' already under budget ({current_verts} verts)")
                    success_count += 1
                    continue

                if self.simplifier_tool == "SIMPLIFY":
                    simplify_tool = TOOL_REGISTRY.get("simplify_geometry")
                    if simplify_tool:
                        res = simplify_tool.execute({
                            "object_name": obj.name,
                            "target": budget,
                            "target_unit": "VERTICES",
                        })
                        if res.get("success"):
                            simplification_log.append(
                                f"Simplified '{obj.name}' ({current_verts} -> {res.get('result_vertices')} verts)"
                            )
                            success_count += 1
                        else:
                            # Fallback to decimate, matching super import logic
                            decimate_tool = TOOL_REGISTRY.get("decimate_mesh")
                            ratio = max(0.01, min(1.0, budget / current_verts))
                            if decimate_tool:
                                dec_res = decimate_tool.execute({"object_name": obj.name, "ratio": ratio})
                                if dec_res.get("success"):
                                    simplification_log.append(
                                        f"Decimated '{obj.name}' (ratio {ratio:.2f}) due to gate rollback"
                                    )
                                    success_count += 1
                                else:
                                    simplification_log.append(f"Failed to simplify '{obj.name}'")
                            else:
                                simplification_log.append(f"Failed to simplify '{obj.name}'")

                elif self.simplifier_tool == "DECIMATE":
                    decimate_tool = TOOL_REGISTRY.get("decimate_mesh")
                    if decimate_tool:
                        ratio = max(0.01, min(1.0, budget / current_verts))
                        res = decimate_tool.execute({"object_name": obj.name, "ratio": ratio})
                        if res.get("success"):
                            simplification_log.append(
                                f"Decimated '{obj.name}' ({current_verts} -> {res.get('result_vertices')} verts, ratio {ratio:.2f})"
                            )
                            success_count += 1
                        else:
                            simplification_log.append(f"Failed to decimate '{obj.name}'")

                elif self.simplifier_tool == "REMESH":
                    remesh_tool = TOOL_REGISTRY.get("remesh_mesh")
                    if remesh_tool:
                        max_dim = max(obj.dimensions) if any(obj.dimensions) else 1.0
                        N = max(10.0, min(200.0, math.sqrt(budget / 2.78)))
                        voxel_size = max(0.001, max_dim / N)
                        res = remesh_tool.execute({
                            "object_name": obj.name,
                            "mode": "VOXEL",
                            "voxel_size": voxel_size,
                        })
                        if res.get("success"):
                            simplification_log.append(
                                f"Remeshed '{obj.name}' ({current_verts} -> {res.get('result_vertices')} verts, voxel {voxel_size:.4f})"
                            )
                            success_count += 1
                        else:
                            simplification_log.append(f"Failed to remesh '{obj.name}'")

            summary = "; ".join(simplification_log)
            if success_count > 0:
                self.report({"INFO"}, f"Simplification done: {summary}")
                return {"FINISHED"}
            else:
                self.report({"ERROR"}, f"Simplification failed: {summary}")
                return {"CANCELLED"}
        finally:
            if context.window:
                context.window.cursor_modal_restore()


import os
import tempfile
from pathlib import Path

_CHECKPOINT_DIR = Path(tempfile.gettempdir()) / "mcp_blender_checkpoints"


def _list_checkpoint_names() -> list[str]:
    if not _CHECKPOINT_DIR.is_dir():
        return []
    return sorted(
        [p.stem for p in _CHECKPOINT_DIR.glob("*.blend")],
        key=lambda n: (_CHECKPOINT_DIR / f"{n}.blend").stat().st_mtime,
        reverse=True,
    )


class MCP_OT_restore_checkpoint(bpy.types.Operator):
    bl_idname = "mcp_bridge.restore_checkpoint"
    bl_label = "Restore Scene Checkpoint..."
    bl_description = "Restore the scene to a previously saved checkpoint snapshot"
    bl_options = {"REGISTER", "UNDO"}

    checkpoint: bpy.props.EnumProperty(
        name="Checkpoint",
        description="Select a checkpoint to restore",
        items=lambda self, ctx: [
            (n, n, f"Restore checkpoint '{n}'") for n in _list_checkpoint_names()
        ] or [("NONE", "No checkpoints found", "Create one first with 'Create Scene Checkpoint'")],
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=420)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="Restore Scene Checkpoint", icon="FILE_TICK")
        box.prop(self, "checkpoint")
        if self.checkpoint == "NONE":
            box.label(text="No checkpoints available. Create one first.", icon="INFO")

    def execute(self, context):
        if self.checkpoint == "NONE":
            self.report({"WARNING"}, "No checkpoint selected")
            return {"CANCELLED"}

        from ..tools import TOOL_REGISTRY

        if context.window:
            context.window.cursor_modal_set("WAIT")
        try:
            result = TOOL_REGISTRY["restore_scene_checkpoint"].execute({"name": self.checkpoint})
            if not result.get("success"):
                self.report({"ERROR"}, result.get("message", "Restore failed"))
                return {"CANCELLED"}
            self.report({"INFO"}, result["message"])
            return {"FINISHED"}
        finally:
            if context.window:
                context.window.cursor_modal_restore()


class MCP_OT_ai_generate(bpy.types.Operator):
    bl_idname = "mcp_bridge.ai_generate"
    bl_label = "AI Generate 3D Model..."
    bl_description = "Generate a text-to-3D model using Meshy AI or Tripo3D with auto-simplification"
    bl_options = {"REGISTER", "UNDO"}

    provider: bpy.props.EnumProperty(
        name="Provider",
        description="AI 3D generation provider",
        items=[
            ("meshy", "Meshy AI", "Meshy AI text-to-3D generation", "SHADERFX", 0),
            ("tripo", "Tripo3D", "Tripo3D text-to-3D generation", "VIEW3D", 1),
        ],
        default="meshy",
    )

    prompt: bpy.props.StringProperty(
        name="Prompt",
        description="Text description of the 3D model to generate (e.g. 'a medieval sword', 'a wooden chair')",
        default="",
    )

    reduction_method: bpy.props.EnumProperty(
        name="Reduction Method",
        description="Mesh reduction applied after generation",
        items=[
            ("simplify", "Simplify (Preserve Form)", "Form-preserving repair & curvature decimation", "MOD_DECIM", 0),
            ("decimate", "Decimate (Ratio)", "Standard ratio decimation", "MOD_SIMPLIFY", 1),
            ("remesh", "Voxel Remesh", "Uniform voxel reconstruction (destroys UVs)", "MOD_REMESH", 2),
            ("none", "None (Keep Original)", "Do not reduce generated mesh", "RESTRICT_RENDER_OFF", 3),
        ],
        default="simplify",
    )

    target_vertices: bpy.props.IntProperty(
        name="Target Vertices",
        description="Target vertex count budget for the generated model",
        default=30000,
        min=100,
        max=100000,
        step=1000,
    )

    collection_name: bpy.props.StringProperty(
        name="Collection",
        description="Target collection (e.g. 'Generated/Meshy')",
        default="",
    )

    _thread = None
    _job = None
    _timer = None
    _area = None

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="AI Text-to-3D Generation", icon="SHADERFX")
        box.prop(self, "provider")
        box.prop(self, "prompt")

        layout.separator()
        box_sim = layout.box()
        box_sim.label(text="Mesh Reduction & Budget", icon="MOD_DECIM")
        box_sim.prop(self, "reduction_method")
        if self.reduction_method != "none":
            box_sim.prop(self, "target_vertices")

        layout.separator()
        box_opt = layout.box()
        box_opt.label(text="Placement", icon="TOOL_SETTINGS")
        box_opt.prop(self, "collection_name")

    def execute(self, context):
        if not self.prompt.strip():
            self.report({"ERROR"}, "Please enter a prompt for the 3D model")
            return {"CANCELLED"}

        # Generation (task create + poll + download) is pure network/file I/O
        # with no bpy calls, so it runs on a background thread instead of
        # blocking Blender's main thread for however long Meshy/Tripo take --
        # a blocking call here previously froze the whole UI, indistinguishable
        # from a crash, for as long as the AI provider took to respond.
        from ..tools.super_import_ops import generate_ai_model_job

        prompt = self.prompt.strip()
        provider = self.provider.upper()
        self._job = {"done": False, "error": None, "path": None, "credits": None, "status": "Starting..."}

        def worker(job):
            def on_status(text):
                job["status"] = text

            try:
                path, credits = generate_ai_model_job(provider, prompt, status_cb=on_status)
                job["path"] = path
                job["credits"] = credits
            except Exception as exc:
                job["error"] = str(exc)
            finally:
                job["done"] = True

        self._thread = threading.Thread(target=worker, args=(self._job,), daemon=True)
        self._thread.start()

        self._area = context.area
        wm = context.window_manager
        self._timer = wm.event_timer_add(0.25, window=context.window)
        wm.modal_handler_add(self)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type == "ESC":
            self._cleanup(context)
            self.report({"WARNING"}, "AI generation cancelled (any in-flight request may still finish on the provider's side)")
            return {"CANCELLED"}

        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        job = self._job
        if self._area:
            self._area.header_text_set(f"{job['status']}  (Esc to cancel)")

        if not job["done"]:
            return {"PASS_THROUGH"}

        self._cleanup(context)

        if job["error"]:
            self.report({"ERROR"}, job["error"])
            return {"CANCELLED"}

        collection = self.collection_name.strip() or f"Generated/{self.provider.capitalize()}"
        result = TOOL_REGISTRY["super_import"].execute({
            "source_type": "FILE",
            "filepath": str(job["path"]),
            "simplifier_tool": self.reduction_method.upper() if self.reduction_method != "none" else "NONE",
            "target_vertices": self.target_vertices,
            "auto_orient": True,
            "normalize_scale": True,
            "target_size": 2.0,
            "ground_to_floor": True,
            "center_xy": True,
            "collection_name": collection,
        })
        if not result.get("success"):
            self.report({"ERROR"}, result.get("message", "Import of generated model failed"))
            return {"CANCELLED"}
        self.report({"INFO"}, f"{result['message']} | {job['credits']}")
        return {"FINISHED"}

    def _cleanup(self, context):
        wm = context.window_manager
        if self._timer:
            wm.event_timer_remove(self._timer)
            self._timer = None
        if self._area:
            self._area.header_text_set(None)
            self._area = None


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
        layout.operator(MCP_OT_show_env_info.bl_idname, icon="LOCKED")
        layout.operator(MCP_OT_super_import.bl_idname, icon="IMPORT")
        layout.operator(MCP_OT_ai_generate.bl_idname, icon="SHADERFX")
        layout.operator(MCP_OT_normalize_model.bl_idname, icon="ORIENTATION_GIMBAL")
        layout.operator(MCP_OT_simplify_mesh.bl_idname, icon="MOD_DECIM")
        layout.separator()
        layout.operator(MCP_OT_create_checkpoint.bl_idname, icon="FILE_TICK")
        layout.operator(MCP_OT_restore_checkpoint.bl_idname, icon="FILE_REFRESH")
        layout.operator(MCP_OT_regen_names.bl_idname, icon="WORLD")
        layout.operator(MCP_OT_separate_logical_areas.bl_idname, icon="MESH_DATA")
        layout.separator()
        layout.operator(MCP_OT_verify_tools.bl_idname, icon="TOOL_SETTINGS")


CLASSES = (
    MCP_OT_show_env_info,
    MCP_OT_super_import,
    MCP_OT_ai_generate,
    MCP_OT_normalize_model,
    MCP_OT_simplify_mesh,
    MCP_OT_create_checkpoint,
    MCP_OT_restore_checkpoint,
    MCP_OT_show_rename_result,
    MCP_OT_regen_names,
    MCP_OT_show_separate_result,
    MCP_OT_separate_logical_areas,
    MCP_OT_verify_tools,
    VIEW3D_PT_mcp_bridge,
)
