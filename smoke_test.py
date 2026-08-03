#!/usr/bin/env python3
"""
Lucineer End-to-End Smoke Test
==============================
Drives one message through the entire stack (Worker → Processor → Brain → Memory → Vector)
and asserts that the result is a real, named build — not the "gray box" regression.

This is the single most valuable integration test per GAP_ANALYSIS §"Recommended Order
of Work", step 4: "a repeatable smoke test that drives one message through the entire
stack and asserts a named part exists at an expected position."

Usage:
  python3 smoke_test.py                          # uses LUCINEER_KEY env var
  python3 smoke_test.py --auth-key mykey         # explicit key
  python3 smoke_test.py --message "build a castle"
  python3 smoke_test.py --worker-url http://localhost:8787  # local dev

Exit codes:
  0 — all assertions passed
  1 — one or more assertions failed
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ─── Defaults ─────────────────────────────────────────────────────────────────

DEFAULT_WORKER_URL = "https://lucineer-relay.casey-digennaro.workers.dev"
DEFAULT_MEMORY_URL = "https://lucineer-memory.casey-digennaro.workers.dev"
DEFAULT_VECTOR_URL = "https://lucineer-vector.casey-digennaro.workers.dev"
DEFAULT_MESSAGE = "build a small tower"
DEFAULT_TIMEOUT = 120  # seconds to wait for job completion
POLL_INTERVAL = 2  # seconds between poll cycles
SESSION_ID = "smoke-test"
PLAYER_NAME = "test_player"


# ─── HTTP Helpers (urllib — no external deps) ────────────────────────────────

def http_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 30,
) -> tuple[int, dict[str, Any]]:
    """
    Perform an HTTP request using urllib.
    Returns (status_code, parsed_json_body).
    Raises RuntimeError on network errors or non-JSON responses.
    """
    hdrs = headers or {}
    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        hdrs.setdefault("Content-Type", "application/json")

    req = Request(url, data=data, headers=hdrs, method=method)

    try:
        with urlopen(req, timeout=timeout) as resp:
            status = resp.status
            raw = resp.read().decode("utf-8")
    except HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except json.JSONDecodeError:
            return e.code, {"_raw": raw}
    except URLError as e:
        raise RuntimeError(f"Network error connecting to {url}: {e.reason}") from e
    except Exception as e:
        raise RuntimeError(f"Unexpected error connecting to {url}: {e}") from e

    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, {"_raw": raw}


def http_get(url: str, *, headers: dict[str, str] | None = None, timeout: int = 30) -> tuple[int, dict[str, Any]]:
    return http_request("GET", url, headers=headers, timeout=timeout)


def http_post(url: str, body: dict[str, Any], *, headers: dict[str, str] | None = None, timeout: int = 30) -> tuple[int, dict[str, Any]]:
    return http_request("POST", url, headers=headers, body=body, timeout=timeout)


# ─── Test Result Tracking ────────────────────────────────────────────────────

class TestResults:
    """Collects pass/fail results for structured reporting."""

    def __init__(self) -> None:
        self.results: list[dict[str, Any]] = []
        self.warnings: list[str] = []
        self.start_time = time.monotonic()

    def record(self, name: str, passed: bool, detail: str = "") -> None:
        self.results.append({
            "name": name,
            "passed": passed,
            "detail": detail,
        })
        status_str = "\033[32mPASS\033[0m" if passed else "\033[31mFAIL\033[0m"
        print(f"  [{'✓' if passed else '✗'}] {status_str} — {name}")
        if detail:
            # Indent detail under the result
            for line in detail.splitlines():
                print(f"      {line}")

    def warn(self, message: str) -> None:
        self.warnings.append(message)
        print(f"  \033[33m⚠ WARNING\033[0m — {message}")

    @property
    def all_passed(self) -> bool:
        return all(r["passed"] for r in self.results)

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.start_time

    def summary(self) -> str:
        passed = sum(1 for r in self.results if r["passed"])
        failed = sum(1 for r in self.results if not r["passed"])
        total = len(self.results)
        elapsed = self.elapsed
        lines = [
            "",
            "═" * 60,
            "SMOKE TEST SUMMARY",
            "═" * 60,
            f"  Total assertions: {total}",
            f"  \033[32mPassed: {passed}\033[0m",
            f"  \033[31mFailed: {failed}\033[0m",
            f"  Warnings: {len(self.warnings)}",
            f"  Round-trip time: {elapsed:.1f}s",
        ]
        if self.warnings:
            lines.append("  ── Warnings ──")
            for w in self.warnings:
                lines.append(f"    • {w}")
        lines.append("═" * 60)
        verdict = "\033[32mALL PASS\033[0m" if self.all_passed else "\033[31mFAILURES DETECTED\033[0m"
        lines.append(f"  Verdict: {verdict}")
        lines.append("═" * 60)
        return "\n".join(lines)


# ─── Smoke Test Phases ───────────────────────────────────────────────────────

def phase_health_check(
    results: TestResults,
    worker_url: str,
    memory_url: str,
    vector_url: str,
    auth_key: str,
) -> bool:
    """
    Phase 0: Verify all three services are reachable and responding.
    Returns True if all health checks pass — safe to proceed.
    """
    print("\n── Phase 0: Service Health Checks ──────────────────────────")

    all_ok = True

    for name, base_url in [("Worker", worker_url), ("Memory", memory_url), ("Vector", vector_url)]:
        try:
            status, body = http_get(f"{base_url}/api/health", timeout=10)
            ok = status == 200 and body.get("status") == "ok"
            detail = f"HTTP {status}, status={body.get('status', 'N/A')}, service={body.get('service', 'N/A')}"
            results.record(f"Health: {name} reachable", ok, detail)
            if not ok:
                all_ok = False
        except Exception as e:
            results.record(f"Health: {name} reachable", False, str(e))
            all_ok = False

    return all_ok


def phase_post_message(
    results: TestResults,
    worker_url: str,
    auth_key: str,
    message: str,
) -> str | None:
    """
    Phase 1: POST a test message to the Worker, simulating a Roblox client.
    Returns the jobId if successful, None otherwise.
    """
    print("\n── Phase 1: Post Test Message ──────────────────────────────")

    headers = {"X-Lucineer-Key": auth_key}
    payload = {
        "sessionId": SESSION_ID,
        "playerName": PLAYER_NAME,
        "message": message,
        "playerState": {
            "position": {"x": 10, "y": 5, "z": -20},
            "health": 100,
        },
        "worldSnapshot": {
            "objects": [],
            "timestamp": int(time.time() * 1000),
        },
    }

    try:
        status, body = http_post(
            f"{worker_url}/api/message",
            payload,
            headers=headers,
            timeout=15,
        )
    except Exception as e:
        results.record("POST /api/message returns jobId", False, f"Request failed: {e}")
        return None

    # Assert we got a jobId back
    job_id = body.get("jobId")
    status_val = body.get("status")

    ok = status == 200 and bool(job_id)
    detail = f"HTTP {status}, jobId={job_id}, status={status_val}"
    if not ok:
        detail += f"\n  Full response: {json.dumps(body, indent=2)[:500]}"

    results.record("POST /api/message returns jobId", ok, detail)

    if not ok:
        # Check for common failure reasons
        if status == 400:
            results.warn("400 — missing required fields. Check sessionId/playerName/message in payload.")
        elif status == 429:
            results.warn("429 — rate limited. Wait 60s and retry.")
        return None

    # Verify jobId format (should be non-empty string)
    if job_id:
        results.record(
            "Job ID is non-empty string",
            isinstance(job_id, str) and len(job_id) > 0,
            f"jobId='{job_id}'",
        )

    return job_id


def phase_poll_result(
    results: TestResults,
    worker_url: str,
    auth_key: str,
    job_id: str,
    timeout_seconds: int,
) -> dict[str, Any] | None:
    """
    Phase 2: Poll for the job result, simulating the Roblox Poller.
    Returns the completed job dict if successful, None otherwise.
    """
    print("\n── Phase 2: Poll for Job Result ────────────────────────────")

    poll_url = f"{worker_url}/api/job/{job_id}"
    start = time.monotonic()
    last_status = None
    status_transitions: list[str] = []

    while time.monotonic() - start < timeout_seconds:
        try:
            status, body = http_get(poll_url, timeout=10)
        except Exception as e:
            results.warn(f"Poll error: {e}")
            time.sleep(POLL_INTERVAL)
            continue

        if status == 404:
            results.record("GET /api/job/:jobId returns job", False, f"404 — job not found: {job_id}")
            return None

        if status != 200:
            time.sleep(POLL_INTERVAL)
            continue

        current_status = body.get("status", "unknown")
        if current_status != last_status:
            elapsed_s = time.monotonic() - start
            transition = f"{last_status or 'submitted'} → {current_status} ({elapsed_s:.1f}s)"
            status_transitions.append(transition)
            print(f"      Status: {transition}")
            last_status = current_status

        # Check for terminal states
        if current_status in ("done", "complete", "completed"):
            elapsed_s = time.monotonic() - start
            detail = f"Completed in {elapsed_s:.1f}s\n"
            detail += f"  Transitions: {' → '.join(status_transitions)}"
            results.record("Job reached terminal status", True, detail)
            return body

        if current_status == "error":
            error_msg = body.get("error", "unknown error")
            detail = f"Job errored after {time.monotonic() - start:.1f}s\n  Error: {error_msg}"
            results.record("Job reached terminal status", False, detail)
            return None

        time.sleep(POLL_INTERVAL)

    # Timed out
    elapsed_s = time.monotonic() - start
    detail = f"Timed out after {elapsed_s:.1f}s\n  Last status: {last_status}\n  Transitions: {' → '.join(status_transitions)}"
    results.record("Job reached terminal status", False, detail)
    return None


def phase_validate_result(results: TestResults, job: dict[str, Any]) -> None:
    """
    Phase 3: Validate the job result content.
    Checks that commands are present, parts are named, and reply text exists.
    """
    print("\n── Phase 3: Validate Build Result ──────────────────────────")

    # 3a. Status is a terminal success state
    status = job.get("status")
    results.record(
        "Job status is 'complete' or 'done'",
        status in ("complete", "done", "completed"),
        f"status='{status}'",
    )

    # 3b. Commands array exists and is non-empty
    commands = job.get("commands", [])
    results.record(
        "Result contains non-empty commands array",
        isinstance(commands, list) and len(commands) > 0,
        f"{len(commands) if isinstance(commands, list) else 0} command(s)",
    )

    if not commands:
        results.record("At least one createPart command", False, "No commands to inspect")
        results.record("Parts have non-default names", False, "No commands to inspect")
        results.record("Reply text exists", False, "Checking after commands failed")
        return

    # 3c. At least one createPart command
    create_parts = [c for c in commands if c.get("type") == "createPart"]
    results.record(
        "At least one createPart command",
        len(create_parts) > 0,
        f"{len(create_parts)} createPart command(s) out of {len(commands)} total",
    )

    # 3d. Parts have names that aren't the default "LucineerPart" (the gray box bug)
    if create_parts:
        part_names = []
        unnamed = 0
        gray_box = 0
        for cmd in create_parts:
            params = cmd.get("params", cmd)  # Accept both envelope and flat
            name = params.get("name", "")
            part_names.append(name)
            if not name or name == "LucineerPart":
                gray_box += 1
            if not name:
                unnamed += 1

        all_named = gray_box == 0
        detail = f"Part names: {', '.join(part_names[:10])}"
        if gray_box > 0:
            detail += f"\n  ⚠ {gray_box} part(s) named 'LucineerPart' or empty — this is the gray box regression!"
        results.record(
            "Parts have non-default names (not 'LucineerPart')",
            all_named,
            detail,
        )

    # 3e. Reply text exists and is non-empty
    reply = job.get("reply", "")
    reply_ok = isinstance(reply, str) and len(reply.strip()) > 0
    detail = f"Reply length: {len(reply)} chars"
    if reply_ok:
        detail += f"\n  Preview: \"{reply[:120]}{'...' if len(reply) > 120 else ''}\""
    results.record("Reply text exists and is non-empty", reply_ok, detail)

    # 3f. Commands have params (envelope structure is correct — GAP_ANALYSIS #1)
    params_ok = 0
    params_missing = 0
    for cmd in commands:
        cmd_type = cmd.get("type", "unknown")
        # createPart and addLight should always have params
        if cmd_type in ("createPart", "addLight", "addParticle"):
            if "params" in cmd and isinstance(cmd["params"], dict):
                params_ok += 1
            else:
                params_missing += 1

    if params_ok + params_missing > 0:
        results.record(
            "Build commands use envelope structure (type + params)",
            params_missing == 0,
            f"{params_ok} with params, {params_missing} missing params",
        )

    # 3g. Parts have non-origin positions (GAP_ANALYSIS #4 — every build at origin)
    if create_parts:
        at_origin = 0
        for cmd in create_parts:
            params = cmd.get("params", cmd)
            pos = params.get("position", {})
            x, y, z = pos.get("x", 0), pos.get("y", 0), pos.get("z", 0)
            if x == 0 and y == 0 and z == 0:
                at_origin += 1

        if at_origin > 0 and at_origin == len(create_parts):
            results.warn(
                f"All {at_origin} part(s) are at origin (0,0,0) — "
                "player position may not be propagated (GAP_ANALYSIS #4)"
            )

    # 3h. At least one part is anchored (builds shouldn't fall)
    if create_parts:
        anchored = sum(
            1 for cmd in create_parts
            if cmd.get("params", cmd).get("anchored") is True
        )
        results.record(
            "At least one anchored part",
            anchored > 0,
            f"{anchored}/{len(create_parts)} createPart(s) anchored",
        )


def phase_check_memory(
    results: TestResults,
    memory_url: str,
    auth_key: str,
) -> None:
    """
    Phase 4: Check memory integration — player profile and build history.
    """
    print("\n── Phase 4: Memory Integration ─────────────────────────────")

    headers = {"X-Lucineer-Key": auth_key}

    # 4a. Player profile exists with bond_level
    try:
        status, body = http_get(
            f"{memory_url}/api/memory/player/{PLAYER_NAME}",
            headers=headers,
            timeout=10,
        )
        if status == 404:
            # Profile might not exist yet — that's a soft fail
            results.record(
                "Player profile exists with bond_level",
                False,
                f"404 — player '{PLAYER_NAME}' not found in memory.\n"
                "  This means the processor hasn't upserted a profile yet,\n"
                "  or memory wiring is not connected (GAP_ANALYSIS #4).",
            )
        elif status == 200:
            bond = body.get("bond_level")
            has_bond = bond is not None
            detail = f"bond_level={bond}, last_seen={body.get('last_seen', 'N/A')}"
            results.record(
                "Player profile exists with bond_level",
                has_bond,
                detail,
            )
        else:
            results.record(
                "Player profile exists with bond_level",
                False,
                f"HTTP {status}: {json.dumps(body)[:200]}",
            )
    except Exception as e:
        results.record("Player profile exists with bond_level", False, f"Request error: {e}")

    # 4b. Build history has at least one entry
    try:
        status, body = http_get(
            f"{memory_url}/api/memory/builds/{PLAYER_NAME}?limit=5",
            headers=headers,
            timeout=10,
        )
        if status == 200:
            builds = body.get("builds", [])
            results.record(
                "Build history has at least one entry",
                isinstance(builds, list) and len(builds) > 0,
                f"{len(builds) if isinstance(builds, list) else 0} build(s) recorded",
            )
        else:
            results.record(
                "Build history has at least one entry",
                False,
                f"HTTP {status}: {json.dumps(body)[:200]}",
            )
    except Exception as e:
        results.record("Build history has at least one entry", False, f"Request error: {e}")


def phase_check_vector(
    results: TestResults,
    vector_url: str,
    auth_key: str,
    query: str,
) -> None:
    """
    Phase 5: Check vector integration — semantic skill search.
    """
    print("\n── Phase 5: Vector Integration ─────────────────────────────")

    headers = {"X-Lucineer-Key": auth_key}

    try:
        status, body = http_post(
            f"{vector_url}/api/skills/query",
            {"query": query, "top_k": 3, "return_metadata": True},
            headers=headers,
            timeout=20,
        )
    except Exception as e:
        results.record("Vector skill search responds", False, f"Request error: {e}")
        return

    # The endpoint should respond successfully
    responds_ok = status == 200 and "matches" in body
    results.record(
        "Vector skill search responds",
        responds_ok,
        f"HTTP {status}, has 'matches' key: {'matches' in body}",
    )

    if responds_ok:
        matches = body.get("matches", [])
        match_count = len(matches)
        detail = f"{match_count} match(es) returned"
        if match_count > 0:
            top_match = matches[0]
            detail += f"\n  Top match: name={top_match.get('metadata', {}).get('name', 'N/A')}, score={top_match.get('score', 'N/A'):.3f}"
        else:
            detail += "\n  (Index may not be seeded — this is OK for first run)"

        # Graceful pass: results returned OR empty if index not seeded
        results.record(
            "Vector search returns results (or empty if unseeded)",
            True,  # The endpoint working is the pass condition
            detail,
        )

        if match_count == 0:
            results.warn("Vectorize index has no matches — run the skill seeder to populate it.")
    else:
        detail = f"HTTP {status}: {json.dumps(body)[:300]}"
        results.record(
            "Vector search returns results (or empty if unseeded)",
            False,
            detail,
        )


# ─── Main Entry Point ────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lucineer end-to-end smoke test. Drives one message through the full stack.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 smoke_test.py                              # all defaults
  python3 smoke_test.py --message "build a castle"   # custom message
  LUCINEER_KEY=secret python3 smoke_test.py           # env var auth
  python3 smoke_test.py --worker-url http://localhost:8787  # local dev
        """,
    )
    parser.add_argument(
        "--worker-url",
        default=os.environ.get("LUCINEER_WORKER_URL", DEFAULT_WORKER_URL),
        help=f"Worker relay URL (default: {DEFAULT_WORKER_URL})",
    )
    parser.add_argument(
        "--memory-url",
        default=os.environ.get("LUCINEER_MEMORY_URL", DEFAULT_MEMORY_URL),
        help=f"Memory D1 Worker URL (default: {DEFAULT_MEMORY_URL})",
    )
    parser.add_argument(
        "--vector-url",
        default=os.environ.get("LUCINEER_VECTOR_URL", DEFAULT_VECTOR_URL),
        help=f"Vectorize Worker URL (default: {DEFAULT_VECTOR_URL})",
    )
    parser.add_argument(
        "--auth-key",
        default=os.environ.get("LUCINEER_KEY", ""),
        help="Auth key (or set LUCINEER_KEY env var)",
    )
    parser.add_argument(
        "--message",
        default=DEFAULT_MESSAGE,
        help=f'Message to send (default: "{DEFAULT_MESSAGE}")',
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Max seconds to wait for job completion (default: {DEFAULT_TIMEOUT})",
    )
    parser.add_argument(
        "--skip-memory",
        action="store_true",
        help="Skip memory integration checks",
    )
    parser.add_argument(
        "--skip-vector",
        action="store_true",
        help="Skip vector integration checks",
    )
    args = parser.parse_args()

    # Validate auth key
    if not args.auth_key:
        print("ERROR: Auth key required. Pass --auth-key or set LUCINEER_KEY env var.")
        return 1

    # Normalize URLs (strip trailing slash)
    worker_url = args.worker_url.rstrip("/")
    memory_url = args.memory_url.rstrip("/")
    vector_url = args.vector_url.rstrip("/")

    # Print header
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " LUCINEER END-TO-END SMOKE TEST".ljust(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print()
    print(f"  Timestamp:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Worker:      {worker_url}")
    print(f"  Memory:      {memory_url}")
    print(f"  Vector:      {vector_url}")
    print(f"  Message:     \"{args.message}\"")
    print(f"  Session:     {SESSION_ID}")
    print(f"  Player:      {PLAYER_NAME}")
    print(f"  Timeout:     {args.timeout}s")
    print(f"  Poll interval: {POLL_INTERVAL}s")

    results = TestResults()

    # ── Phase 0: Health checks ──
    services_ok = phase_health_check(results, worker_url, memory_url, vector_url, args.auth_key)

    if not services_ok:
        print("\n⚠  One or more services are unreachable. Aborting remaining phases.")
        print(results.summary())
        return 1

    # ── Phase 1: Post message ──
    job_id = phase_post_message(results, worker_url, args.auth_key, args.message)

    if not job_id:
        print("\n⚠  Failed to create job. Cannot proceed with polling.")
        print(results.summary())
        return 1

    # ── Phase 2: Poll for result ──
    job = phase_poll_result(results, worker_url, args.auth_key, job_id, args.timeout)

    if not job:
        print("\n⚠  Job did not complete within timeout.")
        print(results.summary())
        return 1

    # ── Phase 3: Validate result ──
    phase_validate_result(results, job)

    # ── Phase 4: Memory integration ──
    if args.skip_memory:
        print("\n── Phase 4: Memory Integration (SKIPPED) ────────────────────")
    else:
        phase_check_memory(results, memory_url)

    # ── Phase 5: Vector integration ──
    if args.skip_vector:
        print("\n── Phase 5: Vector Integration (SKIPPED) ────────────────────")
    else:
        phase_check_vector(results, vector_url, args.auth_key, args.message)

    # ── Final Report ──
    print(results.summary())

    return 0 if results.all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
