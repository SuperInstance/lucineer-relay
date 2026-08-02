# Lucineer Relay

*The bridge between a chat box in Roblox and five AI models thinking simultaneously about what to build.*

---

A player types "build me a castle on the hill." Those six words travel from a Roblox client through an HTTPS request to a Cloudflare Worker running on the edge, which stores them in a Durable Object backed by SQLite, which hands them to a Python processor running as a systemd daemon, which checks a Vectorize index for relevant skills, fetches the player's conversation history from a D1 database, and routes the request through a pipeline of five language models — Seed-2.0-mini to parse intent, Qwen3.6 to plan the spatial layout, Qwen3-Coder-480B to generate build commands, and Hermes-405B to wrap it all in the voice of a gruff master builder who's been constructing things since before this engine existed.

Twelve seconds later, twenty-eight JSON commands travel back. A castle appears in the world, stone by stone, each part fading in with a sound and a particle burst. Lucineer says: *"Castle's up — walls, corner towers, keep, the works. Gate's in but I left the portcullis mechanism for you. Even a foreman needs something to do."*

This repo is the plumbing that makes that possible.

---

## What lives here

**The Worker** (`src/`) — a Cloudflare Worker with a Durable Object that manages a SQLite-backed job queue. It accepts messages from Roblox players, stores them as jobs, lets the processor claim and complete them, and manages world state per session. Job claiming prevents duplicate work. Stale job cleanup recovers from crashed processors. Rate limiting keeps a single session from flooding the pipeline.

**The Processor** (`process_v2.py`) — a Python daemon that polls the Worker for pending jobs every two seconds. For each job, it tries the fast path first: keyword matching against 17 build templates that produce results in under a second. If no template matches, it falls back to `brain.py` — the 5-model deep pipeline that can take 30-180 seconds for novel builds. Either way, the result goes back to the Worker, which stores it for the Roblox client to pick up.

**The Brain** integration — the processor calls `brain.py` at `../lucineer-brain/brain.py`, which routes through DeepInfra models. The brain returns JSON with a reply (in Lucineer's voice) and build commands (matching the CommandExecutor schema).

**Memory integration** — every job logs to the D1 memory worker. Player profiles are upserted. Build history is recorded with positions and command counts. Conversations are stored — both the player's message and Lucineer's reply — so the next time the player returns, Lucineer can reference what they built last time. *"Your bridge held through the last blow. I checked."*

**Skill search** — before falling back to the deep brain, the processor queries the Vectorize index for semantically similar skills. "Build me a tower" finds the Scrap Tower skill at 0.68 confidence. This doesn't replace the brain — it gives the brain context about what the system already knows how to build.

---

## The live endpoints

The Worker is deployed at `https://lucineer-relay.casey-digennaro.workers.dev`:

- `POST /api/message` — player sends a chat message (no auth required)
- `GET /api/job/:id` — poll a job's status
- `POST /api/job/:id/result` — processor posts the result (auth required)
- `GET /api/jobs/pending` — processor claims pending jobs (auth required)
- `POST /api/state` — update world state (auth required)
- `GET /api/state/:session` — fetch world state
- `GET /api/health` — health check (no auth)

---

## The daemon

The processor runs as a systemd user service:

```bash
systemctl --user start lucineer-processor   # start
systemctl --user status lucineer-processor  # check
systemctl --user stop lucineer-processor    # stop
tail -50 processor-daemon.log               # logs
```

It restarts on crash. It logs heartbeats every 60 seconds. It circuit-breaks after 5 consecutive failures. It's been running since 9:30 this morning.

---

*The bridge doesn't care what crosses it. It just holds.*
