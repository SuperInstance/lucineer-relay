# Contributing to Lucineer Worker

Thanks for helping build the Slackwater pipeline. This is a hybrid TypeScript + Python project — the Worker runs on Cloudflare, the processor runs on a Python daemon.

---

## Project Layout

```
src/                          TypeScript (Cloudflare Worker)
├── index.ts                  Router, auth middleware, API handlers
├── types.ts                  Shared interfaces (Env, Job, TrajectoryEvent, …)
├── emotional-memory.ts       D1-backed emotional memory (The Listener's Ear)
├── templates.ts              Fast-path build templates
├── RequestQueue.ts           Per-isolate request queueing and response cache
└── do/
    └── LucineerSession.ts    Durable Object: SQLite schema, job lifecycle

*.py                          Python (Processor daemon)
├── process_v2.py             Hybrid-intelligence processor (fast path + deep brain)
├── bond.py                   Player bond scoring system
├── build_templates_v2.py     Visually polished fast-path templates
└── playtest_harness.py       Simulated player testing

tests/                        Python tests (pytest)
├── test_bond.py              Bond scoring tests
├── test_build_templates_v2.py Template structural tests
├── test_process_v2.py        Pure-function tests for processor
├── test_process_v2_resilience.py Circuit breaker, auth, filtering tests
└── test_validate_job.py      Job validation guard tests
```

---

## Development Setup

### Prerequisites

- Node.js 18+ (for Cloudflare Workers)
- Python 3.10+
- `wrangler` CLI (`npm install -g wrangler`)

### Install Dependencies

```bash
npm install          # Workers toolchain
pip install pytest   # Python test runner
```

### Running Tests

```bash
# Python tests (267+ tests covering pure functions)
python3 -m pytest -v

# Run a specific test file
python3 -m pytest tests/test_bond.py -v

# Run a single test class
python3 -m pytest tests/test_process_v2.py::TestStripMarkdownFences -v
```

### Local Worker Development

```bash
npx wrangler dev     # Start local Worker on :8787
```

### Deploy

```bash
npx wrangler deploy  # Deploy to production
```

---

## Code Conventions

### TypeScript (Worker)

- Use strict type annotations on all public interfaces
- Export types from `types.ts` and import them where needed
- The `Env` interface lists all bindings — update it when adding bindings
- Durable Object RPC methods are declared in `LucineerSessionRPC` interface

### Python (Processor)

- Add type hints to all new functions (`def foo(x: str) -> dict | None:`)
- Use `log()` from `process_v2.py` for all logging — never `print()` directly
- Pure functions (JSON extraction, validation, keyword matching) should have no side effects
- Test pure functions in `tests/test_process_v2*.py`

### Testing Guidelines

- Every new pure function should have tests
- Test edge cases: `None`, empty strings, wrong types, boundary values
- Use parametrize for table-driven tests
- Tests must pass without network access (no real API calls)
- Mock external services — never call the production Worker

### Commit Messages

Use conventional prefixes:

```
feat:     new feature
fix:      bug fix
test:     test additions or improvements
docs:     documentation only
refactor: code restructuring with no behavior change
```

---

## Architecture Notes

- The Worker is the **single ingress point** — Roblox and the processor both talk to it
- The Durable Object uses **SQLite** (not KV) for structured job queries
- The processor polls with **atomic claiming** (CAS) — never assume exclusive access
- Trajectories are the **highest-value data** — R2 write failures must surface
- Auth failures are **loud** — `_check_auth_failure` exists because a silent auth failure hid a dead processor for days

---

## License

MIT — see [LICENSE](LICENSE).
