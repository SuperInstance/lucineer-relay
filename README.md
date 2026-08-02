# ⚡ Lucineer Relay

Cloudflare Worker that bridges Roblox and OpenClaw for Lucineer.

## API

| Endpoint | Method | Purpose |
|----------|--------|---------|
| /api/message | POST | Receive chat from Roblox |
| /api/job/:id | GET | Poll job status |
| /api/job/:id/result | POST | OpenClaw posts result |
| /api/jobs/pending | GET | OpenClaw polls for unprocessed jobs |
| /api/state | POST | Update world state |
| /api/state/:session | GET | Get world state |
| /api/health | GET | Health check |

Live at: https://lucineer-relay.casey-digennaro.workers.dev
