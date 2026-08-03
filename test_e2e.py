#!/usr/bin/env python3
"""
End-to-end smoke test for the Lucineer worker pipeline.

Creates a real job via POST /api/message, polls GET /api/job/:id until the
job is complete, then verifies the reply contains character voice and that
valid build commands were returned.

Uses curl subprocess calls, matching process_v2.py.
"""
import json
import os
import subprocess
import sys
import time
import uuid

WORKER_URL = os.environ.get(
    "LUCINEER_WORKER_URL",
    "https://lucineer-relay.casey-digennaro.workers.dev",
)
AUTH_KEY = os.environ.get("LUCINEER_AUTH_KEY", "AUTH_KEY_PLACEHOLDER")

POLL_INTERVAL = 2.0
POLL_TIMEOUT = 60.0

# Character-voice markers we expect in a Lucineer build reply.
VOICE_MARKERS = [
    "i ", "me", "my", "yard", "tide", "planks", "boat", "water",
    "dock", "lantern", "cargo", "mooring", "keeper", "beacon",
]


def _curl(args: list[str]) -> dict:
    """Run curl and return parsed JSON."""
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=20,
        )
        return json.loads(result.stdout) if result.stdout else {}
    except Exception as exc:
        print(f"[ERROR] curl/subprocess failed: {exc}")
        return {}


def api_get(path: str) -> dict:
    """GET from the Worker via curl."""
    return _curl([
        "curl", "-s", "--max-time", "10",
        "-H", f"X-Lucineer-Key: {AUTH_KEY}",
        f"{WORKER_URL}{path}",
    ])


def api_post(path: str, data: dict) -> dict:
    """POST to the Worker via curl."""
    return _curl([
        "curl", "-s", "--max-time", "10",
        "-X", "POST",
        "-H", f"X-Lucineer-Key: {AUTH_KEY}",
        "-H", "Content-Type: application/json",
        "-d", json.dumps(data),
        f"{WORKER_URL}{path}",
    ])


def create_job(session_id: str, player_name: str, message: str) -> str | None:
    """Create a job and return its id, or None on failure."""
    response = api_post("/api/message", {
        "sessionId": session_id,
        "playerName": player_name,
        "message": message,
    })
    job_id = response.get("jobId")
    if not job_id:
        print(f"[ERROR] Job creation failed: {response}")
        return None
    return job_id


def poll_job(job_id: str) -> dict | None:
    """Poll until the job completes, errors, or times out."""
    deadline = time.time() + POLL_TIMEOUT
    while time.time() < deadline:
        job = api_get(f"/api/job/{job_id}")
        status = job.get("status")
        if status in ("complete", "error"):
            return job
        time.sleep(POLL_INTERVAL)
    return None


def check_status(job: dict) -> bool:
    """Check that the job completed successfully."""
    status = job.get("status")
    if status == "complete":
        print("[CHECK] Job status is 'complete' ... PASS")
        return True
    print(f"[CHECK] Job status is '{status}' (expected 'complete') ... FAIL")
    return False


def check_voice(reply) -> bool:
    """Check that the reply contains at least one character-voice marker."""
    if not isinstance(reply, str) or not reply.strip():
        print("[CHECK] Reply contains character voice ... FAIL (empty reply)")
        return False
    lowered = reply.lower()
    if any(marker in lowered for marker in VOICE_MARKERS):
        print("[CHECK] Reply contains character voice ... PASS")
        return True
    print(f"[CHECK] Reply contains character voice ... FAIL (reply: {reply!r})")
    return False


def check_commands(commands) -> bool:
    """Check that commands are valid JSON/list and non-empty."""
    # The Worker already JSON-decodes the commands field; explicitly ensure we
    # can round-trip it without error.
    try:
        if isinstance(commands, str):
            commands = json.loads(commands)
        json.dumps(commands)
    except Exception as exc:
        print(f"[CHECK] Commands are valid JSON ... FAIL ({exc})")
        return False

    if not isinstance(commands, list):
        print(f"[CHECK] Commands are valid JSON ... FAIL (not a list: {type(commands)})")
        return False

    print("[CHECK] Commands are valid JSON ... PASS")

    if len(commands) > 0:
        print(f"[CHECK] Command count > 0 ({len(commands)}) ... PASS")
        return True
    print("[CHECK] Command count > 0 ... FAIL")
    return False


def main() -> int:
    session_id = f"e2e-smoke-{uuid.uuid4().hex[:8]}"
    player_name = "E2E_Tester"
    # "lighthouse" maps to a keyword template with many commands and a voice reply.
    message = "build a lighthouse"

    print("=" * 60)
    print("Lucineer end-to-end smoke test")
    print(f"Worker: {WORKER_URL}")
    print(f"Session: {session_id}")
    print("=" * 60)

    print(f"[STEP] Creating job: {message!r}")
    job_id = create_job(session_id, player_name, message)
    if not job_id:
        print("[RESULT] FAIL — could not create job")
        return 1
    print(f"[STEP] Created job {job_id}")

    print(f"[STEP] Polling job for up to {int(POLL_TIMEOUT)}s...")
    job = poll_job(job_id)
    if not job:
        print("[RESULT] FAIL — timed out waiting for job completion")
        return 1

    print(f"[INFO] Final job: {json.dumps(job, indent=2)}")

    results = [
        check_status(job),
        check_voice(job.get("reply")),
        check_commands(job.get("commands")),
    ]

    if all(results):
        print("[RESULT] PASS")
        return 0
    print("[RESULT] FAIL")
    return 1


if __name__ == "__main__":
    sys.exit(main())
