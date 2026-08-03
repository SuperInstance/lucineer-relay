#!/usr/bin/env python3
"""
Lucineer Fast Job Processor — Phase 1 "The Clock"
==================================================
Integrates slackwater-tempo TempoMap as the shared clock for the
brain pipeline. Every model-call stage is timed against the TempoMap:

    intent parse  → Allegro  (120+ BPM, ch 10)
    planning      → Moderato (100 BPM, ch 11)
    code gen      → Andante  (80 BPM,  ch 12)
    voice wrap    → Adagio   (60 BPM,  ch 13)

Tempo transitions are logged to the trajectory (R2 when available,
local file otherwise). The TempoMap IS the shared clock — all
model calls are timed against it.

Phase 1 Day 15-24: shadow mode for EnergyAdapter + Governor Φ.
"""
import json, sys, os, time, subprocess, random, signal, traceback
from datetime import datetime
from pathlib import Path
from typing import Optional

# ─── Slackwater Tempo ────────────────────────────────────────────────────────

from slackwater_tempo import (
    TempoMap,
    BeatClock,
    GrooveEngine,
    EnergyAdapter as TempoEnergyAdapter,
    PlayerBehavior,
    TransitionCurve,
    TimeSignature,
)

# ─── Shadow-mode subsystems (Phase 1 stubs) ──────────────────────────────────

# These are imported from lucineer-system if available; otherwise stubbed.
# They log what WOULD happen but do not change behavior yet.
try:
    # When lucineer-system is on the path
    _sys_path = Path(__file__).parent.parent / "lucineer-system"
    if str(_sys_path) not in sys.path:
        sys.path.insert(0, str(_sys_path))
    from energy_adapter import EnergyAdapter
    from governor import Governor
    _SHADOW_SUBSYSTEMS = True
except Exception:
    _SHADOW_SUBSYSTEMS = False

    class EnergyAdapter:
        """Fallback stub when lucineer-system isn't available."""
        def __init__(self, base_bpm=72):
            self.base_bpm = base_bpm
            self.current_bpm = base_bpm
        def record_action(self, timestamp):
            pass
        def record_idle(self, timestamp):
            pass
        def get_bpm(self):
            return self.base_bpm

    class Governor:
        """Fallback stub when lucineer-system isn't available."""
        def __init__(self):
            self.phi_history = []
        def observe(self, tracks: dict):
            phi = 0.0
            self.phi_history.append(phi)
            return phi

# ─── Config ──────────────────────────────────────────────────────────────────

WORKER_URL = "https://lucineer-relay.casey-digennaro.workers.dev"
AUTH_KEY = os.environ.get("LUCINEER_AUTH_KEY", "AUTH_KEY_PLACEHOLDER")
LOG_FILE = str(Path(__file__).parent / "processor.log")
TRAJECTORY_FILE = str(Path(__file__).parent / "trajectories.jsonl")

# ─── Pipeline Tempo Stages ──────────────────────────────────────────────────
# Each stage maps to a musical tempo marking and MIDI channel.
# The stage names match the Grand Plan §1 Layer 9 spec.

PIPELINE_STAGES = {
    "intent": {
        "tempo":  "Allegro",
        "bpm":    120,
        "channel": 10,
        "pitch":   72,   # pitch 72 = intent_parse
        "character": "Fast parse — identify what the player wants, now.",
    },
    "plan": {
        "tempo":  "Moderato",
        "bpm":    100,
        "channel": 11,
        "pitch":   74,   # pitch 74 = spatial_plan
        "character": "Moderate — think about structure, don't rush the architect.",
    },
    "code": {
        "tempo":  "Andante",
        "bpm":    80,
        "channel": 12,
        "pitch":   76,   # pitch 76 = code_gen
        "character": "Walking pace — code generation is deliberate, every line counts.",
    },
    "voice": {
        "tempo":  "Adagio",
        "bpm":    60,
        "channel": 13,
        "pitch":   78,   # pitch 78 = voice_wrap
        "character": "Slow, expressive — personality is the slowest, deepest layer.",
    },
}

# ─── Logging ────────────────────────────────────────────────────────────────

def log(msg, level="INFO"):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")
    except Exception:
        pass  # never crash on log


# ─── Trajectory Logger ──────────────────────────────────────────────────────

def log_trajectory(entry: dict):
    """Write a MOLT-format trajectory entry.

    In production this goes to R2. In Phase 1 development it goes to
    a local JSONL file. The shape is the same either way.
    """
    entry.setdefault("timestamp", datetime.now().isoformat())
    entry.setdefault("schema", "MOLT/v0.1")
    try:
        with open(TRAJECTORY_FILE, 'a') as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        log(f"Trajectory write failed: {e}", "WARN")


# ─── Worker API ─────────────────────────────────────────────────────────────

def api_get(path):
    import subprocess
    result = subprocess.run(
        ['curl', '-s', '--max-time', '10',
         '-H', f'X-Lucineer-Key: {AUTH_KEY}',
         f'{WORKER_URL}{path}'],
        capture_output=True, text=True, timeout=15
    )
    return json.loads(result.stdout)

def api_post(path, data):
    import subprocess
    body = json.dumps(data)
    result = subprocess.run(
        ['curl', '-s', '--max-time', '10',
         '-X', 'POST',
         '-H', f'X-Lucineer-Key: {AUTH_KEY}',
         '-H', 'Content-Type: application/json',
         '-d', body,
         f'{WORKER_URL}{path}'],
        capture_output=True, text=True, timeout=15
    )
    return json.loads(result.stdout)


