# TODO

Open work following the simplify_geometry audit (commit `321a6b0`, which fixed
the ratio-solver bug, the per-vertex Python hot spots, the missing progress
feedback, and put the providers' own remeshers into both pipelines).

Ordered roughly by value.

## 1. Verify the fix on the real workload

Never actually measured end-to-end. The 78 MB / 1,033,549-vertex Meshy cat is
still on disk at `%TEMP%\mcp_blender_assets\meshy\img_e42060ad4b6a\model.glb`;
a benchmark script sits in the session scratchpad but was not run.

- [ ] Time `simplify_geometry` on that GLB at a 50k budget, before vs after.
- [ ] Confirm the HUD actually ticks through the phases in the real UI (the
      headless path disables it via `bpy.app.background`, so tests prove nothing
      here).
- [ ] Confirm the texture survives: UV layers and material intact after the
      pre-pass + collapse.

## 2. The freeze is shorter, not cancellable

`MCP_OT_ai_generate.modal()` still calls `super_import` in one blocking shot
(`extension/panels/viewport_panel.py`), so download → import → simplify happens
between two event-loop ticks. Esc does nothing during it.

- [ ] Split the post-generation work across modal timer ticks (import →
      per-object simplify → normalize) so Esc works and the HUD repaints
      naturally instead of via forced `wm.redraw_timer` swaps.

## 3. `holes_fill` produces UV-less patches

`_repair()` closes pinholes with `bmesh.ops.holes_fill`, and the new faces have
no UVs — on the textured glTF assets this tool is documented for, those patches
sample UV (0,0) and render as a flat wrong-coloured spot.

- [ ] Interpolate UVs onto filled faces, or skip hole-filling when the mesh has
      a UV layer and report that it was skipped.

## 4. "Untextured" was the viewport, not the asset

A model that arrives with a baseColor texture still shows up grey in Solid
shading, which is what made the generated cat look broken.

- [ ] Switch the viewport to Material Preview after a successful textured
      import, and/or report "textured: yes" in the completion message.

## 5. `target_poly_budget` means two different things

`domain_facades.py` passes `target_vertices` into `import_online_asset` as
`target_poly_budget`, which `asset_source_ops.py` documents and treats as a
*triangle* budget (it converts back to vertices per-object by tri/vert ratio).
A 50k vertex request therefore lands as a ~25k vertex target.

- [ ] Pick one unit, name it accordingly, and fix the conversion at the boundary.

## 6. Text-to-3D gets no server-side budget

Only the image-to-3D endpoints take a polygon budget so far. Meshy text-to-3D
goes through `/v2/text-to-3d` (preview + refine), Tripo through `text_to_model`.

- [ ] Check whether either accepts a polycount/face limit on the current API
      version, and wire it up the same way if so.

## 7. Docs are stale on the new default

The vertex budget default is now 50k in the panel, `super_import`, and the
facade, but `import_online_asset`'s description still advertises "10k
background props, 30k hero props, 100k ceiling", and `simplify_geometry_planner`
still presets `BACKGROUND=10_000 / HERO=30_000 / MAX=100_000`.

- [ ] Reconcile the presets and the tool descriptions with the new default.

## 8. Live test coverage for the new behaviour

The 66 live tests pass, but none of them exercise what changed.

- [ ] Pre-pass path: a mesh far above budget reduces correctly and the gate
      still measures against the true original.
- [ ] `preserve_boundaries=True` actually protects a hole rim now.
- [ ] The solver applies the best sample, not the last, when it does not
      converge inside `_MAX_RATIO_ITERATIONS`.

## 9. Unrelated hangs found while diagnosing this one

Both are the same shape as the original bug — heavy work on the main thread
with no bound — and neither is fixed.

- [ ] `capture_multiview_audit` (`extension/tools/vision_feedback_ops.py`)
      stitches its contact sheet with a per-pixel nested Python loop over
      `list(img.pixels)`, and `shading_mode="RENDERED"` runs four full renders.
      Vectorise with `foreach_get`/`foreach_set`, refuse RENDERED above a poly
      budget, and give it `HEAVY_REQUEST_TIMEOUT_S` on the MCP side — it
      currently gets the 15 s default, so it times out client-side and invites
      retries that queue *more* renders behind the frozen one.
- [ ] `render_scene` (`extension/tools/render_ops.py`) uses whatever engine,
      sample count and resolution the scene happens to carry, with no cap and
      no cancellation.
- [ ] `bridge/dispatch.py` never discards a request whose client already timed
      out (`_generation` only bumps on addon reload), so retries pile up behind
      a blocked main thread.

## 10. Unverified assumptions in what was just shipped

Gaps in the evidence, not known bugs — each is a thing that passed review and
tests but was never confirmed against the real thing.

- [ ] `should_remesh` / `target_polycount` (Meshy) and `face_limit` (Tripo) are
      exercised only against mocked HTTP in the test suite. Nobody has watched a
      real generation come back at the requested budget, and an unknown field
      could be silently ignored rather than rejected.
- [ ] The curvature weight is a new formula: `2*acos(|mean normal|)/pi`. It
      reproduces the old "max angle between incident face normals" exactly for a
      two-face vertex and generalises to normal dispersion above that, but the
      old behaviour on high-valence vertices is only equivalent in spirit, not
      identically.
- [ ] Live tests were run on Blender 5.2 and 4.1.1; the manifest targets 4.2+,
      which was not run. `mesh.loops.foreach_get("edge_index")` and
      `calc_loop_triangles()` are the version-sensitive calls.
- [ ] `_PREPASS_FACTOR = 8`, `_WEIGHT_BUCKETS = 64` and
      `_DEVIATION_TWO_SIDED_MAX_FACES = 400_000` are reasoned guesses, not
      measured thresholds, and none are exposed as parameters.
