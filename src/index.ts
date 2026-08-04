import { LucineerSession } from "./do/LucineerSession";
import type {
  Env,
  IncomingMessage,
  JobResult,
  TrajectoryEvent,
  Job,
  WorldSnapshot,
} from "./types";
import { BUILD_TEMPLATES, type BuildTemplate } from "./templates";

export { LucineerSession };

// ---------------------------------------------------------------------------
// Fast Path — keyword matching for instant template responses
// ---------------------------------------------------------------------------

/**
 * Keyword map: lowercase keyword → template key.
 * Mirrors the matching logic in process_v2.py's KEYWORDS dict but
 * trimmed to the 10 templates embedded in the Worker.
 */
const FAST_KEYWORDS: Record<string, string> = {
  // Direct template names
  tower: "tower", spire: "tower", pillar: "tower",
  house: "house", cabin: "house", home: "house", shack: "house",
  castle: "castle", fortress: "castle", fort: "castle", keep: "castle", citadel: "castle", palace: "castle",
  bridge: "bridge", crossing: "bridge",
  windmill: "windmill", mill: "windmill",
  garden: "garden", park: "garden", yard: "garden", flowerbed: "garden",
  dock: "dock", pier: "dock", wharf: "dock", jetty: "dock",
  lighthouse: "lighthouse", beacon: "lighthouse",
  cottage: "cottage",
  well: "well", "water well": "well", wishwell: "well", "wishing well": "well",
};

/** Build verbs — at least one must be present for a keyword match. */
const BUILD_VERB_RE = /\b(build|make|create|put|raise|place|add|give me|construct|throw up|put up)\b/i;

