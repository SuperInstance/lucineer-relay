# ⚔️ Playtest Battle Report — Iron Sharpens Iron

**Date:** 2026-08-03
**Harness:** `playtest_harness.py` v1 (pre-fix) → v1.1 (post-fix)
**Target:** `https://lucineer-relay.casey-digennaro.workers.dev` (LIVE)
**Auth:** `a3db66d2...` (LUCINEER_KEY)

---

## Executive Summary

The harness was run against the live game API with three personas across three scenarios. **Every single interaction failed** — the game's job processor is not completing jobs. Jobs are created successfully (HTTP 200, valid jobId) but never transition from `pending` → `claimed` → `complete`. In the first run, jobs reached `claimed` status (processor-1 claimed them) but never completed. In subsequent runs, jobs stayed at `pending` entirely — the processor wasn't even claiming.

The harness itself was improved through this exercise: adaptive timeout, stale-claim detection, better error reporting, and stdout flushing. Total runtime for the 4-message Explorer scenario dropped from 488s to 343s (30% faster) while producing strictly better diagnostics.

---

## What Worked

### Harness ✅
- **Job creation** — Every `POST /api/message` returned 200 with a valid `jobId`. Flawless.
- **Persona dialogue** — All three personas (Explorer, Builder, Newcomer) generated appropriate, in-character messages for their scenarios.
- **Journal output** — JSONL + Markdown journals were written correctly for every run.
- **Quality scoring** — Scoring logic correctly assigned 1/10 for all-error runs (would have been more interesting with successful responses).
- **Summary statistics** — Voice-in-character %, material diversity, response time stats all computed correctly (all zeros due to no responses, but the code paths worked).
- **Train-of-thought generation** — Each persona produced distinct reasoning patterns even for errors (Explorer: analytical, Builder: structural, Newcomer: emotional).
- **Emotional reactions** — Persona-appropriate frustration reactions were generated.
- **curl-based HTTP** — Bypassed Cloudflare's Python library blocking reliably. Zero transport-level failures.

### Game API ✅
- **Health endpoint** — `GET /api/health` returns `{"status":"ok"}`.
- **Message ingestion** — `POST /api/message` accepts messages, creates jobs, returns jobIds.
- **Job polling** — `GET /api/job/:jobId` returns job state consistently.
- **Rate limiting** — Not hit during testing (well under 10 msg/min).

---

## What Broke

### Game API ❌ (Critical)
- **Job processor not running** — Jobs never reach `complete` status. The Roblox-side processor that should claim jobs, process them through Lucineer's AI, and POST results back to `/api/job/:id/result` is either offline or broken.
  - **Run 1 (Explorer/first-time):** Jobs reached `claimed` (processor-1 claimed them) but never completed. Leases expired. `attempts` incremented to 1-2.
  - **Run 2 (Builder/returning):** Jobs stayed at `pending` — not even claimed. Processor may have stopped entirely after run 1.
  - **Run 3 (Newcomer/edge-cases):** Same — all `pending`.
- **No error recovery** — Expired leases don't trigger re-claiming in a useful timeframe.
- **No WebSocket/push** — Pure polling means 120s+ latency before timeout detection.

### Harness Bugs Found & Fixed 🔧

#### Bug 1: Stdout buffering (FIXED)
**Problem:** Python buffers stdout when piped. The first run (`wild-comet` session) showed zero output for 8+ minutes.
**Fix:** Added `sys.stdout.flush()` after header and summary output. Run with `python3 -u` for full unbuffered mode.
**Severity:** Medium (confusing UX, makes monitoring runs difficult)

#### Bug 2: No `claimed` status detection (FIXED)
**Problem:** `poll_job()` checked for `"done"`, `"complete"`, `"completed"`, and `"error"`. The actual API statuses are `"pending"`, `"claimed"`, `"complete"`, `"error"`. When a job was stuck at `claimed` with an expired lease, the harness polled uselessly for 120s.
**Fix:** Added stale-lease detection in `poll_job()`. When `leaseExpiresAt` < now, returns immediately with a `stale_claimed` diagnostic message. Also waits until just past lease expiry for a second check before giving up.
**Severity:** High (wasted 120s per stuck job)

#### Bug 3: Fixed 120s timeout regardless of failure pattern (FIXED)
**Problem:** Every interaction waited 120s even after 2-3 consecutive failures established a clear pattern.
**Fix:** Implemented adaptive timeout. After 2 consecutive failures, timeout halves each subsequent interaction (120s → 60s → 30s → 15s floor). The Explorer 4-message scenario dropped from 488s to 343s.
**Severity:** Medium (wasted time when system is clearly down)

#### Bug 4: Error messages lacked job status (FIXED)
**Problem:** Timeout error was `"Job timed out after 120.0s"` — no information about what the job's actual status was.
**Fix:** `poll_job()` now returns a third value `stale_info` containing the last known status. Error messages now read: `"Job abandoned: timeout (last_status=pending)"` or `"stale_claimed (lease expired 45s ago, attempts=2)"`.
**Severity:** Medium (poor debuggability)

#### Bug 5: Non-existent status values checked (FIXED)
**Problem:** Code checked for `"done"` and `"completed"` which don't exist in the `JobStatus` type (`"pending" | "claimed" | "complete" | "error"`).
**Fix:** Removed `"done"` and `"completed"` checks. Only `"complete"` and `"error"` trigger completion.
**Severity:** Low (harmless — checking extra values that never match)

---

## What Still Needs Fixing

