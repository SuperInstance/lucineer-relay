#!/usr/bin/env python3
"""
Lucineer AI Playtest Harness
============================
Sends messages to the Slackwater game as AI player personas, journals each
interaction with train-of-thought reasoning, and produces training data
for later refinement.

Uses curl for HTTP calls (Cloudflare blocks Python HTTP libraries).

Usage:
  python3 playtest_harness.py --persona explorer --scenario first-time
  python3 playtest_harness.py --persona builder --scenario stress
  python3 playtest_harness.py --all-personas --scenario edge-cases
  python3 playtest_harness.py --persona newcomer --continuous
  python3 playtest_harness.py --persona explorer --freeform "build a volcano"

Auth:
  Set LUCINEER_KEY env var, or pass --auth-key.
"""
from __future__ import annotations

import argparse
import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

# ─── Constants ───────────────────────────────────────────────────────────────

_DEFAULT_WORKER_URL = os.environ.get(
    "LUCINEER_WORKER_URL",
    "https://lucineer-relay.casey-digennaro.workers.dev",
)
WORKER_URL = _DEFAULT_WORKER_URL


def _set_worker_url(url: str) -> None:
    """Update the module-level WORKER_URL used by helper functions."""
    global WORKER_URL
    WORKER_URL = url
DEFAULT_AUTH_KEY = os.environ.get("LUCINEER_KEY", "AUTH_KEY_PLACEHOLDER")
JOURNAL_DIR = "/home/eileen/projects/playtest-journals"
POLL_INTERVAL = 2.0
POLL_TIMEOUT = 120.0
ADAPTIVE_TIMEOUT_MIN = 15.0  # After repeated failures, shorten timeout
CONSECUTIVE_FAILURES_FOR_ADAPTIVE = 2  # Start adapting after N consecutive timeouts

# Character-voice markers — used to detect if Lucineer stays in character
VOICE_MARKERS = [
    "i ", "me", "my", "yard", "tide", "planks", "boat", "water",
    "dock", "lantern", "cargo", "mooring", "keeper", "beacon",
    "shore", "slight", "current", "drift", "channel", "weathered",
    "fish", "sail", "mast", "anchor", "helm", "compass", "chart",
]

# Materials we consider "diverse" for material-diversity scoring
KNOWN_MATERIALS = [
    "Wood", "WoodPlank", "Plank", "Stone", "Brick", "Concrete",
    "Metal", "Cobblestone", "Sand", "Grass", "Glass", "Neon",
    "Marble", "Granite", "Ice", "Snow", "Leaves", "Dirt",
]


# ─── HTTP Helpers (curl-based) ───────────────────────────────────────────────

def curl_request(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    body: dict[str, Any] | None = None,
    timeout: int = 15,
) -> tuple[int, dict[str, Any]]:
    """Perform HTTP via curl subprocess. Returns (status_code, parsed_json)."""
    cmd = ["curl", "-s", "-w", "\n%{http_code}", "--max-time", str(timeout), "-X", method]

    hdrs = headers or {}
    if body is not None:
        hdrs.setdefault("Content-Type", "application/json")
        cmd.extend(["-d", json.dumps(body)])

    for key, val in hdrs.items():
        cmd.extend(["-H", f"{key}: {val}"])
    cmd.append(url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 5)
        output = result.stdout.strip()
        lines = output.rsplit("\n", 1)
        if len(lines) == 2:
            raw_body, status_str = lines
        else:
            raw_body, status_str = output, "0"

        try:
            status = int(status_str.strip())
        except ValueError:
            status = 0

        try:
            return status, json.loads(raw_body)
        except json.JSONDecodeError:
            return status, {"_raw": raw_body}

    except subprocess.TimeoutExpired:
        return 0, {"_error": f"curl timed out after {timeout}s"}
    except Exception as e:
        return 0, {"_error": str(e)}


def send_message(
    session_id: str,
    player_name: str,
    message: str,
    auth_key: str,
) -> tuple[str | None, float]:
    """POST a message to the game. Returns (job_id, send_time)."""
    start = time.monotonic()
    status, body = curl_request(
        "POST",
        f"{WORKER_URL}/api/message",
        headers={"X-Lucineer-Key": auth_key},
        body={
            "sessionId": session_id,
            "playerName": player_name,
            "message": message,
        },
    )
    elapsed = time.monotonic() - start
    if status != 200:
        return None, elapsed
    return body.get("jobId"), elapsed


