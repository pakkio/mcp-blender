"""Budget-driven, form-preserving mesh reduction.

decimate_mesh / remesh_mesh (remesh_decimate_ops.py) are the wrong shape for
a messy imported asset: Collapse assumes a welded, manifold mesh, but glTF/
STL/FBX exporters split vertices at every UV seam and material boundary, so
what looks like one surface is really disconnected shells touching at their
edges. Collapse pulls those shells apart independently -- the "holes" a flat
decimate produces on real assets. And a flat ratio spends its budget evenly,
so a fork's thin tines get thinned at the same rate as its flat handle.

simplify_geometry repairs the mesh first (weld coincident verts, drop loose
geometry, close pinhole gaps), then reduces with the vertex budget spent
where the surface is flat and dense (limited dissolve, then curvature-
weighted Decimate), then measures what it produced (two-sided surface
deviation + new-hole count) and rolls back rather than handing back a
mesh that silently lost a feature.

Everything here runs inside one blocking execute() on Blender's main thread,
and the inputs are frequently enormous (a Meshy image-to-3D result arrives at
~1M vertices / 2M triangles). Two consequences shape the code below: every
per-element pass goes through foreach_get/numpy rather than a Python loop,
and each phase reports to the viewport HUD with a forced redraw, because a UI
that cannot repaint while this runs is indistinguishable from a hung Blender.
"""

import math
import time

import bmesh
import bpy
import numpy as np
from mathutils.bvhtree import BVHTree

from . import simplify_geometry_planner as planner
from .base import ToolBase

_MAX_RATIO_ITERATIONS = 4
_DEVIATION_SAMPLE_LIMIT = 4000
# Exact coincident-vertex and shell counts are diagnostics only (the quality
# gate uses neither), and both cost more than the rest of _analyze on a dense
# mesh -- above this they are reported as None, i.e. "not measured", rather
# than as a 0 that reads like "measured, none found".
_ANALYZE_EXACT_LIMIT = 60_000
# Above this many source faces, deviation is measured one-sided; see
# _measure_deviation.
_DEVIATION_TWO_SIDED_MAX_FACES = 400_000
# A mesh further than this multiple above its budget gets a cheap unweighted
# collapse into range before the form-preserving pass runs. See _fast_prepass.
_PREPASS_FACTOR = 8
# Distinct weight levels written to the protection vertex group. Decimate's
# influence factor has no use for more resolution than this, and each level
# costs exactly one RNA call instead of one per vertex.
_WEIGHT_BUCKETS = 64
_HUD_MIN_INTERVAL_S = 0.2


# Internal phase status -> plain-language hint for the cursor badge and the
# Status line. Matched by prefix (statuses embed live numbers), first hit
# wins; unknown statuses pass through untouched.
_HUMAN_HINTS = (
    ("Analyzing", "Checking the mesh for holes and loose bits"),
    ("Repairing", "Welding split seams so shrinking can't tear holes"),
    ("Dissolving", "Erasing unneeded vertices in flat areas"),
    ("Pre-pass", "Quick rough shrink before the careful pass"),
    ("Computing curvature", "Finding sharp edges and thin bits to protect"),
    ("Writing protection", "Marking the details that must survive"),
    ("Solving collapse", "Aiming the shrink at your vertex budget"),
    ("Applying collapse", "Shrinking flat zones, keeping the details"),
    ("Measuring", "Comparing the result with the original"),
    ("Quality gate failed", "Too much changed - restoring the original"),
)


def _human_hint(status):
    for prefix, hint in _HUMAN_HINTS:
        if status.startswith(prefix):
            return hint
    if status.startswith("Done:"):
        return status
    return status


class _Progress:
    """Phase-by-phase HUD feedback for a run that can take minutes.

    simplify_geometry is called from inside a single blocking execute() (the
    viewport panel's AI Generate button reaches it through super_import), so
    Blender's event loop never runs while it works. A plain tag_redraw()
    therefore paints nothing until the whole run is over, which is why the
    old behaviour was a HUD frozen on the caller's "Simplifying..." frame for
    the entire reduction. Each phase() pushes through
    push_hud_update(force_redraw=True), throttled so the forced redraws do
    not themselves become a cost, and carries elapsed seconds so that even a
    long C-level step visibly ticks. It also drives the cursor badge (a small
    "% - what" pill next to the mouse, where the user is actually looking
    while the WAIT cursor shows) with a plain-language hint per phase.
    """

    def __init__(self, object_name, verts, base=0.0, span=100.0, enabled=True):
        self.enabled = bool(enabled) and not bpy.app.background
        self.label = f"Simplify '{object_name}' ({verts:,} verts)"
        self.base = float(base)
        self.span = float(span)
        self.started = time.perf_counter()
        self.started_wall = time.time()
        self._last_push = 0.0
        self._log = []
        # History card: every phase() call is recorded here with timing,
        # even when the HUD push is throttled or disabled (background mode).
        # Each entry: {step, status, elapsed_s, dt_s, progress_pct, extra}.
        self.history = []
        self._last_step_t = self.started

    def phase(self, status, fraction, force=False, extra=None):
        now = time.perf_counter()
        elapsed = now - self.started
        dt = now - self._last_step_t
        self._last_step_t = now
        percent = self.base + self.span * max(0.0, min(1.0, fraction))
        entry = {
            "step": len(self.history) + 1,
            "status": str(status),
            "elapsed_s": round(elapsed, 3),
            "dt_s": round(dt, 3),
            "progress_pct": round(percent, 1),
        }
        if isinstance(extra, dict) and extra:
            try:
                entry["extra"] = {k: extra[k] for k in extra}
            except Exception:
                entry["extra"] = {}
        self.history.append(entry)
        self._log.append(status)
        if not self.enabled:
            return entry
        wall_now = time.time()
        if not force and wall_now - self._last_push < _HUD_MIN_INTERVAL_S:
            return entry
        self._last_push = wall_now
        try:
            from .progress_hud_ops import push_hud_update

            push_hud_update(
                title=self.label,
                status=f"{_human_hint(status)}  [{elapsed:.0f}s]",
                progress_percent=percent,
                details=self._log[-4:],
                force_redraw=True,
                cursor_badge=True,
                badge_text=_human_hint(status),
            )
        except Exception:
            self.enabled = False
        return entry

    def total_seconds(self):
        return round(time.perf_counter() - self.started, 3)

    def history_payload(self):
        return {"total_seconds": self.total_seconds(), "steps": list(self.history)}


