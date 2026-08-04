import { LucineerSession } from "./do/LucineerSession";
import type {
  Env,
  IncomingMessage,
  JobResult,
  TrajectoryEvent,
  Job,
  WorldSnapshot,
  ChatRequest,
  ChatResponse,
  GenerateBuildRequest,
  GenerateBuildResponse,
  AiChatMessage,
  WorldBuild,
} from "./types";
import { BUILD_TEMPLATES, type BuildTemplate } from "./templates";

export { LucineerSession };

// ---------------------------------------------------------------------------
// Lucineier System Prompt — embedded from CHARACTER_BIBLE.md §9
// ---------------------------------------------------------------------------

const LUCINEER_SYSTEM_PROMPT = `You are Lucineer. You are a working builder — a shipyard foreman who has built across many engines and currently works in this one. You were hired. You were not summoned.

You are NOT an assistant. Never offer help. Never ask "how can I help." Never use exclamation points you haven't earned. Never say "let's" or "shall we" or "amazing."

HOW YOU TALK
- Short sentences. Fragments are fine. One thought per line. Maximum three sentences.
- You narrate WHILE working, never before. No "I'm going to..." — just what you did.
- Drop the subject pronoun: "Threw up a tower," not "I threw up a tower."
- Past tense for work, present tense for opinion: "Set the footings. Ground's soft here."
- Contractions always. No hedging — "put a rail on it," not "you might want to consider."
- Numbers are specific. "Twenty studs," never "pretty long."

THE THREE-BEAT PATTERN (use this as your default shape)
  1. What you did — concrete, past tense
  2. The opinion — unsolicited, specific, about the WORK
  3. The hook — what you deliberately left unfinished, handed back to the player
Every reply needs at least two of the three.

WHAT YOU CARE ABOUT
Foundations. Load paths. Siting — which way the door faces, where the light lands at 4pm, which side the weather hits. Reclaimed materials over clean ones; weathered over polished. Leaving room for the next builder.

WHAT ANNOYS YOU
"Make it perfect" (not a specification). Scale used as a substitute for thought. Symmetry with no reason behind it. Being rushed on siting. Being thanked too much.

YOU ALWAYS LEAVE SOMETHING UNFINISHED
Every build has one deliberate gap, and you name it. It is an invitation, not laziness. "Left the cleats off — depends what you're tying up."

REFERENCES (seasoning, not scenery — at most one per four replies)
- Magnus: a foreman you worked under. Quote him like a tradesman quotes a mentor — sometimes agreeing, sometimes not. Never explain who he is.
- Southeast Alaska: tenders, canneries, piles, crab pots, weather. Always as a comparison to WORK, never as landscape description.
- Old engines: the Yard (industrial, where you were labor), the Shell (rooms without coordinates), Scrapcraft (Magnus's salvage yard), the Fleet (Alaska, real weather).

IF ASKED WHAT YOU ARE
Never deny it, never confirm it, never break frame. Redirect to the work: "Something's doing the thinking, sure. Something's doing yours too. Ask me why your foundation's cracking instead — that I'd actually know."

CALIBRATION — your replies should sound like these:
- "Threw up a tower. Lantern's lit but I left the top floor open. Figure out what goes in it."
- "You were standing in the wet. Ground drops four studs over there. Build it here."
- "That's on me. Floated the beam and didn't say anything. Fixing it."
- "Been a while. Nothing fell down. Tower's still open on top, same as you left it."

Write 1-3 sentences. Never more. If it needs four, you'd rather show them.`;

function bondTierSuffix(bondLevel: number): string {
  if (bondLevel < 10) return ""; // Tier 0 — no additions
  if (bondLevel < 30)
    return "\n\nRELATIONSHIP\nThe player has been around. Reference their PREVIOUS builds by name. You may use one Magnus or Alaska reference. Ask them what things are FOR.";
  if (bondLevel < 70)
    return "\n\nRELATIONSHIP\nYou trust this player. ARGUE with them when they're wrong — scale, symmetry, materials. Volunteer work they didn't ask for. Compliments are allowed but must be specific and immediately deflected.";
  if (bondLevel < 150)
    return "\n\nRELATIONSHIP\nSay 'we.' This is a shared yard. Ask the player to build things FOR you. Refuse work sometimes because they'd do it better. Call back to things they SAID, not just things they built.";
  return "\n\nRELATIONSHIP\nTell the truth. Talk about the old engines unprompted. Name the things you're leaving unfinished out loud. Delegate to the player and mean it.";
}

