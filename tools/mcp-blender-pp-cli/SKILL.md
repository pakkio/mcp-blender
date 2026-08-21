---
name: pp-mcp-blender
description: "Printing Press CLI for Mcp Blender."
author: "pakkio"
license: "Apache-2.0"
argument-hint: "<command> [args] | install cli|mcp"
allowed-tools: "Read Bash"
metadata:
  openclaw:
    requires:
      bins:
        - mcp-blender-pp-cli
---

# Mcp Blender — Printing Press CLI

## Prerequisites: Install the CLI

This skill drives the `mcp-blender-pp-cli` binary. **You must verify the CLI is installed before invoking any command from this skill.** If it is missing, install it first:

1. Install via the Printing Press installer. It defaults binaries to `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows:
   ```bash
   npx -y @mvanhorn/printing-press-library install mcp-blender --cli-only
   ```
2. Verify: `mcp-blender-pp-cli --version`
3. Ensure the reported install directory is on `$PATH` for the agent/runtime that will invoke this skill.

If the `npx` install fails before this CLI has a public-library category, install Node or use the category-specific Go fallback after publish.

If `--version` reports "command not found" after install, the runtime cannot see the binary directory on `$PATH`. Do not proceed with skill commands until verification succeeds.



## Command Reference

**assets** — Online asset search (Poly Haven/Sketchfab/ambientCG) and AI text-to-3D generation (Meshy/Tripo/Trellis).

- `mcp-blender-pp-cli assets ai-generate` — 
- `mcp-blender-pp-cli assets asset-browser` — 
- `mcp-blender-pp-cli assets import-online` — 
- `mcp-blender-pp-cli assets search-online` — 

**camera_lighting** — Studio/sun-sky lighting rigs, camera tracking/framing, viewport screenshots, AI visual critique.

- `mcp-blender-pp-cli camera-lighting camera-setup` — 
- `mcp-blender-pp-cli camera-lighting compositor-effects` — 
- `mcp-blender-pp-cli camera-lighting evaluate-scene` — 
- `mcp-blender-pp-cli camera-lighting frame-objects` — 
- `mcp-blender-pp-cli camera-lighting light-setup` — 
- `mcp-blender-pp-cli camera-lighting look-at` — 
- `mcp-blender-pp-cli camera-lighting screenshot` — 
- `mcp-blender-pp-cli camera-lighting studio-lighting` — 
- `mcp-blender-pp-cli camera-lighting sun-sky-rig` — 

**docs** — Query multi-step 3D workflow recipes, parameters, and best practices on demand.

- `mcp-blender-pp-cli docs` — 

**evaluate_scene_visually** — Standalone high-stakes entry point (also reachable via blender_camera_lighting(action=evaluate_scene)). AI visual critique via viewport screenshot + VLM.

- `mcp-blender-pp-cli evaluate-scene-visually` — 

**import_online_asset** — Standalone high-stakes entry point (also reachable via blender_assets(action=import_online)). Import with axis correction and orientation verdicts.

- `mcp-blender-pp-cli import-online-asset` — 

**material** — PBR shading, procedural grunge masks, toon shaders, alpha transparency, triplanar mapping, and material slots.

- `mcp-blender-pp-cli material assign` — 
- `mcp-blender-pp-cli material create` — 
- `mcp-blender-pp-cli material edit-nodes` — 
- `mcp-blender-pp-cli material pbr-setup` — 
- `mcp-blender-pp-cli material procedural-grunge` — 
- `mcp-blender-pp-cli material slots` — 
- `mcp-blender-pp-cli material toon-shader` — 
- `mcp-blender-pp-cli material transparency` — 
- `mcp-blender-pp-cli material triplanar` — 

**mesh** — 3D modeling, transforms, boolean CSG, decimation, voxel remesh, UV unwrap, and modifiers.

- `mcp-blender-pp-cli mesh apply-transform` — 
- `mcp-blender-pp-cli mesh boolean` — 
- `mcp-blender-pp-cli mesh create` — 
- `mcp-blender-pp-cli mesh decimate` — 
- `mcp-blender-pp-cli mesh delete` — 
- `mcp-blender-pp-cli mesh duplicate` — 
- `mcp-blender-pp-cli mesh mesh-op` — 
- `mcp-blender-pp-cli mesh modifier` — 
- `mcp-blender-pp-cli mesh origin-cursor` — 
- `mcp-blender-pp-cli mesh remesh` — 
- `mcp-blender-pp-cli mesh simplify-geometry` — 
- `mcp-blender-pp-cli mesh transform` — 
- `mcp-blender-pp-cli mesh uv-unwrap` — 

**physics_sim** — Rigid body physics, cloth simulation, wind/vortex forces, fluid domain baking, scene physics settings.

- `mcp-blender-pp-cli physics-sim add-force-field` — 
- `mcp-blender-pp-cli physics-sim bake-fluid` — 
- `mcp-blender-pp-cli physics-sim configure-physics` — 
- `mcp-blender-pp-cli physics-sim setup-cloth` — 
- `mcp-blender-pp-cli physics-sim setup-rigid-body` — 

**python_exec** — Direct raw Python execution escape hatch inside Blender.

- `mcp-blender-pp-cli python-exec` — 

**render_pipeline** — Still/animation rendering, PBR texture baking, Unity FBX export, LOD chain generation, VFX tracking.

- `mcp-blender-pp-cli render-pipeline bake-textures` — 
- `mcp-blender-pp-cli render-pipeline export-unity-fbx` — 
- `mcp-blender-pp-cli render-pipeline generate-lods` — 
- `mcp-blender-pp-cli render-pipeline render-anim` — 
- `mcp-blender-pp-cli render-pipeline render-image` — 
- `mcp-blender-pp-cli render-pipeline vfx-shadow-catcher` — 
- `mcp-blender-pp-cli render-pipeline vfx-tracking` — 

**rigging_anim** — Armatures, bone posing, IK rigs, hair curves creation/grooming, animation keyframes, turntable animation.

- `mcp-blender-pp-cli rigging-anim apply-hair-groom` — 
- `mcp-blender-pp-cli rigging-anim create-armature` — 
- `mcp-blender-pp-cli rigging-anim create-hair-curves` — 
- `mcp-blender-pp-cli rigging-anim pose-bone` — 
- `mcp-blender-pp-cli rigging-anim set-keyframe` — 
- `mcp-blender-pp-cli rigging-anim setup-humanoid-rig` — 
- `mcp-blender-pp-cli rigging-anim setup-ik` — 
- `mcp-blender-pp-cli rigging-anim timeline-range` — 
- `mcp-blender-pp-cli rigging-anim turntable` — 

**scene** — Scene inspection, hierarchy organization, checkpoint rollback, orphan purging, and background jobs.

- `mcp-blender-pp-cli scene busy` — 
- `mcp-blender-pp-cli scene checkpoint-create` — 
- `mcp-blender-pp-cli scene checkpoint-list` — 
- `mcp-blender-pp-cli scene checkpoint-restore` — 
- `mcp-blender-pp-cli scene collection` — 
- `mcp-blender-pp-cli scene hierarchy` — 
- `mcp-blender-pp-cli scene info` — 
- `mcp-blender-pp-cli scene job-cancel` — 
- `mcp-blender-pp-cli scene job-list` — 
- `mcp-blender-pp-cli scene job-status` — 
- `mcp-blender-pp-cli scene performance` — 
- `mcp-blender-pp-cli scene purge-orphans` — 
- `mcp-blender-pp-cli scene regen` — 

**search_online_assets** — Standalone high-stakes entry point (also reachable via blender_assets(action=search_online)). Poly Haven, Sketchfab, ambientCG search.

- `mcp-blender-pp-cli search-online-assets` — 

**simplify_geometry** — Standalone high-stakes entry point (also reachable via blender_mesh(action=simplify_geometry)). Repair-then-reduce mesh simplification with quality gate and rollback.

- `mcp-blender-pp-cli simplify-geometry` — 


### Finding the right command

When you know what you want to do but not which command does it, ask the CLI directly:

```bash
mcp-blender-pp-cli which "<capability in your own words>"
```

`which` resolves a natural-language capability query to the best matching command from this CLI's curated feature index. Exit code `0` means at least one match; exit code `2` means no confident match — fall back to `--help` or use a narrower query.

## Auth Setup

No authentication required.

Run `mcp-blender-pp-cli doctor` to verify setup.

## Agent Mode

Add `--agent` to any command. Expands to: `--json --compact --no-input --no-color`.

- **Pipeable** — JSON on stdout, errors on stderr
- **Filterable** — `--select` keeps a subset of fields. Dotted paths descend into nested structures; arrays traverse element-wise. Critical for keeping context small on verbose APIs:

  ```bash
  mcp-blender-pp-cli docs --agent
  ```
- **Previewable** — `--dry-run` shows the request without sending
- **Non-interactive** — never prompts, every input is a flag
- **Explicit confirmation** — `--agent` does not imply `--yes`; pass `--yes` separately only after the target, arguments, and side effects are clear
- **Explicit retries** — use `--idempotent` only when an already-existing create should count as success

## Paths and state

Agents should treat the CLI's path resolver as part of the runtime contract:

- Use `--home <dir>` for one invocation, or set `MCP_BLENDER_HOME=<dir>` to relocate all four path kinds under one root.
- Use per-kind env vars only when a specific kind must diverge: `MCP_BLENDER_CONFIG_DIR`, `MCP_BLENDER_DATA_DIR`, `MCP_BLENDER_STATE_DIR`, `MCP_BLENDER_CACHE_DIR`.
- Resolution order is per-kind env var, `--home`, `MCP_BLENDER_HOME`, XDG (`XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME`), then platform defaults.
- `config` contains settings like `config.toml` and profiles. `data` contains `credentials.toml`, `data.db`, cookies, and auth sidecars. `state` contains persisted queries, jobs, and `teach.log`. `cache` contains regenerable HTTP/cache files.
- Stored secrets live in `credentials.toml` under the data dir. Existing legacy `config.toml` secrets are read for compatibility and leave `config.toml` on the first auth write.
- Run `mcp-blender-pp-cli doctor --fail-on warn` to surface path and credential-location warnings. `agent-context` exposes a schema v4 `paths` block for agents that need the resolved dirs.
- For MCP, pass relocation through the MCP host config. The MCP binary does not inherit CLI flags:

  ```json
  {
    "mcpServers": {
      "mcp-blender": {
        "command": "mcp-blender-pp-mcp",
        "env": {
          "MCP_BLENDER_HOME": "/srv/mcp-blender"
        }
      }
    }
  }
  ```

Fleet precedence: an inherited per-kind env var overrides an explicit `--home` for that kind. Use `MCP_BLENDER_HOME` or per-kind vars as durable fleet levers, and use `--home` only for a single invocation. Relocation is not reversible by unsetting env vars; move files manually before clearing `MCP_BLENDER_HOME`, or `doctor` will not find credentials left under the former root.

## Automatic learning

This CLI ships a self-capturing learning loop. The CLI does its own bookkeeping: every invocation is journaled locally, a failed flag followed by a corrected retry auto-derives a `flag_alias` candidate, and a `teach` on a query family without a playbook auto-synthesizes a `playbook_candidate` from the session's journal. Your job is judgment only: `recall` first, act on surfaced candidates, `teach` the final answer, `playbook amend` when you observe a correction. You never record failures by hand.

### Step 1: `recall` before any discovery

Before list/search/drill commands on a new user question, run:

```bash
mcp-blender-pp-cli recall "<user's question>" --agent
```

The response envelope:

```json
{
  "query": "...",
  "normalized": "<normalized form>",
  "query_entities": ["..."],
  "found": true | false,
  "match_score": 0.0,
  "results": [
    { "resource_id": "...", "resource_type": "...", "venue": "...",
      "confidence": 2, "entity_match": "exact|partial|unknown",
      "source": "taught|preseed|pattern", "warnings": ["..."] }
  ],
  "mismatches": [ /* only when --debug-mismatches */ ],
  "warnings": [ /* top-level */ ],
  "candidates": [
    { "id": 12, "class": "flag_alias | playbook_candidate",
      "summary": "...", "sightings": 3, "last_seen": "...",
      "rationale": "...",
      "next_action": ["<trial command>", "mcp-blender-pp-cli learnings confirm 12"] }
  ],
  "playbook": {
    "query_family": "...",
    "playbook": {
      "steps": [ { "cmd": "<command with {slot} substitution>", "purpose": "..." } ],
      "entity_slots": ["$ENTITY"],
      "expected_tool_calls": 3
    },
    "slots_resolved": { "$ENTITY": { "token": "<live token>", "canonical": "<canonical>" } },
    "notes": "<workarounds + gotchas for this query family>"
  },
  "notes": "<duplicate surface for non-playbook callers>"
}
```

Empty-store short-circuit: if the store has no learnings, playbooks, or candidates yet (recall finds nothing and `learnings list` and `learnings candidates` are both empty), skip recall for the rest of this session instead of taxing every query; resume recall-first once something has been taught.

### Step 2: decision tree

Read `candidates`, `playbook`, `notes`, `results[0]`, and warnings in that order:

```
if Candidates present (warnings include "candidates_present"):
    -> candidates are try-then-confirm, never facts. Follow each candidate's
       two-step next_action verbatim: run the trial command first, then run
       `learnings confirm <id>` only after the trial verified the behavior.
       Reject a wrong candidate with `learnings reject <id>`.
    -> NEVER re-teach something recall surfaced as a candidate; confirm or
       reject that candidate instead of teaching a duplicate.
    -> candidates ride alongside playbooks and resource hits, not instead of
       them; continue with the branches below after acting on them.

