import { LucineerSession } from "./do/LucineerSession";
import type { Env, IncomingMessage, JobResult } from "./types";

export { LucineerSession };

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // --- Health check (no auth) ---
    if (path === "/api/health" && method === "GET") {
      return Response.json({ status: "ok", timestamp: Date.now() });
    }

    // --- Auth check for all other endpoints ---
    const authKey = request.headers.get("X-Lucineer-Key");
    if (!authKey || authKey !== env.LUCINEER_KEY) {
      return Response.json({ error: "Unauthorized" }, { status: 401 });
    }

    // --- POST /api/message — receive chat from Roblox ---
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

      // Jobs live in the default DO; world state is session-scoped
      const stub = env.LUCINEER_SESSION.getByName("default");
      const { jobId } = await stub.createJob(body);

      // Asynchronously forward to OpenClaw
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

      // Fire and forget — the result comes back via the callback
      try {
        const callbackBase =
          env.OPENCLAW_CALLBACK_URL || "http://172.22.219.126:18789/api/lucineer/message";
        await fetch(callbackBase, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Lucineer-Key": env.LUCINEER_KEY,
          },
          body: JSON.stringify(openclawPayload),
        });
      } catch (err) {
        // OpenClaw might be down; mark the job as error
        await stub.setJobError(
          jobId,
          `Failed to reach OpenClaw: ${err instanceof Error ? err.message : String(err)}`,
        );
        return Response.json(
          { jobId, error: "Failed to forward to OpenClaw" },
          { status: 502 },
        );
      }

      return Response.json({ jobId, status: "processing" });
    }

    // --- GET /api/job/:jobId — poll job status ---
    const jobMatch = path.match(/^\/api\/job\/([\da-f]+)$/);
    if (jobMatch && method === "GET") {
      const jobId = jobMatch[1];
      // We don't know which session this belongs to, so try the default DO
      const stub = env.LUCINEER_SESSION.getByName("default");
      const job = await stub.getJob(jobId);
      if (!job) {
        return Response.json({ error: "Job not found" }, { status: 404 });
      }
      return Response.json(job);
    }

    // --- POST /api/job/:jobId/result — OpenClaw posts result ---
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
      return Response.json({ ok: true, jobId });
    }

    // --- POST /api/state — update world state ---
    if (path === "/api/state" && method === "POST") {
      let body: { sessionId: string; worldSnapshot: Record<string, unknown> };
      try {
        body = (await request.json()) as { sessionId: string; worldSnapshot: Record<string, unknown> };
      } catch {
        return Response.json({ error: "Invalid JSON" }, { status: 400 });
      }

      if (!body.sessionId || !body.worldSnapshot) {
        return Response.json(
          { error: "Missing required fields: sessionId, worldSnapshot" },
          { status: 400 },
        );
      }

      // World state lives in the session-scoped DO
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
    if (path === "/api/jobs/pending" && method === "GET") {
      const stub = env.LUCINEER_SESSION.getByName("default");
      const jobs = await stub.getPendingJobs();
      return Response.json({ jobs });
    }

    // --- 404 ---
    return Response.json({ error: "Not found" }, { status: 404 });
  },
} satisfies ExportedHandler<Env>;
