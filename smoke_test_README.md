# Lucineer Smoke Test

**End-to-end integration test for the Lucineer build pipeline.**

This test drives a single message through the entire stack — Worker → Processor →
Brain → Memory → Vector — and asserts the result is a real, named build, not the
"gray box" regression described in [GAP_ANALYSIS.md](../lucineer-system/GAP_ANALYSIS.md) §#1.

It is the single most valuable integration test per the gap analysis "Recommended
Order of Work", step 4:

> *"a repeatable smoke test that drives one message through the entire stack and
> asserts a named part exists at an expected position."*

---

## Quick Start

```bash
# Set the auth key (required)
export LUCINEER_KEY="your-secret-key"

# Run with all defaults (posts "build a small tower" to production Worker)
python3 smoke_test.py

# Custom message
python3 smoke_test.py --message "build me a castle"

# Against local dev Worker
python3 smoke_test.py --worker-url http://localhost:8787

# Skip memory/vector checks (if those services aren't wired yet)
python3 smoke_test.py --skip-memory --skip-vector
```

---

## Requirements

- Python 3.10+ (uses `__future__` annotations and `|` union syntax)
- No external dependencies — uses only `urllib` from the standard library
- The auth key must be set via `--auth-key` or `LUCINEER_KEY` environment variable

---

## Command-Line Arguments

| Argument | Default | Description |
|---|---|---|
| `--worker-url` | `https://lucineer-relay.casey-digennaro.workers.dev` | Worker relay URL |
| `--memory-url` | `https://lucineer-memory.casey-digennaro.workers.dev` | Memory D1 Worker URL |
| `--vector-url` | `https://lucineer-vector.casey-digennaro.workers.dev` | Vectorize Worker URL |
| `--auth-key` | (from `LUCINEER_KEY` env var) | Shared secret for authenticated endpoints |
| `--message` | `build a small tower` | The chat message to send |
| `--timeout` | `120` | Max seconds to wait for job completion |
| `--skip-memory` | — | Skip Phase 4 (memory checks) |
| `--skip-vector` | — | Skip Phase 5 (vector checks) |

---

## What It Tests

### Phase 0: Service Health Checks

Verifies that all three services (Worker, Memory, Vector) are reachable and
responding to `GET /api/health`. If any service is down, the test aborts early
with a clear diagnostic.

**Assertions:**
- Worker responds with `{"status": "ok"}`
- Memory service responds with `{"status": "ok"}`
- Vector service responds with `{"status": "ok"}`

---

### Phase 1: Post Test Message

Simulates a Roblox client sending a chat message. Posts to `POST /api/message`
with `sessionId`, `playerName`, `message`, and a `playerState` containing a
position vector.

**Assertions:**
- Response is HTTP 200
- Response body contains a non-empty `jobId` string

**Failure causes:**
- `400` — missing required fields (check payload shape)
- `429` — rate limit exceeded (wait 60s and retry)
- Network error — Worker is down or unreachable

---

### Phase 2: Poll for Job Result

Simulates the Roblox Poller. Polls `GET /api/job/{jobId}` every 2 seconds up
to the timeout (default 120s). Logs status transitions as they occur.

**Assertions:**
- Job reaches a terminal status (`complete`, `done`, or `completed`) before timeout
- Error status is reported clearly if the job fails

**What status transitions tell you:**
- `submitted → pending` — job is queued, waiting for processor
- `pending → claimed` — processor picked it up (if claiming is implemented)
- `claimed → complete` — normal happy path
- `pending → complete` — processor posted result without claiming (legacy path)
- Stuck at `pending` — processor is not running or can't reach the Worker
- Stuck at `claimed` — processor crashed mid-job; lease must expire

---

### Phase 3: Validate Build Result

The core quality gate. Inspects the completed job's `commands` and `reply`.

**Assertions:**