def _format_history_for_hud(history):
    """One short line per step for the HUD card details list."""
    lines = []
    for e in history:
        try:
            lines.append(f"{e['elapsed_s']:.1f}s (+{e['dt_s']:.1f}s) [{e['progress_pct']:.0f}%] {e['status']}"[:96])
        except Exception:
            continue
    return lines


def _save_history_card(progress, status, completed_summary, next_steps=None):
    """Persist the run's history card to the viewport HUD.

    The live HUD only shows the last 4 details lines, but HUD_STATE keeps
    the full list, so pass the whole formatted history -- the card becomes
    the on-screen record of time data + each simplifying step.
    """
    try:
        from .progress_hud_ops import push_hud_update

        push_hud_update(
            title=progress.label,
            status=status,
            progress_percent=100.0,
            details=_format_history_for_hud(progress.history),
            completed_summary=completed_summary,
            next_steps=next_steps or [],
            force_redraw=True,
            cursor_badge=False,
        )
    except Exception:
        pass


# Last-run card: the previous simplify_geometry run, kept for the
# "Previous Simplify" panel box and the show_last_simplify_card tool.
_LAST_CARD: dict | None = None


def get_last_card() -> dict | None:
    """The previous simplify_geometry run's card, or None before the first run."""
    return _LAST_CARD


def _record_last_run(
    *,
    object_name,
    success,
    message,
    original_vertices=None,
    result_vertices=None,
    target_vertices=None,
    rolled_back=False,
    dry_run=False,
    gate_reason="",
    history=None,
    suggested_retry_target=None,
):
    global _LAST_CARD
    history = history or {"total_seconds": 0.0, "steps": []}
    _LAST_CARD = {
        "object_name": object_name,
        "success": bool(success),
        "rolled_back": bool(rolled_back),
        "dry_run": bool(dry_run),
        "message": str(message),
        "original_vertices": original_vertices,
        "result_vertices": result_vertices,
        "target_vertices": target_vertices,
        "total_seconds": history.get("total_seconds", 0.0),
        "gate_reason": str(gate_reason or ""),
        "when": time.time(),
        "suggested_retry_target": suggested_retry_target,
        "history": history,
    }
    return _LAST_CARD