/** Negation — if present, don't match. */
const NEGATION_RE = /\b(don'?t|do not|never|stop|no|not)\b/i;

/**
 * Try to match a player message against the fast-path keyword templates.
 * Returns the matched template + the canonical build name, or null.
 *
 * Matching rules (same as process_v2.py match_keyword):
 *   1. Must contain a build verb (build, make, create, etc.)
 *   2. Must NOT contain negation (don't build a...)
 *   3. Longest keyword match wins (so 'castle' beats 'well' in 'build a castle well')
 *   4. Word-boundary matching (so 'arc' doesn't match 'search')
 */
function matchFastPath(message: string): { template: BuildTemplate; buildName: string } | null {
  const msgLower = message.toLowerCase();

  // Must have a build verb
  if (!BUILD_VERB_RE.test(msgLower)) return null;

  // Must not have negation
  if (NEGATION_RE.test(msgLower)) return null;

  // Score all candidates, pick the longest keyword match
  let bestKey: string | null = null;
  let bestTemplate: string | null = null;

  for (const [keyword, templateKey] of Object.entries(FAST_KEYWORDS)) {
    // Word-boundary regex for this keyword
    const re = new RegExp(`\\b${keyword.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
    if (re.test(msgLower)) {
      if (!bestKey || keyword.length > bestKey.length) {
        bestKey = keyword;
        bestTemplate = templateKey;
      }
    }
  }

  if (!bestTemplate) return null;

  const template = BUILD_TEMPLATES[bestTemplate];
  if (!template) return null;

  return { template, buildName: bestTemplate };
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Validate the internal processor key.
 * Accepts either the new LUCINEER_INTERNAL_KEY or the legacy LUCINEER_KEY
 * during the transition period.
 */
function isAuthorized(request: Request, env: Env): boolean {
  const authKey = request.headers.get("X-Lucineer-Key");
  if (!authKey) return false;

  if (env.LUCINEER_INTERNAL_KEY && authKey === env.LUCINEER_INTERNAL_KEY) {
    return true;
  }
  if (env.LUCINEER_KEY && authKey === env.LUCINEER_KEY) {
    return true;
  }
  if (env.LUCINEER_SHARED_SECRET && authKey === env.LUCINEER_SHARED_SECRET) {
    return true;
  }
  return false;
}

/** Return a 401 response. */
function unauthorized(): Response {
  return Response.json({ error: "Unauthorized" }, { status: 401 });
}

/**
 * Extract the session ID from a job ID.
 * Job IDs are formatted as `<urlEncodedSessionId>.<randomHex>`.
 * Returns the decoded session ID, or "default" as a fallback.
 */
function sessionIdFromJobId(jobId: string): string {
  const dotIdx = jobId.indexOf(".");
  if (dotIdx > 0) {
    return decodeURIComponent(jobId.substring(0, dotIdx));
  }
  return "default";
}

/**
 * Get a Durable Object stub routed by session ID.
 * This replaces the old getByName("default") pattern that serialized
 * all players through one object.
 */
function sessionStub(env: Env, sessionId: string): DurableObjectStub<LucineerSession> {
  return env.LUCINEER_SESSION.getByName(encodeURIComponent(sessionId));
}

/** Safely parse an optional JSON body on internal POST endpoints. */
async function parseJsonBody<T>(request: Request): Promise<T | undefined> {
  try {
    return (await request.json()) as T;
  } catch {
    return undefined;
  }
}

// ---------------------------------------------------------------------------
// Worker entry point
// ---------------------------------------------------------------------------

// The Roblox client isn't subject to browser CORS, but the web client
// (lucineer.com/play.html) is — every response needs these headers or the
// browser silently discards it. All endpoints here are either already
// public/keyless by design or still gated by X-Lucineer-Key, so a
// permissive origin doesn't change what's reachable, only who can read it.
const CORS_HEADERS: Record<string, string> = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, X-Lucineer-Key",
};

function withCors(response: Response): Response {
  const headers = new Headers(response.headers);
  for (const [key, value] of Object.entries(CORS_HEADERS)) {
    headers.set(key, value);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }
    try {
      return withCors(await handleRequest(request, env));
    } catch (e) {
      return withCors(
        Response.json(
          { error: "Internal server error", detail: String(e) },
          { status: 500 },
        ),
      );
    }
  },
} satisfies ExportedHandler<Env>;

async function handleRequest(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const path = url.pathname;
  const method = request.method;

  // --- Health check (no auth) ---
  if (path === "/api/health" && method === "GET") {
    return Response.json({ status: "ok", timestamp: Date.now() });
  }

  // =====================================================================
  // PUBLIC FAST PATH — GET /api/quick/:message
  // No auth required. Returns a template instantly if the message
  // matches a known build keyword. Designed for low-friction web game
  // calls where setting up headers is cumbersome.
  // =====================================================================
  const quickMatch = path.match(/^\/api\/quick\/(.+)$/);
  if (quickMatch && method === "GET") {
    const message = decodeURIComponent(quickMatch[1]);
    const fastMatch = matchFastPath(message);
    if (fastMatch) {
      return Response.json({
        status: "complete",
        reply: fastMatch.template.reply,
        commands: fastMatch.template.commands,
        source: "template",
        buildName: fastMatch.buildName,
        timestamp: Date.now(),
      });
    }
    // No match — tell the caller to use the deep path
    return Response.json({
      status: "no_template",
      message: "No quick template for that request. Use POST /api/message for the full brain pipeline.",
    });
  }

  // =====================================================================
  // PUBLIC ENDPOINT — POST /api/message
  // No auth required (the Roblox client doesn't have the internal key).
  // Rate-limited per session to prevent abuse.
  // =====================================================================
  if (path === "/api/message" && method === "POST") {
    let body: IncomingMessage;
    try {
      body = (await request.json()) as IncomingMessage;
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400 });
    }

    if (!body.sessionId || !body.playerName || !body.message) {
      return Response.json(
        { error: "Missing required fields: sessionId, playerName, message" },
        { status: 400 },
      );
    }

    // ── FAST PATH ────────────────────────────────────────────────────────
    // Check for keyword-matched build templates BEFORE anything else —
    // before rate limiting, before DO calls. Templates are pure computation
    // and should return in under 200ms from the edge.
    // ────────────────────────────────────────────────────────────────────
    const fastMatch = matchFastPath(body.message);
    if (fastMatch) {
      return Response.json({
        status: "complete",
        reply: fastMatch.template.reply,
        commands: fastMatch.template.commands,
        source: "template",
        buildName: fastMatch.buildName,
        jobId: null,
        timestamp: Date.now(),
      });
    }

    const stub = sessionStub(env, body.sessionId);
    const withinLimit = await stub.checkRateLimit(body.sessionId);
    if (!withinLimit) {
      return Response.json(
        { error: "Rate limit exceeded. Max 10 messages per minute per session." },
        { status: 429 },
      );
    }

    // ── DEEP PATH ────────────────────────────────────────────────────────
    // No template match — create a job for the brain pipeline.
    // ────────────────────────────────────────────────────────────────────
    const { jobId } = await stub.createJob(body);

    // Register this session in the default DO's session registry so that
    // batch claim can fan out to it. Non-fatal — failing here shouldn't
    // block the player from getting a jobId.
    try {
      await sessionStub(env, "default").registerSession(body.sessionId);
    } catch {
      // Registry best-effort; the job is still created.
    }

    // No push path — the processor polls POST /api/jobs/claim.
    return Response.json({ jobId, status: "processing" });
  }

  // =====================================================================
  // CLIENT POLLING — No auth required
  // The Roblox client polls this endpoint to check job status.
  // The jobId itself serves as a capability token.
  // =====================================================================

  // Match /api/job/:jobId — accept session-prefixed IDs (contains dots, percent-encoding)
  const jobMatch = path.match(/^\/api\/job\/([^/]+)$/);
  if (jobMatch && method === "GET") {
    const jobId = decodeURIComponent(jobMatch[1]);
    const sessionId = sessionIdFromJobId(jobId);
    const stub = sessionStub(env, sessionId);
    const job = await stub.getJob(jobId);
    if (!job) {
      return Response.json({ error: "Job not found" }, { status: 404 });
    }
    return Response.json(job);
  }

  // =====================================================================
  // INTERNAL ENDPOINTS — Require processor auth
  // =====================================================================
  if (!isAuthorized(request, env)) {
    return unauthorized();
  }

  // --- GET /api/diag — diagnostic endpoint ---
  if (path === "/api/diag" && method === "GET") {
    // Diag runs on the "default" DO
    const stub = sessionStub(env, "default");
    try {
      const result = await stub.diag();
      return Response.json(result);
    } catch (e) {
      return Response.json({ error: String(e) }, { status: 500 });
    }
  }

  // --- POST /api/job/:jobId/result — processor posts results ---
  // Accept session-prefixed job IDs
  const resultMatch = path.match(/^\/api\/job\/(.+)\/result$/);
  if (resultMatch && method === "POST") {
    const jobId = decodeURIComponent(resultMatch[1]);
    let body: JobResult;
    try {
      body = (await request.json()) as JobResult;
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400 });
    }

    if (!body.reply) {
      return Response.json({ error: "Missing required field: reply" }, { status: 400 });
    }

    const sessionId = sessionIdFromJobId(jobId);
    const stub = sessionStub(env, sessionId);
    const job = await stub.getJob(jobId);
    if (!job) {
      return Response.json({ error: "Job not found" }, { status: 404 });
    }

    await stub.setJobResult(jobId, body);

    return Response.json({
      ok: true,
      jobId,
      filtered: false,
      filterNotice:
        "TextService:FilterStringAsync() must be called on `reply` before display. " +
        "This is required by Roblox policy for user-influenced text.",
    });
  }

  // --- POST /api/job/:jobId/claim — atomically claim a single job ---
  const claimMatch = path.match(/^\/api\/job\/(.+)\/claim$/);
  if (claimMatch && method === "POST") {
    const jobId = decodeURIComponent(claimMatch[1]);
    const sessionId = sessionIdFromJobId(jobId);
    const stub = sessionStub(env, sessionId);
    const job = await stub.claimJob(jobId);
    if (!job) {
      return Response.json(
        { ok: false, error: "Job already claimed or not found" },
        { status: 409 },
      );
    }
    return Response.json({ ok: true, job });
  }

  // --- POST /api/job/:jobId/renew — extend a claimed job's lease ---
  const renewMatch = path.match(/^\/api\/job\/(.+)\/renew$/);
  if (renewMatch && method === "POST") {
    const jobId = decodeURIComponent(renewMatch[1]);
    const body = await parseJsonBody<{ workerId?: string }>(request);
    const sessionId = sessionIdFromJobId(jobId);
    const stub = sessionStub(env, sessionId);
    const job = await stub.renewLease(jobId, body?.workerId);
    if (!job) {
      return Response.json(
        { error: "Job not found or not currently claimed" },
        { status: 404 },
      );
    }
    return Response.json({ ok: true, job });
  }

  // --- POST /api/jobs/claim — batch claim pending jobs atomically ---
  // Accepts query params or a JSON body: { workerId, limit, sessionId }
  // This is the preferred endpoint for processors. It atomically selects
  // and claims jobs in one operation, preventing race conditions.
  if (path === "/api/jobs/claim" && method === "POST") {
    const body = await parseJsonBody<{
      workerId?: string;
      limit?: number;
      sessionId?: string;
    }>(request);

    const workerId =
      url.searchParams.get("workerId") ||
      body?.workerId ||
      `worker-${Date.now()}`;
    const limit = Math.min(
      Number(url.searchParams.get("limit") || body?.limit || 5),
      20,
    );

    // Discover active sessions from the registry in the default DO.
    // A specific sessionId (query or body) overrides discovery.
    const sessionParam =
      url.searchParams.get("sessionId") || body?.sessionId;
    let sessionIds: string[];
    if (sessionParam) {
      sessionIds = [sessionParam];
    } else {
      try {
        const registry = sessionStub(env, "default");
        sessionIds = await registry.getActiveSessions();
        if (sessionIds.length === 0) {
          sessionIds = ["default"];
        }
      } catch {
        sessionIds = ["default"];
      }
    }

    const allJobs: { jobId: string; job: Job }[] = [];
    for (const sid of sessionIds) {
      const stub = sessionStub(env, sid);
      const jobs: Job[] = await stub.claimPendingJobs(workerId, limit - allJobs.length);
      for (const job of jobs) {
        allJobs.push({ jobId: job.id, job });
      }
      if (allJobs.length >= limit) break;
    }

    return Response.json({
      ok: true,
      claimed: allJobs.length,
      workerId,
      jobs: allJobs,
    });
  }

  // --- POST /api/state — update world state ---
  if (path === "/api/state" && method === "POST") {
    let body: { sessionId: string; worldSnapshot: WorldSnapshot };
    try {
      body = (await request.json()) as {
        sessionId: string;
        worldSnapshot: WorldSnapshot;
      };
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400 });
    }

    if (!body.sessionId || !body.worldSnapshot) {
      return Response.json(
        { error: "Missing required fields: sessionId, worldSnapshot" },
        { status: 400 },
      );
    }

    const stub = sessionStub(env, body.sessionId);
    await stub.updateWorldState(body.sessionId, body.worldSnapshot);
    return Response.json({ ok: true });
  }

  // --- GET /api/state/:sessionId — retrieve world state ---
  const stateMatch = path.match(/^\/api\/state\/(.+)$/);
  if (stateMatch && method === "GET") {
    const sessionId = decodeURIComponent(stateMatch[1]);
    const stub = sessionStub(env, sessionId);
    const state = await stub.getWorldState(sessionId);
    if (!state) {
      return Response.json({ error: "No state found for session" }, { status: 404 });
    }
    return Response.json(state);
  }

  // --- GET /api/jobs/pending — processor polls for unprocessed jobs ---
  // NOTE: Processors should prefer POST /api/jobs/claim for atomic claiming.
  // This endpoint is kept for backward compatibility.
  if (path === "/api/jobs/pending" && method === "GET") {
    const stub = sessionStub(env, "default");
    const jobs = await stub.getPendingJobs();
    return Response.json({
      jobs,
      notice: "Prefer POST /api/jobs/claim for atomic batch claiming.",
    });
  }

  // =====================================================================
  // R2 MOLT TRAJECTORY WRITER
  // POST /api/trajectory — writes session events to R2.
  // =====================================================================
  if (path === "/api/trajectory" && method === "POST") {
    let body: { sessionId: string; events: TrajectoryEvent[] };
    try {
      body = (await request.json()) as { sessionId: string; events: TrajectoryEvent[] };
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400 });
    }

    if (!body.sessionId) {
      return Response.json({ error: "Missing required field: sessionId" }, { status: 400 });
    }
    if (!body.events || !Array.isArray(body.events) || body.events.length === 0) {
      return Response.json({ error: "Missing or empty required field: events" }, { status: 400 });
    }

    const timestamp = Date.now();
    const r2Key = `trajectories/${body.sessionId}/${timestamp}.json`;

    const payload = {
      sessionId: body.sessionId,
      timestamp,
      events: body.events,
    };

    try {
      await env.LUCINEER_TRAJECTORIES.put(
        r2Key,
        JSON.stringify(payload),
        {
          customMetadata: {
            sessionId: body.sessionId,
            eventCount: String(body.events.length),
            timestamp: String(timestamp),
          },
        },
      );

      return Response.json({
        ok: true,
        key: r2Key,
        eventsWritten: body.events.length,
      });
    } catch (e) {
      return Response.json(
        { error: "Failed to write trajectory to R2", detail: String(e) },
        { status: 500 },
      );
    }
  }

  // --- 404 ---
  return Response.json({ error: "Not found" }, { status: 404 });
}