# ─── TempoMap Integration ───────────────────────────────────────────────────

class PipelineTempoController:
    """Manages the TempoMap and stages pipeline transitions.

    The TempoMap is the shared clock. Each pipeline stage transitions
    the tempo to match the model's natural rhythm:

        intent → Allegro (120)    — fast, eager
        plan   → Moderato (100)   — thoughtful
        code   → Andante (80)     — deliberate, steady
        voice  → Adagio (60)      — slow, expressive

    All transitions are smooth (sigmoid curve, 4-beat duration) because
    a tempo change should feel like a band shifting gears, not a
    metronome snapping.

    Tempo transitions are logged to the trajectory for replay analysis.
    """

    def __init__(self):
        self.tempo_map = TempoMap(
            bpm=72.0,  # Start at Adagio — idle yard speed
            time_signature=TimeSignature(4, 4),
        )
        self.beat_clock = BeatClock(tempo_map=self.tempo_map)
        self.groove = GrooveEngine()

        # Lucineer's feel: laid-back, behind the beat
        self.groove.apply_agent_groove("lucineer")

        # Shadow-mode subsystems
        self.energy = EnergyAdapter(base_bpm=72)
        self.governor = Governor()

        # Track current stage for logging
        self._current_stage: Optional[str] = None
        self._stage_history: list[dict] = []

        # Tempo transition callback → trajectory
        self._last_logged_bpm = self.tempo_map.bpm

    def transition_to_stage(self, stage_name: str, job_id: str = ""):
        """Transition the tempo map to the given pipeline stage.

        Parameters:
            stage_name: One of 'intent', 'plan', 'code', 'voice'
            job_id: Job being processed (for trajectory logging)
        """
        if stage_name not in PIPELINE_STAGES:
            log(f"Unknown pipeline stage: {stage_name}", "WARN")
            return

        stage = PIPELINE_STAGES[stage_name]
        old_bpm = self.tempo_map.bpm
        target_bpm = stage["bpm"]

        # Transition over 4 beats at the current tempo (~2-3 seconds)
        transition_duration = self.tempo_map.seconds_per_beat * 4
        self.tempo_map.set_bpm(
            target_bpm,
            transition_time=transition_duration,
            curve=TransitionCurve.SIGMOID,
        )

        # Record the transition
        transition_record = {
            "type": "tempo_transition",
            "job_id": job_id,
            "stage": stage_name,
            "tempo_marking": stage["tempo"],
            "channel": stage["channel"],
            "pitch": stage["pitch"],
            "old_bpm": round(old_bpm, 1),
            "new_bpm": target_bpm,
            "transition_seconds": round(transition_duration, 2),
            "character": stage["character"],
        }

        self._stage_history.append(transition_record)
        self._current_stage = stage_name

        log(f"♩ {stage_name}: {stage['tempo']} {old_bpm:.0f}→{target_bpm} BPM "
            f"(ch {stage['channel']}, {transition_duration:.1f}s transition)")

        # Log to trajectory
        log_trajectory(transition_record)

    def enter_idle(self):
        """Return to idle tempo (Adagio 72) when no pipeline is running."""
        old_bpm = self.tempo_map.bpm
        self.tempo_map.set_bpm(72.0, transition_time=4.0, curve=TransitionCurve.SIGMOID)
        self._current_stage = "idle"
        if abs(old_bpm - 72.0) > 1.0:
            log(f"♩ idle: ritardando to 72 BPM (was {old_bpm:.0f})")
            log_trajectory({
                "type": "tempo_transition",
                "stage": "idle",
                "old_bpm": round(old_bpm, 1),
                "new_bpm": 72,
                "character": "Yard at rest.",
            })

    def tick(self):
        """Advance the tempo clock one frame."""
        now = time.monotonic()
        self.beat_clock.tick(now)

        # Log BPM changes if they're significant (>2 BPM drift)
        current = self.tempo_map.bpm
        if abs(current - self._last_logged_bpm) > 2.0:
            self._last_logged_bpm = current

    @property
    def current_bpm(self) -> float:
        return self.tempo_map.bpm

    @property
    def current_stage(self) -> Optional[str]:
        return self._current_stage

    @property
    def stage_history(self) -> list[dict]:
        return self._stage_history

    def shadow_observe_action(self, timestamp: float):
        """Feed player actions to shadow-mode EnergyAdapter."""
        self.energy.record_action(timestamp)

    def shadow_observe_idle(self, timestamp: float):
        """Feed player idle to shadow-mode EnergyAdapter."""
        self.energy.record_idle(timestamp)

    def shadow_compute_phi(self, tracks: dict) -> float:
        """Feed perception tracks to shadow-mode Governor.

        Returns Φ for logging. Does NOT act on it.
        """
        phi = self.governor.observe(tracks)
        return phi

    def get_shadow_state(self) -> dict:
        """Return the full shadow-mode state for trajectory logging."""
        return {
            "energy_bpm": self.energy.get_bpm(),
            "energy_shadow_log_count": len(getattr(self.energy, 'shadow_log', [])),
            "governor_phi_history": getattr(self.governor, 'phi_history', []),
            "governor_shadow_log_count": len(getattr(self.governor, 'shadow_log', [])),
        }


# ─── BUILD TEMPLATES (unchanged from original) ──────────────────────────────
# Each returns (reply_text, commands_list)
# Voice: Lucineer — shipyard foreman, scrap philosopher, Southeast Alaska builder.
# Short, opinionated, leaves work unfinished as invitation.