class SimplifyGeometryTool(ToolBase):
    name = "simplify_geometry"
    description = (
        "Reduce a mesh to a vertex budget while preserving its form: repairs the mesh (welds seams, drops "
        "loose geometry, closes pinhole gaps), removes vertices from flat/dense regions first, protects thin "
        "features and boundaries via curvature-weighted decimation, then measures the result and rolls back "
        "rather than returning a mesh with new holes or a lost feature. Use this instead of decimate_mesh on "
        "imported/downloaded assets, which are usually not the welded manifold mesh decimate_mesh assumes. "
        "Returns a 'history' card with total_seconds plus per-step elapsed/dt for every phase "
        "(analyze/repair/dissolve/pre-pass/collapse-solver-iterations/apply/measure) and saves the same "
        "card to the viewport HUD."
    )

    def execute(self, params: dict) -> dict:
        object_name = params.get("object_name")
        if not object_name:
            return {"success": False, "message": "'object_name' is required"}

        obj = bpy.data.objects.get(object_name)
        if not obj or obj.type != "MESH":
            return {"success": False, "message": f"Object '{object_name}' not found or not a MESH"}

        blocked = _unusable_context(obj)
        if blocked:
            return {"success": False, "message": blocked}

        current_verts = len(obj.data.vertices)
        # Only a TRIANGLES budget needs the triangle count, and counting them
        # is a pass over every polygon in the mesh -- don't pay for it on the
        # VERTICES/preset calls that never look at it.
        unit = str(params.get("target_unit", "VERTICES")).upper()
        current_tris = _triangle_count(obj.data) if unit == "TRIANGLES" else 0

        target_verts, error = planner.resolve_target_vertices(
            target=params.get("target"),
            target_unit=params.get("target_unit", "VERTICES"),
            preset=params.get("preset"),
            current_verts=current_verts,
            current_tris=current_tris,
        )
        if error:
            return {"success": False, "message": error}

        if target_verts >= current_verts:
            _record_last_run(
                object_name=object_name,
                success=True,
                message=f"'{object_name}' already has {current_verts} vertices, at or under the {target_verts} target; nothing to do",
                original_vertices=current_verts,
                result_vertices=current_verts,
                target_vertices=target_verts,
                gate_reason="no reduction needed",
            )
            return {
                "success": True,
                "message": f"'{object_name}' already has {current_verts} vertices, at or under the {target_verts} target; nothing to do",
                "object_name": object_name,
                "original_vertices": current_verts,
                "result_vertices": current_verts,
                "target_vertices": target_verts,
                "gate": {"passed": True, "reason": "no reduction needed"},
            }

        dry_run = bool(params.get("dry_run", False))
        repair = bool(params.get("repair", True))
        weld_factor = float(params.get("weld_factor", 1e-4))
        preserve_uv = bool(params.get("preserve_uv", True))
        preserve_boundaries = bool(params.get("preserve_boundaries", True))
        sharp_angle = float(params.get("sharp_angle", 3.0))
        tolerance = float(params.get("tolerance", 0.05))
        use_symmetry = bool(params.get("use_symmetry", False))
        symmetry_axis = params.get("symmetry_axis", "X").upper()
        max_deviation_pct = float(params.get("max_deviation_pct", 2.0))
        allow_new_holes = int(params.get("allow_new_holes", 0))
        rollback_on_failure = bool(params.get("rollback_on_failure", True))
        # Reasoned defaults, not measured thresholds (see TODO.md #10) -- exposed
        # so a caller who hits a bad tradeoff on a specific mesh can override
        # them instead of waiting on a code change.
        prepass_factor = float(params.get("prepass_factor", _PREPASS_FACTOR))
        deviation_two_sided_max_faces = int(
            params.get("deviation_two_sided_max_faces", _DEVIATION_TWO_SIDED_MAX_FACES)
        )

        # Private convention with callers that drive the HUD themselves (see
        # super_import_ops): map this run's 0-100% onto their slice of the bar
        # instead of fighting them for it.
        hud = params.get("_hud") or {}
        progress = _Progress(
            object_name,
            current_verts,
            base=hud.get("base", 0.0),
            span=hud.get("span", 100.0),
            enabled=hud.get("enabled", True),
        )
        progress.label = f"Simplify '{object_name}' ({current_verts:,} -> ~{target_verts:,} verts)"

        progress.phase("Analyzing mesh...", 0.02, force=True)
        analysis = _analyze(obj)
        progress.phase(
            f"Analyzed: {analysis['vertices']:,} verts, {analysis['faces']:,} faces, "
            f"{analysis['boundary_edges']} boundary edges, {analysis['non_manifold_edges']} non-manifold",
            0.05,
            extra={"vertices": analysis["vertices"], "faces": analysis["faces"]},
        )

        if dry_run:
            estimated_ratio = planner.estimate_initial_ratio(current_verts, len(obj.data.polygons), target_verts)
            progress.phase("Done: dry run (no changes)", 1.0, force=True)
            history = progress.history_payload()
            _save_history_card(
                progress,
                status=f"Dry run {current_verts:,} -> ~{target_verts:,} verts [{history['total_seconds']:.1f}s]",
                completed_summary=f"Dry run {current_verts:,} -> ~{target_verts:,} verts in {history['total_seconds']:.1f}s",
            )
            _record_last_run(
                object_name=object_name,
                success=True,
                message=f"Dry run: '{object_name}' would be reduced from {current_verts} to ~{target_verts} vertices",
                original_vertices=current_verts,
                result_vertices=current_verts,
                target_vertices=target_verts,
                dry_run=True,
                gate_reason="dry run (no changes)",
                history=history,
            )
            return {
                "success": True,
                "message": f"Dry run: '{object_name}' would be reduced from {current_verts} to ~{target_verts} vertices",
                "object_name": object_name,
                "original_vertices": current_verts,
                "target_vertices": target_verts,
                "analysis": analysis,
                "estimated_initial_ratio": round(estimated_ratio, 4),
                "dry_run": True,
                "history": history,
            }

        original_mesh_copy = obj.data.copy()
        original_verts_count = current_verts
        # Shape keys cannot survive a topology change. Clearing them is not
        # something a caller can discover afterwards, so it gets reported.
        had_shape_keys = bool(obj.data.shape_keys)

        view_layer = bpy.context.view_layer
        prev_active = view_layer.objects.active
        prev_hide_viewport = obj.hide_viewport
        try:
            prev_hidden = obj.hide_get()
        except Exception:
            prev_hidden = False

        # The ratio solve reads evaluated geometry off the depsgraph and the
        # apply goes through an operator; both need the object visible and
        # active. All three are restored in the finally below.
        obj.hide_viewport = False
        try:
            obj.hide_set(False)
        except Exception:
            pass
        view_layer.objects.active = obj
        if had_shape_keys:
            obj.shape_key_clear()

        try:
            diag = _bbox_diagonal(obj.data)
            bm = bmesh.new()
            bm.from_mesh(obj.data)

            repair_stats = None
            if repair:
                progress.phase(f"Repairing {current_verts:,} vertices (weld, close gaps)...", 0.08, force=True)
                repair_stats = _repair(bm, weld_factor=weld_factor, diag=diag)
                progress.phase(
                    f"Repaired: welded {repair_stats['welded_vertices']:,}, "
                    f"filled {repair_stats['pinhole_faces_filled']} pinholes, {len(bm.verts):,} verts left",
                    0.15,
                    extra=repair_stats,
                )

            delimit = {"MATERIAL", "SHARP"}
            if preserve_uv:
                delimit |= {"UV", "SEAM"}
            progress.phase("Dissolving flat regions...", 0.22, force=True)
            dissolved = _dissolve_flat(bm, angle_limit_deg=sharp_angle, delimit=delimit)
            progress.phase(
                f"Dissolved {dissolved:,} verts in flat areas, {len(bm.verts):,} left",
                0.28,
                extra={"dissolved_vertices": dissolved, "verts_after": len(bm.verts)},
            )

            bm.to_mesh(obj.data)
            obj.data.update()
            bm.free()

            post_dissolve_verts = len(obj.data.vertices)

            prepass_stats = None
            if post_dissolve_verts > target_verts * prepass_factor:
                prepass_target = int(target_verts * prepass_factor)
                progress.phase(
                    f"Pre-pass collapse {post_dissolve_verts:,} -> ~{prepass_target:,} vertices...",
                    0.35,
                    force=True,
                )
                prepass_stats = _fast_prepass(obj, prepass_target)
                progress.phase(
                    f"Pre-pass done: {prepass_stats['vertices_before']:,} -> "
                    f"{prepass_stats['vertices_after']:,} verts (ratio {prepass_stats['ratio']})",
                    0.45,
                    extra=prepass_stats,
                )

            if len(obj.data.vertices) > target_verts:
                collapse_stats = _weighted_collapse(
                    obj,
                    target_verts=target_verts,
                    preserve_boundaries=preserve_boundaries,
                    tolerance=tolerance,
                    use_symmetry=use_symmetry,
                    symmetry_axis=symmetry_axis,
                    progress=progress,
                )
                progress.phase(
                    f"Collapsed: {collapse_stats.get('result_vertices', len(obj.data.vertices)):,} verts "
                    f"(ratio {collapse_stats.get('final_ratio')}, {collapse_stats.get('iterations')} iters)",
                    0.88,
                    extra={
                        "iterations": collapse_stats.get("iterations"),
                        "final_ratio": collapse_stats.get("final_ratio"),
                    },
                )
            else:
                collapse_stats = {"applied": False, "iterations": 0}
                progress.phase(
                    f"Collapse skipped: {len(obj.data.vertices):,} verts already at/below target",
                    0.88,
                )

            result_verts = len(obj.data.vertices)

            progress.phase("Measuring surface deviation...", 0.9, force=True)
            deviation = _measure_deviation(
                original_mesh_copy, obj.data, two_sided_max_faces=deviation_two_sided_max_faces
            )
            new_boundary_edges = _count_boundary_edges(obj.data) - analysis["boundary_edges"]
            new_boundary_edges = max(0, new_boundary_edges)
            progress.phase(
                f"Measured: mean {deviation['mean_pct']:.3f}%, max {deviation['max_pct']:.3f}% "
                f"({deviation['sampled_points']} pts, two_sided={deviation['two_sided']}), "
                f"+{new_boundary_edges} boundary edges",
                0.93,
                extra={**deviation, "new_boundary_edges": new_boundary_edges},
            )

            gate = planner.evaluate_quality_gate(
                deviation_max_pct=deviation["max_pct"],
                new_boundary_edges=new_boundary_edges,
                max_deviation_pct=max_deviation_pct,
                allow_new_holes=allow_new_holes,
            )

            if not gate["passed"] and rollback_on_failure:
                progress.phase("Quality gate failed -- rolling back", 1.0, force=True)
                obj.data.clear_geometry()  # release derived data before swapping the mesh block
                obj.data = original_mesh_copy
                obj.data.update()
                suggested_target = planner.suggest_retry_target(target_verts, deviation["max_pct"], max_deviation_pct)
                history = progress.history_payload()
                _save_history_card(
                    progress,
                    status=f"Rolled back {original_verts_count:,} verts [{history['total_seconds']:.1f}s]",
                    completed_summary=(
                        f"Rolled back {original_verts_count:,} verts in {history['total_seconds']:.1f}s "
                        f"-- {gate['reason']}"
                    ),
                    next_steps=[f"Retry with target={suggested_target}"],
                )
                _record_last_run(
                    object_name=object_name,
                    success=False,
                    message=(
                        f"Quality gate failed and '{object_name}' was rolled back to its original {original_verts_count} "
                        f"vertices: {gate['reason']}. Try target={suggested_target}."
                    ),
                    original_vertices=original_verts_count,
                    result_vertices=original_verts_count,
                    target_vertices=target_verts,
                    rolled_back=True,
                    gate_reason=gate["reason"],
                    history=history,
                    suggested_retry_target=suggested_target,
                )
                return {
                    "success": False,
                    "message": (
                        f"Quality gate failed and '{object_name}' was rolled back to its original {original_verts_count} "
                        f"vertices: {gate['reason']}. Try target={suggested_target}, or repair=true / a coarser "
                        f"remesh_mesh pass first if the mesh has extensive non-manifold geometry."
                    ),
                    "object_name": object_name,
                    "original_vertices": original_verts_count,
                    "result_vertices": original_verts_count,
                    "target_vertices": target_verts,
                    "rolled_back": True,
                    "analysis": analysis,
                    "repair": repair_stats,
                    "dissolved_vertices": dissolved,
                    "prepass": prepass_stats,
                    "collapse": collapse_stats,
                    "deviation": deviation,
                    "new_boundary_edges": new_boundary_edges,
                    "gate": gate,
                    "suggested_retry_target": suggested_target,
                    "history": history,
                }

            bpy.data.meshes.remove(original_mesh_copy)
            progress.phase(f"Done: {original_verts_count:,} -> {result_verts:,} vertices", 1.0, force=True)
            history = progress.history_payload()
            _save_history_card(
                progress,
                status=f"Done {original_verts_count:,} -> {result_verts:,} verts [{history['total_seconds']:.1f}s]",
                completed_summary=(
                    f"Simplified {original_verts_count:,} -> {result_verts:,} verts "
                    f"(target {target_verts:,}) in {history['total_seconds']:.1f}s"
                ),
            )
            _record_last_run(
                object_name=object_name,
                success=True,
                message=(
                    f"Simplified '{object_name}' from {original_verts_count} to {result_verts} vertices "
                    f"(target {target_verts}); {gate['reason']}"
                ),
                original_vertices=original_verts_count,
                result_vertices=result_verts,
                target_vertices=target_verts,
                gate_reason=gate["reason"],
                history=history,
            )

            return {
                "success": True,
                "message": (
                    f"Simplified '{object_name}' from {original_verts_count} to {result_verts} vertices "
                    f"(target {target_verts}); {gate['reason']}"
                ),
                "object_name": object_name,
                "original_vertices": original_verts_count,
                "result_vertices": result_verts,
                "target_vertices": target_verts,
                "rolled_back": False,
                "analysis": analysis,
                "repair": repair_stats,
                "dissolved_vertices": dissolved,
                "prepass": prepass_stats,
                "collapse": collapse_stats,
                "deviation": deviation,
                "new_boundary_edges": new_boundary_edges,
                "shape_keys_removed": had_shape_keys,
                "gate": gate,
                "history": history,
            }
        except Exception as exc:
            if rollback_on_failure:
                try:
                    obj.data.clear_geometry()
                    obj.data = original_mesh_copy
                    obj.data.update()
                except Exception:
                    pass
            try:
                progress.phase(f"Failed: {exc}", 1.0, force=True)
                history = progress.history_payload()
                _save_history_card(
                    progress,
                    status=f"Failed after {history['total_seconds']:.1f}s: {exc}",
                    completed_summary=f"Simplify failed after {history['total_seconds']:.1f}s",
                )
            except Exception:
                history = {"total_seconds": 0.0, "steps": []}
            _record_last_run(
                object_name=object_name,
                success=False,
                message=f"simplify_geometry failed: {exc}",
                history=history,
            )
            return {"success": False, "message": f"simplify_geometry failed: {exc}", "history": history}
        finally:
            obj.hide_viewport = prev_hide_viewport
            try:
                obj.hide_set(prev_hidden)
            except Exception:
                pass
            try:
                view_layer.objects.active = prev_active
            except Exception:
                pass


