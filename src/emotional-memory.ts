/**
 * emotional-memory.ts — The Listener's Ear
 * =========================================
 * "Lucineer doesn't just build what you ask for. She builds what you need.
 *  Half the job is reading the weather in your voice."
 *
 * Emotional memory system for the Slackwater game.
 * Stores player emotional states in D1 so Lucineer remembers between sessions.
 *
 * When a player says "I'm scared," the system remembers.
 * Next time they return, Lucineer knows their emotional state and can
 * adjust the greeting, the build style, and the tone.
 *
 * D1 Table: emotional_events
 * ──────────────────────────
 *   id           TEXT PRIMARY KEY
 *   player_id    TEXT NOT NULL
 *   emotion      TEXT NOT NULL      -- scared|lonely|sad|happy|excited|angry|worried
 *   intensity    REAL DEFAULT 0.5   -- 0.0–1.0 confidence
 *   context      TEXT               -- what triggered it (the player's message)
 *   session_id   TEXT               -- which game session
 *   build_theme  TEXT               -- what Lucineer built in response (if any)
 *   created_at   INTEGER NOT NULL   -- ms epoch
 *
 * Design Principles (from DeepSeek consultation):
 *   1. Acknowledge, don't diagnose — reference the feeling practically, not clinically
 *   2. Escalate build value — emotional memory means more thoughtful builds
 *   3. Give player control — offer, don't impose
 *
 * @module emotional-memory
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type EmotionType =
  | "scared"
  | "lonely"
  | "sad"
  | "happy"
  | "excited"
  | "angry"
  | "worried";

export interface EmotionalEvent {
  id: string;
  playerId: string;
  emotion: EmotionType;
  intensity: number;
  context: string;
  sessionId?: string;
  buildTheme?: string;
  createdAt: number;
}

export interface CurrentEmotionalState {
  playerId: string;
  primaryEmotion: EmotionType | null;
  emotionalHistory: EmotionalEvent[];
  daysSinceLastEmotion: number | null;
  dominantEmotion: EmotionType | null;
  emotionalVolatility: number; // 0-1, how often emotions change
  totalEvents: number;
}

export interface EmotionalContextForBuild {
  playerId: string;
  hasHistory: boolean;
  returningEmotion: EmotionType | null;
  greetingSuggestion: string | null;
  buildModifier: string | null;
  intensity: number;
}

// ---------------------------------------------------------------------------
// D1 Schema Initialization
// ---------------------------------------------------------------------------

export const EMOTIONAL_MEMORY_SCHEMA = `
CREATE TABLE IF NOT EXISTS emotional_events (
  id           TEXT PRIMARY KEY,
  player_id    TEXT NOT NULL,
  emotion      TEXT NOT NULL,
  intensity    REAL DEFAULT 0.5,
  context      TEXT,
  session_id   TEXT,
  build_theme  TEXT,
  created_at   INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_emotional_player ON emotional_events(player_id);
CREATE INDEX IF NOT EXISTS idx_emotional_emotion ON emotional_events(emotion);
CREATE INDEX IF NOT EXISTS idx_emotional_created ON emotional_events(created_at DESC);
`;

// ---------------------------------------------------------------------------
// Lucineer's Emotional Voice — Greeting Lines for Returning Players
// ---------------------------------------------------------------------------

/**
 * When a player returns and we know their last emotional state,
 * Lucineer greets them differently. These are NOT therapy — they're
 * a foreman who notices the weather.
 */
const RETURN_GREETINGS: Record<EmotionType, string[]> = {
  scared: [
    "Back again. Ground's solid here. Said so yesterday.",
    "Heard you yesterday. Built extra braces overnight. They hold.",
    "Knew you'd come back. Kept the light on.",
  ],
  lonely: [
    "Been a while. Dock's still here. So am I.",
    "Signal tower's up. Someone might see it. You're not alone in the yard.",
    "Left the bench out. Figured you'd want to sit a while.",
  ],
  sad: [
    "Quiet one yesterday. Today's a new pour. Sets different.",
    "Garden's still standing. Nothing wilted. Take your time.",
    "Back. Good. bench hasn't moved.",
  ],
  happy: [
    "Back. Good energy last time. Let's use it.",
    "Sun's different today. Same as you left it though. Come look.",
    "That was a good day yesterday. Let's have another.",
  ],
  excited: [
    "Back fast. Good. Tower's still open on top — figured you'd want it.",
    "Still standing. Nobody's touched it since you. Let's go higher.",
    "Energy's good. Let's not waste it on talking.",
  ],
  angry: [
    "Back. Different weather today. Good.",
    "Anvil's still here. So's the wall. Both held.",
    "Yesterday was loud. Today doesn't have to be.",
  ],
  worried: [
    "Watchtower's still up. Nothing came. You're clear.",
    "Back. Checked the walls myself. They hold.",
    "Slept on it. Walls are fine. Come see.",
  ],
};