| # | Assertion | What It Catches |
|---|---|---|
| 3a | Status is `complete`/`done` | Job didn't actually finish |
| 3b | Non-empty `commands` array | Brain/template returned nothing |
| 3c | At least one `createPart` command | Build has no physical parts |
| 3d | **Parts have non-default names (not `LucineerPart`)** | **The gray box bug (GAP_ANALYSIS #1)** — `CommandExecutor` receiving the envelope instead of `params`, causing every fallback to fire |
| 3e | Reply text is non-empty | Lucineer's dialogue was dropped |
| 3f | Commands use envelope structure (`type` + `params`) | Brain or templates emitting flat commands |
| 3g | At least one anchored part | Parts will fall under gravity |
| Warning | All parts at origin `(0,0,0)` | Player position not propagated (GAP_ANALYSIS #4) |

**The gray box check (3d)** is the most critical assertion in the system. It directly
tests the #1 bug from the gap analysis: if `CommandExecutor.createPart` receives the
envelope `{type: "createPart", params: {...}}` instead of the inner `params` table,
every field is `nil`, every fallback fires, and every part becomes:

- Named `LucineerPart`
- At position `(0, 5, 0)`
- Sized `4 × 1 × 4`
- `SmoothPlastic`, color `(180, 180, 180)`

---

### Phase 4: Memory Integration

Checks that `lucineer-memory` (D1) has recorded the interaction.

**Assertions:**
- `GET /api/memory/player/test_player` — profile exists with `bond_level` field
- `GET /api/memory/builds/test_player?limit=5` — at least one build in history

**Failure causes:**
- Memory Worker not wired into the processor (GAP_ANALYSIS #4)
- Auth mismatch between processor and memory Worker
- D1 schema not deployed

---

### Phase 5: Vector Integration

Checks that `lucineer-vector` (Vectorize) is responding to semantic queries.

**Assertions:**
- `POST /api/skills/query` returns HTTP 200 with a `matches` array
- Empty matches are OK (graceful pass) if the index hasn't been seeded yet

**Warnings:**
- If matches are empty, suggests running the skill seeder

---

## Exit Codes

| Code | Meaning |
|---|---|
| `0` | All assertions passed |
| `1` | One or more assertions failed (or services unreachable) |

Use in CI:
```bash
python3 smoke_test.py && echo "✓ All green" || echo "✗ Failures detected"
```

---

## Interpreting Output

Each assertion prints a line:

```
  [✓] PASS — Health: Worker reachable
      HTTP 200, status=ok, service=N/A
```

Failed assertions show in red:

```
  [✗] FAIL — Parts have non-default names (not 'LucineerPart')
      Part names: LucineerPart, LucineerPart, LucineerPart
      ⚠ 3 part(s) named 'LucineerPart' or empty — this is the gray box regression!
```

Warnings are yellow:

```
  ⚠ WARNING — All 3 part(s) are at origin (0,0,0) — player position may not be propagated
```

The final summary:

```
══════════════════════════════════════════════
SMOKE TEST SUMMARY
══════════════════════════════════════════════
  Total assertions: 15
  Passed: 14
  Failed: 1
  Warnings: 1
  Round-trip time: 8.3s
══════════════════════════════════════════════
  Verdict: FAILURES DETECTED
══════════════════════════════════════════════
```

---

## When to Run This

1. **After any change to the Worker, Processor, or Brain** — catches boundary regressions
2. **Before deploying Roblox client changes** — verifies the server-side still works
3. **After deploying a new Worker** — confirms the deployment is live
4. **As part of CI/CD** — gates releases on a green full-stack run
5. **When debugging "nothing happens in game"** — pinpoints exactly which layer failed

---

## Relationship to Other Tests

This smoke test is **complementary** to, not a replacement for:

- **Unit tests** in the Worker (TypeScript) — test individual endpoints
- **Brain tests** in `lucineer-brain/` — test model routing and JSON parsing
- **Studio playtests** — the only true end-to-end test that exercises the Roblox
  client's `CommandExecutor`, `Poller`, and `ChatHandler`

The smoke test covers the **HTTP boundary** between Roblox and the Worker, which
is where the gap analysis found the most contract mismatches. A Studio playtest
remains the gold standard for validating the full experience.