class ShowLastSimplifyCardTool(ToolBase):
    name = "show_last_simplify_card"
    description = (
        "Re-show the previous simplify_geometry run's history card on the viewport HUD "
        "and return it (object, vertex counts, total time, per-step timings, gate verdict). "
        "Fails cleanly when no simplify run has happened yet this session."
    )

    def execute(self, params: dict) -> dict:
        import types as _types

        card = get_last_card()
        if not card:
            return {"success": False, "message": "No simplify_geometry run recorded yet this session"}
        steps = (card.get("history") or {}).get("steps", [])
        shim = _types.SimpleNamespace(
            label=f"Simplify '{card.get('object_name')}' (previous run)",
            history=steps,
        )
        _save_history_card(
            shim,
            status=f"Previous: {card.get('message', '')}"[:120],
            completed_summary=(
                f"Previous: {card.get('original_vertices')} -> {card.get('result_vertices')} verts "
                f"in {card.get('total_seconds', 0.0):.1f}s"
            ),
            next_steps=(
                [f"Retry with target={card['suggested_retry_target']}"]
                if card.get("suggested_retry_target") else []
            ),
        )
        return {
            "success": True,
            "message": f"Re-showing previous simplify card for '{card.get('object_name')}'",
            "card": card,
        }


def _unusable_context(obj):
    """Preconditions the work below silently misbehaves without.

    Writing a bmesh into a mesh that is open in Edit Mode corrupts it, and an
    object outside the active view layer is not evaluated by the depsgraph at
    all -- the ratio solve would read stale geometry and modifier_apply would
    fail into the generic handler as an unexplained rollback.
    """
    if obj.mode != "OBJECT":
        return (
            f"'{obj.name}' is in {obj.mode} mode; simplify_geometry needs Object Mode "
            "(writing to a mesh that is open for editing corrupts it)"
        )
    if obj.name not in bpy.context.view_layer.objects:
        return (
            f"'{obj.name}' is not in the active view layer (its collection is excluded, or it "
            "belongs to another scene); the collapse solve needs it evaluated by the depsgraph"
        )
    return None