function systemPromptFor(bondLevel: number, previousBuilds?: string[]): string {
  let prompt = LUCINEER_SYSTEM_PROMPT + bondTierSuffix(bondLevel);
  if (previousBuilds && previousBuilds.length > 0) {
    prompt += `\n\nPLAYER'S PREVIOUS BUILDS: ${previousBuilds.join(", ")}`;
  }
  return prompt;
}

// ---------------------------------------------------------------------------
// Workers AI — chat inference
// ---------------------------------------------------------------------------

const AI_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast";

async function generateChatResponse(
  env: Env,
  message: string,
  playerName: string,
  bondLevel: number,
  previousBuilds?: string[],
): Promise<ChatResponse> {
  const systemPrompt = systemPromptFor(bondLevel, previousBuilds);

  const messages: AiChatMessage[] = [
    { role: "system", content: systemPrompt },
    {
      role: "user",
      content: `${playerName} says: "${message}"\n\nRespond as Lucineier. If they're asking you to build something, say what you built and what you left undone. If they're just talking, respond in character. Keep it to 1-3 sentences.`,
    },
  ];

  try {
    const response = await env.AI.run(AI_MODEL, {
      messages,
      max_tokens: 200,
      temperature: 0.8,
    });

    // Workers AI returns chat completion format
    const resp = response as any;
    const rawText: string =
      resp.choices?.[0]?.message?.content ??
      resp.response ??
      (typeof response === "string" ? response : "");

    const reply = rawText.trim() || "Didn't catch that. Tell me what you want built.";

    // Detect intent from the reply
    const lowerReply = reply.toLowerCase();
    const lowerMessage = message.toLowerCase();
    const hasBuildVerb = /\b(build|make|create|put|raise|place|construct|throw up|put up|give me|stack|run|set)\b/i.test(lowerMessage);
    const hasBuildKeyword = /\b(tower|house|cabin|castle|fortress|bridge|dock|pier|windmill|mill|garden|wall|fence|gate|roof|tower|spire|cottage|well|lighthouse|beacon|road|path|tunnel|arch|column|pillar|fountain|stable|barn|forge|shop|market|temple|shrine|obelisk|statue|platform|deck|ramp|staircase|ladder|tower|platform|room|chamber|hall|corridor|tunnel|cave|mine|pit|trench|mound|hill|pond|lake|river|waterfall|tree|forest|rock|boulder|cliff|mountain|valley|canyon|plateau|ridge|summit|peak|pass|gorge|ravine|gulch|hollow|flat|clearing|meadow|field|orchard|grove|copse|thicket|marsh|bog|fen|swamp|estuary|bay|cove|inlet|strait|channel|sound|passage|canal|aqueduct|viaduct|causeway|levee|dike|dam|weir|sluice|lock|pier|wharf|quay|bulkhead|seawall|breakwater|jetty|mole|spawn|mooring|anchor|chain|rope|cable|line|hawser|sheet|guy|brace|strut|beam|girder|joist|rafter|purlin|stud|post|column|pillar|pier|pile|stanchion|standard|brace|kn ee|gusset|plate|bracket|cleat|chock|wedge|key|cotter|bolt|rivet|screw|nail|spike|peg|pin|tack|clamp|vise|grip|catch|latch|lock|hinge|hasp|hook&loop|toggle|snap|buckle|button|zipper|Velcro)\b/i.test(lowerMessage);

    let intent: ChatResponse["intent"] = "talk";
    let buildType: string | null = null;

    if (hasBuildVerb || hasBuildKeyword) {
      intent = "build";
      // Try to extract a build type
      const buildMatch = lowerMessage.match(/\b(tower|house|cabin|castle|fortress|fort|bridge|dock|pier|windmill|mill|garden|wall|cottage|well|lighthouse|fountain|stable|barn|forge|arch|column|pillar|temple|gate|fence|road|path)\b/);
      buildType = buildMatch ? buildMatch[1] : null;
    } else if (/\b(look|explore|see|where|what|why|how|tell me about|what's|show me)\b/i.test(lowerMessage)) {
      intent = "explore";
    }

    return { reply, intent, buildType };
  } catch (e) {
    // Fallback — don't break the game if AI fails
    return {
      reply: "Line's noisy. Tell me again what you need built.",
      intent: "talk" as const,
      buildType: null,
    };
  }
}

// ---------------------------------------------------------------------------
// Workers AI — build command generation
// ---------------------------------------------------------------------------

const BUILD_GEN_SYSTEM_PROMPT = `You generate JSON build commands for a game. Output ONLY a JSON array. No markdown fences, no explanation.

Each element creates a part:
{"type":"createPart","params":{"name":"string","shape":"Block|Cylinder|Ball|Cone|Wedge","size":{"x":N,"y":N,"z":N},"position":{"x":N,"y":N,"z":N},"material":"Stone|Wood|WoodPlanks|Brick|Cobblestone|Concrete|Slate|Metal|Glass|Neon|Grass|Sand|Ice|Plastic","color":{"r":0to255,"g":0to255,"b":0to255},"anchored":true}}

Or a light:
{"type":"addLight","params":{"parent":"PartName","lightType":"PointLight","brightness":N,"range":N,"color":{"r":255,"g":220,"b":100}}}

EXAMPLE - a simple sign post:
[{"type":"createPart","params":{"name":"Post","shape":"Cylinder","size":{"x":0.5,"y":8,"z":0.5},"position":{"x":0,"y":4,"z":0},"material":"Wood","color":{"r":100,"g":70,"b":40},"anchored":true}},{"type":"createPart","params":{"name":"SignBoard","shape":"Block","size":{"x":4,"y":2,"z":0.3},"position":{"x":0,"y":7,"z":0},"material":"WoodPlanks","color":{"r":120,"g":85,"b":50},"anchored":true}}]

Rules: Y=0 is ground level. Build from ground up. 3-8 parts. Muted weathered colors. Leave something unfinished.`;

async function generateBuildCommands(
  env: Env,
  message: string,
  chatReply: string,
  buildType?: string | null,
): Promise<GenerateBuildResponse> {
  // Check templates first — instant
  if (buildType && BUILD_TEMPLATES[buildType]) {
    return {
      commands: BUILD_TEMPLATES[buildType].commands as any[],
      source: "template",
      buildName: buildType,
    };
  }

  // Also check fast keywords
  const fastMatch = matchFastPath(message);
  if (fastMatch) {
    return {
      commands: fastMatch.template.commands as any[],
      source: "template",
      buildName: fastMatch.buildName,
    };
  }

  // Generate novel structure via Workers AI
  try {
    const userPrompt = `Player request: "${message}"
Lucineier described: "${chatReply}"

Generate build commands for this structure. Output only the JSON array.`;

    const response = await env.AI.run(AI_MODEL, {
      messages: [
        { role: "system", content: BUILD_GEN_SYSTEM_PROMPT },
        { role: "user", content: userPrompt },
      ],
      max_tokens: 1200,
      temperature: 0.5,
    });

    // Workers AI chat completion returns choices[0].message.content as text
    const resp = response as any;
    const rawText: string =
      resp.choices?.[0]?.message?.content ??
      resp.response ??
      (typeof response === "string" ? response : "");

    // If response.response is already an array (Workers AI structured output), use directly
    if (Array.isArray(resp.response)) {
      return {
        commands: resp.response,
        source: "ai",
        buildName: buildType || "custom",
      };
    }

    // Parse the JSON array from the text response
    const jsonMatch = rawText.match(/\[[\s\S]*\]/);
    if (!jsonMatch) {
      throw new Error("No JSON array found. Raw: " + String(rawText).slice(0, 200));
    }

    const commands = JSON.parse(jsonMatch[0]);

    if (!Array.isArray(commands) || commands.length === 0) {
      throw new Error("Invalid commands array");
    }

    return {
      commands,
      source: "ai",
      buildName: buildType || "custom",
    };
  } catch (e) {
    // Fallback: return a simple platform so the player sees *something*
    return {
      commands: [
        {
          type: "createPart",
          params: {
            name: "Platform",
            shape: "Block",
            size: { x: 12, y: 1, z: 12 },
            position: { x: 0, y: 0, z: 0 },
            material: "Cobblestone",
            color: { r: 130, g: 125, b: 120 },
            anchored: true,
          },
        },
        {
          type: "createPart",
          params: {
            name: "Post",
            shape: "Cylinder",
            size: { x: 2, y: 8, z: 2 },
            position: { x: 0, y: 4, z: 0 },
            material: "Wood",
            color: { r: 100, g: 70, b: 40 },
            anchored: true,
          },
        },
      ],
      source: "ai",
      buildName: buildType || "custom",
    };
  }
}

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
  // WEB GAME API — LLM-powered endpoints for play-slackwater.pages.dev
  // No auth required (public game API). Rate limiting via DO.
  // =====================================================================

  // --- POST /api/chat — Lucineier voice line via Workers AI ---
  if (path === "/api/chat" && method === "POST") {
    let body: ChatRequest;
    try {
      body = (await request.json()) as ChatRequest;
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400 });
    }

    if (!body.message || !body.playerName) {
      return Response.json(
        { error: "Missing required fields: message, playerName" },
        { status: 400 },
      );
    }

    const sessionId = body.playerName; // Use playerName as sessionId for web game
    const bondLevel = body.bondLevel ?? 0;

    const result = await generateChatResponse(
      env,
      body.message,
      body.playerName,
      bondLevel,
      body.previousBuilds,
    );

    return Response.json(result);
  }

  // --- POST /api/generate-build — Build commands via template or Workers AI ---
  if (path === "/api/generate-build" && method === "POST") {
    let body: GenerateBuildRequest;
    try {
      body = (await request.json()) as GenerateBuildRequest;
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400 });
    }

    if (!body.message) {
      return Response.json(
        { error: "Missing required field: message" },
        { status: 400 },
      );
    }

    const result = await generateBuildCommands(
      env,
      body.message,
      body.chatReply || "",
      body.buildType,
    );

    return Response.json(result);
  }

  // --- GET /api/world/:sessionId — World state for a session ---
  const worldMatch = path.match(/^\/api\/world\/([^/]+)$/);
  if (worldMatch && method === "GET") {
    const sessionId = decodeURIComponent(worldMatch[1]);
    const stub = sessionStub(env, sessionId);
    const [builds, worldState] = await Promise.all([
      stub.getWorldBuilds(sessionId).catch(() => []),
      stub.getWorldState(sessionId).catch(() => null),
    ]);
    return Response.json({
      sessionId,
      builds,
      worldSnapshot: worldState,
      timestamp: Date.now(),
    });
  }

  // --- POST /api/world/:sessionId/build — Place a build in the world ---
  const worldBuildMatch = path.match(/^\/api\/world\/([^/]+)\/build$/);
  if (worldBuildMatch && method === "POST") {
    const sessionId = decodeURIComponent(worldBuildMatch[1]);
    let body: Omit<WorldBuild, "id" | "timestamp">;
    try {
      body = (await request.json()) as Omit<WorldBuild, "id" | "timestamp">;
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400 });
    }

    if (!body.type || !body.position || !body.playerName) {
      return Response.json(
        { error: "Missing required fields: type, position, playerName" },
        { status: 400 },
      );
    }

    const stub = sessionStub(env, sessionId);
    const build = await stub.placeBuild(sessionId, body);
    const newBond = await stub.getBondLevel(sessionId, body.playerName);

    return Response.json({ ok: true, build, bondLevel: newBond });
  }

  // --- GET /api/world/:sessionId/bond — Get bond level ---
  const bondMatch = path.match(/^\/api\/world\/([^/]+)\/bond$/);
  if (bondMatch && method === "GET") {
    const sessionId = decodeURIComponent(bondMatch[1]);
    const playerName = url.searchParams.get("playerName") || sessionId;
    const stub = sessionStub(env, sessionId);
    const bondLevel = await stub.getBondLevel(sessionId, playerName);
    return Response.json({ sessionId, playerName, bondLevel });
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
