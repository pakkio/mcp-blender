# Building mcp-blender-pp-cli: a build log

I'm writing this the way I wish more generated-code sessions got written up:
not a changelog, not a design doc, but what actually happened, in order,
including the parts where I was wrong. If you're picking this repo up cold —
human or model — read this before you touch `internal/client/wsbridge_map.go`
or `internal/blenderassets/`. It'll save you from re-discovering three bugs
I already found the hard way.

## The premise

`mcp-blender` exposes 138 Blender automation tools to an LLM over MCP,
aggregated down to 14 low-context "facade" tools for the common case. Someone
asked: can [CLI Printing Press](https://github.com/mvanhorn/cli-printing-press)
— a tool that turns an API spec into a full Go CLI — turn *this* into a
standalone command-line tool? Printing Press is built for REST APIs, GraphQL
endpoints, and scraped websites. mcp-blender is none of those.

That mismatch is the entire story of this build log.

## First wrong assumption: "it's basically a REST API"

I read the MCP tool signatures, wrote a `spec.yaml` that maps the 14 facade
tools to synthetic REST paths (`POST /blender_mesh/create`, etc.), and ran
`printing-press generate`. It worked — cleanly, first try. `go vet`, `go
test`, `go build`, all green. 238 files, working `--help` on every
subcommand.

Then I ran `doctor`:

```
network error (Get "ws://127.0.0.1:9876/": unsupported protocol scheme "ws")
```

Right. mcp-blender's actual transport is a WebSocket bridge
(`extension/bridge/server.py` ↔ `mcp_server/src/mcp_blender/bridge.py`) between
the MCP server and the Blender addon — request/response envelopes over one
persistent connection, not HTTP verbs and status codes. The generator has no
concept of this. Nothing in the generated `internal/client/client.go` could
ever talk to real Blender.

**Lesson:** when you point a spec-driven generator at something that isn't
actually the shape it expects, it will happily generate something that
compiles and is completely non-functional. Passing `go build` is not evidence
of anything except that the Go compiler is satisfied. Test against the real
target before declaring victory — I didn't skip this step, but it's worth
saying loudly because it would have been easy to.

## The fix: a second transport, bolted on deliberately

I didn't try to make the generator understand WebSocket — that's out of
scope for one CLI. Instead: `internal/wsbridge/` is a ~150-line client that
speaks the *actual* protocol (`{"id","method","params"}` in,
`{"id","result"}`/`{"id","error"}` out), and `internal/client/client.go` grew
one branch: if the base URL is `ws://`, skip the entire HTTP machinery
(retries, rate limiting, redirects, the response cache) and hand off to the
bridge client instead. `internal/client/wsbridge_map.go` translates the
spec's synthetic paths back to real Blender method names
(`/blender_mesh/create` → `create_object`), read directly out of
`domain_facades.py`'s `method_map` dicts so there's no guessing.

I verified this against a **hand-rolled mock server** first — a ~20-line
Python script replaying the exact envelope shape from
`extension/bridge/protocol.py` — before touching real Blender. That mock
server came back to bite me later (see below), but as a first correctness
check it was the right call: cheap, fast, no Blender startup cost, and it
caught the protocol shape being right before anything more expensive ran.

## Second wrong assumption: my own spec was accurate

I wrote `spec.yaml` by reading `domain_facades.py`'s docstrings — the
higher-level MCP tool descriptions. I did not cross-check every declared
parameter name against the actual Blender-side tool that receives it. This
came back three separate times:

1. **`simplify_geometry`** — I declared the param `target_verts`. The real
   tool (`extension/tools/simplify_geometry_ops.py`) reads `target`. Wrong
   key = silently ignored = "One of 'target' or 'preset' is required" error
   that took a live test run to surface, not a code review.
2. **`evaluate_scene_visually`** — I declared `camera_name`/`prompt`/
   `resolution`. The real tool takes `question`/`target_object`/`view`/
   `model`. Not close enough to even partially work.
3. **`organize_scene_hierarchy`** — I assumed a flat `collection_path` +
   `object_names` body. The real shape is `{"groups": [{"name", "objects",
   "collection_path"}]}` — a list of group specs, not a flat call.

None of these were caught by `go build`, `go vet`, or `go test`. All three
were caught by running the command against real Blender and reading the
error message. The fix each time was the same shape: read the actual
Python tool source (not the docstring, not my memory of the docstring),
find the literal `params.get(...)` calls, match the CLI to that.

**Lesson:** a docstring is a summary written for a different audience (an
LLM calling the tool via natural-language reasoning) and is not a substitute
for the source of truth (`params.get("exact_key")`). If you're hand-writing
a spec against an existing implementation, grep the implementation for every
param name before you trust the docs.

## Third mistake: my own leftover background process lied to me

Early in testing, I spun up that mock WebSocket server on port 9876 to
verify the protocol shape. Later, when I moved to testing against real
Blender, I killed what I thought was the mock and ran the "100 cones" test.
It passed. I ran `scene info`. It reported a scene with a Cube, Camera, and
Light — the *mock's hardcoded response*, not the real scene.

The mock hadn't died. It was still bound to `127.0.0.1:9876`, silently
shadowing the real Blender bridge that was trying to listen on the same
port. Every "successful" call for a stretch of this session was talking to
a fake server that always says yes.

Once I caught it (by noticing the response never changed no matter what I
did) and killed the actual process, a second problem showed up: `doctor`
*still* reported the bridge as "reachable" for a few minutes after I killed
the mock — because the generated client's HTTP-style response cache had
cached the mock's `bridge_status` reply for 5 minutes, and my WebSocket
patch didn't disable caching (there was no reason to design for a *stateful
local process* using a cache built for *stateless REST resources*).

