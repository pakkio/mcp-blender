# Patch: WebSocket transport for the Blender bridge

**Date:** 2026-08-21
**Files touched:**
- `internal/wsbridge/wsbridge.go` (new)
- `internal/client/wsbridge_map.go` (new)
- `internal/client/client.go` (modified: import, `doInternal` branch, `doWebSocketBridge`, `unwrapBridgeParams`, `renameBridgeKeys`)
- `go.mod` / `go.sum` (added `github.com/gorilla/websocket`)

## Why

mcp-blender's real transport is a local WebSocket bridge between the MCP server
and the Blender addon (`ws://127.0.0.1:9876`, see
`extension/bridge/server.py` / `mcp_server/src/mcp_blender/bridge.py` in the
main repo) -- not a REST HTTP API. The generator's default client is HTTP-only,
so `spec.yaml` here models the 14 aggregated-mode MCP tools as synthetic REST
paths purely to get scaffolding, then this patch replaces the actual wire call.

## What it does

- `doInternal` in `client.go` detects `ws://`/`wss://` base URLs and calls
  `doWebSocketBridge` instead of doing an HTTP round-trip. Dry-run and
  verify-mode short-circuits (both HTTP-agnostic) still run first, unchanged.
- `doWebSocketBridge` maps the request path to the real Blender-side method
  name via `bridgeMethodByPath` (mirrors the `method_map` dicts in
  `mcp_server/src/mcp_blender/tools/domain_facades.py`), applies the
  `HEAVY_REQUEST_TIMEOUT_S`-equivalent 600s timeout for bake/render/remesh/
  simplify paths, and calls `wsbridge.Call`.
- `wsbridge.Call` dials fresh per call (the CLI is one-shot, unlike the
  persistent MCP server), sends `{"id","method","params"}`, and returns the
  `result` or `error` field of the matching response envelope.
- `unwrapBridgeParams` reconciles this CLI's two generated body shapes
  (`--stdin` = already-structured JSON; `--params` = one string flag wrapped
  as `{"params": "<string>"}`) into the flat kwargs dict the bridge expects.
- `renameBridgeKeys` fixes wire-name mismatches between `spec.yaml` (hand-written
  from `domain_facades.py` docstrings) and the real Blender-side param names.
  Currently one entry: `simplify_geometry` reads `target`, not `target_verts`
  (discovered by live-testing against a real Blender session -- the wrong key
  was silently ignored and the tool errored "One of 'target' or 'preset' is
  required"). Add further entries here if more mismatches surface.

## Known limitations (by design, not bugs)

- `search-online-assets`, `import-online-asset`, `blender_assets(ai_generate,
  import_online)`, `evaluate-scene-visually`, and `scene regen` are NOT wired
  to the WebSocket bridge. Their real implementation runs inside the Python
  `mcp_server` process (HTTP fetch to Poly Haven/Sketchfab/ambientCG/Meshy/
  Tripo, a VLM call, or an LLM call) -- not a pure Blender bridge method.
  Calling these commands returns a clear error naming the reason instead of a
  silent no-op.
- The `--params` flag (as opposed to `--stdin`) only round-trips values that
  are themselves valid JSON once parsed out of the wrapper string; a
  non-JSON string falls back to `{"params": "<string>"}}`, which is wrong for
  most bridge methods. Prefer `--stdin` with a real JSON body for anything
  beyond trivial single-string params.
- HTTP-only client features (response cache, rate limiting, retries,
  redirects) do not apply over this transport and are bypassed entirely, not
  reimplemented for WebSocket. The response cache in particular can return a
  stale `bridge_status` "reachable" verdict after a bridge disconnects within
  its 5-minute TTL -- always pass `--no-cache` when checking live
  connectivity/state during interactive debugging.

## Regeneration note

A reprint (`/printing-press-reprint mcp-blender` or a fresh `generate` run)
will overwrite `internal/client/client.go` and drop the branch above. Re-apply
this patch (or extend `spec.yaml`'s `mcp:` block with a documented custom
transport, if the generator ever grows first-class WebSocket support) before
treating a reprint as a drop-in replacement.