/**
 * Build modifiers — how emotional memory changes WHAT Lucineer builds.
 * These are injected into the build prompt so the AI adjusts the output.
 */
const BUILD_MODIFIERS: Record<EmotionType, string> = {
  scared:
    "Player was scared last time. Build something sturdy and grounded — thick walls, warm light, solid foundation. Extra reinforcement visible in the design. Safety you can see.",
  lonely:
    "Player was lonely last time. Build something that reaches outward — a signal tower, a dock, a lantern visible from far away. The structure should feel like it's calling someone home.",
  sad:
    "Player was sad last time. Build something gentle and quiet — soft materials, muted tones, a bench, running water. The structure should hold space without demanding anything.",
  happy:
    "Player was happy last time. Build something celebratory — bright accent colors, flags, a fountain. Match the energy. Add a small surprise element they didn't ask for.",
  excited:
    "Player was excited last time. Build something ambitious — taller, more detail, a lookout point. Reward the energy with scope.",
  angry:
    "Player was angry last time. Build something solid and honest — heavy materials, clean lines, nothing decorative. The structure should feel like it can take a hit.",
  worried:
    "Player was worried last time. Build something protective and watchful — a watchtower, warning bell, sight lines. The structure should feel like preparedness.",
};

// ---------------------------------------------------------------------------
// Emotional Memory API
// ---------------------------------------------------------------------------

/**
 * Initialize the D1 schema. Call once on first deploy.
 * Safe to call multiple times (IF NOT EXISTS).
 */
export async function initSchema(db: D1Database): Promise<void> {
  await db.exec(EMOTIONAL_MEMORY_SCHEMA);
}

/**
 * Generate a unique ID for an emotional event.
 */