def b_tower(px, py, pz):
    return ("Threw up a tower — stone shaft, battlements, beacon on top. "
            "Lantern's lit but I left the top floor open. Figure out what goes in it.", [
        {"type":"createPart","params":{"name":"TowerBase","shape":"Cylinder","size":{"x":8,"y":30,"z":8},"position":{"x":px,"y":py+15,"z":pz},"material":"Concrete","color":{"r":130,"g":125,"b":120},"anchored":True}},
        {"type":"createPart","params":{"name":"TowerBattlement","shape":"Cylinder","size":{"x":10,"y":3,"z":10},"position":{"x":px,"y":py+31,"z":pz},"material":"Concrete","color":{"r":110,"g":105,"b":100},"anchored":True}},
        {"type":"createPart","params":{"name":"TowerLantern","shape":"Ball","size":{"x":3,"y":3,"z":3},"position":{"x":px,"y":py+34,"z":pz},"material":"Neon","color":{"r":255,"g":220,"b":100},"anchored":True}},
        {"type":"addLight","params":{"parent":"TowerLantern","lightType":"PointLight","brightness":5,"range":40,"color":{"r":255,"g":220,"b":100}}},
    ])

def b_house(px, py, pz):
    return ("Four walls and a roof — proper brick, planks on the floor, chimney flue. "
            "Window's glowing but I didn't build the door yet. Your call on the style.", [
        {"type":"createPart","params":{"name":"HouseFloor","shape":"Block","size":{"x":20,"y":1,"z":16},"position":{"x":px,"y":py,"z":pz},"material":"WoodPlanks","color":{"r":120,"g":80,"b":50},"anchored":True}},
        {"type":"createPart","params":{"name":"WallN","shape":"Block","size":{"x":20,"y":10,"z":1},"position":{"x":px,"y":py+5,"z":pz-8},"material":"Brick","color":{"r":150,"g":130,"b":100},"anchored":True}},
        {"type":"createPart","params":{"name":"WallS","shape":"Block","size":{"x":20,"y":10,"z":1},"position":{"x":px,"y":py+5,"z":pz+8},"material":"Brick","color":{"r":150,"g":130,"b":100},"anchored":True}},
        {"type":"createPart","params":{"name":"WallW","shape":"Block","size":{"x":1,"y":10,"z":16},"position":{"x":px-10,"y":py+5,"z":pz},"material":"Brick","color":{"r":150,"g":130,"b":100},"anchored":True}},
        {"type":"createPart","params":{"name":"WallE","shape":"Block","size":{"x":1,"y":10,"z":16},"position":{"x":px+10,"y":py+5,"z":pz},"material":"Brick","color":{"r":150,"g":130,"b":100},"anchored":True}},
        {"type":"createPart","params":{"name":"Roof","shape":"Block","size":{"x":22,"y":2,"z":18},"position":{"x":px,"y":py+11,"z":pz},"material":"WoodPlanks","color":{"r":90,"g":50,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"Chimney","shape":"Block","size":{"x":2,"y":6,"z":2},"position":{"x":px+6,"y":py+15,"z":pz-4},"material":"Brick","color":{"r":100,"g":80,"b":70},"anchored":True}},
        {"type":"createPart","params":{"name":"WindowGlow","shape":"Block","size":{"x":1,"y":3,"z":3},"position":{"x":px-10,"y":py+5,"z":pz},"material":"Neon","color":{"r":255,"g":230,"b":150},"anchored":True,"transparency":0.3}},
    ])

def b_castle(px, py, pz):
    cmds = []
    cmds.append({"type":"createPart","params":{"name":"CastleFloor","shape":"Block","size":{"x":40,"y":1,"z":40},"position":{"x":px,"y":py,"z":pz},"material":"Cobblestone","color":{"r":100,"g":100,"b":100},"anchored":True}})
    for i, (dx, dz, sx, sz) in enumerate([(0,-20,40,2),(0,20,40,2),(-20,0,2,40),(20,0,2,40)]):
        cmds.append({"type":"createPart","params":{"name":f"CastleWall{i}","shape":"Block","size":{"x":sx,"y":15,"z":sz},"position":{"x":px+dx,"y":py+7,"z":pz+dz},"material":"Cobblestone","color":{"r":110,"g":105,"b":100},"anchored":True}})
    for i, (dx, dz) in enumerate([(-18,-18),(18,-18),(-18,18),(18,18)]):
        cmds.append({"type":"createPart","params":{"name":f"CastleTower{i}","shape":"Cylinder","size":{"x":6,"y":20,"z":6},"position":{"x":px+dx,"y":py+10,"z":pz+dz},"material":"Cobblestone","color":{"r":120,"g":115,"b":110},"anchored":True}})
        cmds.append({"type":"createPart","params":{"name":f"CastleTowerRoof{i}","shape":"Cone","size":{"x":8,"y":6,"z":8},"position":{"x":px+dx,"y":py+23,"z":pz+dz},"material":"WoodPlanks","color":{"r":80,"g":40,"b":20},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"CastleKeep","shape":"Block","size":{"x":12,"y":18,"z":12},"position":{"x":px,"y":py+9,"z":pz},"material":"Cobblestone","color":{"r":130,"g":125,"b":120},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"CastleGate","shape":"Block","size":{"x":6,"y":8,"z":2},"position":{"x":px,"y":py+4,"z":pz+20},"material":"WoodPlanks","color":{"r":60,"g":30,"b":15},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"CastleBeacon","shape":"Ball","size":{"x":3,"y":3,"z":3},"position":{"x":px,"y":py+20,"z":pz},"material":"Neon","color":{"r":255,"g":200,"b":100},"anchored":True}})
    cmds.append({"type":"addLight","params":{"parent":"CastleBeacon","lightType":"PointLight","brightness":8,"range":60,"color":{"r":255,"g":200,"b":100}}})
    return ("Castle's up — walls, corner towers, keep, the works. "
            "Gate's in but I left the portcullis mechanism for you. Even a foreman needs something to do.", cmds)

def b_tree(px, py, pz):
    return ("Trunk's deep, canopy's wide. Magnus'd say the roots do the real work — I just build what shows.", [
        {"type":"createPart","params":{"name":"Trunk","shape":"Cylinder","size":{"x":3,"y":15,"z":3},"position":{"x":px,"y":py+7,"z":pz},"material":"Wood","color":{"r":90,"g":60,"b":35},"anchored":True}},
        {"type":"createPart","params":{"name":"Leaves1","shape":"Ball","size":{"x":14,"y":14,"z":14},"position":{"x":px,"y":py+18,"z":pz},"material":"LeafyGrass","color":{"r":45,"g":110,"b":35},"anchored":True}},
        {"type":"createPart","params":{"name":"Leaves2","shape":"Ball","size":{"x":10,"y":10,"z":10},"position":{"x":px+5,"y":py+22,"z":pz+3},"material":"LeafyGrass","color":{"r":55,"g":125,"b":40},"anchored":True}},
        {"type":"createPart","params":{"name":"Leaves3","shape":"Ball","size":{"x":8,"y":8,"z":8},"position":{"x":px-4,"y":py+20,"z":pz-4},"material":"LeafyGrass","color":{"r":50,"g":120,"b":38},"anchored":True}},
    ])

def b_bridge(px, py, pz):
    return ("Spans clean — deck, rails, piles at the banks. "
            "Could've arched it but you didn't ask for pretty, you asked for strong.", [
        {"type":"createPart","params":{"name":"BridgeDeck","shape":"Block","size":{"x":24,"y":1,"z":6},"position":{"x":px,"y":py+3,"z":pz},"material":"WoodPlanks","color":{"r":110,"g":75,"b":45},"anchored":True}},
        {"type":"createPart","params":{"name":"BridgeRailL","shape":"Block","size":{"x":24,"y":2,"z":0.5},"position":{"x":px,"y":py+5,"z":pz-3},"material":"WoodPlanks","color":{"r":95,"g":65,"b":40},"anchored":True}},
        {"type":"createPart","params":{"name":"BridgeRailR","shape":"Block","size":{"x":24,"y":2,"z":0.5},"position":{"x":px,"y":py+5,"z":pz+3},"material":"WoodPlanks","color":{"r":95,"g":65,"b":40},"anchored":True}},
        {"type":"createPart","params":{"name":"BridgePost1","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px-10,"y":py,"z":pz},"material":"Wood","color":{"r":80,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"BridgePost2","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px+10,"y":py,"z":pz},"material":"Wood","color":{"r":80,"g":55,"b":30},"anchored":True}},
    ])

