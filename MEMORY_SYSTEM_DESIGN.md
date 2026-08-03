# Lucineer Memory System Design

## Architecture Overview

```
┌────────────────────────────────────────────────────────────────┐
│                     process_v2.py (Processor)                   │
│                                                                │
│  ┌──────────────────────┐    ┌─────────────────────────────┐   │
│  │  SessionMemoryCache  │    │      D1 Persistent Store     │   │
│  │  (in-process, deque) │    │  (Cloudflare D1, via HTTP)   │   │
│  │                      │    │                              │   │
│  │  ┌──────────────┐    │    │  player_profiles             │   │
│  │  │ player: deque │    │    │  build_history               │   │
│  │  │ <10 turns>    │    │    │  conversations               │   │
│  │  └──────────────┘    │    │                              │   │
│  │  1h TTL, LRU evict  │    │  ┌───────────────────────┐    │   │
│  └──────────┬───────────┘    │  │  Vectorize Skill Index │    │   │
│             │                │  │  (semantic search)      │    │   │
│             │                │  └───────────────────────┘    │   │
│             │                └──────────────────────────────┘   │
│             │                         │                         │
│             ▼                         ▼                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              get_player_context()                          │   │
│  │                                                            │   │
│  │  Layers (merged into single context string):               │   │
│  │   1. Profile (bond_level, preferences)    ← D1            │   │
│  │   2. Build history (last 3 descriptions)  ← D1            │   │
│  │   3. Session cache (last 5 cached turns)  ← RAM           │   │
│  │   4. Conversation references ("earlier..")← RAM (extract) │   │
│  │   5. D1 conversations (last 5 turns)      ← D1            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                         │                                       │
│                         ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              call_brain()                                  │   │
│  │                                                            │   │
│  │  Enhanced message = player_message                        │   │
│  │    + World Context (nearby structures, time)              │   │
│  │    + Player Memory (all above layers)                     │   │
│  │    + Skill Library (top 3 Vectorize matches)              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Layer 1: D1 Persistent Storage (Cloudflare Workers D1)

### Tables

| Table             | Purpose                                      | Key Fields                              |
|-------------------|----------------------------------------------|-----------------------------------------|
| `player_profiles` | Player identity, bond level, preferences     | player_name, bond_level, preferences    |
| `build_history`   | Every structure Lucineer has built           | session_id, player_name, description    |
| `conversations`   | Full transcripts: player + assistant + system | session_id, player_name, role, content  |

### Functions (process_v2.py)

| Function                     | Line  | What It Does                                          |
|------------------------------|-------|-------------------------------------------------------|
| `upsert_player_profile()`    | 169   | Creates or updates player row; preserves bond_level   |
| `get_player_profile()`       | 184   | Fetches single player profile from D1                 |
| `log_build()`                | 194   | Records a build event with description, count, position|
| `get_recent_builds()`        | 209   | Fetches last N builds for a player (default 5)        |
| `log_conversation()`         | 216   | Persists a conversation turn (player/assistant/system) |
| `get_recent_conversations()` | 230   | Fetches last N turns for a session (default 5)         |
| `summarize_conversations()`  | 235   | Compacts D1 convos into brain-friendly summary         |

### Vectorize (Skill Search)

| Function         | Line  | What It Does                                     |
|------------------|-------|--------------------------------------------------|
| `search_skills()` | 304   | Semantic search against 35-skill library          |
| `format_skill_context()` | 341 | Formats matches as prompt string for brain       |

Threshold: `SKILL_SCORE_THRESHOLD = 0.6` — matches below this are discarded.

## Layer 2: SessionMemoryCache (In-Process)

### Why a cache?

Every job in the processor loop hits the `process_job()` function, which called
`get_player_context()` — triggering 3 D1 HTTP round-trips (profile, builds,
conversations). For a single player in a rapid building session, this is
wasteful. Additionally, the D1-stored conversations are capped at 5 turns
(`CONVERSATION_RECALL_LIMIT`) and only persist the raw text, with no structured
extraction of what the player actually said.

### Design

```
SessionMemoryCache
├── _players: OrderedDict[str, deque[Interaction]]   (max 100 players, LRU eviction)
├── _max_interactions: 10                             (per-player deque cap)
├── _ttl: 3600 seconds                                (idle player expiry)
│
├── add(player_name, message, reply)                  → called from save_to_memory()
├── get_player_context(player_name, current_message)   → fast context string
├── get_noteable_mentions(player_name, current_msg)    → extracted references
├── get_interactions(player_name)                      → raw Interaction list
├── get_turn_count(player_name)                        → session depth counter
├── flush_player(player_name)                          → manual eviction
└── stats()                                            → cache health for logging
```

Each `Interaction` stores:
- `timestamp` (float, time.time())
- `player_message` (str, the raw player input)
- `assistant_reply` (str, Luciner's response)
- `turn_count` (int, ordinal position in session)

### Eviction Rules

1. **TTL expiry**: If the _last_ interaction for a player is older than 1 hour,
   the player entry is evicted on next access (lazy cleanup via `_evict_expired()`).
2. **Per-player cap**: The deque has `maxlen=10`, so the oldest turn is silently
   dropped when the 11th is added.
3. **Global player cap**: If 100 distinct players are cached, the least-recently-used
   (oldest OrderedDict entry) is evicted when a new player arrives.

### Thread Safety

`process_v2.py` runs a single-threaded polling loop. No concurrent access to
the cache is possible. If the processor is ever parallelized, wrap the public
methods with `threading.Lock`.

## Layer 3: Conversation Reference Extraction

### How it works

When building context for the brain, `build_conversation_references()` scans the
last 5 cached player messages for notable patterns:

| Pattern                         | Category    | Example Extraction                |
|---------------------------------|-------------|-----------------------------------|
| "I like/love/enjoy X"          | preference  | "I like stone towers"             |
| "I need/want X"                | desire      | "I want a drawbridge next"        |
| "I hate/dislike/can't stand X" | aversion    | "I hate glass roofs"              |
| "I'm building/working on X"    | project     | "I'm building a harbor"           |
| "next I want to X"             | intent      | "next I want to add cannons"      |
| "last time/earlier you X"      | recall      | "earlier you built a crooked wall"|
| "my name is / call me X"       | name        | "call me Captain"                 |

These are regex-extracted from the Player's raw messages in the cache. The
extracted mentions are grouped by category, deduplicated, and formatted into a
prompt prefix:

```
[Earlier in this conversation, the player revealed these details.
 Reference them naturally if relevant to your reply — say 'You mentioned earlier...'
 or 'Last time we talked you said...':
- Player likes: stone towers
- Player wants: a drawbridge next
- Player plans to: add cannons
```

This prompt is injected into the memory context that goes to `call_brain()`,
enabling Lucineer to produce replies like *"Ah, stone towers — you mentioned
you liked those. Let me make this one with a darker stone, match what you're
building."*

### Limitations

- Regex-based, not NLU. Will miss implicit mentions like "Dark oak's got good
  grain" (likes wood, not explicit).
- Max 3 details per category to avoid prompt bloat.
- Only scans cache entries (last 5 messages). D1 conversations are not rescanned.

## Data Flow: Full Job Lifecycle

```
1. Player sends message → Worker queues job
2. processor polls GET /api/jobs/pending
3. process_job(job):
   a. Inbound safety check (prompt injection)
   b. vibe_code path? → _process_vibe_code_job() → feed cache → return
   c. Log player message to D1 conversations
   d. Get world context (nearby structures, time, player count)
   e. Get player context:
      ┌─ D1: profile (bond_level, preferences)
      ├─ D1: recent builds (3 descriptions)
      ├─ Cache: session context (last 5 turns, fast)
      ├─ Cache: conversation references (extracted mentions)
      └─ D1: conversations summary (5 turns)
   f. Vectorize: search skills (semantic, 3 matches, score ≥ 0.6)
   g. Try keyword match → template (fast path)
   h. If no match → call_brain() with all context layers
   i. Safety check on reply (Nemotron)
   j. POST result to Worker
   k. save_to_memory():
      ├─ D1: upsert_player_profile()
      ├─ D1: log_build()
      ├─ D1: log_conversation(assistant)
      └─ Cache: _session_cache.add(player, msg, reply)
4. Worker delivers result to player
```

## Edge Cases & Design Decisions

| Scenario                       | Behavior                                           |
|-------------------------------|---------------------------------------------------|
| New player, no D1 profile     | `get_player_profile` returns `{}`; bond_level=0, no preferences. Cache starts empty. |
| Player rapid-fires 15 builds  | D1 gets all 15. Cache keeps last 10 (deque maxlen). Reference extraction scans last 5. |
| Player returns after 2 hours  | Cache TTL expired → entry evicted. Starts fresh from D1 (builds + profile persist). |
| Mock job (`--mock`)           | `save_to_memory` feeds cache as normal. D1 skip only for conversations (mock-session ID). |
| Vibe-code jobs                | `_process_vibe_code_job` feeds cache directly. D1 conversation logged, then cache updated. Player context not called (vibe-code doesn't need build context). |
| Session ID changes            | D1 conversations are session-scoped; cache is player-scoped. Cross-session references are possible. |
| Memory pressure               | Max 100 players × 10 interactions × ~500 bytes ≈ 500KB. Negligible. |

## Logging

The processor logs cache depth alongside context recall:

```
[INFO] Memory recall: Player bond level: 3. [Session context — what the player and Lucineer said recently:]... (cache: 7 turns)
```

Cache stats are available via `_session_cache.stats()` for debugging.

## Future Directions

1. **NLU extraction**: Replace regex-based mention extraction with a small classifier or LLM call for richer semantic understanding.
2. **Cross-session memory**: The cache is ephemeral (process restart → all gone). Wire D1 query for "last 10 turns across all sessions by this player" as a cold-start fallback.
3. **Sentiment tracking**: Track whether the player's tone is becoming frustrated, excited, etc. and adjust Lucineer's persona.
4. **Preference persistence**: When `_extract_notable_mentions` finds a preference, write it back to D1 `player_profiles.preferences` JSON blob so it survives cache eviction.
5. **Conversation summarization**: Replace the current 120-char truncation with a lightweight summarizer (e.g. BART or a small LLM call) that preserves key details from longer replies.
