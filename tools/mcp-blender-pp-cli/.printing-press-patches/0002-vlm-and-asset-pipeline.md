# Patch: native asset search/import, VLM scene evaluation, LLM/dictionary renaming

**Date:** 2026-08-21
**Supersedes:** the "known limitation" section of
`0001-websocket-transport.md`, which said these four commands were
unsupported. They are now implemented natively in Go.

**Files touched:**
- `internal/blenderassets/search.go` (new)
- `internal/blenderassets/importer.go` (new)
- `internal/vlm/vlm.go` (new)
- `internal/cli/promoted_search-online-assets.go` (rewritten)
- `internal/cli/promoted_import-online-asset.go` (rewritten)
- `internal/cli/promoted_evaluate-scene-visually.go` (rewritten -- also fixed
  wrong flag names: the generated version used `--camera-name`/`--prompt`/
  `--resolution` from a spec.yaml written against the wrong param names; the
  real tool takes `--question`/`--target-object`/`--view`/`--model`)
- `internal/cli/scene_regen.go` (rewritten)
- `internal/client/client.go` (added `CallBridge` helper)

## Why these needed more than a path-mapping fix

Patch 0001 mapped synthetic REST paths to real Blender bridge method names for
straight passthrough calls. These four commands are different: their real
Python implementation (`mcp_server/src/mcp_blender/tools/asset_source_ops.py`,
`vision_eval_ops.py`, `localization_ops.py`) does work *outside* the bridge --
HTTP calls to Poly Haven/Sketchfab/ambientCG, HTTP calls to OpenRouter -- and
only uses the bridge for the pieces that must run inside Blender (import a
local file, take a screenshot, rename an object). A single path->method
mapping can't express that; each of these needed its own hand-written
orchestration function.

## What each one does now

- **`search-online-assets`** (`internal/blenderassets/search.go`): pure HTTP,
  no bridge call. Ports `search_polyhaven_models` (relevance+popularity
  ranking, no API key), `search_sketchfab_models` (keyless search; a token is
  only needed to *download*), and `search_ambientcg_assets`.
- **`import-online-asset`** (`internal/blenderassets/importer.go`): downloads
  the asset (Poly Haven: lowest-resolution gltf+bin+textures; Sketchfab:
  signed glb URL via `SKETCHFAB_API_TOKEN`), calls the bridge's `import_file`
  (which already does its own axis conversion and orientation-verdict
  analysis -- nothing to reimplement there), then optionally:
  - `--target-poly-budget`: reads each new mesh's vertex count via
    `get_object_info`, computes a proportional per-object target, and calls
    `simplify_geometry` on each (same quality-gate/rollback behavior as the
    standalone `simplify-geometry` command).
  - `--collection-path`: calls `organize_scene_hierarchy` with a single group
    spanning all newly imported objects.
  - `--location` / `--scale-to-size`: calls `set_object_transform` on every
    new object independently (see narrower-port note below).
- **`evaluate-scene-visually`** (rewritten `promoted_evaluate-scene-visually.go`):
  calls `capture_multiview_audit` or `inspect_focus_shot` (view=FOCUS) over
  the bridge, then `vlm.CritiqueImage` sends the PNG to OpenRouter
  (`OPENROUTER_API_KEY`, model default `google/gemini-2.5-flash`, override via
  `--model` or `OPENROUTER_VISION_MODEL`).
- **`scene regen`** (rewritten `scene_regen.go`): the structural rename
  (`regen_element_names`, a keyword-vocabulary pass over collections/Empties)
  is a *pure bridge call* -- no LLM involved for the base case. `--use-vision`
  adds an OpenRouter-assisted pass over mesh leaves the vocabulary can't name,
  via `inspect_focus_shot` + `vlm.CritiqueImage` + `set_object_properties` per
  candidate, capped at `--max-vision-renames` (default 15).

## Narrower than the Python original (documented, not silent)

- `import-online-asset --location`/`--scale-to-size` apply to every newly
  imported object independently, not to one combined bounding box moved/
  scaled as a rigid group. Fine for single-root imports (the common case);
  imprecise for a multi-root import where pieces should move together.
- ambientCG import is not wired (search is, per provider docs ambientCG is
  primarily textures/materials; this port's import path only handles Poly
  Haven and Sketchfab 3D models). Calling `import-online-asset --provider
  ambientcg` returns a clear error instead of attempting a texture import.
- `--reduction-method` other than `simplify` (decimate, remesh) is not wired;
  requesting one returns a `skipped` note in the result rather than an error,
  since the reduction step is optional in the first place.
- `evaluate-scene-visually`'s Go port does not reproduce the Python client's
  vision-incompatible-model auto-retry across a candidate model list; a
  vision-incompatible `--model` surfaces as an error instead of silently
  trying a fallback model.

## Live-verified (not just compiled)

All four were run against a real running Blender session before this patch
was recorded, not just built:
- `search-online-assets --query castle` returned real Poly Haven/ambientCG hits.
- `import-online-asset --asset-id modular_fort_01 --provider polyhaven
  --collection-path "Test/Fort"` downloaded, imported (22 objects), organized
  into a collection with a root empty, and returned an `"verdict": "ok"`
  orientation report -- all against a live Blender instance on
  `ws://127.0.0.1:9876`.
- `evaluate-scene-visually --question "..."` returned a real Gemini 2.5 Flash
  critique of the multiview capture of the imported fort.
- `scene regen --lang it` renamed Light->Luce, Camera->Fotocamera, and every
  `wall`-prefixed mesh to `Parete`-prefixed, via the real
  `regen_element_names` bridge call.

## Regeneration note

A reprint overwrites all five hand-patched command files and drops
`internal/blenderassets/` and `internal/vlm/` references from them (the
packages themselves survive since the generator doesn't touch arbitrary new
directories, but nothing will call into them). Re-apply this patch after a
reprint.