def _analyze(obj):
    """Diagnosis of the input mesh: what a caller (and the quality gate) need
    to know before touching anything.

    Edge topology comes from the loop->edge map: every face corner is one
    loop, so counting how many loops reference each edge counts how many
    faces touch it -- two C-level array reads instead of a Python pass over a
    bmesh.
    """
    mesh = obj.data
    face_counts = _edge_face_counts(mesh)
    boundary_edges = int(np.count_nonzero(face_counts == 1))
    non_manifold_edges = int(np.count_nonzero((face_counts != 1) & (face_counts != 2)))

    edge_verts = _edge_vertices(mesh)
    if len(edge_verts):
        used = np.bincount(edge_verts.ravel(), minlength=len(mesh.vertices))
        loose_verts = int(np.count_nonzero(used == 0))
    else:
        loose_verts = len(mesh.vertices)

    exact = len(mesh.vertices) < _ANALYZE_EXACT_LIMIT
    return {
        "vertices": len(mesh.vertices),
        "faces": len(mesh.polygons),
        "bbox_diagonal": round(_bbox_diagonal(mesh), 6),
        "boundary_edges": boundary_edges,
        "non_manifold_edges": non_manifold_edges,
        "loose_vertices": loose_verts,
        # None, not 0: these are skipped on a dense mesh, and 0 would read as
        # "measured, none found".
        "coincident_vertices": _count_coincident(mesh) if exact else None,
        "shells": _count_shells(mesh) if exact else None,
    }


def _vertex_coords(mesh):
    co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", co)
    return co.reshape(-1, 3)


def _edge_vertices(mesh):
    ev = np.empty(len(mesh.edges) * 2, dtype=np.int32)
    mesh.edges.foreach_get("vertices", ev)
    return ev.reshape(-1, 2)


def _edge_face_counts(mesh):
    """Number of faces touching each edge, indexed by edge index."""
    n_loops = len(mesh.loops)
    if n_loops == 0 or len(mesh.edges) == 0:
        return np.zeros(len(mesh.edges), dtype=np.int64)
    edge_idx = np.empty(n_loops, dtype=np.int32)
    mesh.loops.foreach_get("edge_index", edge_idx)
    return np.bincount(edge_idx, minlength=len(mesh.edges))


def _triangle_count(mesh):
    if not len(mesh.polygons):
        return 0
    loop_totals = np.empty(len(mesh.polygons), dtype=np.int32)
    mesh.polygons.foreach_get("loop_total", loop_totals)
    return int(np.maximum(loop_totals - 2, 0).sum())


def _bbox_diagonal(mesh):
    if not len(mesh.vertices):
        return 0.0
    co = _vertex_coords(mesh)
    return float(np.linalg.norm(co.max(axis=0) - co.min(axis=0)))


def _count_boundary_edges(mesh):
    return int(np.count_nonzero(_edge_face_counts(mesh) == 1))


def _boundary_vertex_mask(mesh):
    """Vertices touching an edge that is not shared by exactly two faces --
    hole rims and non-manifold junctions.

    _curvature_weights used to assume these were already covered by its
    "fewer than two incident faces" rule, but a vertex on the rim of a hole
    normally has plenty of faces; only its *edges* are one-sided. That made
    preserve_boundaries a no-op.
    """
    mask = np.zeros(len(mesh.vertices), dtype=bool)
    edge_verts = _edge_vertices(mesh)
    if not len(edge_verts):
        return mask
    open_edges = edge_verts[_edge_face_counts(mesh) != 2]
    if len(open_edges):
        mask[open_edges.ravel()] = True
    return mask


