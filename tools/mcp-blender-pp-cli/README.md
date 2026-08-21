# Mcp Blender CLI

> This checkout does not ship a pre-built binary (`mcp-blender-pp-cli.exe` /
> `mcp-blender-pp-cli` is git-ignored). The `npx @mvanhorn/printing-press-library
> install` and "Pre-built binary" paths below assume a published release of
> this CLI, which does not exist for this repo-local fork. Build from source
> instead:

## Build from source

Requires Go 1.26.7+ (see `go.mod`).

```bash
cd tools/mcp-blender-pp-cli
go build -o mcp-blender-pp-cli.exe ./cmd/mcp-blender-pp-cli   # Windows
go build -o mcp-blender-pp-cli ./cmd/mcp-blender-pp-cli       # Linux/macOS

# Optional: the companion MCP server binary
go build -o mcp-blender-pp-mcp.exe ./cmd/mcp-blender-pp-mcp
```

Verify it talks to a running Blender instance (Blender open, mcp-blender
addon's bridge listening on `ws://127.0.0.1:9876` -- check via the addon's
preferences panel):

```bash
./mcp-blender-pp-cli doctor --json --no-cache
```

`--no-cache` matters here: the generated HTTP-style response cache can report
a stale "reachable" verdict for up to 5 minutes after the bridge actually
disconnects. See `.printing-press-patches/0001-websocket-transport.md` for why
this CLI needed a custom WebSocket transport and what it does and doesn't
cover.

---

The sections below are printing-press's generated install docs, written for
this CLI once published to the public library. They don't apply to a
repo-local build; kept for reference / future publishing.

## Install

