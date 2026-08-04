# Fast Path Test Results

**Date:** 2026-08-03  
**Worker:** lucineer-relay (v39ae8efe)  
**URL:** https://lucineer-relay.casey-digennaro.workers.dev

## What Was Built

Added a Worker-side fast path that returns pre-built templates instantly for common build requests, bypassing the DeepInfra brain pipeline entirely.

### Changes
- **`src/templates.ts`** (new): 10 build templates extracted from `process_v2.py`, embedded as JSON with Lucineier voice lines
- **`src/index.ts`** (modified):
  - Added `matchFastPath()` keyword matcher (build verb + keyword + negation detection)
  - POST `/api/message`: checks templates BEFORE rate limiting or DO calls
  - GET `/api/quick/:message`: new public, auth-free endpoint for web game calls

### 10 Template Voice Lines (Tier 0 foreman voice, CHARACTER_BIBLE compliant)

| Build | Voice Line | Commands |
|-------|-----------|----------|
| tower | "Stone shaft's up, battlements are on, beacon's lit. Top floor's open — didn't know what you wanted up there." | 4 |
| house | "Foundation's set, walls are brick, roof's pitched and the chimney's drawing. Didn't hang the door — figured you'd want to pick it." | 20 |
| castle | "Walls are up, towers are capped, banners are flying. Left the murder holes off — seemed like your department." | 28 |
| bridge | "Piers are seated, deck's laid, roof's on. Didn't bolt the cleats down. Depends what you're tying off." | 44 |
| windmill | "Tower's rebuilt — stone base, brick lower, timber up top where the fire got it. Sails are balanced but the grain chute is still empty. Haven't sourced the stones." | 15 |
| garden | "Plaza's reclaimed, beds are in, fountain's weeping. Trellis is up but I didn't plant anything on it. That's your call." | 27 |
| dock | "Piles are driven, planks are down, mooring posts are set. Didn't rig the bumpers — different boats need different ones." | 22 |
| lighthouse | "Tower's up, beacon's lit, keeper's cottage is sealed in. Boat winch is mounted but I didn't run the cable. Didn't want to guess the length." | 15 |
| cottage | "Foundation's cobble, walls are warm brick, roof's pitched and the chimney's smoking. Flower box is up but I didn't plant anything. Didn't want to pick the wrong seeds." | 30 |
| well | "Stone ring's laid, water's in, bucket's on the rope. Roof is up but I left the crank handle loose. Tighten it when you've got a wrench." | 22 |

**Total:** 227 build commands across 10 templates.

All voice lines follow the three-beat pattern: [what he did] → [opinion] → [hook — something left unfinished].

## Test Results

### Template Matches (POST /api/message)

All 10 templates match and return `status=complete, source=template` instantly:

| Keyword | Build | Status | Commands |
|---------|-------|--------|----------|
| tower | tower | ✅ complete | 4 |
| house | house | ✅ complete | 20 |
| castle | castle | ✅ complete | 28 |
| bridge | bridge | ✅ complete | 44 |
| windmill | windmill | ✅ complete | 15 |
| garden | garden | ✅ complete | 27 |
| dock | dock | ✅ complete | 22 |
| lighthouse | lighthouse | ✅ complete | 15 |
| cottage | cottage | ✅ complete | 30 |
| well | well | ✅ complete | 22 |

### Edge Cases

| Test | Input | Expected | Result |
|------|-------|----------|--------|
| Non-build message | "hello there" | Deep path (no build verb) | ✅ processing |
| Synonym match | "construct a fortress" | castle template | ✅ complete/castle |
| Negation | "dont build a tower" | Deep path (negation) | ✅ processing |
| Unknown build | "build a spaceship" | Deep path (no match) | ✅ processing |

### GET /api/quick/:message (no auth)

| Test | Result |
|------|--------|
| `GET /api/quick/build%20a%20castle` | ✅ 28 commands, status=complete |
| `GET /api/quick/build%20a%20spaceship` | ✅ status=no_template |

### Response Times

| Path | Time | Target |
|------|------|--------|
| POST /api/message (fast path) | **~760ms** | <5s ✅ |
| GET /api/quick/:message | **~196ms** | <5s ✅ |
| POST /api/message (deep path) | ~1.1s (job creation only) | N/A — processor takes 30-60s after |

The POST fast path time is dominated by network latency (WSL → Cloudflare edge). The template lookup itself is <1ms at the edge.

### Keyword Synonyms Supported

| Build | Synonyms |
|-------|----------|
| tower | spire, pillar |
| house | cabin, home, shack |
| castle | fortress, fort, keep, citadel, palace |
| bridge | crossing |
| windmill | mill |
| garden | park, yard, flowerbed |
| dock | pier, wharf, jetty |
| lighthouse | beacon |
| cottage | (direct only) |
| well | water well, wishwell, wishing well |

## Architecture

```
Player sends "build a tower"
         │
         ▼
   POST /api/message
         │
    matchFastPath()
         │
    ┌────┴────┐
    │         │
  MATCH    NO MATCH
    │         │
    ▼         ▼
 INSTANT    Rate limit
 RESPONSE   check → DO
 (<1ms)     → createJob
    │       → processor polls
    │       → DeepInfra pipeline
    │       → 30-60s later
    │         │
    ▼         ▼
 { status:   { jobId,
   complete,   status:
   commands,   processing }
   reply }
```

## Deployment

```bash
cd /home/eileen/projects/lucineer-worker
npx wrangler deploy
```

Worker size: 139 KiB (14.42 KiB gzipped) — well within the 1MB limit.