# Absolute distance under which two vertices count as coincident (matches the
# old KDTree find_range radius this replaces).
_COINCIDENT_TOLERANCE = 1e-5


def _count_coincident(mesh):
    """Vertices sitting (near-)exactly on top of another vertex.

    Quantizes every coordinate onto a tolerance-sized lattice and counts
    duplicates per cell with np.unique -- one C-level sort instead of one
    KDTree insert plus one range query per vertex from Python (plus the
    .tolist() conversion feeding them). Straddlers -- two points within
    tolerance landing in adjacent cells -- undercount; acceptable for a
    diagnostic the quality gate never reads.
    """
    coords = _vertex_coords(mesh)
    if len(coords) == 0:
        return 0
    lattice = np.floor(coords / _COINCIDENT_TOLERANCE + 0.5).astype(np.int64)
    _, counts = np.unique(lattice, axis=0, return_counts=True)
    return int(np.sum(counts - 1))


def _count_shells(mesh):
    """Number of connected components over the edge graph.

    Parallel min-label propagation, fully vectorized: every vertex starts
    labelled with its own index; each round pulls every edge endpoint down
    to the smallest label across its incident edges (np.minimum.at, C-level
    scatter-reduce) and then shortcut-jumps all pointers (parent[parent]).
    Labels only ever decrease and are bounded below by 0, so the loop always
    terminates; at the fixpoint the label is constant across each connected
    component (equal to its minimum vertex index -- a strictly decreasing
    chain argument), so distinct labels count the shells. Rounds scale with
    log(diameter) thanks to the jumping. Replaces a per-edge Python
    union-find (plus the .tolist() feeding it): measured ~3x faster
    (58ms -> 18ms at 41k verts), identical counts.
    """
    n_verts = len(mesh.vertices)
    if n_verts == 0:
        return 0

    edges = _edge_vertices(mesh)
    if len(edges) == 0:
        return n_verts

    parent = np.arange(n_verts)
    a = edges[:, 0].astype(parent.dtype, copy=False)
    b = edges[:, 1].astype(parent.dtype, copy=False)
    while True:
        prev = parent.copy()
        np.minimum.at(parent, a, parent[b])
        np.minimum.at(parent, b, parent[a])
        parent = parent[parent]
        if np.array_equal(parent, prev):
            break
    return int(len(np.unique(parent)))


def _repair(bm, weld_factor, diag):
    """Weld coincident verts, drop loose geometry, close pinhole gaps,
    recalc normals. Order matters: welding first is what turns split-at-seam
    shells back into one manifold surface, which is the actual fix for the
    "decimate produces holes" failure mode.
    """
    dist = max(1e-6, weld_factor * diag) if diag > 0 else weld_factor

    before_verts = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=dist)
    welded = before_verts - len(bm.verts)

    loose_verts = [v for v in bm.verts if not v.link_edges]
    if loose_verts:
        bmesh.ops.delete(bm, geom=loose_verts, context="VERTS")

    bmesh.ops.dissolve_degenerate(bm, dist=dist, edges=bm.edges)

    # One pass over the edges collects both lists -- loose-edge deletion used
    # to be its own pass before the dissolve, rim collection another one
    # after it, and dissolving first is what lets the two merge. The dissolve
    # only ever removes degenerate (zero-length/zero-area) geometry, so a
    # loose edge that survives it is still loose and a rim edge still a rim
    # edge; the rim collection still happens post-dissolve exactly as before,
    # so holes_fill sees the identical input.
    loose_edges = []
    boundary_edges = []
    for e in bm.edges:
        faces = e.link_faces
        if not faces:
            loose_edges.append(e)
        elif len(faces) == 1:
            boundary_edges.append(e)
    if loose_edges:
        bmesh.ops.delete(bm, geom=loose_edges, context="EDGES")

    filled = 0
    uv_patched = 0
    if boundary_edges:
        fill_result = bmesh.ops.holes_fill(bm, edges=boundary_edges, sides=4)
        new_faces = fill_result.get("faces", [])
        filled = len(new_faces)
        uv_patched = _restore_uvs_on_filled_faces(bm, new_faces)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)

    return {
        "welded_vertices": welded,
        "loose_vertices_removed": len(loose_verts),
        "loose_edges_removed": len(loose_edges),
        "pinhole_faces_filled": filled,
        "uv_loops_patched": uv_patched,
    }


def _restore_uvs_on_filled_faces(bm, new_faces):
    """Give newly created hole-fill faces real UVs instead of the (0, 0)
    default, which on a textured mesh samples a single wrong-coloured texel
    across the whole patch.

    holes_fill only ever connects existing boundary vertices -- it never
    introduces a new one -- so every corner of a new face is a vertex that
    already carried a UV from one of its *other*, pre-existing faces. Pinhole
    boundaries sit inside one UV island by construction (that is what makes
    them a pinhole rather than a seam), so copying the nearest surviving UV
    for each vertex is exact, not an approximation.
    """
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None or not new_faces:
        return 0

    new_face_set = set(new_faces)
    patched = 0
    for face in new_faces:
        for loop in face.loops:
            for other_loop in loop.vert.link_loops:
                if other_loop.face not in new_face_set:
                    loop[uv_layer].uv = other_loop[uv_layer].uv
                    patched += 1
                    break
    return patched


def _dissolve_flat(bm, angle_limit_deg, delimit):
    """Limited dissolve: removes vertices that carry no shape information
    (flat, dense regions) for free, before any lossy collapse happens."""
    before = len(bm.verts)
    bmesh.ops.dissolve_limit(
        bm,
        angle_limit=math.radians(angle_limit_deg),
        use_dissolve_boundaries=False,
        verts=bm.verts,
        edges=bm.edges,
        delimit=delimit,
    )
    return before - len(bm.verts)