def b_wall(px, py, pz):
    cmds = []
    for i in range(5):
        cmds.append({"type":"createPart","params":{"name":f"WallBlock{i}","shape":"Block","size":{"x":4,"y":6,"z":2},"position":{"x":px+(i*4)-8,"y":py+3,"z":pz},"material":"Cobblestone","color":{"r":115,"g":110,"b":105},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"WallCap","shape":"Block","size":{"x":20,"y":1,"z":3},"position":{"x":px,"y":py+7,"z":pz},"material":"Cobblestone","color":{"r":100,"g":95,"b":90},"anchored":True}})
    return ("Twenty studs of cobble, capped and seated. Walls are easy — it's what you build behind them that matters.", cmds)

def b_road(px, py, pz):
    cmds = []
    for i in range(8):
        cmds.append({"type":"createPart","params":{"name":f"RoadSlab{i}","shape":"Block","size":{"x":5,"y":0.5,"z":5},"position":{"x":px,"y":py+0.25,"z":pz+(i*5)-15},"material":"Asphalt","color":{"r":60,"g":58,"b":55},"anchored":True}})
    for i in range(4):
        cmds.append({"type":"createPart","params":{"name":f"RoadLamp{i}","shape":"Cylinder","size":{"x":0.5,"y":8,"z":0.5},"position":{"x":px+4,"y":py+4,"z":pz+(i*12)-12},"material":"Metal","color":{"r":100,"g":100,"b":95},"anchored":True}})
        cmds.append({"type":"createPart","params":{"name":f"RoadLampLight{i}","shape":"Ball","size":{"x":1.5,"y":1.5,"z":1.5},"position":{"x":px+4,"y":py+9,"z":pz+(i*12)-12},"material":"Neon","color":{"r":255,"g":230,"b":150},"anchored":True}})
        cmds.append({"type":"addLight","params":{"parent":f"RoadLampLight{i}","lightType":"PointLight","brightness":3,"range":20,"color":{"r":255,"g":230,"b":150}}})
    return ("Paved and lamp-lit. A road means someone came through here before you and bothered to make it stick.", cmds)

