# Lucineer Worker TypeScript Audit

Files reviewed: `src/index.ts`, `src/do/LucineerSession.ts`, `src/types.ts`.

## 1. Type safety

### Findings
- **`Env.LUCINEER_SESSION` was untyped.** It was declared as the raw `DurableObjectNamespace`, so `getByName` returned an untyped stub and every DO call relied on a manual cast.
- **`sessionStub` used a dangerous cast.** `as unknown as LucineerSessionRPC & { diag(): ... }` bypassed the type checker and had to be kept in sync by hand.
- **`updateWorldState` cast the snapshot to `any`.** The Worker accepted `Record<string, unknown>` and then cast it to `WorldSnapshot`, losing index-signature checking.
- Worker responses are not explicitly typed. `Response.json(...)` infers `Response`, which is acceptable but means response shapes are not checked at compile time.

### Fixes applied
- `src/types.ts`: `Env.LUCINEER_SESSION` is now `DurableObjectNamespace<import("./do/LucineerSession").LucineerSession>`.
- `src/types.ts`: `LucineerSessionRPC` now declares all public RPC methods, including `diag`, `registerSession`, `getActiveSessions`, and `renewLease`.
- `src/index.ts`: `sessionStub` now returns `DurableObjectStub<LucineerSession>` and the cast is removed.
- `src/index.ts`: `POST /api/state` now types the snapshot as `WorldSnapshot` and the `as any` cast is gone.
- `src/index.ts`: added a typed `parseJsonBody<T>` helper for internal endpoints that accept optional JSON bodies.

## 2. Error handling / HTTP status codes

### Findings
- All routes return an explicit status code: `400` for bad JSON/missing fields, `429` for rate limits, `404` for missing jobs/state, `401` for missing/wrong auth, `409` for single-job claim conflicts, `500` for R2/diag errors, and `404` for unknown routes.
- **Unhandled Durable Object exceptions bubbled out.** If a DO RPC call threw, the Worker would return a generic Cloudflare 500 page instead of JSON.
- **`POST /api/jobs/claim` ignored the request body.** The processor sends `{ workerId, limit }` as JSON, but the Worker only read query params, so the processor's `workerId` and requested batch size were silently discarded.

### Fixes applied
- `src/index.ts`: wrapped the request handler in a top-level `try/catch` that returns a JSON `500` with the error detail.
- `src/index.ts`: `/api/jobs/claim` now accepts `workerId`, `limit`, and `sessionId` from **both** query params and a JSON body, preferring query params when present. The response also echoes the actual `workerId` used.

## 3. Job claiming flow and lease renewal

### Findings
- `LucineerSession` has a correct lease model: claimed jobs get `lease_expires_at = now + 3 min`, stale leases are reset to `pending` in `claimPendingJobs` and the alarm, and jobs that exceed `MAX_ATTEMPTS` are marked `error`.
- **No lease renewal existed.** The processor's deep path can run for ~100 s (plus DeepInfra safety/vibe-code calls). Without renewal, a slow job could exceed the 3-minute lease and be reclaimed by another processor.
- **Batch claim could miss jobs in non-default sessions.** `/api/jobs/claim` only fanned out to an explicit `sessionId` or `"default"`. Since `createJob` routes per `sessionId`, jobs created in other sessions would never be picked up by the processor.

### Fixes applied
- `src/do/LucineerSession.ts`: added `renewLease(jobId, workerId?)` and a registry table (`active_sessions`) with `registerSession` / `getActiveSessions`.
- `src/index.ts`: added `POST /api/job/:jobId/renew` (internal, auth required).
- `src/index.ts`: `POST /api/message` now registers the session in the default DO's registry after creating the job.
- `src/index.ts`: `POST /api/jobs/claim` now discovers active sessions from the registry and fans out across them, falling back to `"default"`.
- `process_v2.py`: added a background `LeaseRenewal` thread that calls `/api/job/:jobId/renew` every 60 s while the deep-brain path is running.

## 4. Session routing

### Findings
- Every per-session DO call routes through `sessionStub(env, sessionId)`; no `getByName("default")` leakage was found for session-scoped operations.
- `/api/diag` and the legacy `/api/jobs/pending` intentionally use the `"default"` DO, which is correct.

### Fixes applied
- The new session registry lives in the `"default"` DO, preserving the rule that session-specific data never routes through `default` by accident.
- Added `getActiveSessions` so the batch claimer can discover sessions without breaking the per-session routing design.

## Remaining operational notes
- The new `active_sessions` table is created inside the existing `LucineerSession` class, so no Wrangler migration is required for the schema change. A normal `wrangler deploy` is sufficient.
- Response types are still inferred. If stricter API contracts are needed later, add explicit response interfaces to `src/types.ts`.