def _curvature_weights(mesh, preserve_boundaries):
    """Per-vertex protection weight in [0, 1] from local curvature: flat
    surfaces score near 0 (safe to collapse), edges/corners/thin features and
    hole rims score near 1.

    Vectorised form of "max angle between a vertex's incident face normals,
    normalised by pi": the mean of k unit normals has length cos(theta/2) in
    the two-face case, so 2*acos(|mean|)/pi reproduces that measure exactly
    where a vertex has two faces and generalises to normal dispersion above
    it -- without the per-vertex O(k^2) Python loop over mathutils angles
    that dominated this function on a dense mesh.

    Normals come from the loop triangles, so an n-gon contributes once per
    triangle it decomposes into; that biases the mean slightly toward larger
    faces, which is the direction you want anyway.
    """
    n_verts = len(mesh.vertices)
    if n_verts == 0:
        return np.zeros(0, dtype=np.float64)

    try:
        mesh.calc_loop_triangles()
    except Exception:
        pass  # 4.1+ computes them on access

    n_tris = len(mesh.loop_triangles)
    if n_tris == 0:
        return np.ones(n_verts, dtype=np.float64)

    tris = np.empty(n_tris * 3, dtype=np.int32)
    mesh.loop_triangles.foreach_get("vertices", tris)
    tris = tris.reshape(-1, 3)

    co = _vertex_coords(mesh)
    normals = np.cross(co[tris[:, 1]] - co[tris[:, 0]], co[tris[:, 2]] - co[tris[:, 0]])
    lengths = np.linalg.norm(normals, axis=1)
    np.divide(normals, lengths[:, None], out=normals, where=lengths[:, None] > 1e-12)

    accumulated = np.stack(
        [
            np.bincount(tris[:, 0], weights=normals[:, axis], minlength=n_verts)
            + np.bincount(tris[:, 1], weights=normals[:, axis], minlength=n_verts)
            + np.bincount(tris[:, 2], weights=normals[:, axis], minlength=n_verts)
            for axis in range(3)
        ],
        axis=1,
    )
    face_counts = np.bincount(tris.ravel(), minlength=n_verts)

    mean_length = np.linalg.norm(accumulated, axis=1) / np.maximum(face_counts, 1)
    weights = 2.0 * np.arccos(np.clip(mean_length, 0.0, 1.0)) / math.pi
    # Loose and single-face vertices carry no reliable curvature signal.
    weights[face_counts < 2] = 1.0
    if preserve_boundaries:
        weights[_boundary_vertex_mask(mesh)] = 1.0
    return np.clip(weights, 0.0, 1.0)


def _write_vertex_group(obj, name, weights):
    """Write per-vertex weights with one RNA call per quantised level.

    VertexGroup.add() takes a list of indices, so bucketing the weights turns
    what used to be one add() per vertex -- over a million of them on a
    generated asset -- into at most _WEIGHT_BUCKETS calls.
    """
    if name in obj.vertex_groups:
        obj.vertex_groups.remove(obj.vertex_groups[name])
    vg = obj.vertex_groups.new(name=name)

    top = _WEIGHT_BUCKETS - 1
    levels = np.clip(np.rint(weights * top).astype(np.int64), 0, top)
    for bucket in range(_WEIGHT_BUCKETS):
        indices = np.flatnonzero(levels == bucket)
        if indices.size:
            vg.add(indices.tolist(), bucket / top, "REPLACE")
    return vg


def _apply_decimate(obj, mod_name):
    """Apply a Decimate modifier by name, always leaving the stack clean."""
    try:
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod_name)
    finally:
        if mod_name in obj.modifiers:
            obj.modifiers.remove(obj.modifiers[mod_name])