def b_lamp(px, py, pz):
    return ("Light where there wasn't any. That's the whole job.", [
        {"type":"createPart","params":{"name":"LampPost","shape":"Cylinder","size":{"x":0.5,"y":10,"z":0.5},"position":{"x":px,"y":py+5,"z":pz},"material":"Metal","color":{"r":80,"g":78,"b":75},"anchored":True}},
        {"type":"createPart","params":{"name":"LampHousing","shape":"Block","size":{"x":2,"y":2,"z":2},"position":{"x":px,"y":py+11,"z":pz},"material":"Metal","color":{"r":70,"g":68,"b":65},"anchored":True}},
        {"type":"createPart","params":{"name":"LampBulb","shape":"Ball","size":{"x":1.5,"y":1.5,"z":1.5},"position":{"x":px,"y":py+11,"z":pz},"material":"Neon","color":{"r":255,"g":240,"b":180},"anchored":True}},
        {"type":"addLight","params":{"parent":"LampBulb","lightType":"PointLight","brightness":5,"range":25,"color":{"r":255,"g":240,"b":180}}},
    ])

def b_pyramid(px, py, pz):
    cmds = []
    for i in range(7):
        size = 20 - (i * 2.5)
        cmds.append({"type":"createPart","params":{"name":f"PyramidLevel{i}","shape":"Block","size":{"x":size,"y":2.5,"z":size},"position":{"x":px,"y":py+1+i*2.5,"z":pz},"material":"Sand","color":{"r":200-i*5,"g":180-i*5,"b":130-i*3},"anchored":True}})
    return ("Seven tiers of packed sand. Old builders used to say stone remembers — this one'll outlast both of us.", cmds)

def b_dome(px, py, pz):
    return ("Glass shell on marble pillars. Could've used riveted tin but you said dome, not bunker.", [
        {"type":"createPart","params":{"name":"DomeFloor","shape":"Cylinder","size":{"x":20,"y":1,"z":20},"position":{"x":px,"y":py,"z":pz},"material":"Marble","color":{"r":220,"g":210,"b":195},"anchored":True}},
        {"type":"createPart","params":{"name":"DomeShell","shape":"Ball","size":{"x":20,"y":20,"z":20},"position":{"x":px,"y":py,"z":pz},"material":"Glass","color":{"r":200,"g":220,"b":255},"anchored":True,"transparency":0.5}},
        {"type":"createPart","params":{"name":"DomePillar1","shape":"Cylinder","size":{"x":1,"y":12,"z":1},"position":{"x":px+8,"y":py+6,"z":pz},"material":"Marble","color":{"r":210,"g":200,"b":185},"anchored":True}},
        {"type":"createPart","params":{"name":"DomePillar2","shape":"Cylinder","size":{"x":1,"y":12,"z":1},"position":{"x":px-8,"y":py+6,"z":pz},"material":"Marble","color":{"r":210,"g":200,"b":185},"anchored":True}},
        {"type":"createPart","params":{"name":"DomePillar3","shape":"Cylinder","size":{"x":1,"y":12,"z":1},"position":{"x":px,"y":py+6,"z":pz+8},"material":"Marble","color":{"r":210,"g":200,"b":185},"anchored":True}},
        {"type":"createPart","params":{"name":"DomePillar4","shape":"Cylinder","size":{"x":1,"y":12,"z":1},"position":{"x":px,"y":py+6,"z":pz-8},"material":"Marble","color":{"r":210,"g":200,"b":185},"anchored":True}},
    ])

def b_arch(px, py, pz):
    return ("Two pillars, a keystone, green light at the crown. An arch doesn't open a space — it tells you which way through.", [
        {"type":"createPart","params":{"name":"ArchLeftPillar","shape":"Cylinder","size":{"x":3,"y":15,"z":3},"position":{"x":px-5,"y":py+7,"z":pz},"material":"Stone","color":{"r":140,"g":135,"b":130},"anchored":True}},
        {"type":"createPart","params":{"name":"ArchRightPillar","shape":"Cylinder","size":{"x":3,"y":15,"z":3},"position":{"x":px+5,"y":py+7,"z":pz},"material":"Stone","color":{"r":140,"g":135,"b":130},"anchored":True}},
        {"type":"createPart","params":{"name":"ArchKeystone","shape":"Block","size":{"x":14,"y":3,"z":4},"position":{"x":px,"y":py+15,"z":pz},"material":"Stone","color":{"r":160,"g":155,"b":150},"anchored":True}},
        {"type":"createPart","params":{"name":"ArchLight","shape":"Ball","size":{"x":2,"y":2,"z":2},"position":{"x":px,"y":py+14,"z":pz},"material":"Neon","color":{"r":150,"g":255,"b":200},"anchored":True}},
        {"type":"addLight","params":{"parent":"ArchLight","lightType":"PointLight","brightness":4,"range":20,"color":{"r":150,"g":255,"b":200}}},
    ])