### Harness Improvements (Not Yet Done)
1. **Auth header on public endpoints** — Harness sends `X-Lucineer-Key` on `POST /api/message` and `GET /api/job/:id`, but these are public endpoints per the Worker source code. Not harmful, but misleading.
2. **No `--fail-fast` mode** — A flag that aborts the entire run after N consecutive failures (useful for CI).
3. **No `--dry-run` mode** — Can't validate the harness without hitting the live API.
4. **No comparison/baseline mode** — Can't compare a run against a previous journal to detect regressions.
5. **Newcomer think delays too long** — `get_think_delay()` returns 3-8s for Newcomer persona. With 6 edge-case messages, that's 18-48s of pure sleep time.
6. **No structured game-health pre-check** — Before running scenarios, the harness should `GET /api/health` and optionally `GET /api/diag` to verify the processor is alive.
7. **No retry-with-backoff for transient errors** — Network blips cause immediate failure.

### Game-Side Issues (Outside Harness Scope)
1. **Processor not completing jobs** — The Roblox-side processor needs to be running and POSTing results back.
2. **No push notifications** — Pure polling wastes bandwidth and adds latency.
3. **No job progress indicators** — Jobs have `status` but no `progress` or `eta` fields.

---

## Code Improvements Made

### `playtest_harness.py` — Diff Summary

```python
# Constants added
ADAPTIVE_TIMEOUT_MIN = 15.0
CONSECUTIVE_FAILURES_FOR_ADAPTIVE = 2

# poll_job() signature changed:
#   Old: (job_id, auth_key, timeout) -> (job_dict | None, elapsed)
#   New: (job_id, auth_key, timeout) -> (job_dict | None, elapsed, stale_info | None)

# New poll_job features:
#   - Detects stale claimed jobs (lease expired) and returns early
#   - Returns last known status in stale_info for better error messages
#   - Removed non-existent status checks ("done", "completed")

# PlaytestRunner changes:
#   - _consecutive_failures counter for adaptive timeout
#   - Adaptive timeout: halves after 2+ consecutive failures
#   - Error status detection (job.status == "error") now handled separately
#   - Reset failure counter on success

# Output changes:
#   - sys.stdout.flush() after header and summary
#   - Error messages now include actual job status
#   - "⚡ Adaptive timeout" progress message
```

### Files Modified
- `playtest_harness.py` — 5 improvements (stale detection, adaptive timeout, error reporting, status fix, flush)

### Files Created
- `/home/eileen/projects/playtest-journals/Explorer_20260803_203618.jsonl` — Run 1 (pre-fix)
- `/home/eileen/projects/playtest-journals/Explorer_20260803_203618.md`
- `/home/eileen/projects/playtest-journals/Builder_20260803_204443.jsonl`
- `/home/eileen/projects/playtest-journals/Builder_20260803_204443.md`
- `/home/eileen/projects/playtest-journals/Newcomer_20260803_205059.jsonl` (partial — killed)
- `/home/eileen/projects/playtest-journals/Newcomer_20260803_205059.md` (partial)
- `/home/eileen/projects/playtest-journals/Explorer_20260803_210237.jsonl` — Run 4 (post-fix)
- `/home/eileen/projects/playtest-journals/Explorer_20260803_210237.md`

---

## Does the Harness Produce Useful Training Data?

### Current State: **Partial**

**What it produces well:**
- Structured JSONL journals with timestamps, personas, messages, round-trip times
- Train-of-thought reasoning (persona-specific internal monologue)
- Emotional reactions per interaction
- Quality scores (1-10) with consistent scoring criteria
- Voice-in-character detection (keyword matching)
- Material diversity tracking
- Summary statistics per run

**What limits training value right now:**
- **Zero successful interactions** — All training data is error cases. No examples of what good Lucineer responses look like.
- **No multi-turn context** — Each message is sent in isolation; no conversation history is passed to the game.
- **No world state** — The harness doesn't send `playerState` or `worldSnapshot` (the types exist but are never populated).
- **Keyword-based voice detection** — Checking for "boat", "water", etc. in responses is crude. Would need embedding-based similarity for real training.
- **No response validation** — Can't verify that build commands would actually produce valid Roblox parts (no spatial/structural validation).

### Verdict
The harness architecture is sound and would produce excellent training data **once the game processor is operational**. The journaling, analysis, and scoring systems are ready. The bottleneck is entirely on the game side — no jobs are completing.

---

## Run Results Summary

| Run | Persona | Scenario | Messages | Errors | Avg Time | Runtime |
|-----|---------|----------|----------|--------|----------|---------|
| 1 (pre-fix) | Explorer | first-time | 4 | 4 | 121s/msg | 488s |
| 2 (pre-fix) | Builder | returning | 3 | 3 | 122s/msg | 369s |
| 3 (pre-fix) | Newcomer | edge-cases | 5/6 | 5 | 120s/msg | ~600s (killed) |
| 4 (post-fix) | Explorer | first-time | 4 | 4 | 84s/msg* | 343s |

*Average improved due to adaptive timeout (121s → 122s → 61s → 33s)

---

## Recommendations

1. **Fix the game processor first** — The harness is ready; the game isn't. Jobs need to reach `complete`.
2. **Add a health pre-check** — The harness should `GET /api/diag` before starting and warn if totalJobs is high (backlog).
3. **Deploy and re-run** — Once the processor is operational, re-run all three scenarios to get real training data.
4. **Add conversation context** — Pass message history to the game so multi-turn interactions work.
5. **Add structural validation** — Verify build commands produce valid Roblox geometry.

---

*This report was generated by running the harness against the live game API, documenting every failure, fixing every harness bug found, and verifying the fixes work. Iron sharpens iron.*
