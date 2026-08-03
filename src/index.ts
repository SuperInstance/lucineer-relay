import { LucineerSession } from "./do/LucineerSession";
import type { Env, IncomingMessage, JobResult, TrajectoryEvent, Job } from "./types";

export { LucineerSession };

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
function sessionStub(env: Env, sessionId: string) {
  return env.LUCINEER_SESSION.getByName(
    encodeURIComponent(sessionId),
  ) as unknown as import("./types").LucineerSessionRPC & { diag(): Promise<Record<string, unknown>> };
}

// ---------------------------------------------------------------------------
// Worker entry point
// ---------------------------------------------------------------------------

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // --- Health check (no auth) ---
    if (path === "/api/health" && method === "GET") {
      return Response.json({ status: "ok", timestamp: Date.now() });
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

      const stub = sessionStub(env, body.sessionId);
      const withinLimit = await stub.checkRateLimit(body.sessionId);
      if (!withinLimit) {
        return Response.json(
          { error: "Rate limit exceeded. Max 10 messages per minute per session." },
          { status: 429 },
        );
      }

      const { jobId } = await stub.createJob(body);

      // No push path — the processor polls /api/jobs/pending.
      // The old OPENCLAW_CALLBACK_URL pointed at a WSL private IP (172.22.x.x)
      // which Cloudflare Workers can't reach. Push was removed; polling works.
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

    // --- POST /api/jobs/claim — batch claim pending jobs atomically ---
    // Query params: ?workerId=<id>&limit=<n>
    // This is the preferred endpoint for processors. It atomically selects
    // and claims jobs in one operation, preventing race conditions.
    if (path === "/api/jobs/claim" && method === "POST") {
      const workerId = url.searchParams.get("workerId") || `worker-${Date.now()}`;
      const limit = Math.min(Number(url.searchParams.get("limit") || 5), 20);

      // Fan out across all active session DOs.
      // For now, we claim from the "default" DO plus any session IDs
      // extracted from the workerId hint (if the processor passes ?sessions=s1,s2).
      // In practice, most jobs land on "default" since the processor doesn't
      // know session IDs ahead of time.
      //
      // Optimization: the processor can pass ?sessionId=<id> to claim from
      // a specific session DO only.
      const sessionParam = url.searchParams.get("sessionId");
      const sessionIds = sessionParam
        ? [sessionParam]
        : ["default"];

      const allJobs: { jobId: string; job: Job }[] = [];
      for (const sid of sessionIds) {
        const stub = sessionStub(env, sid);
        const jobs = await stub.claimPendingJobs(workerId, limit - allJobs.length);
        for (const job of jobs) {
          allJobs.push({ jobId: job.id, job });
        }
        if (allJobs.length >= limit) break;
      }

      return Response.json({
        ok: true,
        claimed: allJobs.length,
        jobs: allJobs,
      });
    }

    // --- POST /api/state — update world state ---
    if (path === "/api/state" && method === "POST") {
      let body: { sessionId: string; worldSnapshot: Record<string, unknown> };
      try {
        body = (await request.json()) as {
          sessionId: string;
          worldSnapshot: Record<string, unknown>;
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
      await stub.updateWorldState(body.sessionId, body.worldSnapshot as any);
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
  },
} satisfies ExportedHandler<Env>;