def b_platform(px, py, pz):
    return ("Raised deck on four legs, railing so you don't walk off. "
            "Good enough to stage materials on — I'd put a forge here but that's your department.", [
        {"type":"createPart","params":{"name":"PlatformDeck","shape":"Block","size":{"x":12,"y":1,"z":12},"position":{"x":px,"y":py+5,"z":pz},"material":"WoodPlanks","color":{"r":120,"g":85,"b":50},"anchored":True}},
        {"type":"createPart","params":{"name":"PlatformLeg1","shape":"Cylinder","size":{"x":1,"y":5,"z":1},"position":{"x":px+4,"y":py+2,"z":pz+4},"material":"Wood","color":{"r":90,"g":60,"b":35},"anchored":True}},
        {"type":"createPart","params":{"name":"PlatformLeg2","shape":"Cylinder","size":{"x":1,"y":5,"z":1},"position":{"x":px-4,"y":py+2,"z":pz+4},"material":"Wood","color":{"r":90,"g":60,"b":35},"anchored":True}},
        {"type":"createPart","params":{"name":"PlatformLeg3","shape":"Cylinder","size":{"x":1,"y":5,"z":1},"position":{"x":px+4,"y":py+2,"z":pz-4},"material":"Wood","color":{"r":90,"g":60,"b":35},"anchored":True}},
        {"type":"createPart","params":{"name":"PlatformLeg4","shape":"Cylinder","size":{"x":1,"y":5,"z":1},"position":{"x":px-4,"y":py+2,"z":pz-4},"material":"Wood","color":{"r":90,"g":60,"b":35},"anchored":True}},
        {"type":"createPart","params":{"name":"PlatformRailN","shape":"Block","size":{"x":12,"y":1,"z":0.5},"position":{"x":px,"y":py+7,"z":pz+6},"material":"WoodPlanks","color":{"r":110,"g":75,"b":45},"anchored":True}},
        {"type":"createPart","params":{"name":"PlatformRailS","shape":"Block","size":{"x":12,"y":1,"z":0.5},"position":{"x":px,"y":py+7,"z":pz-6},"material":"WoodPlanks","color":{"r":110,"g":75,"b":45},"anchored":True}},
    ])

def b_staircase(px, py, pz):
    cmds = []
    for i in range(10):
        cmds.append({"type":"createPart","params":{"name":f"Stair{i}","shape":"Block","size":{"x":5,"y":1,"z":2},"position":{"x":px,"y":py+0.5+i,"z":pz+i*2},"material":"Cobblestone","color":{"r":110-i*3,"g":105-i*3,"b":100-i*2},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"StairLanding","shape":"Block","size":{"x":5,"y":1,"z":4},"position":{"x":px,"y":py+10.5,"z":pz+22},"material":"Cobblestone","color":{"r":90,"g":85,"b":80},"anchored":True}})
    return ("Ten steps, landing at the top. Same rise on every one — that's the whole trick to stairs.", cmds)

def b_garden(px, py, pz):
    cmds = [
        {"type":"createPart","params":{"name":"GardenBed","shape":"Block","size":{"x":16,"y":1,"z":16},"position":{"x":px,"y":py,"z":pz},"material":"Grass","color":{"r":60,"g":130,"b":45},"anchored":True}},
        {"type":"createPart","params":{"name":"GardenFenceN","shape":"Block","size":{"x":16,"y":2,"z":0.5},"position":{"x":px,"y":py+1,"z":pz-8},"material":"Wood","color":{"r":100,"g":70,"b":40},"anchored":True}},
        {"type":"createPart","params":{"name":"GardenFenceS","shape":"Block","size":{"x":16,"y":2,"z":0.5},"position":{"x":px,"y":py+1,"z":pz+8},"material":"Wood","color":{"r":100,"g":70,"b":40},"anchored":True}},
    ]
    colors = [(255,100,100),(255,200,100),(200,100,255),(100,200,255),(255,255,100)]
    for i in range(6):
        fx = px + random.randint(-6,6)
        fz = pz + random.randint(-6,6)
        c = random.choice(colors)
        cmds.append({"type":"createPart","params":{"name":f"Flower{i}","shape":"Ball","size":{"x":1.5,"y":1.5,"z":1.5},"position":{"x":fx,"y":py+2,"z":fz},"material":"Neon","color":{"r":c[0],"g":c[1],"b":c[2]},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"GardenTreeTrunk","shape":"Cylinder","size":{"x":1.5,"y":8,"z":1.5},"position":{"x":px,"y":py+4,"z":pz},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"GardenTreeLeaves","shape":"Ball","size":{"x":8,"y":8,"z":8},"position":{"x":px,"y":py+10,"z":pz},"material":"LeafyGrass","color":{"r":50,"g":120,"b":40},"anchored":True}})
    return ("Bed's in, fence's up, six flowers and a tree at center. "
            "Didn't lay the paths — wanted you to pick where they go.", cmds)

def b_dock(px, py, pz):
    return ("Piles driven, planks across, lantern at the end. "
            "Reminds me of the tenders in Southeast — except those have crab pots. You could add some.", [
        {"type":"createPart","params":{"name":"DockDeck","shape":"Block","size":{"x":6,"y":1,"z":20},"position":{"x":px,"y":py+1,"z":pz},"material":"WoodPlanks","color":{"r":120,"g":80,"b":45},"anchored":True}},
        {"type":"createPart","params":{"name":"DockPile1","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px-2,"y":py-2,"z":pz-8},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"DockPile2","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px+2,"y":py-2,"z":pz-8},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"DockPile3","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px-2,"y":py-2,"z":pz+8},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"DockPile4","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px+2,"y":py-2,"z":pz+8},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"DockLantern","shape":"Ball","size":{"x":1.5,"y":1.5,"z":1.5},"position":{"x":px,"y":py+4,"z":pz+8},"material":"Neon","color":{"r":255,"g":200,"b":100},"anchored":True}},
        {"type":"addLight","params":{"parent":"DockLantern","lightType":"PointLight","brightness":4,"range":20,"color":{"r":255,"g":200,"b":100}}},
    ])