**Lesson, twice over:** (1) verify you're talking to the thing you think
you're talking to — `netstat`/`Get-NetTCPConnection` and check the PID, don't
just trust that killing a background job worked. (2) A cache is a decision
about staleness tolerance, and that decision was made for the wrong kind of
backend. `--no-cache` is now load-bearing for every connectivity check in
this CLI, and it's called out explicitly in the README because the *default*
behavior lies.

## What worked without a fight

- The `import <resource> --input file.jsonl` batch command, generated for
  free, turned "create 100 cones" from a bash loop into one command once I
  had the transport fixed.
- `mesh delete` with a `names` array deleted 200 test objects in one call.
- `simplify_geometry`'s quality gate (2% surface deviation cap, automatic
  rollback, `suggested_retry_target` on failure) behaved *exactly* like the
  Python docstrings promised, the first time I tested it live, on a
  real 500K-vertex import. That's a nice feeling — reading a spec, believing
  it, and having reality agree.
- When I imported a Sketchfab "Floating Castle" model and couldn't see it in
  a screenshot, I used the CLI's *own* `camera-lighting screenshot` command
  to debug the CLI. Turned out the camera was placed inside a 6.4-meter
  skybox dome enclosing a ~1-meter model — not a bug, just bad framing. Using
  the tool to debug the tool is a good sign the tool is actually usable, not
  just demoable.

## Then: "these three commands don't work" (the second pass)

After the transport was fixed, three commands still just returned "no
Blender bridge equivalent" — `search-online-assets`, `import-online-asset`,
`evaluate-scene-visually`, `scene regen`. That wasn't a bug in the WebSocket
patch; it was an honest boundary: those tools' real implementations
(`mcp_server/src/mcp_blender/tools/asset_source_ops.py`, `vision_eval_ops.py`,
`localization_ops.py`) do HTTP fetching (Poly Haven, Sketchfab, ambientCG)
and OpenRouter vision calls **inside the Python `mcp_server` process**, not
over the Blender bridge at all. A path-to-bridge-method mapping — the fix
that worked for everything else — has nothing to map to here.

So I ported the actual logic to Go instead of leaving the gap documented:

- `internal/blenderassets/`: the search ranking algorithm (relevance +
  log-scaled popularity) and the download-then-`import_file` pipeline,
  ported from the Python source, not reinvented.
- `internal/vlm/`: the OpenRouter chat-completions client for image critique,
  same env vars (`OPENROUTER_API_KEY`, `OPENROUTER_VISION_MODEL`) as the
  Python original, so a user's existing `.env` just works.
- `scene regen`'s realization: the *structural* rename
  (`regen_element_names`) is a pure bridge call with zero LLM involvement —
  only the optional `--use-vision` pass needs OpenRouter. I'd assumed the
  whole command needed an LLM; reading the source showed otherwise, which
  meant most of the command "just worked" once wired to the right bridge
  method, and only the enhancement needed new code.

All four were live-tested against a real Blender session before I called
it done: real Poly Haven search hits, a real 22-object fort import organized
into a collection with a root empty, a real Gemini 2.5 Flash critique of a
multiview screenshot, and real Italian renames (`Light` → `Luce`, `wall_*` →
`Parete_*`) via the actual bridge call.

## What's still narrower than the original, on purpose

Documented in `.printing-press-patches/0002-vlm-and-asset-pipeline.md`, not
hidden:

- `--location`/`--scale-to-size` on import apply per-object, not to one
  combined bounding box moved as a rigid group. Fine for single-root
  imports, imprecise for multi-root ones.
- ambientCG import isn't wired (it's primarily textures/materials; only
  Poly Haven and Sketchfab 3D-model import are implemented).
- `ai_generate` (Meshy/Tripo/Trellis text-to-3D) isn't wired at all.

These aren't bugs I ran out of time to fix — they're scope decisions,
written down so a future session doesn't have to rediscover the boundary by
testing and getting confused, the way I found the WebSocket mismatch by
testing and getting confused.

## The actual lesson, if I had to compress this to one paragraph

Every real bug in this build was caught by running the generated code
against the real target and reading what came back — never by code review,
never by the type checker, never by "this looks right." The type checker
confirmed the code was *internally consistent*; it had no opinion on whether
`target_verts` was a key anyone on the other end was listening for. If
you're extending this CLI, the workflow that found every bug here was:
write the code, run it against live Blender, read the actual error, fix,
repeat. Skipping straight from "it compiles" to "it's done" is how three
wrong parameter names and one zombie mock process would have shipped
unnoticed.

---

*Session commits: `8ef9f8b` (generate + WebSocket transport patch),
`8d9cbe0` (native asset/VLM/regen implementations). Read those diffs
alongside this file, not instead of it — this explains the *why*, the
commits show the *what*.*