def poll_job(
    job_id: str,
    auth_key: str,
    timeout: float | None = None,
) -> tuple[dict[str, Any] | None, float, str | None]:
    """Poll until the job completes.

    Returns (job_dict_or_None, poll_elapsed_seconds, stale_status_or_None).
    If the job is stuck in 'claimed' with an expired lease, returns early
    with stale_status set so the caller can report it rather than waiting
    the full timeout.
    """
    deadline = time.monotonic() + (timeout or POLL_TIMEOUT)
    start = time.monotonic()
    last_status: str | None = None
    stale_check_done = False

    while time.monotonic() < deadline:
        status, body = curl_request(
            "GET",
            f"{WORKER_URL}/api/job/{job_id}",
            headers={"X-Lucineer-Key": auth_key},
        )
        if status == 404:
            return None, time.monotonic() - start, None
        if status == 200:
            job_status = body.get("status", "unknown")
            last_status = job_status

            if job_status == "complete":
                return body, time.monotonic() - start, None
            if job_status == "error":
                return body, time.monotonic() - start, None

            # Detect stale claimed jobs (lease expired but never completed)
            if job_status == "claimed" and not stale_check_done:
                lease_expires = body.get("leaseExpiresAt")
                claimed_at = body.get("claimedAt")
                now_ms = int(time.time() * 1000)

                if lease_expires and lease_expires < now_ms:
                    # Lease has expired — job is stale
                    elapsed = time.monotonic() - start
                    return body, elapsed, f"stale_claimed (lease expired {((now_ms - lease_expires) / 1000):.0f}s ago, attempts={body.get('attempts', '?')})"

                # Wait until just past lease expiry, then re-check once
                if lease_expires:
                    wait_until = (lease_expires - now_ms) / 1000 + POLL_INTERVAL
                    if wait_until > 0 and wait_until < (deadline - time.monotonic()):
                        time.sleep(min(wait_until, 30))  # Don't wait more than 30s extra
                        stale_check_done = True
                        continue

        time.sleep(POLL_INTERVAL)

    # Timed out — include the last known status if available
    return None, time.monotonic() - start, f"timeout (last_status={last_status})"


# ─── Journaling ──────────────────────────────────────────────────────────────