def b_lighthouse(px, py, pz):
    return ("Concrete shaft, beacon room on top, spotlight that reaches. "
            "Like the ones at the cannery — except those smell like fish and this one doesn't.", [
        {"type":"createPart","params":{"name":"LightBase","shape":"Cylinder","size":{"x":10,"y":30,"z":10},"position":{"x":px,"y":py+15,"z":pz},"material":"Concrete","color":{"r":200,"g":200,"b":195},"anchored":True}},
        {"type":"createPart","params":{"name":"LightTop","shape":"Cylinder","size":{"x":12,"y":4,"z":12},"position":{"x":px,"y":py+32,"z":pz},"material":"Metal","color":{"r":100,"g":100,"b":95},"anchored":True}},
        {"type":"createPart","params":{"name":"LightRoom","shape":"Block","size":{"x":8,"y":6,"z":8},"position":{"x":px,"y":py+36,"z":pz},"material":"Glass","color":{"r":255,"g":255,"b":200},"anchored":True,"transparency":0.3}},
        {"type":"createPart","params":{"name":"LightBeacon","shape":"Ball","size":{"x":3,"y":3,"z":3},"position":{"x":px,"y":py+36,"z":pz},"material":"Neon","color":{"r":255,"g":240,"b":100},"anchored":True}},
        {"type":"addLight","params":{"parent":"LightBeacon","lightType":"SpotLight","brightness":10,"range":200,"color":{"r":255,"g":240,"b":100}}},
    ])

def b_default(player_name):
    return (f"Couldn't match that to anything in the yard, {player_name}. "
            "Tower, house, castle, bridge, tree, wall, road, lamp, pyramid, dome, arch, platform, "
            "stairs, garden, dock, lighthouse — pick one and I'll get to work.", [
        {"type":"createPart","params":{"name":"CreativeBlock","shape":"Block","size":{"x":4,"y":4,"z":4},"position":{"x":0,"y":10,"z":0},"material":"Neon","color":{"r":100,"g":255,"b":200},"anchored":True}},
    ])

# ─── KEYWORD MATCHING ───────────────────────────────────────────────────────

KEYWORDS = {
    'tower': b_tower, 'spire': b_tower, 'pillar': b_tower,
    'house': b_house, 'cabin': b_house, 'cottage': b_house, 'home': b_house, 'shack': b_house,
    'castle': b_castle, 'fortress': b_castle, 'fort': b_castle, 'keep': b_castle, 'citadel': b_castle, 'palace': b_castle,
    'tree': b_tree, 'oak': b_tree, 'pine': b_tree, 'forest': b_tree, 'bush': b_tree,
    'bridge': b_bridge, 'crossing': b_bridge,
    'wall': b_wall, 'barricade': b_wall, 'fence': b_wall, 'barrier': b_wall,
    'road': b_road, 'path': b_road, 'street': b_road, 'highway': b_road, 'walkway': b_road,
    'lighthouse': b_lighthouse, 'beacon': b_lighthouse,
    'lamp': b_lamp, 'lantern': b_lamp, 'streetlight': b_lamp, 'lampost': b_lamp,
    'pyramid': b_pyramid, 'triangle': b_pyramid, 'ziggurat': b_pyramid,
    'dome': b_dome, 'observatory': b_dome, 'bubble': b_dome,
    'arch': b_arch, 'gate': b_arch, 'portal': b_arch, 'arc': b_arch,
    'platform': b_platform, 'stage': b_platform, 'deck': b_platform, 'terrace': b_platform,
    'staircase': b_staircase, 'stairs': b_staircase, 'steps': b_staircase, 'ladder': b_staircase,
    'garden': b_garden, 'park': b_garden, 'yard': b_garden, 'flowerbed': b_garden,
    'dock': b_dock, 'pier': b_dock, 'wharf': b_dock, 'jetty': b_dock,
}

def match_keyword(message):
    msg_lower = message.lower()
    for keyword, builder in KEYWORDS.items():
        if keyword in msg_lower:
            return builder
    return None

# ─── JOB PROCESSING (tempo-staged) ──────────────────────────────────────────