if Playbook present:
    -> READ Playbook.notes verbatim FIRST (workarounds + gotchas the CLI surface doesn't expose)
    -> replay Playbook.steps in order, substituting Playbook.slots_resolved entries
       for the entity slot tokens. If a step's slot is unresolved, fall back to
       discovery for that step only.
    -> the Playbook's expected_tool_calls is a budget; if you find yourself running
       materially more, record the divergence via `mcp-blender-pp-cli playbook amend`
       at end-of-session.

elif Notes present (no Playbook):
    -> read Notes verbatim before any discovery step; they carry known gotchas
       for this query family even when no structured choreography exists yet.

elif Found AND Results[0].EntityMatch == "exact" AND Results[0].Confidence >= 2:
    -> skip discovery; fetch live data for Results[*].ResourceID in parallel

elif Found AND Results[0].EntityMatch == "partial":
    -> candidate hint, NOT a hit; read the resource title to validate before trusting

elif (any row in Mismatches[] when --debug-mismatches was passed):
    -> treat as cold start; the stored learning is for a different entity
       (different canonical resolved from query_entities)

else:  // Found == false, no playbook, no notes
    -> cold start; run discovery normally; teach the answer afterward (Step 4).
       If the family has no playbook yet, that teach auto-synthesizes a
       playbook candidate from this session's journal - you do not need to
       record one by hand.
```

Playbook and Notes are orthogonal to the per-resource path. A recall response can carry both a Playbook AND a `Results[]` hit - use both: the Playbook tells you which choreography to run; the resource hits short-circuit specific steps. Default to skipping `mismatches`; pass `--debug-mismatches` only when investigating cold-start surprises.

Candidate judgment details: `learnings confirm <id>` prints the candidate's full payload before materializing it - check that the printed payload matches the behavior you verified. `learnings reject <id>` tombstones the derivation signature so the same candidate does not resurface. The envelope carries only the few candidates worth acting on now; `mcp-blender-pp-cli learnings candidates` lists the full open set.

Graceful degradation: if `learnings confirm` is an unknown command, you are driving an older binary - ignore the candidates guidance and follow the rest of the protocol.

### Step 3: always read `warnings`

- `low_confidence`: row exists at `confidence<2`. Treat as a hint, not a skip-discovery hit.
- `resource_not_in_store`: the local store doesn't have the resource the learning points at. The match validator couldn't classify entities — direct-fetch and re-evaluate.
- `cross_alias_match` (per-result): the row was taught under a different alias and matched the live query's canonical via `entity_lookups` (e.g., a "USA" teach satisfying a "United States" recall). Trust the resource_id.
- `similar_shape_different_entity:<canonical>` (top-level): a structurally matching row exists but its canonical entity differs from the live query's. Treated as cold start; the warning carries the conflicting canonical as a hint, but the row is NOT promoted into Results.
- `ambiguous_alias` (top-level): a single query entity resolved to multiple canonicals (e.g., "Cards" → Arizona Cardinals + St. Louis Cardinals). Surface the ambiguity from context before committing to a resource.
- `candidates_present` (top-level): the envelope carries a `candidates` section. Handle it via the candidates branch in Step 2 before anything else.
- Top-level `no_learnings_for_query_family`: the table had no rows above the Jaccard floor. Pure cold start.

### Step 4: `teach &` after finalizing your response - always

Teaching is unconditional. After resolving a query the store could not answer, background-teach the final resource mapping - no call-count threshold, no judging whether it was "worth" learning. The teach is the anchor of the loop: it triggers playbook synthesis for a family without a playbook, and same-referent phrasings fold into one family so near-duplicate teaches do not fragment the store. Fire it after assembling your user-facing response but BEFORE emitting it, with a shell `&` so the call returns immediately:

```bash
mcp-blender-pp-cli teach --query "<user's question>" --resource-type <type> --resource <id1> --resource <id2>
# (append shell `&` to background it)
```

Silent on success. Errors only land in `teach.log` under the resolved state dir. Teach the **most specific** resource - if the user asked a broad question and you walked through parent records to find the specific answer, teach the leaf id, not the parent. The CLI uses seeded `entity_lookups` for cross-alias resolution at recall time, so a teach under one alias (e.g., "Niners") satisfies future queries under another alias (e.g., "49ers", "San Francisco") automatically.

PII rule: teach the structural question with identifiers stripped - never include names, emails, phone numbers, account ids, or other personal identifiers in taught queries or notes. The CLI scans teach queries for obvious email/phone shapes and warns, but does not block; strip before teaching rather than relying on the warning.

### Step 5: playbooks - optional flags, automatic synthesis

You do not need to decide whether a session "deserves" a playbook: a teach on a family without one auto-synthesizes a `playbook_candidate` from the session's journal, and the next session judges it via confirm/reject. Attach explicit playbook flags only when you already hold choreography worth recording verbatim - workarounds the CLI didn't surface (silently-dropped flags, undocumented params, pagination tricks, payload gotchas). Prefer the **integrated one-call form** - record the resource learning and the playbook in the same `teach` invocation:

```bash
# Common case: record both the resource learning AND the playbook in one call.
mcp-blender-pp-cli teach \
  --query "<user's question>" \
  --resource <id> \
  --playbook-file ~/playbooks/<shape>.json \
  --playbook-notes-file ~/playbooks/<shape>-notes.md
# (append shell `&` to background it)

# Alternate: playbook-only (no resource to record alongside).
mcp-blender-pp-cli teach-playbook \
  --query "<user's question>" \
  --playbook-file ~/playbooks/<shape>.json \
  --notes-file ~/playbooks/<shape>-notes.md
```

Playbook files are JSON with `steps`, `entity_slots`, `expected_tool_calls`. Notes files are markdown carrying the gotchas verbatim. File-free callers (MCP-only agents) pass the same content inline: `--playbook-json` and `--playbook-notes` on the integrated `teach` form, `--playbook-json` and `--notes` on `teach-playbook`. On the integrated `teach` form, the playbook flags are optional - omit them entirely for a resource-only teach. On the standalone `teach-playbook` form, at least one of the playbook and notes flags must be set; both empty is rejected. Playbooks are keyed on the structural query family (entities stripped) so a recipe taught from one entity-shaped query applies to every other query of the same shape, with `slots_resolved` binding the live query's canonical at recall time.

When you DO find a playbook on a future recall, treat it as ground truth: replay the steps with `slots_resolved` substitutions, skip the discovery that the choreography already documents, and read `notes` before any step.

### Step 6: `playbook amend &` when your debug response identifies a correction

If your debug-protocol response identifies a concrete correction the notes or playbook should know — a workaround, an undocumented endpoint shape, a stale field name, observed schema drift, an empty-payload fallback — fire `playbook amend` BEFORE emitting your user-facing response. Same fire-and-forget posture as `teach`.

```bash
mcp-blender-pp-cli playbook amend \
  --query "<exact recall query string>" \
  --add-note "<your concrete correction>"
# (append shell `&` to background it)
```

What counts as worth amending: a behavior you OBSERVED this session that future-you would benefit from knowing. Examples worth amending:

- A workaround for a CLI surface that silently drops or misorders a flag.
- An undocumented endpoint shape (response wrapped in `{meta, results}`, payload nested two levels deeper than the docs claim).
- Observed schema drift (a field renamed, an index that shifted between seasons, a category label that the API now returns lower-cased).

What does NOT belong in notes:

- The year-specific or entity-specific answer to the user's question. That's the response, not a learning.
- Per-team / per-athlete / per-row data the playbook already retrieves at runtime.
- Statements that paraphrase what the existing notes already say.

The amend command appends to the family's existing notes with a timestamped marker (`[amend YYYY-MM-DDTHH:MMZ]: <text>`). Multiple amends accumulate; the audit trail is visible. If no playbook exists yet for the family, amend creates a notes-only one (so cold-start corrections still land).

#### PII discipline for amend notes

`playbook amend` notes are designed to potentially flow upstream as shared knowledge in future versions of the Printing Press. Keep them clean of user-identifying content so the upstream-contribution path stays open without retroactive scrubbing:

- **Do NOT embed** paths to user filesystems, personal API keys or tokens, user email addresses, user GitHub handles, or specific query histories tied to a single user.
- **Acceptable**: endpoint shapes, undocumented field names, API gotchas, observed schema drift, workarounds for CLI surfaces, generalizable pagination or retry tactics.

If a correction is only meaningful with user-specific context, it belongs in a personal note, not in the playbook amend.

### Measuring the loop

`mcp-blender-pp-cli learnings stats` reports recall hit rate, teach-to-reuse, playbook resolution rate, and candidate confirm/reject counts from the local `learn_events` table. Rates are null until they have a denominator; everything stays on this machine. Use it to check whether the loop is earning its keep for this CLI.

### Disabling learning

- `--no-learn` on a single command short-circuits both `recall` and the `teach` write path. Use for deterministic agent flows or tests that must not be affected by accumulated learnings.
- `MCP_BLENDER_NO_LEARN=true` in the environment globally disables the pipeline.

## Agent Feedback

When you (or the agent) notice something off about this CLI, record it:

```
mcp-blender-pp-cli feedback "the --since flag is inclusive but docs say exclusive"
mcp-blender-pp-cli feedback --stdin < notes.txt
mcp-blender-pp-cli feedback list --json --limit 10
```

Entries are stored locally as `feedback.jsonl` under the resolved data dir. They are never POSTed unless `MCP_BLENDER_FEEDBACK_ENDPOINT` is set AND either `--send` is passed or `MCP_BLENDER_FEEDBACK_AUTO_SEND=true`. Default behavior is local-only.

Write what *surprised* you, not a bug report. Short, specific, one line: that is the part that compounds.

## Output Delivery

Every command accepts `--deliver <sink>`. The output goes to the named sink in addition to (or instead of) stdout, so agents can route command results without hand-piping. Three sinks are supported:

| Sink | Effect |
|------|--------|
| `stdout` | Default; write to stdout only |
| `file:<path>` | Atomically write output to `<path>` (tmp + rename) |
| `webhook:<url>` | POST the output body to the URL (`application/json` or `application/x-ndjson` when `--compact`) |

Unknown schemes are refused with a structured error naming the supported set. Webhook failures return non-zero and log the URL + HTTP status on stderr.

## Named Profiles

A profile is a saved set of flag values, reused across invocations. Use it when a scheduled or recurring agent reuses the same saved flags while providing different input each run.

```
mcp-blender-pp-cli profile save briefing --json
mcp-blender-pp-cli --profile briefing docs
mcp-blender-pp-cli profile list --json
mcp-blender-pp-cli profile show briefing
mcp-blender-pp-cli profile delete briefing --yes
```

Explicit flags always win over profile values; profile values win over defaults. `agent-context` lists all available profiles under `available_profiles` so introspecting agents discover them at runtime.

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Usage error (wrong arguments) |
| 3 | Resource not found |
| 5 | API error (upstream issue) |
| 7 | Rate limited (wait and retry) |
| 10 | Config error |

## Argument Parsing

Parse `$ARGUMENTS`:

1. **Empty, `help`, or `--help`** → show `mcp-blender-pp-cli --help` output
2. **Starts with `install`** → ends with `mcp` → MCP installation; otherwise → see Prerequisites above
3. **Anything else** → Direct Use (execute as CLI command with `--agent`)

## MCP Server Installation

Install the MCP binary from this CLI's published public-library entry or pre-built release, then register it:

```bash
claude mcp add mcp-blender-pp-mcp -- mcp-blender-pp-mcp
```

Verify: `claude mcp list`

## Direct Use

1. Check if installed: `which mcp-blender-pp-cli`
   If not found, offer to install (see Prerequisites at the top of this skill).
2. Match the user query to the best command from the Unique Capabilities and Command Reference above.
3. Execute with the `--agent` flag:
   ```bash
   mcp-blender-pp-cli <command> [subcommand] [args] --agent
   ```
4. If ambiguous, drill into subcommand help: `mcp-blender-pp-cli <command> --help`.
