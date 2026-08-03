# Phase 1 Day 1-3: Secret Setup Commands

After deploying, set these secrets via `wrangler secret put` or the Cloudflare dashboard.
**Do NOT put real values in wrangler.jsonc — they go in secrets.**

## lucineer-worker (lucineer-relay)
```bash
cd /home/eileen/projects/lucineer-worker
npx wrangler secret put LUCINEER_INTERNAL_KEY    # processor-to-relay auth key
npx wrangler secret put LUCINEER_SHARED_SECRET   # inter-service shared secret
# LUCINEER_KEY is optional (legacy fallback)
```

## lucineer-memory
```bash
cd /home/eileen/projects/lucineer-memory
npx wrangler secret put LUCINEER_SHARED_SECRET   # same value as relay's
```

## lucineer-vector
```bash
cd /home/eileen/projects/lucineer-vector
npx wrangler secret put LUCINEER_SHARED_SECRET   # same value as relay's
```

## R2 Bucket Creation
The `lucineer-trajectories` bucket must exist before deploying the worker:
```bash
npx wrangler r2 bucket create lucineer-trajectories
```
