# Lucineer Deployment Guide

This document covers deploying the Cloudflare Worker relay and the systemd-backed processor daemon.

## Prerequisites

- Node.js + npm (for Wrangler)
- A Cloudflare account with Workers and Durable Objects enabled
- `wrangler` CLI authenticated (`npx wrangler login`)
- Python 3.10+ on the processor host
- systemd user instance available (`systemctl --user`)

## 1. Deploy the Worker

```bash
cd /home/eileen/projects/lucineer-worker
npm install
npm run deploy
```

This deploys `src/index.ts` and creates/updates the `LUCINEER_SESSION` Durable Object binding and the `LUCINEER_TRAJECTORIES` R2 binding defined in `wrangler.jsonc`.

## 2. Set Worker secrets

The internal endpoints require one of the following keys (checked in this order):

```bash
npx wrangler secret put LUCINEER_INTERNAL_KEY
# Optional legacy/shared keys:
# npx wrangler secret put LUCINEER_KEY
# npx wrangler secret put LUCINEER_SHARED_SECRET
```

Use a strong random value. The same value is used as `LUCINEER_KEY` on the processor host.

## 3. Install the systemd service

```bash
mkdir -p ~/.config/systemd/user
cp /home/eileen/projects/lucineer-worker/lucineer-processor.service \
   ~/.config/systemd/user/lucineer-processor.service
```

Edit the service file and replace `AUTH_KEY_PLACEHOLDER` with the key from step 2. If you use the deep-brain or vibe-code paths, also set `DEEPINFRA_API_KEY`:

```ini
Environment=LUCINEER_KEY=your-actual-key-here
Environment=DEEPINFRA_API_KEY=your-deepinfra-key-here
```

Reload systemd:

```bash
systemctl --user daemon-reload
```

## 4. Set environment variables for the processor

The processor reads these environment variables:

| Variable | Required | Default / Notes |
|----------|----------|-----------------|
| `LUCINEER_KEY` | **Yes** | Must match `LUCINEER_INTERNAL_KEY` on the Worker. |
| `LUCINEER_WORKER_ID` | No | Default `processor-1`. Use a unique ID per host if you run multiple processors. |
| `LUCINEER_MEMORY_URL` | No | Default `https://lucineer-memory.casey-digennaro.workers.dev` |
| `LUCINEER_VECTOR_URL` | No | Default `https://lucineer-vector.casey-digennaro.workers.dev` |
| `DEEPINFRA_API_KEY` | Yes for deep/vibe paths | Required by `brain.py`, safety check, and vibe-code. |

If you prefer a separate env file instead of inline `Environment=` lines, you can add:

```ini
EnvironmentFile=/home/eileen/projects/lucineer-worker/.env
```

and create that file with the variables above.

## 5. Start the processor

```bash
systemctl --user enable --now lucineer-processor
```

Or use the helper script:

```bash
./lucineer-ctl.sh start
```

## 6. Verify health

### Check the service

```bash
systemctl --user status lucineer-processor --no-pager -l
journalctl --user -u lucineer-processor -f
```

### Check the Worker

```bash
export KEY=your-actual-key-here
# Public health endpoint
curl -s https://lucineer-relay.casey-digennaro.workers.dev/api/health

# Internal claim endpoint (should return {"ok":true,"claimed":0,...})
curl -s -X POST \
  -H "X-Lucineer-Key: $KEY" \
  https://lucineer-relay.casey-digennaro.workers.dev/api/jobs/claim \
  -d '{"workerId":"test","limit":5}'
```

### Inject a mock job

```bash
python3 process_v2.py --mock "build me a tower"
```

You should see a completed job logged and a result returned.

### Run the full smoke test

```bash
LUCINEER_KEY=$KEY python3 smoke_test.py
```

This drives a real message through Worker → Processor → Memory/Vector and reports pass/fail.

## 7. Clean up old v1 processors (optional)

After confirming `process_v2.py` works, the old processors can be removed:

```bash
rm process.py process-jobs.sh
```

`run-processor.sh` has already been updated to use `process_v2.py`, so it is safe to delete the v1 files. Update `README.md` if it still lists them as current.

## Remaining operational blockers before going live

1. **Auth key placeholder.** `lucineer-processor.service` ships with `AUTH_KEY_PLACEHOLDER`; it must be replaced with the real `LUCINEER_INTERNAL_KEY`.
2. **DeepInfra key.** Deep-brain inference, content safety, and vibe-code require `DEEPINFRA_API_KEY`. The service file only has a commented example.
3. **Memory/Vector services.** The processor defaults to production URLs. Verify those Workers are deployed and reachable; otherwise memory writes will warn and fall back to stubs.
4. **R2 bucket.** `lucineer-trajectories` must exist in Cloudflare and be bound as `LUCINEER_TRAJECTORIES`.
5. **`lucineer-system/brain.py`.** The deep path shells out to `../lucineer-system/brain.py`. Ensure it exists and its Python dependencies are installed on the processor host.
6. **Unique worker IDs for scale.** If you run multiple processor hosts, set a unique `LUCINEER_WORKER_ID` per host so lease renewal and ownership are unambiguous.
7. **Monitoring/alerting.** There is no pager/webhook on circuit-breaker trips or repeated Worker 5xx. Add an alert on `journalctl` errors or Worker exceptions.
8. **Systemd hardening.** `ProtectSystem=strict` plus `ReadWritePaths` may need adjustment if the processor needs to write to additional directories (e.g., model caches, extra log paths).
9. **No Roblox client auth.** `/api/message` is intentionally public; abuse relies on per-session rate limiting and Cloudflare's built-in protections.