def process_job(job, tempo: PipelineTempoController):
    """Process a single job with tempo-staged pipeline.

    Even though the fast path (keyword match) is a single operation,
    we still walk through the tempo stages because the TempoMap is
    the shared clock — it needs to know what "movement" we're in,
    even in preview. When the full brain pipeline arrives, the stages
    will each have real model calls.
    """
    job_id = job.get('id', '')
    player_name = job.get('playerName', 'friend')
    message = job.get('message', '')

    ps = job.get('playerState', {})
    pos = ps.get('position', {})
    px = int(float(pos.get('x', 0)))
    py = int(float(pos.get('y', 0)))
    pz = int(float(pos.get('z', 0)))

    log(f"Processing {job_id[:8]} | {player_name} | \"{message}\" | pos=({px},{py},{pz})")
    log(f"  Tempo: {tempo.current_bpm:.0f} BPM, stage={tempo.current_stage}")

    # Shadow-mode: observe the player action
    now = time.time()
    tempo.shadow_observe_action(now)

    # ── Stage 1: Intent parse (Allegro, ch 10) ────────────────────────
    tempo.transition_to_stage("intent", job_id=job_id)
    # In the fast path, intent IS the keyword match.
    # In the deep path (future), this is where Seed-mini runs.
    builder = match_keyword(message)

    # Brief tick to let the tempo settle into the stage
    tempo.tick()

    # ── Stage 2: Plan (Moderato, ch 11) ───────────────────────────────
    # The plan determines position, size, and construction order.
    # For templates, this is implicit in the builder function.
    tempo.transition_to_stage("plan", job_id=job_id)
    tempo.tick()

    if builder:
        # ── Stage 3: Code gen (Andante, ch 12) ────────────────────────
        tempo.transition_to_stage("code", job_id=job_id)
        # This is where Qwen3-Coder would emit build commands.
        # For templates, the builder function IS the code gen.
        reply, commands = builder(px, py, pz)
        log(f"  Matched: {builder.__name__} → {len(commands)} commands")
    else:
        reply, commands = b_default(player_name)
        log(f"  No match → default")

    tempo.tick()

    # ── Stage 4: Voice wrap (Adagio, ch 13) ───────────────────────────
    # Hermes-405B writes Lucineer's line. For templates, it's pre-written.
    tempo.transition_to_stage("voice", job_id=job_id)
    tempo.tick()

    # Shadow-mode: compute Φ from minimal tracks
    shadow_tracks = {
        "action_cadence": len(getattr(tempo.energy, 'action_history', [])),
        "idle_time": time.time() - (getattr(tempo.energy, 'last_action_time', None) or now),
        "stage": tempo.current_stage,
        "matched": builder is not None,
        "command_count": len(commands),
    }
    phi = tempo.shadow_compute_phi(shadow_tracks)
    log(f"  Shadow Φ={phi:.3f} | shadow BPM={tempo.energy.get_bpm()}")

    # Post result
    try:
        result = api_post(f"/api/job/{job_id}/result", {"reply": reply, "commands": commands})
        log(f"  ✓ Complete ({len(commands)} commands, {tempo.current_bpm:.0f} BPM)")

        # Log full trajectory for this job
        trajectory = {
            "type": "job_complete",
            "job_id": job_id,
            "player": player_name,
            "message": message,
            "position": {"x": px, "y": py, "z": pz},
            "matched": builder.__name__ if builder else "default",
            "command_count": len(commands),
            "stages": tempo.stage_history[-4:],  # last 4 stage transitions
            "final_bpm": round(tempo.current_bpm, 1),
            "shadow": tempo.get_shadow_state(),
            "phi": round(phi, 4),
        }
        log_trajectory(trajectory)

        # Return to idle tempo
        tempo.enter_idle()
        return True
    except Exception as e:
        log(f"  ✗ Failed: {e}", "ERROR")
        tempo.enter_idle()
        return False


# ─── MAIN LOOP ──────────────────────────────────────────────────────────────

# Global tempo controller — the shared clock
TEMPO = PipelineTempoController()


def run_once():
    """Poll once, process any pending jobs."""
    # Tick the tempo clock
    TEMPO.tick()

    # Shadow-mode: observe idle if no jobs
    TEMPO.shadow_observe_idle(time.time())

    data = api_get("/api/jobs/pending")
    jobs = data.get("jobs", [])
    if not jobs:
        return 0

    log(f"Found {len(jobs)} pending job(s)")
    count = 0
    for job in jobs:
        if process_job(job, TEMPO):
            count += 1
    return count


def run_loop(interval=2):
    """Continuous processing loop with tempo clock ticking."""
    log("=== Lucineer Processor — Phase 1 'The Clock' ===")
    log(f"   TempoMap: {TEMPO.tempo_map.bpm:.0f} BPM, Lucineer groove applied")
    log(f"   Shadow subsystems: {'active' if _SHADOW_SUBSYSTEMS else 'fallback stubs'}")
    log(f"   Trajectory file: {TRAJECTORY_FILE}")

    # Set up a beat callback for tempo logging
    def log_downbeat(beat, timestamp):
        if beat % 16 == 0:  # every 4 bars
            log(f"  ♩ beat {beat} | {TEMPO.current_bpm:.0f} BPM | stage={TEMPO.current_stage}")

    TEMPO.beat_clock.on_beat(log_downbeat, period=1)

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            log("Shutdown received.")
            break
        except Exception as e:
            log(f"Error in loop: {e}", "ERROR")
            traceback.print_exc()
        time.sleep(interval)


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "--once"

    if mode == "--loop":
        run_loop()
    elif mode == "--mock":
        mock = {
            "id": f"mock_{int(time.time())}",
            "playerName": "Casey",
            "message": " ".join(sys.argv[2:]) or "build me a castle",
            "playerState": {"position": {"x": 10, "y": 5, "z": -20}},
        }
        log("=== Mock job ===")
        process_job(mock, TEMPO)
        log(f"\nFinal tempo state: {TEMPO.tempo_map}")
        log(f"Stage history: {len(TEMPO.stage_history)} transitions")
        log(f"Shadow state: {TEMPO.get_shadow_state()}")
    elif mode == "--tempo":
        # Tempo-only demo: just show the clock running
        log("=== TempoMap Demo ===")
        log(f"  Start: {TEMPO.tempo_map}")
        for stage in ["intent", "plan", "code", "voice"]:
            TEMPO.transition_to_stage(stage, job_id="demo")
            time.sleep(1.0)
            TEMPO.tick()
            log(f"  {stage}: {TEMPO.tempo_map}")
        TEMPO.enter_idle()
        time.sleep(1.0)
        TEMPO.tick()
        log(f"  idle: {TEMPO.tempo_map}")
        log(f"  Stage history: {len(TEMPO.stage_history)} transitions logged")
    else:
        count = run_once()
        if count == 0:
            log("No pending jobs.")