class Journal:
    """Accumulates journal entries and writes JSONL + Markdown."""

    def __init__(self, persona: str, session_id: str):
        self.persona = persona
        self.session_id = session_id
        self.entries: list[dict[str, Any]] = []
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.jsonl_path = os.path.join(JOURNAL_DIR, f"{persona}_{ts}.jsonl")
        self.md_path = os.path.join(JOURNAL_DIR, f"{persona}_{ts}.md")

    def add_entry(
        self,
        message_sent: str,
        response_received: str,
        build_commands: list[dict[str, Any]],
        round_trip_seconds: float,
        train_of_thought: str,
        emotional_reaction: str,
        quality_score: int,
        notes: str,
        error: str | None = None,
    ) -> dict[str, Any]:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "persona": self.persona,
            "session_id": self.session_id,
            "message_sent": message_sent,
            "response_received": response_received,
            "build_commands": build_commands,
            "round_trip_seconds": round(round_trip_seconds, 2),
            "train_of_thought": train_of_thought,
            "emotional_reaction": emotional_reaction,
            "quality_score": quality_score,
            "notes": notes,
        }
        if error:
            entry["error"] = error

        self.entries.append(entry)
        self._write_jsonl(entry)
        self._write_markdown()
        return entry

    def _write_jsonl(self, entry: dict[str, Any]) -> None:
        os.makedirs(os.path.dirname(self.jsonl_path), exist_ok=True)
        with open(self.jsonl_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _write_markdown(self) -> None:
        os.makedirs(os.path.dirname(self.md_path), exist_ok=True)
        lines = [
            f"# Playtest Journal — {self.persona}",
            f"",
            f"**Session:** `{self.session_id}`",
            f"**Started:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Entries:** {len(self.entries)}",
            f"",
            "---",
            f"",
        ]
        for i, e in enumerate(self.entries, 1):
            lines.append(f"## Entry {i}")
            lines.append(f"")
            lines.append(f"- **Time:** {e['timestamp']}")
            lines.append(f"- **Persona:** {e['persona']}")
            lines.append(f"- **Message Sent:** `{e['message_sent']}`")
            lines.append(f"- **Round Trip:** {e['round_trip_seconds']}s")
            lines.append(f"- **Quality Score:** {e['quality_score']}/10")
            lines.append(f"- **Emotional Reaction:** {e['emotional_reaction']}")
            if e.get("error"):
                lines.append(f"- **⚠ Error:** {e['error']}")
            lines.append(f"")
            lines.append(f"**Response:**")
            lines.append(f"")
            reply = e["response_received"]
            if len(reply) > 500:
                reply = reply[:500] + "..."
            lines.append(f"> {reply}")
            lines.append(f"")
            cmd_count = len(e["build_commands"])
            if cmd_count:
                lines.append(f"**Build Commands:** {cmd_count} command(s)")
                cmd_types: dict[str, int] = {}
                for c in e["build_commands"]:
                    t = c.get("type", "unknown")
                    cmd_types[t] = cmd_types.get(t, 0) + 1
                for ct, count in sorted(cmd_types.items()):
                    lines.append(f"  - `{ct}`: {count}")
                lines.append(f"")
            lines.append(f"**Train of Thought:**")
            lines.append(f"")
            lines.append(f"{e['train_of_thought']}")
            lines.append(f"")
            if e["notes"]:
                lines.append(f"**Notes:** {e['notes']}")
                lines.append(f"")
            lines.append(f"---")
            lines.append(f"")

        with open(self.md_path, "w") as f:
            f.write("\n".join(lines))

    def print_summary(self) -> None:
        if not self.entries:
            print("\n  No entries to summarize.")
            return

        times = [e["round_trip_seconds"] for e in self.entries if not e.get("error")]
        cmd_counts = [len(e["build_commands"]) for e in self.entries if not e.get("error")]
        scores = [e["quality_score"] for e in self.entries]
        errors = sum(1 for e in self.entries if e.get("error"))
        voice_hits = 0
        mat_diversity: dict[str, int] = {}

        for e in self.entries:
            reply = e.get("response_received", "").lower()
            if any(m in reply for m in VOICE_MARKERS):
                voice_hits += 1
            for c in e.get("build_commands", []):
                params = c.get("params", c)
                mat = params.get("material", "")
                if mat:
                    mat_diversity[mat] = mat_diversity.get(mat, 0) + 1

        total = len(self.entries)
        non_error = total - errors

        print(f"\n{'═' * 60}")
        print(f"  PLAYTEST SUMMARY — {self.persona}")
        print(f"{'═' * 60}")
        print(f"  Total interactions:  {total}")
        print(f"  Errors:              {errors}")
        if times:
            print(f"  Response time:       min={min(times):.1f}s  max={max(times):.1f}s  avg={sum(times)/len(times):.1f}s")
        if cmd_counts:
            print(f"  Build commands:      min={min(cmd_counts)}  max={max(cmd_counts)}  avg={sum(cmd_counts)/len(cmd_counts):.1f}")
        if non_error > 0:
            print(f"  Voice in character:  {voice_hits}/{non_error} ({voice_hits/non_error*100:.0f}%)")
        if scores:
            print(f"  Quality scores:      min={min(scores)}  max={max(scores)}  avg={sum(scores)/len(scores):.1f}")
        if mat_diversity:
            top_mats = sorted(mat_diversity.items(), key=lambda x: -x[1])[:5]
            print(f"  Material diversity:  {', '.join(f'{m}({c})' for m, c in top_mats)}")
        print(f"{'═' * 60}")
        print(f"  Journal files:")
        print(f"    JSONL: {self.jsonl_path}")
        print(f"    MD:    {self.md_path}")
        print(f"{'═' * 60}")
        sys.stdout.flush()


# ─── Analysis Helpers ────────────────────────────────────────────────────────

def generate_train_of_thought(
    persona: str,
    message: str,
    reply: str,
    commands: list[dict[str, Any]],
    round_trip: float,
    history: list[dict[str, Any]],
    error: str | None = None,
) -> str:
    """Generate a train-of-thought analysis for this interaction."""

    if error:
        return (
            f"I sent '{message}' but encountered an error: {error}. "
            f"This is a failure point — the game couldn't process my request. "
            f"I should note whether this is reproducible and whether it's "
            f"specific to this input pattern. Round-trip was {round_trip:.1f}s before failure."
        )

    parts = []
    cmd_count = len(commands)
    cmd_types: dict[str, int] = {}
    for c in commands:
        t = c.get("type", "unknown")
        cmd_types[t] = cmd_types.get(t, 0) + 1

    # Persona-specific reasoning
    if persona == "Explorer":
        parts.append(f"I sent '{message}' to test boundaries and variety.")
        if cmd_count > 8:
            parts.append(f"Lucineer responded generously — {cmd_count} commands is a rich build.")
        elif cmd_count > 0:
            parts.append(f"The build was modest — {cmd_count} commands. Maybe the request was too simple.")
        else:
            parts.append("No build commands returned — this could be a conversational reply or a miss.")
        if round_trip > 30:
            parts.append(f"Response time was slow ({round_trip:.1f}s) — might need optimization.")
        elif round_trip < 10:
            parts.append(f"Quick response ({round_trip:.1f}s) — felt snappy and natural.")
        if len(history) > 2:
            parts.append(f"This is interaction #{len(history)+1} — I'm building a picture of Lucineer's range.")
    elif persona == "Builder":
        parts.append(f"I requested '{message}' with specific structural intent.")
        if "createPart" in cmd_types:
            parts.append(f"Got {cmd_types['createPart']} parts — checking spatial coherence.")
        if cmd_count > 0:
            # Check for positioning diversity
            positions = []
            for c in commands:
                p = c.get("params", c).get("position", {})
                if p:
                    positions.append((p.get("x", 0), p.get("y", 0), p.get("z", 0)))
            if len(set(positions)) > 1:
                parts.append(f"Parts are spread across {len(set(positions))} unique positions — good spatial awareness.")
            else:
                parts.append("All parts at same position — possible stacking or positioning issue.")
        parts.append(f"Round-trip {round_trip:.1f}s, {cmd_count} commands total.")
    elif persona == "Newcomer":
        parts.append(f"I nervously typed '{message}'.")
        if reply:
            reply_preview = reply[:100]
            parts.append(f"Lucineer said: \"{reply_preview}\"")
        if cmd_count > 0:
            parts.append(f"It built something for me — {cmd_count} commands! That's exciting.")
        parts.append(f"Took {round_trip:.1f}s which felt {'quick' if round_trip < 15 else 'a bit slow'} to me.")

    # Voice check
    reply_lower = reply.lower()
    voice_hits = sum(1 for m in VOICE_MARKERS if m in reply_lower)
    if voice_hits > 3:
        parts.append("Lucineer's voice is strong — lots of character markers detected.")
    elif voice_hits > 0:
        parts.append("Lucineer's voice is present but could be stronger.")
    else:
        parts.append("Voice feels flat — Lucineer might be dropping character.")

    # Material diversity
    materials = set()
    for c in commands:
        m = c.get("params", c).get("material", "")
        if m:
            materials.add(m)
    if materials:
        parts.append(f"Materials used: {', '.join(sorted(materials))}.")

    return " ".join(parts)


def score_quality(
    reply: str,
    commands: list[dict[str, Any]],
    round_trip: float,
    error: str | None = None,
) -> int:
    """Score the interaction quality 1-10."""
    if error:
        return 2

    score = 5  # baseline

    # Reply quality
    if reply and len(reply.strip()) > 20:
        score += 1
    if reply and len(reply.strip()) > 100:
        score += 1

    # Build quality
    if commands:
        score += 1
    if len(commands) >= 5:
        score += 1

    # Speed bonus
    if round_trip < 10:
        score += 1
    if round_trip > 45:
        score -= 2

    # Voice check
    reply_lower = (reply or "").lower()
    voice_hits = sum(1 for m in VOICE_MARKERS if m in reply_lower)
    if voice_hits > 3:
        score += 1

    return max(1, min(10, score))


def check_voice_in_character(reply: str) -> bool:
    """Check if the reply stays in character."""
    if not reply or not reply.strip():
        return False
    lowered = reply.lower()
    return any(marker in lowered for marker in VOICE_MARKERS)


def get_emotional_reaction(persona: str, quality: int, error: str | None, cmd_count: int) -> str:
    """Generate a persona-appropriate emotional reaction."""
    if error:
        reactions = {
            "Explorer": "frustrated but intrigued by the failure case",
            "Builder": "annoyed — needed that build to work",
            "Newcomer": "confused and worried I did something wrong",
        }
        return reactions.get(persona, "disappointed")

    if quality >= 8:
        reactions = {
            "Explorer": "excited and impressed by the complexity",
            "Builder": "satisfied — this is what I wanted",
            "Newcomer": "delighted and amazed it actually worked",
        }
    elif quality >= 6:
        reactions = {
            "Explorer": "pleased but wanting more variety",
            "Builder": "content, though I see room for refinement",
            "Newcomer": "happy and a bit more confident now",
        }
    elif quality >= 4:
        reactions = {
            "Explorer": "neutral — acceptable but not surprising",
            "Builder": "underwhelmed — expected more structure",
            "Newcomer": "okay I guess, not sure what to think",
        }
    else:
        reactions = {
            "Explorer": "disappointed — that was boring",
            "Builder": "frustrated — poor output",
            "Newcomer": "let down and confused",
        }
    return reactions.get(persona, "neutral")


# ─── Player Personas ─────────────────────────────────────────────────────────

class PlayerPersona:
    """Base persona — generates messages for a given scenario step."""

    name: str = "Base"
    player_name: str = "Player"

    def get_message(self, scenario: str, step: int, history: list[dict[str, Any]]) -> str:
        raise NotImplementedError

    def get_think_delay(self) -> float:
        """How long to 'think' before sending (simulating human typing)."""
        return random.uniform(1.0, 3.0)


class ExplorerPersona(PlayerPersona):
    """Explorer — asks for varied builds, tests boundaries."""

    name = "Explorer"
    player_name = "Explorer_Eli"

    # Message banks per scenario
    FIRST_TIME = [
        "hi there!",
        "build a castle",
        "wow, can you make it bigger?",
        "what happens if I build on the water?",
    ]
    RETURNING = [
        "I'm back! Remember me?",
        "can you upgrade my lighthouse?",
        "build something crazy — surprise me",
    ]
    STRESS = [
        "build a tower",
        "build a bridge",
        "build a boat",
        "build a garden",
        "build a waterfall",
    ]
    EDGE_CASES = [
        "build nothing",
        "what's your name?",
        "can you fly?",
        "build a portal to another dimension",
        "I don't want to build anything",
        "tell me a story",
    ]
    FREEFORM_POOL = [
        "build a towering skyscraper",
        "create a hidden underground base",
        "build a cozy cabin in the woods",
        "make a spinning windmill",
        "construct a grand cathedral",
        "build a pier stretching over the ocean",
        "create a mysterious cave entrance",
        "build a giant treehouse",
        "make a glowing crystal garden",
        "build an ancient ruin",
        "what happens if I ask for a floating island?",
        "build a campfire scene",
        "create a market stall with goods",
        "build a clock tower",
        "make a rainbow bridge",
    ]

    def get_message(self, scenario: str, step: int, history: list[dict[str, Any]]) -> str:
        bank = {
            "first-time": self.FIRST_TIME,
            "returning": self.RETURNING,
            "stress": self.STRESS,
            "edge-cases": self.EDGE_CASES,
        }.get(scenario, self.FREEFORM_POOL)

        if scenario == "freeform" or step >= len(bank):
            # For freeform or overflow, pick something contextual or random
            if history:
                last_reply = history[-1].get("response_received", "").lower()
                if "castle" in last_reply or "tower" in last_reply:
                    return random.choice(["add a moat around it", "put a dragon on top", "make it glow"])
            return random.choice(self.FREEFORM_POOL)

        return bank[step]

    def get_think_delay(self) -> float:
        return random.uniform(0.5, 2.0)  # Explorer is quick to experiment


class BuilderPersona(PlayerPersona):
    """Builder — systematic, requests specific structures, refines."""

    name = "Builder"
    player_name = "Builder_Sam"

    FIRST_TIME = [
        "hey, I want to build something specific",
        "build a watchtower — 4 floors, stone base",
        "make the top floor taller",
        "add windows to the second floor",
    ]
    RETURNING = [
        "I'm back to finish my project",
        "add a roof to my watchtower",
        "build a connecting wall around it",
    ]
    STRESS = [
        "build wall section north",
        "build wall section east",
        "build wall section south",
        "build wall section west",
        "add a gate on the north wall",
        "place a turret on each corner",
    ]
    EDGE_CASES = [
        "build a structure with exactly 0 parts",
        "build a house with negative dimensions",
        "make the tower infinitely tall",
        "build with a material called unobtainium",
    ]
    FREEFORM_POOL = [
        "build a fortified gatehouse",
        "create a spiral staircase",
        "build a vaulted cellar",
        "construct a guard barracks",
        "build a marketplace with stalls",
        "create a fountain centerpiece",
        "build a stable with hay bales",
        "construct a library with bookshelves",
        "build a bell tower with a bell",
        "add fortified battlements",
        "build a greenhouse with glass panels",
        "create a statue on a pedestal",
        "build a training dummy arena",
    ]

    def get_message(self, scenario: str, step: int, history: list[dict[str, Any]]) -> str:
        bank = {
            "first-time": self.FIRST_TIME,
            "returning": self.RETURNING,
            "stress": self.STRESS,
            "edge-cases": self.EDGE_CASES,
        }.get(scenario, self.FREEFORM_POOL)

        if scenario == "freeform" or step >= len(bank):
            if history:
                # Refine previous builds
                refinements = [
                    "make the last build taller",
                    "add decorative trim to that",
                    "widen the structure",
                    "add a second story",
                    "reinforce it with stone",
                ]
                return random.choice(refinements)
            return random.choice(self.FREEFORM_POOL)

        return bank[step]

    def get_think_delay(self) -> float:
        return random.uniform(1.5, 3.5)  # Builder thinks carefully


class NewcomerPersona(PlayerPersona):
    """Newcomer — cautious, asks questions, makes typos."""

    name = "Newcomer"
    player_name = "Newbie_Nina"

    FIRST_TIME = [
        "um... hi?",
        "can you... build something? maybe a small house?",
        "oh wow it worked! can you make it prettier?",
        "what else can you do?",
    ]
    RETURNING = [
        "I'm back... I think",
        "remember that house you built me?",
        "can you add a garden to it?",
    ]
    STRESS = [
        "build a tower",
        "wait",
        "sorry I meant a small tower",
        "ok build a fence",
        "and a gate",
        "and maybe some flowers?",
    ]
    EDGE_CASES = [
        "h",
        "...",
        "what's your name?",
        "are you a real person?",
        "I'm scared",
        "build nothing",
    ]
    FREEFORM_POOL = [
        "can you build a little cottage?",
        "um, build a bridge please?",
        "sorry, can you make a small pond?",
        "build a... a treehouse?",
        "oops, I meant build a garden",
        "can you make something pretty?",
        "build a tiny lighthouse?",
        "um, how about a fence?",
        "pleese build a small tower",  # intentional typo
        "can you... make a bench?",
        "build a cute little shed?",
        "sorry, what can you build?",
        "ok build a mailbox",
    ]

    def get_message(self, scenario: str, step: int, history: list[dict[str, Any]]) -> str:
        bank = {
            "first-time": self.FIRST_TIME,
            "returning": self.RETURNING,
            "stress": self.STRESS,
            "edge-cases": self.EDGE_CASES,
        }.get(scenario, self.FREEFORM_POOL)

        if scenario == "freeform" or step >= len(bank):
            msg = random.choice(self.FREEFORM_POOL)
            # Occasionally add a typo
            if random.random() < 0.3:
                msg = self._add_typo(msg)
            return msg

        return bank[step]

    def get_think_delay(self) -> float:
        return random.uniform(3.0, 8.0)  # Newcomer types slowly

    @staticmethod
    def _add_typo(text: str) -> str:
        """Add a random typo to simulate a hesitant typist."""
        if len(text) < 3:
            return text
        pos = random.randint(1, min(len(text) - 2, 10))
        typo_type = random.choice(["swap", "double", "missing"])
        if typo_type == "swap" and pos + 1 < len(text):
            return text[:pos] + text[pos + 1] + text[pos] + text[pos + 2:]
        elif typo_type == "double":
            return text[:pos] + text[pos] + text[pos:]
        else:  # missing
            return text[:pos] + text[pos + 1:]


PERSONAS: dict[str, type[PlayerPersona]] = {
    "explorer": ExplorerPersona,
    "builder": BuilderPersona,
    "newcomer": NewcomerPersona,
}

SCENARIOS = ["first-time", "returning", "stress", "edge-cases", "freeform"]


# ─── Test Runner ─────────────────────────────────────────────────────────────

class PlaytestRunner:
    """Runs playtest scenarios for a persona and journals results."""

    def __init__(
        self,
        persona: PlayerPersona,
        auth_key: str,
        session_id: str | None = None,
    ):
        self.persona = persona
        self.auth_key = auth_key
        self.session_id = session_id or f"playtest-{persona.name.lower()}-{int(time.time())}"
        self.journal = Journal(persona.name, self.session_id)
        self._consecutive_failures = 0  # For adaptive timeout

    def run_interaction(self, message: str) -> dict[str, Any]:
        """Send a single message and journal the result."""
        print(f"\n  📤 Sending: \"{message}\"")

        # Simulate human think/typing time
        delay = self.persona.get_think_delay()
        if delay > 0:
            time.sleep(delay)

        job_id, send_time = send_message(
            self.session_id,
            self.persona.player_name,
            message,
            self.auth_key,
        )

        if not job_id:
            error = "Failed to create job (no jobId returned)"
            print(f"  ❌ {error}")
            entry = self.journal.add_entry(
                message_sent=message,
                response_received="",
                build_commands=[],
                round_trip_seconds=send_time,
                train_of_thought=generate_train_of_thought(
                    self.persona.name, message, "", [], send_time,
                    self.journal.entries, error=error,
                ),
                emotional_reaction=get_emotional_reaction(self.persona.name, 2, error, 0),
                quality_score=2,
                notes="Job creation failed",
                error=error,
            )
            return entry

        print(f"  ⏳ Job {job_id} created, polling...")

        # Adaptive timeout: shorten polling after repeated failures
        current_timeout = POLL_TIMEOUT
        if self._consecutive_failures >= CONSECUTIVE_FAILURES_FOR_ADAPTIVE:
            current_timeout = max(ADAPTIVE_TIMEOUT_MIN, POLL_TIMEOUT / (2 ** (self._consecutive_failures - 1)))
            print(f"  ⚡ Adaptive timeout: {current_timeout:.0f}s ({self._consecutive_failures} consecutive failures)")

        job, poll_time, stale_info = poll_job(job_id, self.auth_key, timeout=current_timeout)

        if not job:
            self._consecutive_failures += 1
            error_msg = f"Job timed out after {current_timeout:.0f}s"
            if stale_info:
                error_msg = f"Job abandoned: {stale_info}"
            print(f"  ❌ {error_msg}")
            entry = self.journal.add_entry(
                message_sent=message,
                response_received="",
                build_commands=[],
                round_trip_seconds=send_time + poll_time,
                train_of_thought=generate_train_of_thought(
                    self.persona.name, message, "", [], send_time + poll_time,
                    self.journal.entries, error=error_msg,
                ),
                emotional_reaction=get_emotional_reaction(self.persona.name, 2, error_msg, 0),
                quality_score=1,
                notes=error_msg,
                error=error_msg,
            )
            return entry

        # Check for error status from the game
        if job.get("status") == "error":
            self._consecutive_failures += 1
            error_msg = f"Job error: {job.get('error', 'unknown error')}"
            print(f"  ❌ {error_msg}")
            entry = self.journal.add_entry(
                message_sent=message,
                response_received="",
                build_commands=[],
                round_trip_seconds=send_time + poll_time,
                train_of_thought=generate_train_of_thought(
                    self.persona.name, message, "", [], send_time + poll_time,
                    self.journal.entries, error=error_msg,
                ),
                emotional_reaction=get_emotional_reaction(self.persona.name, 2, error_msg, 0),
                quality_score=1,
                notes=error_msg,
                error=error_msg,
            )
            return entry

        # Success — reset failure counter
        self._consecutive_failures = 0

        reply = job.get("reply", "")
        commands = job.get("commands", [])
        if isinstance(commands, str):
            try:
                commands = json.loads(commands)
            except json.JSONDecodeError:
                commands = []

        round_trip = send_time + poll_time
        quality = score_quality(reply, commands, round_trip)

        print(f"  ✅ Got reply ({len(reply)} chars, {len(commands)} commands, {round_trip:.1f}s)")
        reply_preview = reply[:120] + "..." if len(reply) > 120 else reply
        print(f"  💬 \"{reply_preview}\"")

        tot = generate_train_of_thought(
            self.persona.name,
            message,
            reply,
            commands,
            round_trip,
            self.journal.entries,
        )

        # Build notes
        notes_parts: list[str] = []
        if check_voice_in_character(reply):
            notes_parts.append("Voice was in character")
        else:
            notes_parts.append("Voice dropped character")
        if commands:
            materials = set()
            for c in commands:
                m = c.get("params", c).get("material", "")
                if m:
                    materials.add(m)
            if materials:
                notes_parts.append(f"Materials: {', '.join(sorted(materials))}")
        # Check for anchored parts
        create_parts = [c for c in commands if c.get("type") == "createPart"]
        if create_parts:
            anchored = sum(1 for c in create_parts if c.get("params", c).get("anchored"))
            notes_parts.append(f"{anchored}/{len(create_parts)} parts anchored")

        entry = self.journal.add_entry(
            message_sent=message,
            response_received=reply,
            build_commands=commands,
            round_trip_seconds=round_trip,
            train_of_thought=tot,
            emotional_reaction=get_emotional_reaction(self.persona.name, quality, None, len(commands)),
            quality_score=quality,
            notes="; ".join(notes_parts),
        )
        return entry

    def run_scenario(self, scenario: str, max_steps: int = 20) -> None:
        """Run a scripted scenario."""
        print(f"\n{'─' * 60}")
        print(f"  🎭 Persona: {self.persona.name}")
        print(f"  📋 Scenario: {scenario}")
        print(f"  🆔 Session: {self.session_id}")
        print(f"{'─' * 60}")

        step = 0
        while step < max_steps:
            message = self.persona.get_message(scenario, step, self.journal.entries)
            if not message:
                break

            self.run_interaction(message)
            step += 1

            # For scripted scenarios, stop when we've used the bank
            if scenario != "freeform" and scenario != "continuous":
                bank_sizes = {
                    "first-time": 4,
                    "returning": 3,
                    "stress": 6,
                    "edge-cases": 6,
                }
                if step >= bank_sizes.get(scenario, 4):
                    break

        self.journal.print_summary()

    def run_continuous(self, max_interactions: int = 50) -> None:
        """Run continuously until stopped or max_interactions reached."""
        print(f"\n{'─' * 60}")
        print(f"  🎭 Persona: {self.persona.name}")
        print(f"  📋 Mode: CONTINUOUS")
        print(f"  🆔 Session: {self.session_id}")
        print(f"  ⏹️  Max interactions: {max_interactions}")
        print(f"{'─' * 60}")

        for i in range(max_interactions):
            print(f"\n  ── Interaction {i + 1}/{max_interactions} ──")
            message = self.persona.get_message("freeform", i, self.journal.entries)
            self.run_interaction(message)

        self.journal.print_summary()

    def run_freeform(self, message: str) -> None:
        """Send a single freeform message."""
        self.run_interaction(message)
        self.journal.print_summary()


# ─── CLI Entry Point ─────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lucineer AI Playtest Harness — sends messages as AI personas and journals results.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 playtest_harness.py --persona explorer --scenario first-time
  python3 playtest_harness.py --persona builder --scenario stress
  python3 playtest_harness.py --all-personas --scenario edge-cases
  python3 playtest_harness.py --persona newcomer --continuous --max-interactions 10
  python3 playtest_harness.py --persona explorer --freeform "build a volcano"

Personas:
  explorer  — tests boundaries, varied builds, boundary-pushing requests
  builder   — systematic, specific structures, refines and iterates
  newcomer  — cautious, asks questions, makes typos, types slowly

Scenarios:
  first-time   — greeting → first build → reaction → second build
  returning    — references previous builds
  stress       — rapid-fire messages
  edge-cases   — weird inputs and boundary conditions
  freeform     — random/varied messages (default for --continuous)
        """,
    )

    parser.add_argument(
        "--persona",
        choices=list(PERSONAS.keys()),
        help="Which persona to run",
    )
    parser.add_argument(
        "--all-personas",
        action="store_true",
        help="Run all three personas",
    )
    parser.add_argument(
        "--scenario",
        choices=SCENARIOS,
        default="first-time",
        help="Test scenario to run (default: first-time)",
    )
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Keep sending messages until stopped or --max-interactions reached",
    )
    parser.add_argument(
        "--max-interactions",
        type=int,
        default=20,
        help="Max interactions for --continuous mode (default: 20)",
    )
    parser.add_argument(
        "--freeform",
        type=str,
        default=None,
        help="Send a single freeform message (overrides scenario)",
    )
    parser.add_argument(
        "--auth-key",
        default=DEFAULT_AUTH_KEY,
        help="Auth key (or set LUCINEER_KEY env var)",
    )
    parser.add_argument(
        "--worker-url",
        default=_DEFAULT_WORKER_URL,
        help=f"Worker relay URL (default: {_DEFAULT_WORKER_URL})",
    )

    args = parser.parse_args()

    # Normalize worker URL (module-level for helper functions)
    _set_worker_url(args.worker_url.rstrip("/"))
    auth_key = args.auth_key

    if not args.persona and not args.all_personas:
        print("ERROR: Must specify --persona or --all-personas")
        parser.print_help()
        return 1

    # Determine which personas to run
    persona_keys = list(PERSONAS.keys()) if args.all_personas else [args.persona]

    # Create journal directory
    os.makedirs(JOURNAL_DIR, exist_ok=True)

    # Print header
    print()
    print("╔" + "═" * 58 + "╗")
    print("║" + " LUCINEER AI PLAYTEST HARNESS".ljust(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print(f"  Worker:    {WORKER_URL}")
    print(f"  Auth:      {'✅ set' if auth_key != 'AUTH_KEY_PLACEHOLDER' else '⚠️  placeholder'}")
    print(f"  Journal:   {JOURNAL_DIR}")
    print(f"  Time:      {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    sys.stdout.flush()

    overall_start = time.monotonic()

    for pkey in persona_keys:
        persona_cls = PERSONAS[pkey]
        persona = persona_cls()

        # Each persona gets its own session
        session_id = f"playtest-{pkey}-{int(time.time())}"

        runner = PlaytestRunner(persona, auth_key, session_id)

        if args.freeform:
            runner.run_freeform(args.freeform)
        elif args.continuous:
            runner.run_continuous(max_interactions=args.max_interactions)
        else:
            runner.run_scenario(args.scenario)

    elapsed = time.monotonic() - overall_start
    print(f"\n⏱️  Total elapsed: {elapsed:.1f}s")

    return 0


if __name__ == "__main__":
    sys.exit(main())