def _fast_prepass(obj, target_verts):
    """Unweighted Collapse into range before the form-preserving pass runs.

    Curvature weighting, the ratio solve and the deviation measurement all
    cost time proportional to the mesh handed to them, and generated or
    scanned assets arrive two orders of magnitude above the budget (1.03M
    vertices for a Meshy image-to-3D result against a 30k budget). Getting
    close first with the cheap C-level collapse leaves the expensive,
    form-aware work an input of the size it was designed for. Nothing is
    hidden by this: the quality gate still measures the final result against
    the true original, so a pre-pass that lost a feature still fails.
    """
    before = len(obj.data.vertices)
    ratio = max(0.0001, min(1.0, target_verts / max(1, before)))
    mod = obj.modifiers.new(name="Simplify_Prepass", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.ratio = ratio
    _apply_decimate(obj, mod.name)
    return {
        "vertices_before": before,
        "vertices_after": len(obj.data.vertices),
        "ratio": round(ratio, 5),
    }


def _weighted_collapse(obj, target_verts, preserve_boundaries, tolerance, use_symmetry, symmetry_axis, progress=None):
    """Reduce to target_verts with Decimate Collapse, weighted so flat
    regions give up vertices first and curved/boundary vertices survive.

    Collapse's `ratio` parameter is face-based, so hitting a vertex target
    needs a solve: set a ratio, read what it produced, correct via secant, up
    to _MAX_RATIO_ITERATIONS times, then apply the best ratio tried.

    Each trial reads the evaluated result straight off the depsgraph. The
    previous approach copied the whole mesh into a scratch object and applied
    a modifier per iteration, which cost three full mesh copies and three
    undo-pushing operator calls -- and was wrong besides: vertex *groups* live
    on the object while only their weights live in the mesh, so the scratch
    object never had the protection group, and every trial measured an
    unweighted collapse whose ratio was then applied weighted.
    """
    if progress:
        progress.phase("Computing curvature weights...", 0.5, force=True)
    weights = _curvature_weights(obj.data, preserve_boundaries)
    if progress:
        try:
            import numpy as _np

            mean_w = float(_np.mean(weights)) if len(weights) else 0.0
        except Exception:
            mean_w = 0.0
        progress.phase(
            f"Curvature done: {len(weights):,} weights, mean protection {mean_w:.2f}",
            0.55,
            extra={"vertices": len(weights), "mean_weight": round(mean_w, 3)},
        )

    vg_name = "_SimplifyProtect"
    if progress:
        progress.phase("Writing protection weights...", 0.58, force=True)
    _write_vertex_group(obj, vg_name, weights)
    if progress:
        progress.phase(f"Protection group written ({_WEIGHT_BUCKETS} levels)", 0.59)

    current_verts = len(obj.data.vertices)
    current_faces = len(obj.data.polygons)

    mod = obj.modifiers.new(name="Simplify_Collapse", type="DECIMATE")
    mod.decimate_type = "COLLAPSE"
    mod.vertex_group = vg_name
    mod.vertex_group_factor = 1.0
    mod.invert_vertex_group = True  # calibrated: weight=1.0 otherwise gets MORE decimated, not less
    if use_symmetry:
        mod.use_symmetry = True
        if hasattr(mod, "symmetry_axis"):
            mod.symmetry_axis = symmetry_axis
    mod_name = mod.name

    try:
        depsgraph = bpy.context.evaluated_depsgraph_get()
        ratio = planner.estimate_initial_ratio(current_verts, current_faces, target_verts)
        samples = []
        iterations = 0

        for iterations in range(1, _MAX_RATIO_ITERATIONS + 1):
            if progress:
                progress.phase(
                    f"Solving collapse ratio ({iterations}/{_MAX_RATIO_ITERATIONS}, try {ratio:.4f})...",
                    0.6 + 0.05 * iterations,
                    force=True,
                )
            mod.ratio = ratio
            obj.update_tag()
            depsgraph.update()
            result_verts = len(obj.evaluated_get(depsgraph).data.vertices)
            samples.append((ratio, result_verts))
            if progress:
                progress.phase(
                    f"Solver iter {iterations}: ratio {ratio:.4f} -> {result_verts:,} verts "
                    f"(target {target_verts:,})",
                    0.6 + 0.05 * iterations,
                    extra={"iteration": iterations, "ratio": round(ratio, 5), "result_verts": result_verts},
                )

            if planner.within_tolerance(result_verts, target_verts, tolerance):
                break

            if len(samples) >= 2:
                (r1, v1), (r2, v2) = samples[-2], samples[-1]
                ratio = planner.secant_next_ratio(r1, v1, r2, v2, target_verts)
            else:
                ratio = max(0.0001, min(1.0, ratio * (target_verts / max(1, result_verts))))

        # The *best* sample, not the last one: an unconverged solve ends on
        # its newest guess, which can sit further from the target than an
        # earlier iteration already got.
        best_ratio, best_verts = min(samples, key=lambda sample: abs(sample[1] - target_verts))
        mod.ratio = best_ratio

        if progress:
            progress.phase(f"Applying collapse (ratio {best_ratio:.4f})...", 0.85, force=True)
        _apply_decimate(obj, mod_name)
        if progress:
            progress.phase(
                f"Collapse applied: {len(obj.data.vertices):,} verts (predicted {best_verts:,})",
                0.87,
                extra={"result_vertices": len(obj.data.vertices), "predicted_vertices": best_verts},
            )
    finally:
        if mod_name in obj.modifiers:
            obj.modifiers.remove(obj.modifiers[mod_name])
        if vg_name in obj.vertex_groups:
            obj.vertex_groups.remove(obj.vertex_groups[vg_name])

    return {
        "applied": True,
        "iterations": iterations,
        "final_ratio": round(best_ratio, 4),
        "predicted_vertices": best_verts,
        "result_vertices": len(obj.data.vertices),
        "solver_samples": [[round(r, 5), v] for r, v in samples],
    }


def _sample_points(coords, limit):
    stride = max(1, len(coords) // limit)
    return coords[::stride].tolist()


def _measure_deviation(original_mesh, result_mesh, two_sided_max_faces=_DEVIATION_TWO_SIDED_MAX_FACES):
    """Two-sided surface deviation between the original and simplified mesh,
    as a percentage of the original's bbox diagonal.

    Both directions matter: original->result alone reports 0 for a mesh that
    lost a whole feature (nothing on the result is "far" from a point on a
    thin part removed entirely), and only shows up when measured the other
    way, result->original, i.e. how far the original's surface now is from
    its nearest point on the simplified result.

    The expensive half is the BVH over the *original*: on a million-triangle
    import, building it costs more than every other step here combined. Above
    _DEVIATION_TWO_SIDED_MAX_FACES only the direction that needs the cheap
    BVH (built over the already-reduced result) is measured -- that is the
    lost-feature direction, the one the quality gate exists for -- and the
    result says two_sided=False rather than implying it checked both.
    """
    diag = _bbox_diagonal(original_mesh)
    empty = {"mean_pct": 0.0, "max_pct": 0.0, "sampled_points": 0, "two_sided": False}
    if not len(original_mesh.vertices) or not len(result_mesh.vertices) or diag <= 1e-9:
        return empty

    bm_result = bmesh.new()
    bm_result.from_mesh(result_mesh)
    bvh_result = BVHTree.FromBMesh(bm_result)

    distances = []
    for point in _sample_points(_vertex_coords(original_mesh), _DEVIATION_SAMPLE_LIMIT):
        _, _, _, dist = bvh_result.find_nearest(point)
        if dist is not None:
            distances.append(dist)

    two_sided = len(original_mesh.polygons) <= two_sided_max_faces
    if two_sided:
        bm_orig = bmesh.new()
        bm_orig.from_mesh(original_mesh)
        bvh_orig = BVHTree.FromBMesh(bm_orig)
        for point in _sample_points(_vertex_coords(result_mesh), _DEVIATION_SAMPLE_LIMIT):
            _, _, _, dist = bvh_orig.find_nearest(point)
            if dist is not None:
                distances.append(dist)
        bm_orig.free()

    bm_result.free()

    if not distances:
        return empty

    mean_pct = (sum(distances) / len(distances)) / diag * 100.0
    max_pct = max(distances) / diag * 100.0
    return {
        "mean_pct": round(mean_pct, 4),
        "max_pct": round(max_pct, 4),
        "sampled_points": len(distances),
        "two_sided": two_sided,
    }
