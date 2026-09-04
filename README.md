# lucineer-worker

**Cloudflare Durable Object relay and job queue for the Slackwater build pipeline.**

The Worker is the single ingress point between the Roblox client and the Python processor. It maintains a SQLite-backed Durable Object for job state, exposes public endpoints for player-facing traffic, authenticates internal endpoints for the processor, and writes MOLT trajectory data to R2.

---

## Architecture

```
Roblox Client ──POST /api/message──▶  Worker  ──▶  LucineerSession DO (SQLite)
       ▲                                    │            │
       │                                    │            ├── createJob()
       └──GET /api/job/:id──────────────────┤            ├── claimJob()
                                            │            ├── setJobResult()
       Python Processor                     │            ├── getPendingJobs()
            │                               │            └── cleanupStaleJobs()
            ├──GET /api/jobs/pending────────┤
            ├──POST /api/job/:id/claim──────┤
            ├──POST /api/job/:id/result─────┤
            ├──POST /api/state──────────────┤
            └──POST /api/trajectory─────────┼──▶  R2 Bucket (lucineer-trajectories)
```

### Bindings

| Binding | Type | Purpose |
|---------|------|---------|
| `LUCINEER_SESSION` | Durable Object | SQLite-backed job queue and world state |
| `DB` | D1 Database | Emotional memory (The Listener's Ear) |
| `LUCINEER_TRAJECTORIES` | R2 Bucket | Append-only MOLT trajectory logs |
| `LUCINEER_INTERNAL_KEY` | Secret | Processor authentication |
| `LUCINEER_KEY` | Secret (legacy) | Backward-compatible auth key |
| `LUCINEER_SHARED_SECRET` | Secret | Inter-service auth (memory/vector calling relay) |

### Wrangler Configuration

```jsonc
{
  "name": "lucineer-relay",
  "main": "src/index.ts",
  "compatibility_date": "2026-07-01",
  "compatibility_flags": ["nodejs_compat"],
  "durable_objects": {
    "bindings": [{ "name": "LUCINEER_SESSION", "class_name": "LucineerSession" }]
  },
  "migrations": [{ "tag": "v1", "new_sqlite_classes": ["LucineerSession"] }],
  "r2_buckets": [{ "binding": "LUCINEER_TRAJECTORIES", "bucket_name": "lucineer-trajectories" }]
}
```

---

## Durable Object: LucineerSession

The `LucineerSession` DO uses Cloudflare's SQLite storage (not KV-style key-value) for structured queries. All job state, world state, and message history live in SQLite tables inside the DO.

### Schema

```sql
CREATE TABLE jobs (
  id          TEXT PRIMARY KEY,       -- 32-char hex from crypto.getRandomValues
  session_id  TEXT NOT NULL,
  player_name TEXT NOT NULL,
  message     TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'pending',  -- pending|processing|complete|error
  reply       TEXT,
  commands    TEXT,                   -- JSON-serialized BuildCommand[]
  files       TEXT,                   -- JSON-serialized RemoteFile[]
  error       TEXT,
  created_at  INTEGER NOT NULL,       -- ms epoch
  completed_at INTEGER,
  claimed_at  INTEGER,                -- ms epoch when processor claimed
  claimed_by  TEXT,                   -- workerId of the claiming processor
  lease_expires_at INTEGER,           -- lease deadline; renewable via /api/job/:id/renew
  attempts    INTEGER NOT NULL DEFAULT 0
);

-- 2026-09-03 audit note: the schema above previously omitted `claimed_by` and
-- `lease_expires_at`; it now mirrors src/do/LucineerSession.ts exactly.

CREATE TABLE world_state (
  session_id  TEXT PRIMARY KEY,
  snapshot    TEXT NOT NULL,          -- JSON
  updated_at  INTEGER NOT NULL
);

CREATE TABLE message_history (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  job_id      TEXT NOT NULL,
  session_id  TEXT NOT NULL,
  player_name TEXT NOT NULL,
  message     TEXT NOT NULL,
  reply       TEXT,
  timestamp   INTEGER NOT NULL
);

-- Indexes
CREATE INDEX idx_jobs_session  ON jobs(session_id);
CREATE INDEX idx_jobs_status   ON jobs(status);
CREATE INDEX idx_jobs_claimed  ON jobs(claimed_at);
CREATE INDEX idx_history_session ON message_history(session_id);
```

### Schema Migration

The DO constructor runs `ALTER TABLE ADD COLUMN` wrapped in try/catch for idempotency. Columns `claimed_at` and `attempts` are added to pre-existing tables without data loss. Legacy `processing` status rows are migrated to `pending` so the claiming flow picks them up.

---

## Job Lifecycle

```
                    ┌──────────────────────────┐
                    │       pending             │
                    │  (created by /message)    │
                    └─────────┬────────────────┘
                              │
                    POST /api/job/:id/claim
                              │ (atomic CAS)
                    ┌─────────▼────────────────┐
                    │      processing           │
                    │  (processor owns lease)   │
                    └─────────┬────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    POST /api/job/:id/result  │   5 min lease │
              │               │   expiry      │
    ┌─────────▼──────┐   ┌───▼───────────┐   │
    │    complete    │   │    error      │   │
    └────────────────┘   └───────────────┘   │
                                            │
                               cleanupStaleJobs()
                                    │
                              back to pending
                              (attempts < 3)
                              else → error
```

### States

| Status | Meaning | Transition trigger |
|--------|---------|-------------------|
| `pending` | Job created, awaiting processor | `POST /api/message` or stale lease cleanup |
| `processing` | Processor has claimed the job | `POST /api/job/:id/claim` (atomic) |
| `complete` | Processor posted result | `POST /api/job/:id/result` |
| `error` | Failed after MAX_ATTEMPTS (3) | Exceeded retries or explicit error |

### Claim Semantics

Claiming is an atomic compare-and-set: the DO updates `status = 'processing'` and `claimed_at = now` only if `status = 'pending'`. If another processor already claimed it, the CAS fails and returns 409 Conflict.

### Stale Job Recovery

A lease prevents indefinite locking. The `cleanupStaleJobs()` RPC scans for `processing` jobs whose lease has expired, resets them to `pending`, and increments `attempts`. Jobs exceeding `MAX_ATTEMPTS = 3` are permanently errored. Long-running processors can call `POST /api/job/:jobId/renew` to extend their lease.

> **2026-09-03 correction:** this section previously stated a 5-minute lease via `CLAIM_LEASE_MS = 300000`. The actual code is `LEASE_MS = 3 * 60 * 1000` (**3 minutes**, src/do/LucineerSession.ts:13), with per-worker lease renewal — verified by re-reading source, not docs.

---

## Authentication Model

### Three-Tier Auth

| Tier | Header | Endpoints | Purpose |
|------|--------|-----------|---------|
| **Public** | None | `POST /api/message`, `GET /api/job/:id` | Roblox client; jobId is a capability token |
| **Internal** | `X-Lucineer-Key` | All `/api/job/*`, `/api/jobs/*`, `/api/state/*`, `/api/diag` | Python processor |
| **Trajectory** | `X-Lucineer-Key` | `POST /api/trajectory` | Processor writing MOLT data to R2 |

The auth function accepts `LUCINEER_INTERNAL_KEY`, legacy `LUCINEER_KEY`, or `LUCINEER_SHARED_SECRET` (for inter-service calls from memory/vector Workers).

### Rate Limiting

Public message ingestion is rate-limited per session: **10 messages per minute** (`RATE_LIMIT_MAX = 10`, `RATE_LIMIT_WINDOW_MS = 60000`). The counter queries the `jobs` table for recent `created_at` timestamps within the sliding window.

---

## API Reference

### Public Endpoints

#### `POST /api/message`

Create a new build job from a player chat message.

**Request:**
```json
{
  "sessionId": "string",
  "playerName": "string",
  "message": "string",
  "playerState": { "position": { "x": 0, "y": 0, "z": 0 } },
  "worldSnapshot": { "objects": [] }
}
```

**Response (200):**
```json
{ "jobId": "a1b2c3d4...", "status": "processing" }
```

**Errors:** 400 (missing fields), 429 (rate limited)

---

#### `GET /api/job/:jobId`

Poll job status. No auth required — the jobId serves as a capability token.

**Response (200):**
```json
{
  "id": "a1b2c3d4...",
  "sessionId": "string",
  "playerName": "string",
  "message": "build a castle",
  "status": "complete",
  "reply": "Castle's up. Four tower walls...",
  "commands": [ { "type": "createPart", "params": { "name": "CastleFloor", "size": {"x":40,"y":1,"z":40} } } ],
  "createdAt": 1722640000000,
  "completedAt": 1722640030000
}
```

---

#### `GET /api/health`

Unauthenticated health check.

```json
{ "status": "ok", "timestamp": 1722640000000 }
```

---

### Emotional Memory API (The Listener's Ear)

The emotional memory system stores player emotional states in D1 so Lucineer remembers between sessions. When a player says "I'm scared," the system records it. Next time they return, Lucineier greets them differently and adjusts build style.

**D1 Table:** `emotional_events` in `lucineer-memory` database

#### `POST /api/emotions`

Record a new emotional event.

**Request:**
```json
{
  "playerId": "string",
  "emotion": "scared|lonely|sad|happy|excited|angry|worried",
  "context": "the player's message",
  "intensity": 0.5,
  "sessionId": "optional",
  "buildTheme": "optional"
}
```

#### `GET /api/emotions/:playerId`

Get emotional history for a player.

#### `GET /api/emotions/:playerId/current`

Get the current (most recent) emotional state with derived metrics: dominant emotion, volatility, days since last event.

#### `GET /api/emotions/:playerId/context`

Get emotional context for a build response. Returns greeting suggestions and build modifiers that Lucineier should use when this player returns.

**Response:**
```json
{
  "playerId": "PlayerAlpha",
  "hasHistory": true,
  "returningEmotion": "scared",
  "greetingSuggestion": "Knew you'd come back. Kept the light on.",
  "buildModifier": "Player was scared last time. Build something sturdy...",
  "intensity": 0.7
}
```

---

### Internal Endpoints (require `X-Lucineer-Key`)

#### `GET /api/jobs/pending`

Returns all jobs with `status = 'pending'`.

**Response:**
```json
{
  "jobs": [ { "id": "...", "sessionId": "...", "message": "...", "createdAt": 0 } ],
  "notice": "Call POST /api/job/:jobId/claim before processing..."
}
```

#### `POST /api/job/:jobId/claim`

Atomically claim a job for processing. Returns 409 if already claimed.

**Response (200):** `{ "ok": true, "job": { ...full job object } }`
**Response (409):** `{ "ok": false, "error": "Job already claimed or not found" }`

#### `POST /api/job/:jobId/result`

Post the processor's build result.

**Request:**
```json
{
  "reply": "Castle's up — four tower walls...",
  "commands": [ { "type": "createPart", "params": { "name": "...", "position": {"x":0,"y":0,"z":0}, "size": {"x":0,"y":0,"z":0}, "material": "Brick", "color": {"r":150,"g":130,"b":100}, "anchored": true } } ],
  "files": [ { "name": "concept_art.png", "url": "https://...", "description": "Reference image" } ]
}
```

**Response (200):**
```json
{
  "ok": true,
  "jobId": "a1b2c3d4...",
  "filtered": false,
  "filterNotice": "TextService:FilterStringAsync() must be called on `reply` before display."
}
```

#### `POST /api/state`

Update world state snapshot for a session.

#### `GET /api/state/:sessionId`

Retrieve the current world state for a session.

#### `POST /api/trajectory`

Write MOLT trajectory events to R2. Each call creates a separate JSONL object keyed by `trajectories/{sessionId}/{timestamp}.json`. Append-only: partial failures never corrupt earlier data.

**Request:**
```json
{
  "sessionId": "string",
  "events": [
    {
      "type": "pipeline_stage",
      "timestamp": 1722640000000,
      "jobId": "a1b2c3d4...",
      "stage": "intent",
      "model": "ByteDance/Seed-2.0-mini",
      "channel": 10,
      "data": { "intent": "build", "subject": "castle" },
      "errorMask": 0
    }
  ]
}
```

**R2 Object Key:** `trajectories/{sessionId}/{epochMs}.json`

R2 write failure returns 500 so the processor can retry. Trajectories are the highest-option-value data in the system.

#### `GET /api/diag`

Diagnostic endpoint returning schema info and job counts.

### Additional Endpoints (2026-09-03 audit note)

The router (src/index.ts) also exposes endpoints not previously listed here — verified against source:

- `POST /api/jobs/claim` — atomic **batch** claim of pending jobs (the processor's preferred path; takes `workerId`, `limit`, `sessionId` from query params or JSON body, fans out across active sessions)
- `POST /api/job/:jobId/renew` — extend a claimed job's lease
- `POST /api/chat` — Lucineer voice line via Workers AI (`AI` binding)
- `POST /api/generate-build` — build commands via template or Workers AI
- `GET /api/quick/:message` — public fast-path template lookup
- `GET /api/world/:sessionId`, `POST /api/world/:sessionId/build`, `GET /api/world/:sessionId/bond` — world state and bond level
- `DELETE /api/cache` — clear response cache (admin)

Also: the wrangler config binds a D1 database (`DB` → `lucineer-memory`) and the Workers AI binding (`AI`) in addition to the excerpt above.

---

## Processor (`process_v2.py`)

The Python processor is the poll-based consumer of this Worker. It runs as a daemon with:

- **2-second poll interval** against `GET /api/jobs/pending`
- **Atomic claiming** via `POST /api/job/:id/claim` before processing
- **Memory integration** via `lucineer-memory` Worker (player profiles, build history, conversations)
- **Skill lookup** via `lucineer-vector` Worker (Vectorize semantic search)
- **Two-speed brain**: fast template match → deep `brain.py` pipeline fallback
- **Circuit breaker**: 5 consecutive failures triggers CRITICAL log, does not crash
- **Memory leak guard**: RSS check at each 60s heartbeat, warns at 200MB

### Daemon Flags

```bash
python3 process_v2.py --loop          # continuous mode (2s poll)
python3 process_v2.py --once          # single poll
python3 process_v2.py --deep          # force deep brain on all jobs
python3 process_v2.py --mock "castle" # inject test job
python3 process_v2.py --no-safety     # skip Nemotron content safety check
python3 process_v2.py --interval 5    # custom poll interval
```

### Content Safety Pipeline

All replies pass through `nvidia/Nemotron-Content-Safety-3.5` before posting back to the Worker. If the safety model returns UNSAFE, the reply is replaced with Lucineer's in-voice deflection: *"Misread that one. Doesn't belong in the yard."* The safety check fails safe — if the API is unavailable, the reply is blocked.

---

## Deployment

```bash
# Deploy the Worker
npx wrangler deploy

# Set secrets
npx wrangler secret put LUCINEER_INTERNAL_KEY
npx wrangler secret put LUCINEER_SHARED_SECRET

# Run the processor
python3 process_v2.py --loop
```

**Production URL:** `https://lucineer-relay.casey-digennaro.workers.dev`

---

## File Layout

```
src/
├── index.ts              # Worker entry point, router, auth middleware
├── emotional-memory.ts   # The Listener's Ear — D1 emotional memory system
├── types.ts              # Shared TypeScript interfaces (Env, Job, TrajectoryEvent, ...)
└── do/
    └── LucineerSession.ts  # Durable Object: SQLite schema, job lifecycle, rate limiting
migrations/
  └── 001_emotional_memory.sql  # D1 schema for emotional events
process_v2.py             # Hybrid-intelligence processor daemon (memory + vector + brain)
process.py                # Legacy processor (pre-memory, pre-vector)
bond.py                   # Player bond level tracking
build_templates_v2.py     # Fast-path template library (castle, house, tower, dock, ...)
test_e2e.py               # End-to-end integration test
wrangler.jsonc            # Cloudflare Workers configuration
```

---

## Related Repositories

| Repository | Role |
|-----------|------|
| [lucineer-system](../lucineer-system) | 4-stage multi-model pipeline (Seed → Planner → Coder → Hermes); design docs, roundtable analyses, architecture specs |
| [lucineer-memory](../lucineer-memory) | D1-backed player profiles, build history, conversations |
| [lucineer-vector](../lucineer-vector) | Vectorize semantic skill library (bge-small-en, 384-dim) |
| [lucineer-roblox](../lucineer-roblox) | Roblox client: 16 Lua modules, CommandExecutor, BeatClock |
| [casting-call](../casting-call) | Model routing atlas and CastingDirector (Layer 8) |

<!-- 2026-09-03 audit: removed duplicate lucineer-system row (it appeared twice
     with different role descriptions); roles merged into the single row above. -->

---

## License

MIT