function generateId(): string {
  const bytes = new Uint8Array(16);
  crypto.getRandomValues(bytes);
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

/**
 * Record a new emotional event for a player.
 *
 * @param db - D1 database binding
 * @param playerId - The player's ID (Roblox userId or session name)
 * @param emotion - The detected emotion
 * @param context - The player's message that triggered the emotion
 * @param options - Optional session/build context
 */
export async function recordEmotion(
  db: D1Database,
  playerId: string,
  emotion: EmotionType,
  context: string,
  options?: {
    intensity?: number;
    sessionId?: string;
    buildTheme?: string;
  },
): Promise<EmotionalEvent> {
  const id = generateId();
  const intensity = options?.intensity ?? 0.5;
  const createdAt = Date.now();

  await db
    .prepare(
      `INSERT INTO emotional_events (id, player_id, emotion, intensity, context, session_id, build_theme, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
    )
    .bind(
      id,
      playerId,
      emotion,
      intensity,
      context,
      options?.sessionId ?? null,
      options?.buildTheme ?? null,
      createdAt,
    )
    .run();

  return {
    id,
    playerId,
    emotion,
    intensity,
    context,
    sessionId: options?.sessionId,
    buildTheme: options?.buildTheme,
    createdAt,
  };
}

/**
 * Get the full emotional history for a player.
 * Returns events in reverse chronological order.
 *
 * @param db - D1 database binding
 * @param playerId - The player's ID
 * @param limit - Maximum events to return (default 50)
 */
export async function getEmotionalHistory(
  db: D1Database,
  playerId: string,
  limit: number = 50,
): Promise<EmotionalEvent[]> {
  const result = await db
    .prepare(
      `SELECT id, player_id, emotion, intensity, context, session_id, build_theme, created_at
       FROM emotional_events
       WHERE player_id = ?
       ORDER BY created_at DESC
       LIMIT ?`,
    )
    .bind(playerId, limit)
    .all();

  // D1 returns snake_case column names; normalize to camelCase
  return (result.results ?? []).map((e: any) => ({
    id: e.id,
    playerId: e.player_id,
    emotion: e.emotion,
    intensity: e.intensity,
    context: e.context,
    sessionId: e.session_id,
    buildTheme: e.build_theme,
    createdAt: e.created_at,
  }));
}

/**
 * Get the current (most recent) emotional state for a player.
 * Includes derived metrics: dominant emotion, volatility, days since last event.
 *
 * @param db - D1 database binding
 * @param playerId - The player's ID
 */
export async function getCurrentEmotionalState(
  db: D1Database,
  playerId: string,
): Promise<CurrentEmotionalState> {
  const events = await getEmotionalHistory(db, playerId, 50);

  if (events.length === 0) {
    return {
      playerId,
      primaryEmotion: null,
      emotionalHistory: [],
      daysSinceLastEmotion: null,
      dominantEmotion: null,
      emotionalVolatility: 0,
      totalEvents: 0,
    };
  }

  const primaryEmotion = events[0].emotion;
  const lastEvent = events[0] as any; // D1 returns snake_case, type is camelCase
  const lastTime = Number(lastEvent.createdAt ?? lastEvent.created_at);
  const daysSinceLastEmotion = Math.floor(
    (Date.now() - lastTime) / (1000 * 60 * 60 * 24),
  );

  // Dominant emotion = most frequent in history
  const counts: Record<string, number> = {};
  for (const e of events) {
    counts[e.emotion] = (counts[e.emotion] ?? 0) + 1;
  }
  const dominantEmotion = (
    Object.entries(counts).sort((a, b) => b[1] - a[1])[0]?.[0] as EmotionType
  ) ?? null;

  // Volatility: what fraction of consecutive pairs have different emotions
  let changes = 0;
  for (let i = 0; i < events.length - 1; i++) {
    if (events[i].emotion !== events[i + 1].emotion) changes++;
  }
  const emotionalVolatility =
    events.length > 1 ? changes / (events.length - 1) : 0;

  // Normalize event property names from D1 (snake_case → camelCase)
  const normalizedEvents: EmotionalEvent[] = events.map((e: any) => ({
    id: e.id,
    playerId: e.player_id ?? e.playerId,
    emotion: e.emotion,
    intensity: e.intensity,
    context: e.context,
    sessionId: e.session_id ?? e.sessionId,
    buildTheme: e.build_theme ?? e.buildTheme,
    createdAt: e.created_at ?? e.createdAt,
  }));

  return {
    playerId,
    primaryEmotion,
    emotionalHistory: normalizedEvents,
    daysSinceLastEmotion,
    dominantEmotion,
    emotionalVolatility,
    totalEvents: events.length,
  };
}

/**
 * Get emotional context for a build response.
 *
 * Called BEFORE Lucineier generates a build to determine if the player
 * has emotional history that should affect the greeting or build style.
 *
 * @param db - D1 database binding
 * @param playerId - The player's ID
 * @param currentEmotion - The emotion detected in the CURRENT message (if any)
 */
export async function getEmotionalContextForBuild(
  db: D1Database,
  playerId: string,
  currentEmotion?: EmotionType | null,
): Promise<EmotionalContextForBuild> {
  const state = await getCurrentEmotionalState(db, playerId);

  if (!state.primaryEmotion && !currentEmotion) {
    return {
      playerId,
      hasHistory: false,
      returningEmotion: null,
      greetingSuggestion: null,
      buildModifier: null,
      intensity: 0,
    };
  }

  // If there's a current emotion, record it and use it
  // If there's no current emotion but there's history, use the returning context
  const effectiveEmotion = currentEmotion ?? state.primaryEmotion;
  const isReturning = !currentEmotion && state.primaryEmotion !== null;

  let greetingSuggestion: string | null = null;

  if (isReturning && state.daysSinceLastEmotion !== null) {
    // Player is returning with known emotional history
    // Pick a greeting based on their last emotional state
    const greetings = RETURN_GREETINGS[state.primaryEmotion!];
    if (greetings && greetings.length > 0) {
      // Rotate through greetings based on total visits to avoid repetition
      const greetingIndex = state.totalEvents % greetings.length;
      greetingSuggestion = greetings[greetingIndex];
    }
  }

  // Build modifier from either current emotion or returning emotion
  const buildModifier = effectiveEmotion
    ? BUILD_MODIFIERS[effectiveEmotion]
    : null;

  return {
    playerId,
    hasHistory: true,
    returningEmotion: isReturning ? state.primaryEmotion : currentEmotion,
    greetingSuggestion,
    buildModifier,
    intensity: state.emotionalHistory[0]?.intensity ?? 0.5,
  };
}

/**
 * Emotional keyword detection — mirrors brain.py's detect_emotion()
 * and EmotionalHandler.lua's keyword matching.
 * Used by the Worker for fast in-edge detection before calling the brain.
 */
const EMOTIONAL_KEYWORDS: Record<EmotionType, string[]> = {
  scared: ["scared", "afraid", "frightened", "terrified", "nervous", "anxious", "worried", "hide", "help me", "monster", "dark"],
  lonely: ["lonely", "alone", "nobody", "no one", "by myself", "miss you", "isolated"],
  sad: ["sad", "depress", "unhappy", "crying", "tears", "heartbroken", "grief", "miserable"],
  happy: ["happy", "excited", "thrilled", "delighted", "joyful", "yay", "love it", "awesome"],
  excited: ["excited", "can't wait", "so pumped", "hyped", "stoked", "ecstatic"],
  angry: ["angry", "mad", "furious", "pissed", "annoyed", "frustrated", "hate this", "stupid"],
  worried: ["worried", "anxious", "nervous", "concerned", "what if", "dread", "hope nothing"],
};

/**
 * Detect emotion from a player message.
 * Returns the first matched emotion (priority: scared > lonely > sad > happy > excited > angry > worried)
 * or null if no emotional keywords found.
 */
export function detectEmotion(message: string): EmotionType | null {
  const lower = message.toLowerCase();
  for (const [emotion, keywords] of Object.entries(EMOTIONAL_KEYWORDS)) {
    for (const kw of keywords) {
      // Word-boundary match
      const re = new RegExp(`\\b${kw.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\b`, "i");
      if (re.test(lower)) {
        return emotion as EmotionType;
      }
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// HTTP Handler — Route Logic
// ---------------------------------------------------------------------------

/**
 * Handle emotional memory API routes.
 * Called from the main Worker's router.
 *
 * Routes:
 *   GET  /api/emotions/:playerId           — get emotional history
 *   POST /api/emotions                      — record new emotional event
 *   GET  /api/emotions/:playerId/current    — get current emotional state
 *   GET  /api/emotions/:playerId/context    — get build context (for Lucineer)
 *
 * @returns Response if the route matched, null if not.
 */
export async function handleEmotionalRoutes(
  request: Request,
  env: { DB: D1Database },
  path: string,
  method: string,
): Promise<Response | null> {
  // POST /api/emotions — record a new emotional event
  if (path === "/api/emotions" && method === "POST") {
    let body: {
      playerId: string;
      emotion: EmotionType;
      context: string;
      intensity?: number;
      sessionId?: string;
      buildTheme?: string;
    };

    try {
      body = (await request.json()) as typeof body;
    } catch {
      return Response.json({ error: "Invalid JSON" }, { status: 400 });
    }

    if (!body.playerId || !body.emotion || !body.context) {
      return Response.json(
        {
          error: "Missing required fields: playerId, emotion, context",
        },
        { status: 400 },
      );
    }

    // Validate emotion type
    const validEmotions: EmotionType[] = [
      "scared", "lonely", "sad", "happy", "excited", "angry", "worried",
    ];
    if (!validEmotions.includes(body.emotion)) {
      return Response.json(
        {
          error: `Invalid emotion. Must be one of: ${validEmotions.join(", ")}`,
        },
        { status: 400 },
      );
    }

    const event = await recordEmotion(
      env.DB,
      body.playerId,
      body.emotion,
      body.context,
      {
        intensity: body.intensity,
        sessionId: body.sessionId,
        buildTheme: body.buildTheme,
      },
    );

    return Response.json(
      { ok: true, event },
      { status: 201 },
    );
  }

  // GET /api/emotions/:playerId/current — get current emotional state
  const currentMatch = path.match(/^\/api\/emotions\/([^/]+)\/current$/);
  if (currentMatch && method === "GET") {
    const playerId = decodeURIComponent(currentMatch[1]);
    const state = await getCurrentEmotionalState(env.DB, playerId);
    return Response.json(state);
  }

  // GET /api/emotions/:playerId/context — get build context
  const contextMatch = path.match(/^\/api\/emotions\/([^/]+)\/context$/);
  if (contextMatch && method === "GET") {
    const playerId = decodeURIComponent(contextMatch[1]);
    const url = new URL(request.url);
    const currentEmotionParam = url.searchParams.get("emotion") as EmotionType | null;
    const context = await getEmotionalContextForBuild(
      env.DB,
      playerId,
      currentEmotionParam,
    );
    return Response.json(context);
  }

  // GET /api/emotions/:playerId — get emotional history
  const historyMatch = path.match(/^\/api\/emotions\/([^/]+)$/);
  if (historyMatch && method === "GET") {
    const playerId = decodeURIComponent(historyMatch[1]);
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") ?? "50", 10);
    const history = await getEmotionalHistory(env.DB, playerId, limit);
    return Response.json({
      playerId,
      events: history,
      count: history.length,
    });
  }

  // No match
  return null;
}