The recommended path installs both the `mcp-blender-pp-cli` binary and the `pp-mcp-blender` agent skill (Claude Code, Codex, Cursor, Gemini CLI, GitHub Copilot, and other agents supported by the upstream [`skills`](https://github.com/vercel-labs/skills) CLI) in one shot:

```bash
npx -y @mvanhorn/printing-press-library install mcp-blender
```

For CLI only (no skill):

```bash
npx -y @mvanhorn/printing-press-library install mcp-blender --cli-only
```

For skill only — installs the skill into the same agents as the default command above, but skips the CLI binary (use this to update or reinstall just the skill):

```bash
npx -y @mvanhorn/printing-press-library install mcp-blender --skill-only
```

To constrain the skill install to one or more specific agents (repeatable — agent names match the [`skills`](https://github.com/vercel-labs/skills) CLI):

```bash
npx -y @mvanhorn/printing-press-library install mcp-blender --agent claude-code
npx -y @mvanhorn/printing-press-library install mcp-blender --agent claude-code --agent codex
```

### Without Node

The generated install path is category-agnostic until this CLI is published. If `npx` is not available before publish, install Node or use the category-specific Go fallback from the public-library entry after publish.

### Pre-built binary

Download a pre-built binary for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/mcp-blender-current). On macOS, clear the Gatekeeper quarantine: `xattr -d com.apple.quarantine <binary>`. On Unix, mark it executable: `chmod +x <binary>`.

<!-- pp-hermes-install-anchor -->
## Install for Hermes

Install the CLI binary first. The installer writes binaries to a per-user managed bin directory by default: `$HOME/.local/bin` on macOS/Linux and `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows.

```bash
npx -y @mvanhorn/printing-press-library install mcp-blender --cli-only
```

Then install the focused Hermes skill.

From the Hermes CLI:

```bash
hermes skills install mvanhorn/printing-press-library/cli-skills/pp-mcp-blender --force
```

Inside a Hermes chat session:

```bash
/skills install mvanhorn/printing-press-library/cli-skills/pp-mcp-blender --force
```

Restart the Hermes session or gateway if the newly installed skill is not visible immediately.

## Install for OpenClaw
Install both the CLI binary and the focused OpenClaw skill. The installer defaults binaries to a per-user bin directory (`$HOME/.local/bin` on macOS/Linux, `%LOCALAPPDATA%\Programs\PrintingPress\bin` on Windows):

```bash
npx -y @mvanhorn/printing-press-library install mcp-blender --agent openclaw
```

Restart the OpenClaw session or gateway if the newly installed skill is not visible immediately.

## Use with Claude Desktop

This CLI ships an [MCPB](https://github.com/modelcontextprotocol/mcpb) bundle — Claude Desktop's standard format for one-click MCP extension installs (no JSON config required).

To install:

1. Download the `.mcpb` for your platform from the [latest release](https://github.com/mvanhorn/printing-press-library/releases/tag/mcp-blender-current).
2. Double-click the `.mcpb` file. Claude Desktop opens and walks you through the install.

Requires Claude Desktop 1.0.0 or later. Pre-built bundles ship for macOS Apple Silicon (`darwin-arm64`) and Windows (`amd64`, `arm64`); for other platforms, use the manual config below.

<details>
<summary>Manual JSON config (advanced)</summary>

If you can't use the MCPB bundle (older Claude Desktop, unsupported platform), install the MCP binary and configure it manually.


Install the MCP binary from this CLI's published public-library entry or pre-built release.

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mcp-blender": {
      "command": "mcp-blender-pp-mcp"
    }
  }
}
```

</details>

## Quick Start

### 1. Install

See [Install](#install) above.

### 2. Verify Setup

```bash
mcp-blender-pp-cli doctor
```

This checks your configuration.

### 3. Try Your First Command

```bash
mcp-blender-pp-cli docs
```

## Usage

Run `mcp-blender-pp-cli --help` for the full command reference and flag list.

## Paths & environment variables

This CLI separates local files into four path kinds:

| Kind | Contents |
|------|----------|
| `config` | User-editable settings such as `config.toml` and saved profiles |
| `data` | Durable local data such as `data.db` |
| `state` | Runtime state such as persisted queries, jobs, and `teach.log` |
| `cache` | Regenerable HTTP/cache files |

Each kind resolves independently. The ladder is:

1. Per-kind env var: `MCP_BLENDER_CONFIG_DIR`, `MCP_BLENDER_DATA_DIR`, `MCP_BLENDER_STATE_DIR`, or `MCP_BLENDER_CACHE_DIR`
2. `--home <dir>` for this invocation
3. `MCP_BLENDER_HOME` for a flat relocated root
4. XDG env vars: `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_STATE_HOME`, `XDG_CACHE_HOME`
5. Platform defaults matching existing installs

For containers and agent sandboxes, prefer a single relocated root:

```bash
export MCP_BLENDER_HOME=/srv/mcp-blender
mcp-blender-pp-cli doctor
```

Under `MCP_BLENDER_HOME=/srv/mcp-blender`, the four dirs resolve to `/srv/mcp-blender/config`, `/srv/mcp-blender/data`, `/srv/mcp-blender/state`, and `/srv/mcp-blender/cache`.

MCP servers do not receive CLI flags from the host. Put relocation in the host `env` block:

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

Precedence matters in fleets: an ambient per-kind variable such as `MCP_BLENDER_DATA_DIR` overrides an explicit `--home` for that kind. Use `MCP_BLENDER_HOME` or the per-kind variables for durable fleet relocation; treat `--home` as the weaker per-invocation lever.

Relocation is one-way. Unsetting `MCP_BLENDER_HOME` does not move files back to platform defaults, and `doctor` cannot find files left under a former root. Move the files manually before unsetting relocation variables.

Existing installs keep working because the platform-default rung matches the legacy layout. Run `mcp-blender-pp-cli doctor --fail-on warn` to check path warnings in automation.

## Commands

### assets

Online asset search (Poly Haven/Sketchfab/ambientCG) and AI text-to-3D generation (Meshy/Tripo/Trellis).

- **`mcp-blender-pp-cli assets ai-generate`** - 
- **`mcp-blender-pp-cli assets asset-browser`** - 
- **`mcp-blender-pp-cli assets import-online`** - 
- **`mcp-blender-pp-cli assets search-online`** - 

### camera_lighting

Studio/sun-sky lighting rigs, camera tracking/framing, viewport screenshots, AI visual critique.

- **`mcp-blender-pp-cli camera-lighting camera-setup`** - 
- **`mcp-blender-pp-cli camera-lighting compositor-effects`** - 
- **`mcp-blender-pp-cli camera-lighting evaluate-scene`** - 
- **`mcp-blender-pp-cli camera-lighting frame-objects`** - 
- **`mcp-blender-pp-cli camera-lighting light-setup`** - 
- **`mcp-blender-pp-cli camera-lighting look-at`** - 
- **`mcp-blender-pp-cli camera-lighting screenshot`** - 
- **`mcp-blender-pp-cli camera-lighting studio-lighting`** - 
- **`mcp-blender-pp-cli camera-lighting sun-sky-rig`** - 

### docs

Query multi-step 3D workflow recipes, parameters, and best practices on demand.

- **`mcp-blender-pp-cli docs`** - 

### evaluate_scene_visually

Standalone high-stakes entry point (also reachable via blender_camera_lighting(action=evaluate_scene)). AI visual critique via viewport screenshot + VLM.

- **`mcp-blender-pp-cli evaluate-scene-visually`** - 

### import_online_asset

Standalone high-stakes entry point (also reachable via blender_assets(action=import_online)). Import with axis correction and orientation verdicts.

- **`mcp-blender-pp-cli import-online-asset`** - 

### material

PBR shading, procedural grunge masks, toon shaders, alpha transparency, triplanar mapping, and material slots.

- **`mcp-blender-pp-cli material assign`** - 
- **`mcp-blender-pp-cli material create`** - 
- **`mcp-blender-pp-cli material edit-nodes`** - 
- **`mcp-blender-pp-cli material pbr-setup`** - 
- **`mcp-blender-pp-cli material procedural-grunge`** - 
- **`mcp-blender-pp-cli material slots`** - 
- **`mcp-blender-pp-cli material toon-shader`** - 
- **`mcp-blender-pp-cli material transparency`** - 
- **`mcp-blender-pp-cli material triplanar`** - 

### mesh

3D modeling, transforms, boolean CSG, decimation, voxel remesh, UV unwrap, and modifiers.

- **`mcp-blender-pp-cli mesh apply-transform`** - 
- **`mcp-blender-pp-cli mesh boolean`** - 
- **`mcp-blender-pp-cli mesh create`** - 
- **`mcp-blender-pp-cli mesh decimate`** - 
- **`mcp-blender-pp-cli mesh delete`** - 
- **`mcp-blender-pp-cli mesh duplicate`** - 
- **`mcp-blender-pp-cli mesh mesh-op`** - 
- **`mcp-blender-pp-cli mesh modifier`** - 
- **`mcp-blender-pp-cli mesh origin-cursor`** - 
- **`mcp-blender-pp-cli mesh remesh`** - 
- **`mcp-blender-pp-cli mesh simplify-geometry`** - 
- **`mcp-blender-pp-cli mesh transform`** - 
- **`mcp-blender-pp-cli mesh uv-unwrap`** - 

### physics_sim

Rigid body physics, cloth simulation, wind/vortex forces, fluid domain baking, scene physics settings.

- **`mcp-blender-pp-cli physics-sim add-force-field`** - 
- **`mcp-blender-pp-cli physics-sim bake-fluid`** - 
- **`mcp-blender-pp-cli physics-sim configure-physics`** - 
- **`mcp-blender-pp-cli physics-sim setup-cloth`** - 
- **`mcp-blender-pp-cli physics-sim setup-rigid-body`** - 

### python_exec

Direct raw Python execution escape hatch inside Blender.

- **`mcp-blender-pp-cli python-exec`** - 

### render_pipeline

Still/animation rendering, PBR texture baking, Unity FBX export, LOD chain generation, VFX tracking.

- **`mcp-blender-pp-cli render-pipeline bake-textures`** - 
- **`mcp-blender-pp-cli render-pipeline export-unity-fbx`** - 
- **`mcp-blender-pp-cli render-pipeline generate-lods`** - 
- **`mcp-blender-pp-cli render-pipeline render-anim`** - 
- **`mcp-blender-pp-cli render-pipeline render-image`** - 
- **`mcp-blender-pp-cli render-pipeline vfx-shadow-catcher`** - 
- **`mcp-blender-pp-cli render-pipeline vfx-tracking`** - 

### rigging_anim

Armatures, bone posing, IK rigs, hair curves creation/grooming, animation keyframes, turntable animation.

- **`mcp-blender-pp-cli rigging-anim apply-hair-groom`** - 
- **`mcp-blender-pp-cli rigging-anim create-armature`** - 
- **`mcp-blender-pp-cli rigging-anim create-hair-curves`** - 
- **`mcp-blender-pp-cli rigging-anim pose-bone`** - 
- **`mcp-blender-pp-cli rigging-anim set-keyframe`** - 
- **`mcp-blender-pp-cli rigging-anim setup-humanoid-rig`** - 
- **`mcp-blender-pp-cli rigging-anim setup-ik`** - 
- **`mcp-blender-pp-cli rigging-anim timeline-range`** - 
- **`mcp-blender-pp-cli rigging-anim turntable`** - 

### scene

Scene inspection, hierarchy organization, checkpoint rollback, orphan purging, and background jobs.

- **`mcp-blender-pp-cli scene busy`** - 
- **`mcp-blender-pp-cli scene checkpoint-create`** - 
- **`mcp-blender-pp-cli scene checkpoint-list`** - 
- **`mcp-blender-pp-cli scene checkpoint-restore`** - 
- **`mcp-blender-pp-cli scene collection`** - 
- **`mcp-blender-pp-cli scene hierarchy`** - 
- **`mcp-blender-pp-cli scene info`** - 
- **`mcp-blender-pp-cli scene job-cancel`** - 
- **`mcp-blender-pp-cli scene job-list`** - 
- **`mcp-blender-pp-cli scene job-status`** - 
- **`mcp-blender-pp-cli scene performance`** - 
- **`mcp-blender-pp-cli scene purge-orphans`** - 
- **`mcp-blender-pp-cli scene regen`** - 

### search_online_assets

Standalone high-stakes entry point (also reachable via blender_assets(action=search_online)). Poly Haven, Sketchfab, ambientCG search.

- **`mcp-blender-pp-cli search-online-assets`** - 

### simplify_geometry

Standalone high-stakes entry point (also reachable via blender_mesh(action=simplify_geometry)). Repair-then-reduce mesh simplification with quality gate and rollback.

- **`mcp-blender-pp-cli simplify-geometry`** - 


### Self-learning loop

This CLI caches per-question discovery so repeat queries skip the walk and structurally similar queries get answered via entity substitution. The loop also self-captures: every invocation is journaled locally, and failed-flag corrections plus fresh teaches surface as candidates on the next `recall` for confirm/reject judgment. Agents call `recall` before discovery and fire `teach &` after answering. See the `## Automatic learning` section in `SKILL.md` for the full protocol.

- **`mcp-blender-pp-cli recall <query>`** - Look up cached resources for a query before running discovery
- **`mcp-blender-pp-cli teach`** - Record a query -> resource mapping (silent on success, safe to background with `&`)
- **`mcp-blender-pp-cli learnings list`** - Inspect taught rows
- **`mcp-blender-pp-cli learnings forget <query>`** - Undo a teach
- **`mcp-blender-pp-cli learnings candidates`** - List auto-captured candidates awaiting confirm/reject
- **`mcp-blender-pp-cli learnings stats`** - Local loop metrics: recall hit rate, teach-to-reuse, playbook resolution, candidate counts
- **`mcp-blender-pp-cli teach-pattern`** - Install a query/resource template up front
- **`mcp-blender-pp-cli teach-lookup`** - Add an entity mapping (e.g. country code, team alias) for pattern substitution

Pass `--no-learn` or set `MCP_BLENDER_NO_LEARN=true` to disable the loop for deterministic flows.

The local store's schema version stamp is one-way: once this version of `mcp-blender-pp-cli` opens the database, older binaries refuse it with a version error — upgrade the binary rather than downgrading.

## Output Formats

```bash
# Human-readable table (default in terminal, JSON when piped)
mcp-blender-pp-cli docs

# JSON for scripting and agents
mcp-blender-pp-cli docs --json
# Filter to specific fields by name
mcp-blender-pp-cli docs --json --select <field>[,<field>...]

# Dry run — show the request without sending
mcp-blender-pp-cli docs --dry-run

# Agent mode — JSON + compact + no prompts in one flag
mcp-blender-pp-cli docs --agent
```

## Agent Usage

This CLI is designed for AI agent consumption:

- **Non-interactive** - never prompts, every input is a flag
- **Pipeable** - `--json` output to stdout, errors to stderr
- **Filterable** - `--select <field>[,<field>...]` returns only fields you need
- **Previewable** - `--dry-run` shows the request without sending
- **Explicit retries** - add `--idempotent` to create retries when a no-op success is acceptable
- **Explicit confirmation** - `--agent` does not imply `--yes`; pass `--yes` separately only after the target, arguments, and side effects are clear
- **Piped input** - write commands can accept structured input when their help lists `--stdin`
- **Agent-safe by default** - no colors or formatting unless `--human-friendly` is set

Exit codes: `0` success, `2` usage error, `3` not found, `5` API error, `7` rate limited, `10` config error.

## Health Check

```bash
mcp-blender-pp-cli doctor
```

Verifies configuration and connectivity to the API.

## Configuration

Run `mcp-blender-pp-cli doctor` to see the resolved config, data, state, and cache directories. The platform-default config path is ``; `--home`, `MCP_BLENDER_HOME`, and per-kind env vars can relocate it.

Static request headers can be configured under `headers`; per-command header overrides take precedence.

## Troubleshooting
**Not found errors (exit code 3)**
- Check the resource ID is correct
- Run the `list` command to see available items

---

Generated by [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press)
