import { LucineerSession } from "./do/LucineerSession";
import type { Env, IncomingMessage, JobResult } from "./types";

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

    // Diagnostic endpoint — shows DO schema state
    if (path === "/api/diag" && method === "GET") {
      try {
        const stub = env.LUCINEER_SESSION.getByName("default");
        const result = await stub.diag();
        return Response.json(result);
      } catch (e) {
        return Response.json({ error: String(e) }, { status: 500 });
      }
    }

    // =====================================================================
    // PUBLIC ENDPOINT — POST /api/message
    // No auth required (the Roblox client doesn't have the internal key).
    // Rate-limited per session to prevent abuse.
    // FIX #3: Removed auth requirement from this player-facing endpoint.
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

      // FIX #3: Basic rate limiting — max 10 messages per session per minute
      const stub = env.LUCINEER_SESSION.getByName("default");
      const withinLimit = await stub.checkRateLimit(body.sessionId);
      if (!withinLimit) {
        return Response.json(
          { error: "Rate limit exceeded. Max 10 messages per minute per session." },
          { status: 429 },
        );
      }

      const { jobId } = await stub.createJob(body);

      // Asynchronously forward to OpenClaw (push path).
      // FIX #6d: Make push failure non-fatal — the processor also polls.
      // The job exists in the DO regardless; if push fails, polling picks it up.
      const callbackUrl = `${url.origin}/api/job/${jobId}/result`;
      const openclawPayload = {
        jobId,
        sessionId: body.sessionId,
        playerName: body.playerName,
        message: body.message,
        playerState: body.playerState ?? null,
        worldSnapshot: body.worldSnapshot ?? null,
        callbackUrl,
      };

      const callbackBase =
        env.OPENCLAW_CALLBACK_URL ||
        "${OPENCLAW_CALLBACK_URL}";

      // Fire and forget — don't fail the request if push is unavailable.
      // The processor also polls /api/jobs/pending, so the job will be picked up.
      try {
        await fetch(callbackBase, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(openclawPayload),
        });
      } catch (err) {
        // Push failed — log and continue. The polling processor will pick this up.
        console.warn(
          `[lucineer] Push to processor failed (job ${jobId}); falling back to poll. ` +
            `Error: ${err instanceof Error ? err.message : String(err)}`,
        );
      }

      return Response.json({ jobId, status: "processing" });
    }

    // =====================================================================
    // INTERNAL ENDPOINTS — Require processor auth
    // FIX #3: All endpoints below require LUCINEER_INTERNAL_KEY (or legacy
    // LUCINEER_KEY). The Roblox client never touches these.
    // =====================================================================
    if (!isAuthorized(request, env)) {
      return unauthorized();
    }

    // --- GET /api/job/:jobId — poll job status ---
    const jobMatch = path.match(/^\/api\/job\/([\da-f]+)$/);
    if (jobMatch && method === "GET") {
      const jobId = jobMatch[1];
      const stub = env.LUCINEER_SESSION.getByName("default");
      const job = await stub.getJob(jobId);
      if (!job) {
        return Response.json({ error: "Job not found" }, { status: 404 });
      }
      return Response.json(job);
    }

    // --- POST /api/job/:jobId/result — OpenClaw posts result ---
    // FIX #5: The result includes a `filtered: false` field to signal the
    // client that TextService:FilterStringAsync() MUST be applied before
    // displaying the reply to any player.
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

      // FIX #5: Return explicit signal that filtering is required.
      // The Roblox client MUST call TextService:FilterStringAsync() on
      // `reply` before displaying it to any player. This is a Roblox
      // policy requirement for any user-influenced text shown to others.
      return Response.json({
        ok: true,
        jobId,
        filtered: false,
        filterNotice:
          "TextService:FilterStringAsync() must be called on `reply` before display. " +
          "This is required by Roblox policy for user-influenced text.",
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

    // --- GET /api/jobs/pending — OpenClaw polls for unprocessed jobs ---
    // FIX #6: Returns only jobs that are unclaimed (claimed_at IS NULL).
    // Processors should call claimJob(jobId) immediately after selecting
    // a job to prevent duplicate processing.
    if (path === "/api/jobs/pending" && method === "GET") {
      const stub = env.LUCINEER_SESSION.getByName("default");
      const jobs = await stub.getPendingJobs();
      return Response.json({
        jobs,
        // Remind processors to claim before working
        notice: "Call POST /api/job/:jobId/claim before processing to prevent duplicate work.",
      });
    }

    // --- POST /api/job/:jobId/claim — atomically claim a job ---
    // FIX #6: Atomic job claiming. Returns the job if the claim succeeded,
    // or null if another processor already claimed it.
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

    // --- 404 ---
    return Response.json({ error: "Not found" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
