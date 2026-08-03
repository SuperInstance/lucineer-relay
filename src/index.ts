import { LucineerSession } from "./do/LucineerSession";
import type { Env, IncomingMessage, JobResult, TrajectoryEvent } from "./types";

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

  // Check new key first, fall back to legacy key
  if (env.LUCINEER_INTERNAL_KEY && authKey === env.LUCINEER_INTERNAL_KEY) {
    return true;
  }
  if (env.LUCINEER_KEY && authKey === env.LUCINEER_KEY) {
    return true;
  }
  // Also accept the shared secret for inter-service calls (memory/vector calling relay)
  if (env.LUCINEER_SHARED_SECRET && authKey === env.LUCINEER_SHARED_SECRET) {
    return true;
  }
  return false;
}

/** Return a 401 response. */
function unauthorized(): Response {
  return Response.json({ error: "Unauthorized" }, { status: 401 });
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

      const stub = env.LUCINEER_SESSION.getByName("default");
      const withinLimit = await stub.checkRateLimit(body.sessionId);
      if (!withinLimit) {
        return Response.json(
          { error: "Rate limit exceeded. Max 10 messages per minute per session." },
          { status: 429 },
        );
      }

      const { jobId } = await stub.createJob(body);

      // The processor polls /api/jobs/pending — no push path needed.
      return Response.json({ jobId, status: "processing" });
    }

    // =====================================================================
    // CLIENT POLLING — No auth required
    // The Roblox client polls this endpoint to check job status.
    // The jobId itself serves as a capability token — knowing the ID
    // is sufficient to read status. This is the T-Minus model.
    // =====================================================================
    if (path.startsWith("/api/job/") && method === "GET") {
      const jobId = path.replace("/api/job/", "");
      // Guard against sub-paths like /api/job/:id/result on GET
      if (jobId.includes("/")) {
        // Sub-path GETs aren't public endpoints — fall through to auth gate
      } else {
        const stub = env.LUCINEER_SESSION.getByName("default");
        const job = await stub.getJob(jobId);
        if (!job) {
          return Response.json({ error: "Job not found" }, { status: 404 });
        }
        return Response.json(job);
      }
    }

    // =====================================================================
    // INTERNAL ENDPOINTS — Require processor auth
    // Everything below this point requires a valid X-Lucineer-Key.
    // The Roblox client never touches these.
    // =====================================================================
    if (!isAuthorized(request, env)) {
      return unauthorized();
    }

    // --- GET /api/diag — diagnostic endpoint (now behind auth) ---
    if (path === "/api/diag" && method === "GET") {
      try {
        const stub = env.LUCINEER_SESSION.getByName("default");
        const result = await stub.diag();
        return Response.json(result);
      } catch (e) {
        return Response.json({ error: String(e) }, { status: 500 });
      }
    }

    // --- POST /api/job/:jobId/result — processor posts results ---
    const resultMatch = path.match(/^\/api\/job\/([\da-f]+)\/result$/);
    if (resultMatch && method === "POST") {
      const jobId = resultMatch[1];
      let body: JobResult;
      try {
        body = (await request.json()) as JobResult;
      } catch {
        return Response.json({ error: "Invalid JSON" }, { status: 400 });
      }

      if (!body.reply) {
        return Response.json({ error: "Missing required field: reply" }, { status: 400 });
      }

      const stub = env.LUCINEER_SESSION.getByName("default");
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

    // --- POST /api/job/:jobId/claim — atomically claim a job ---
    const claimMatch = path.match(/^\/api\/job\/([\da-f]+)\/claim$/);
    if (claimMatch && method === "POST") {
      const jobId = claimMatch[1];
      const stub = env.LUCINEER_SESSION.getByName("default");
      const job = await stub.claimJob(jobId);
      if (!job) {
        return Response.json(
          { ok: false, error: "Job already claimed or not found" },
          { status: 409 },
        );
      }
      return Response.json({ ok: true, job });
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

      const stub = env.LUCINEER_SESSION.getByName("default");
      await stub.updateWorldState(body.sessionId, body.worldSnapshot);
      return Response.json({ ok: true });
    }

    // --- GET /api/state/:sessionId — retrieve world state ---
    const stateMatch = path.match(/^\/api\/state\/(.+)$/);
    if (stateMatch && method === "GET") {
      const sessionId = decodeURIComponent(stateMatch[1]);
      const stub = env.LUCINEER_SESSION.getByName("default");
      const state = await stub.getWorldState(sessionId);
      if (!state) {
        return Response.json({ error: "No state found for session" }, { status: 404 });
      }
      return Response.json(state);
    }

    // --- GET /api/jobs/pending — processor polls for unprocessed jobs ---
    if (path === "/api/jobs/pending" && method === "GET") {
      const stub = env.LUCINEER_SESSION.getByName("default");
      const jobs = await stub.getPendingJobs();
      return Response.json({
        jobs,
        notice: "Call POST /api/job/:jobId/claim before processing to prevent duplicate work.",
      });
    }

    // =====================================================================
    // R2 MOLT TRAJECTORY WRITER
    // POST /api/trajectory — writes session events to R2.
    // "The only item where delay is unrecoverable" — Grand Plan Phase 1.
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

      // Write to R2 — one object per trajectory write, keyed by session + timestamp.
      // This is append-only: each write is a separate JSONL object so partial
      // failures never corrupt earlier data.
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
        // R2 write failure is critical — trajectories are the highest-option-value
        // data in the system. Return 500 so the processor knows to retry.
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
