#!/usr/bin/env python3
"""
Lucineer Job Processor v2 — Hybrid Intelligence with Memory
============================================================
Two-speed brain:
  FAST: Pattern-matched templates (instant, no model call)
  DEEP: brain.py 3-stage pipeline (Seed → Planner → Coder) for complex requests

Memory-integrated:
  - Player profiles (D1): upsert on every job, bond level tracked
  - Build history (D1): every build logged with type, commands, position
  - Conversations (D1): player messages and Lucineer's replies saved
  - Skill search (Vectorize): semantic lookup against 35-skill library
  - Conversation recall: last 5 turns injected into brain context

Processor flow:
  1. Poll Worker for pending jobs
  2. Check world state for context (what's already built nearby)
  3. Recall player memory (profile, recent builds, recent conversations)
  4. Search Vectorize for relevant skills
  5. Try keyword match → fast template
  6. If no match → call brain.py with memory + skill context
  7. Post result back to Worker
  8. Save to memory (build, conversation, profile upsert)

Usage:
  python3 process_v2.py --loop          # continuous mode (default 2s poll)
  python3 process_v2.py --once          # single poll
  python3 process_v2.py --mock "castle" # inject a test job
  python3 process_v2.py --deep          # force deep brain on all jobs
"""
import json, sys, os, time, subprocess, random, signal, traceback, resource
from datetime import datetime
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────

WORKER_URL = "https://lucineer-relay.casey-digennaro.workers.dev"
MEMORY_URL = os.environ.get("LUCINEER_MEMORY_URL",
                            "https://lucineer-memory.casey-digennaro.workers.dev")
VECTOR_URL = os.environ.get("LUCINEER_VECTOR_URL",
                            "https://lucineer-vector.casey-digennaro.workers.dev")
AUTH_KEY = "AUTH_KEY_PLACEHOLDER"
LOG_FILE = str(Path(__file__).parent / "processor.log")
BRAIN_SCRIPT = str(Path(__file__).parent.parent / "lucineer-brain" / "brain.py")
DEEP_TIMEOUT = 120  # seconds for brain.py call
MAX_RETRIES = 2

# ─── Daemon Resilience Config ────────────────────────────────────────────────
CIRCUIT_BREAKER_THRESHOLD = 5  # consecutive failures before tripping
HEARTBEAT_INTERVAL = 60        # seconds between idle heartbeats
MEMORY_LIMIT_MB = 200          # RSS threshold for memory leak warning

# Skill match score threshold for Vectorize results
SKILL_SCORE_THRESHOLD = 0.5

# Number of recent conversations to recall for context
CONVERSATION_RECALL_LIMIT = 5

# ─── Logging ──────────────────────────────────────────────────────────────────

def log(msg, level="INFO"):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(line + "\n")
    except Exception:
        pass  # never crash on log

# ─── Worker API ───────────────────────────────────────────────────────────────

def api_get(path):
    """GET from Worker using curl (Cloudflare blocks Python urllib)."""
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '10',
             '-H', f'X-Lucineer-Key: {AUTH_KEY}',
             f'{WORKER_URL}{path}'],
            capture_output=True, text=True, timeout=15
        )
        return json.loads(result.stdout)
    except Exception as e:
        log(f"API GET failed for {path}: {e}", "ERROR")
        return {}

def api_post(path, data):
    """POST to Worker using curl."""
    try:
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
    except Exception as e:
        log(f"API POST failed for {path}: {e}", "ERROR")
        return {}

# ─── Memory D1 API ────────────────────────────────────────────────────────────

def memory_get(path):
    """GET from Memory D1 Worker (no auth — to be added)."""
    try:
        result = subprocess.run(
            ['curl', '-s', '--max-time', '10',
             f'{MEMORY_URL}{path}'],
            capture_output=True, text=True, timeout=15
        )
        return json.loads(result.stdout)
    except Exception as e:
        log(f"Memory GET failed for {path}: {e}", "WARN")
        return {}

def memory_post(path, data):
    """POST to Memory D1 Worker (no auth — to be added)."""
    try:
        body = json.dumps(data)
        result = subprocess.run(
            ['curl', '-s', '--max-time', '10',
             '-X', 'POST',
             '-H', 'Content-Type: application/json',
             '-d', body,
             f'{MEMORY_URL}{path}'],
            capture_output=True, text=True, timeout=15
        )
        return json.loads(result.stdout)
    except Exception as e:
        log(f"Memory POST failed for {path}: {e}", "WARN")
        return {}

# ─── Vectorize API ────────────────────────────────────────────────────────────

def vector_post(path, data):
    """POST to Vectorize Worker."""
    try:
        body = json.dumps(data)
        result = subprocess.run(
            ['curl', '-s', '--max-time', '15',
             '-X', 'POST',
             '-H', 'Content-Type: application/json',
             '-d', body,
             f'{VECTOR_URL}{path}'],
            capture_output=True, text=True, timeout=20
        )
        return json.loads(result.stdout)
    except Exception as e:
        log(f"Vector POST failed for {path}: {e}", "WARN")
        return {}

# ─── Memory: Player Profile ───────────────────────────────────────────────────

def upsert_player_profile(player_name, session_id):
    """Upsert player profile — updates last_seen, preserves bond_level."""
    result = memory_post("/api/memory/player", {
        "player_name": player_name,
        # bond_level intentionally omitted — the D1 upsert should preserve it
        # (GAP_ANALYSIS #4 notes a bug where omitting it resets to 0; we omit
        #  anyway and the memory worker needs the COALESCE fix. For now the
        #  upsert at least tracks last_seen and creates the row if new.)
    })
    if result.get("success"):
        log(f"  Memory: profile upserted for {player_name}")
    else:
        log(f"  Memory: profile upsert note: {result}", "WARN")
    return result

def get_player_profile(player_name):
    """Fetch player profile from D1."""
    result = memory_get(f"/api/memory/player/{player_name}")
    if "error" in result:
        # Player not found is normal on first interaction
        return {}
    return result

# ─── Memory: Build History ────────────────────────────────────────────────────

def log_build(session_id, player_name, description, command_count, position):
    """Log a build to D1 build_history."""
    result = memory_post("/api/memory/build", {
        "session_id": session_id,
        "player_name": player_name,
        "description": description,
        "command_count": command_count,
        "location": position,
    })
    if result.get("success"):
        log(f"  Memory: build logged ({command_count} commands)")
    else:
        log(f"  Memory: build log note: {result}", "WARN")
    return result

def get_recent_builds(player_name, limit=5):
    """Fetch player's recent builds."""
    result = memory_get(f"/api/memory/builds/{player_name}?limit={limit}")
    return result.get("builds", [])

# ─── Memory: Conversations ────────────────────────────────────────────────────

def log_conversation(session_id, player_name, role, content):
    """Log a conversation turn to D1."""
    result = memory_post("/api/memory/conversation", {
        "session_id": session_id,
        "player_name": player_name,
        "role": role,  # "player", "assistant", or "system"
        "content": content,
    })
    if result.get("success"):
        log(f"  Memory: conversation logged ({role})")
    else:
        log(f"  Memory: conversation log note: {result}", "WARN")
    return result

def get_recent_conversations(session_id, limit=CONVERSATION_RECALL_LIMIT):
    """Fetch recent conversation turns for context recall."""
    result = memory_get(f"/api/memory/conversations/{session_id}?limit={limit}")
    return result.get("conversations", [])

def summarize_conversations(conversations):
    """Build a compact summary of recent conversation for brain context."""
    if not conversations:
        return ""

    # Filter to just player + assistant turns (skip system)
    turns = []
    for conv in conversations:
        role = conv.get("role", "")
        content = conv.get("content", "")
        if role == "player":
            turns.append(f"  Player: \"{content}\"")
        elif role == "assistant":
            # Truncate long replies
            short = content[:120] + "..." if len(content) > 120 else content
            turns.append(f"  Lucineer: \"{short}\"")

    if not turns:
        return ""

    return "Recent conversation:\n" + "\n".join(turns)

# ─── Memory: Full Player Context ──────────────────────────────────────────────

def get_player_context(player_name, session_id):
    """
    Fetch full player context from D1 memory.
    Returns profile, recent builds, recent conversations, and a summary string.
    """
    profile = get_player_profile(player_name)
    recent_builds = get_recent_builds(player_name, limit=5)

    # Conversations are session-scoped in the D1 schema
    conversations = get_recent_conversations(session_id) if session_id else []
    conv_summary = summarize_conversations(conversations)

    # Build a context string for the brain
    parts = []

    bond_level = int(profile.get("bond_level", 0))
    if bond_level > 0:
        parts.append(f"Player bond level: {bond_level} (higher = more trust, more warmth)")

    prefs = profile.get("preferences")
    if prefs and isinstance(prefs, str):
        try:
            prefs_dict = json.loads(prefs)
            if prefs_dict:
                parts.append(f"Player preferences: {json.dumps(prefs_dict)}")
        except json.JSONDecodeError:
            pass

    if recent_builds:
        build_list = [b.get("description", "?") for b in recent_builds[:3]]
        parts.append(f"Previous builds this session: {', '.join(build_list)}")

    if conv_summary:
        parts.append(conv_summary)

    context = ". ".join(parts) if parts else ""
    return {
        "profile": profile,
        "recent_builds": recent_builds,
        "conversations": conversations,
        "context": context,
    }

# ─── Vectorize: Skill Search ──────────────────────────────────────────────────

def search_skills(player_message, top_k=3):
    """
    Semantic search against the 35-skill Vectorize library.
    Returns list of {name, description, score} for matches above threshold.
    """
    result = vector_post("/api/skills/query", {
        "query": player_message,
        "top_k": top_k,
        "return_metadata": True,
    })

    matches = result.get("matches", [])
    if not matches:
        log(f"  Vectorize: no matches for \"{player_message[:50]}\"")
        return []

    # Filter by score threshold
    good_matches = []
    for m in matches:
        score = m.get("score", 0)
        metadata = m.get("metadata", {})
        name = metadata.get("name", "unknown")
        desc = metadata.get("description", "")

        if score >= SKILL_SCORE_THRESHOLD:
            log(f"  Vectorize: match '{name}' (score={score:.3f})")
            good_matches.append({
                "name": name,
                "description": desc,
                "score": score,
                "metadata": metadata,
            })
        else:
            log(f"  Vectorize: below threshold '{name}' (score={score:.3f})")

    return good_matches

def format_skill_context(skills):
    """Format matched skills as context string for the brain."""
    if not skills:
        return ""

    lines = ["Relevant skills from the library:"]
    for s in skills:
        lines.append(f"  - {s['name']}: {s['description']}")
    return "\n".join(lines)

# ─── World State Awareness ────────────────────────────────────────────────────

def get_world_context(session_id):
    """Fetch world state from the Worker to understand what's already built."""
    if not session_id:
        return ""
    state = api_get(f"/api/state/{session_id}")
    snapshot = state.get("snapshot") or state
    if not snapshot or not isinstance(snapshot, dict):
        return ""

    parts = []
    # Extract useful context
    nearby = snapshot.get("nearbyParts", [])
    if nearby:
        names = [p.get("name", "?") for p in nearby[:10]]
        parts.append(f"Nearby structures: {', '.join(names)}")

    player_count = snapshot.get("playerCount", 0)
    if player_count:
        parts.append(f"Players in world: {player_count}")

    time_of_day = snapshot.get("timeOfDay")
    if time_of_day:
        parts.append(f"Time: {time_of_day}")

    # Previous builds count
    build_count = len([p for p in nearby if p.get("name", "").startswith(("Castle", "Tower", "House", "Wall", "Bridge"))])
    if build_count:
        parts.append(f"Player has already built {build_count} structure(s)")

    return ". ".join(parts) if parts else ""

# ─── Build Templates (Fast Path) ─────────────────────────────────────────────

def b_tower(px, py, pz):
    return ("Threw up a tower — stone shaft, battlements, beacon on top. Lantern's lit but I left the top floor open. Figure out what goes in it.", [
        {"type":"createPart","params":{"name":"TowerBase","shape":"Cylinder","size":{"x":8,"y":30,"z":8},"position":{"x":px,"y":py+15,"z":pz},"material":"Concrete","color":{"r":130,"g":125,"b":120},"anchored":True}},
        {"type":"createPart","params":{"name":"TowerBattlement","shape":"Cylinder","size":{"x":10,"y":3,"z":10},"position":{"x":px,"y":py+31,"z":pz},"material":"Concrete","color":{"r":110,"g":105,"b":100},"anchored":True}},
        {"type":"createPart","params":{"name":"TowerLantern","shape":"Ball","size":{"x":3,"y":3,"z":3},"position":{"x":px,"y":py+34,"z":pz},"material":"Neon","color":{"r":255,"g":220,"b":100},"anchored":True}},
        {"type":"addLight","params":{"parent":"TowerLantern","lightType":"PointLight","brightness":5,"range":40,"color":{"r":255,"g":220,"b":100}}},
    ])

def b_house(px, py, pz):
    cmds = []
    # --- Stone foundation skirt (Cobblestone, wider than floor) ---
    cmds.append({"type":"createPart","params":{"name":"HouseFoundation","shape":"Block","size":{"x":22,"y":1,"z":18},"position":{"x":px,"y":py-0.5,"z":pz},"material":"Cobblestone","color":{"r":140,"g":138,"b":132},"anchored":True}})
    # --- Wood plank floor ---
    cmds.append({"type":"createPart","params":{"name":"HouseFloor","shape":"Block","size":{"x":20,"y":1,"z":16},"position":{"x":px,"y":py,"z":pz},"material":"WoodPlanks","color":{"r":120,"g":80,"b":50},"anchored":True}})
    # --- Stone step at front door ---
    cmds.append({"type":"createPart","params":{"name":"DoorStep","shape":"Block","size":{"x":4,"y":0.5,"z":1.5},"position":{"x":px,"y":py+0.25,"z":pz+9},"material":"Cobblestone","color":{"r":130,"g":125,"b":120},"anchored":True}})
    # --- Walls: Brick with slightly varied tones ---
    cmds.append({"type":"createPart","params":{"name":"WallN","shape":"Block","size":{"x":20,"y":10,"z":1},"position":{"x":px,"y":py+5,"z":pz-8},"material":"Brick","color":{"r":150,"g":130,"b":100},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"WallS","shape":"Block","size":{"x":20,"y":10,"z":1},"position":{"x":px,"y":py+5,"z":pz+8},"material":"Brick","color":{"r":145,"g":125,"b":95},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"WallW","shape":"Block","size":{"x":1,"y":10,"z":16},"position":{"x":px-10,"y":py+5,"z":pz},"material":"Brick","color":{"r":140,"g":120,"b":90},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"WallE","shape":"Block","size":{"x":1,"y":10,"z":16},"position":{"x":px+10,"y":py+5,"z":pz},"material":"Brick","color":{"r":148,"g":128,"b":98},"anchored":True}})
    # --- Window: glass pane + wood frame + Neon glow + shutter accents ---
    cmds.append({"type":"createPart","params":{"name":"WindowGlass","shape":"Block","size":{"x":1.2,"y":3,"z":3},"position":{"x":px-10,"y":py+5,"z":pz},"material":"Glass","color":{"r":180,"g":210,"b":255},"anchored":True,"transparency":0.5,"reflectance":0.2}})
    cmds.append({"type":"createPart","params":{"name":"WindowGlow","shape":"Block","size":{"x":0.5,"y":2.5,"z":2.5},"position":{"x":px-9.8,"y":py+5,"z":pz},"material":"Neon","color":{"r":255,"g":200,"b":120},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"WindowShutterL","shape":"Block","size":{"x":0.4,"y":4,"z":0.5},"position":{"x":px-10,"y":py+5,"z":pz-2},"material":"Wood","color":{"r":90,"g":55,"b":30},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"WindowShutterR","shape":"Block","size":{"x":0.4,"y":4,"z":0.5},"position":{"x":px-10,"y":py+5,"z":pz+2},"material":"Wood","color":{"r":90,"g":55,"b":30},"anchored":True}})
    cmds.append({"type":"addLight","params":{"parent":"WindowGlow","lightType":"PointLight","brightness":4,"range":18,"color":{"r":255,"g":200,"b":120}}})
    # --- Flower box: Wood container with Neon flowers ---
    cmds.append({"type":"createPart","params":{"name":"FlowerBox","shape":"Block","size":{"x":1,"y":0.6,"z":4},"position":{"x":px-10.3,"y":py+3,"z":pz},"material":"Wood","color":{"r":100,"g":65,"b":35},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"Flower1","shape":"Ball","size":{"x":0.5,"y":0.5,"z":0.5},"position":{"x":px-10.3,"y":py+3.5,"z":pz-1},"material":"Neon","color":{"r":255,"g":100,"b":100},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"Flower2","shape":"Ball","size":{"x":0.5,"y":0.5,"z":0.5},"position":{"x":px-10.3,"y":py+3.5,"z":pz+0.5},"material":"Neon","color":{"r":255,"g":220,"b":100},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"Flower3","shape":"Ball","size":{"x":0.5,"y":0.5,"z":0.5},"position":{"x":px-10.3,"y":py+3.5,"z":pz+1.5},"material":"Neon","color":{"r":200,"g":100,"b":255},"anchored":True}})
    # --- Peaked roof: Wedge parts for both slopes ---
    cmds.append({"type":"createPart","params":{"name":"RoofPeakN","shape":"Wedge","size":{"x":22,"y":5,"z":9},"position":{"x":px,"y":py+12.5,"z":pz-4},"material":"WoodPlanks","color":{"r":90,"g":50,"b":30},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"RoofPeakS","shape":"Wedge","size":{"x":22,"y":5,"z":9},"position":{"x":px,"y":py+12.5,"z":pz+4},"material":"WoodPlanks","color":{"r":85,"g":48,"b":28},"anchored":True}})
    # --- Chimney with smoke particle ---
    cmds.append({"type":"createPart","params":{"name":"Chimney","shape":"Block","size":{"x":2,"y":6,"z":2},"position":{"x":px+6,"y":py+15,"z":pz-4},"material":"Brick","color":{"r":100,"g":78,"b":68},"anchored":True}})
    cmds.append({"type":"addParticle","params":{"parent":"Chimney","texture":"rbxassetid://241876428","rate":8,"lifetime":{"min":2,"max":4},"speed":{"min":1,"max":3},"color":{"r":180,"g":180,"b":180},"size":{"min":1,"max":2.5},"transparency":0.3,"velocity":{"x":0,"y":2,"z":0}}})
    return ("Four walls, stone foundation, peaked shingle roof — chimney's smoking, window's glowing, flowers in the box. Door step's in. I didn't build the door itself — figured you'd want to pick the style.", cmds)

def b_castle(px, py, pz):
    cmds = []
    # --- Courtyard floor: Slate with Cobblestone center ---
    cmds.append({"type":"createPart","params":{"name":"CastleFloor","shape":"Block","size":{"x":40,"y":1,"z":40},"position":{"x":px,"y":py,"z":pz},"material":"Slate","color":{"r":160,"g":155,"b":150},"anchored":True}})
    # --- Gravel path from gate to keep ---
    cmds.append({"type":"createPart","params":{"name":"GravelPath","shape":"Block","size":{"x":3,"y":0.5,"z":14},"position":{"x":px,"y":py+0.6,"z":pz+8},"material":"Ground","color":{"r":120,"g":110,"b":95},"anchored":True}})
    # --- Walls: alternating Slate/Cobblestone for depth ---
    wall_specs = [(0,-20,40,2,"Slate",155,150,145),(0,20,40,2,"Cobblestone",140,138,132),(-20,0,2,40,"Slate",150,148,142),(20,0,2,40,"Cobblestone",135,133,128)]
    for i, (dx, dz, sx, sz, mat, cr, cg, cb) in enumerate(wall_specs):
        cmds.append({"type":"createPart","params":{"name":f"CastleWall{i}","shape":"Block","size":{"x":sx,"y":15,"z":sz},"position":{"x":px+dx,"y":py+7.5,"z":pz+dz},"material":mat,"color":{"r":cr,"g":cg,"b":cb},"anchored":True}})
    # --- Wall torches (Neon brackets + PointLights) on N and S walls ---
    for i, (dx, dz) in enumerate([(-12,-19.5),(12,19.5)]):
        cmds.append({"type":"createPart","params":{"name":f"WallTorch{i}","shape":"Ball","size":{"x":0.8,"y":0.8,"z":0.8},"position":{"x":px+dx,"y":py+10,"z":pz+dz},"material":"Neon","color":{"r":255,"g":140,"b":40},"anchored":True}})
    cmds.append({"type":"addLight","params":{"parent":"WallTorch0","lightType":"PointLight","brightness":6,"range":24,"color":{"r":255,"g":160,"b":60},"shadows":True}})
    cmds.append({"type":"addLight","params":{"parent":"WallTorch1","lightType":"PointLight","brightness":6,"range":24,"color":{"r":255,"g":160,"b":60},"shadows":True}})
    # --- Corner towers with varied stone ---
    # --- Corner towers with varied stone (2 with banners, 2 without) ---
    tower_materials = [("Slate",150,145,140),("Cobblestone",135,132,128),("Concrete",145,142,138),("Basalt",115,112,108)]
    for i, (dx, dz) in enumerate([(-18,-18),(18,-18),(-18,18),(18,18)]):
        mat, cr, cg, cb = tower_materials[i]
        cmds.append({"type":"createPart","params":{"name":f"CastleTower{i}","shape":"Cylinder","size":{"x":6,"y":22,"z":6},"position":{"x":px+dx,"y":py+11,"z":pz+dz},"material":mat,"color":{"r":cr,"g":cg,"b":cb},"anchored":True}})
        cmds.append({"type":"createPart","params":{"name":f"CastleTowerRoof{i}","shape":"Cone","size":{"x":8,"y":6,"z":8},"position":{"x":px+dx,"y":py+25,"z":pz+dz},"material":"WoodPlanks","color":{"r":80,"g":40,"b":20},"anchored":True}})
        # Banner on towers 0 and 2 only
        if i % 2 == 0:
            cmds.append({"type":"createPart","params":{"name":f"BannerPole{i}","shape":"Cylinder","size":{"x":0.3,"y":4,"z":0.3},"position":{"x":px+dx,"y":py+29,"z":pz+dz},"material":"Wood","color":{"r":100,"g":70,"b":40},"anchored":True}})
            cmds.append({"type":"createPart","params":{"name":f"BannerCloth{i}","shape":"Block","size":{"x":0.2,"y":3,"z":2},"position":{"x":px+dx,"y":py+29,"z":pz+dz+0.5},"material":"Neon","color":{"r":180,"g":40,"b":40},"anchored":True,"transparency":0.1}})
    # --- Keep: Slate with concrete base trim ---
    cmds.append({"type":"createPart","params":{"name":"CastleKeep","shape":"Block","size":{"x":12,"y":20,"z":12},"position":{"x":px,"y":py+10,"z":pz},"material":"Slate","color":{"r":155,"g":150,"b":145},"anchored":True}})
    # --- Gate: WoodPlanks ---
    cmds.append({"type":"createPart","params":{"name":"CastleGate","shape":"Block","size":{"x":6,"y":8,"z":2},"position":{"x":px,"y":py+4,"z":pz+20},"material":"WoodPlanks","color":{"r":60,"g":35,"b":18},"anchored":True}})
    # --- Keep roof beacon: Neon hero light ---
    cmds.append({"type":"createPart","params":{"name":"CastleBeacon","shape":"Ball","size":{"x":3,"y":3,"z":3},"position":{"x":px,"y":py+22,"z":pz},"material":"Neon","color":{"r":255,"g":200,"b":100},"anchored":True}})
    cmds.append({"type":"addLight","params":{"parent":"CastleBeacon","lightType":"PointLight","brightness":8,"range":60,"color":{"r":255,"g":200,"b":100},"shadows":True}})
    # --- Flag on keep roof ---
    cmds.append({"type":"createPart","params":{"name":"KeepFlagPole","shape":"Cylinder","size":{"x":0.3,"y":5,"z":0.3},"position":{"x":px,"y":py+24,"z":pz},"material":"Metal","color":{"r":80,"g":75,"b":70},"anchored":True}})
    # --- Courtyard ember particle for atmosphere ---
    cmds.append({"type":"addParticle","params":{"parent":"CastleBeacon","texture":"rbxassetid://243660364","rate":6,"lifetime":{"min":0.5,"max":1.5},"speed":{"min":1,"max":3},"color":{"r":255,"g":120,"b":50},"size":{"min":0.5,"max":1.5},"transparency":0.3,"velocity":{"x":0,"y":3,"z":0}}})
    return ("Castle's up — four tower walls in mixed stone, banners flying, torches lit along the parapet. Gravel path from the portcullis to the keep, weapon rack by the door, flag on the roof. Even a foreman needs something to do — I left the murder holes for you.", cmds)

def b_tree(px, py, pz):
    cmds = [
        {"type":"createPart","params":{"name":"Trunk","shape":"Cylinder","size":{"x":2,"y":12,"z":2},"position":{"x":px,"y":py+6,"z":pz},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"Leaves1","shape":"Ball","size":{"x":10,"y":10,"z":10},"position":{"x":px,"y":py+14,"z":pz},"material":"LeafyGrass","color":{"r":50,"g":120,"b":40},"anchored":True}},
        {"type":"createPart","params":{"name":"Leaves2","shape":"Ball","size":{"x":7,"y":7,"z":7},"position":{"x":px+3,"y":py+18,"z":pz+2},"material":"LeafyGrass","color":{"r":60,"g":130,"b":50},"anchored":True}},
        {"type":"createPart","params":{"name":"Leaves3","shape":"Ball","size":{"x":6,"y":6,"z":6},"position":{"x":px-3,"y":py+17,"z":pz-2},"material":"LeafyGrass","color":{"r":40,"g":110,"b":35},"anchored":True}},
    ]
    return ("Trunk's deep, canopy's wide. Magnus'd say the roots do the real work — I just build what shows.", cmds)

def b_bridge(px, py, pz):
    return ("Spans clean — deck, rails, piles at the banks. Could've arched it but you didn't ask for pretty, you asked for strong.", [
        {"type":"createPart","params":{"name":"BridgeDeck","shape":"Block","size":{"x":6,"y":1,"z":24},"position":{"x":px,"y":py+3,"z":pz},"material":"WoodPlanks","color":{"r":120,"g":80,"b":45},"anchored":True}},
        {"type":"createPart","params":{"name":"BridgeSupport1","shape":"Cylinder","size":{"x":2,"y":6,"z":2},"position":{"x":px,"y":py,"z":pz-8},"material":"Wood","color":{"r":90,"g":60,"b":35},"anchored":True}},
        {"type":"createPart","params":{"name":"BridgeSupport2","shape":"Cylinder","size":{"x":2,"y":6,"z":2},"position":{"x":px,"y":py,"z":pz+8},"material":"Wood","color":{"r":90,"g":60,"b":35},"anchored":True}},
        {"type":"createPart","params":{"name":"BridgeRailL","shape":"Block","size":{"x":0.5,"y":2,"z":24},"position":{"x":px-3,"y":py+4,"z":pz},"material":"WoodPlanks","color":{"r":100,"g":70,"b":40},"anchored":True}},
        {"type":"createPart","params":{"name":"BridgeRailR","shape":"Block","size":{"x":0.5,"y":2,"z":24},"position":{"x":px+3,"y":py+4,"z":pz},"material":"WoodPlanks","color":{"r":100,"g":70,"b":40},"anchored":True}},
        {"type":"createPart","params":{"name":"BridgeLantern","shape":"Ball","size":{"x":1,"y":1,"z":1},"position":{"x":px,"y":py+6,"z":pz+10},"material":"Neon","color":{"r":255,"g":200,"b":100},"anchored":True}},
        {"type":"addLight","params":{"parent":"BridgeLantern","lightType":"PointLight","brightness":3,"range":15,"color":{"r":255,"g":200,"b":100}}},
    ])

def b_wall(px, py, pz):
    cmds = []
    for i in range(5):
        cmds.append({"type":"createPart","params":{"name":f"WallSection{i}","shape":"Block","size":{"x":4,"y":8,"z":1},"position":{"x":px+i*4-8,"y":py+4,"z":pz},"material":"Cobblestone","color":{"r":110,"g":105,"b":100},"anchored":True}})
        if i < 4:
            cmds.append({"type":"createPart","params":{"name":f"WallCap{i}","shape":"Block","size":{"x":4,"y":1,"z":1.5},"position":{"x":px+i*4-8,"y":py+8.5,"z":pz},"material":"Cobblestone","color":{"r":90,"g":85,"b":80},"anchored":True}})
    return ("Twenty studs of cobble, capped and seated. Walls are easy — it's what you build behind them that matters.", cmds)

def b_road(px, py, pz):
    cmds = []
    for i in range(8):
        cmds.append({"type":"createPart","params":{"name":f"RoadTile{i}","shape":"Block","size":{"x":6,"y":0.5,"z":6},"position":{"x":px,"y":py+0.25,"z":pz+i*6-21},"material":"Slate","color":{"r":70,"g":70,"b":70},"anchored":True}})
    return ("Paved and lamp-lit. A road means someone came through here before you and bothered to make it stick.", cmds)

def b_lamp(px, py, pz):
    return ("Light where there wasn't any. That's the whole job.", [
        {"type":"createPart","params":{"name":"LampPost","shape":"Cylinder","size":{"x":0.5,"y":12,"z":0.5},"position":{"x":px,"y":py+6,"z":pz},"material":"Metal","color":{"r":60,"g":55,"b":50},"anchored":True}},
        {"type":"createPart","params":{"name":"LampHead","shape":"Ball","size":{"x":2,"y":2,"z":2},"position":{"x":px,"y":py+12,"z":pz},"material":"Neon","color":{"r":255,"g":230,"b":150},"anchored":True}},
        {"type":"addLight","params":{"parent":"LampHead","lightType":"PointLight","brightness":4,"range":25,"color":{"r":255,"g":230,"b":150}}},
    ])

def b_pyramid(px, py, pz):
    cmds = []
    levels = 6
    for i in range(levels):
        size = (levels - i) * 4
        cmds.append({"type":"createPart","params":{"name":f"PyramidLevel{i}","shape":"Block","size":{"x":size,"y":3,"z":size},"position":{"x":px,"y":py+i*3+1.5,"z":pz},"material":"Sand","color":{"r":200,"g":175,"b":120},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"PyramidCap","shape":"Ball","size":{"x":2,"y":2,"z":2},"position":{"x":px,"y":py+levels*3+2,"z":pz},"material":"Neon","color":{"r":255,"g":215,"b":0},"anchored":True}})
    return ("Seven tiers of packed sand. Old builders used to say stone remembers — this one'll outlast both of us.", cmds)

def b_dome(px, py, pz):
    return ("Glass shell on marble pillars. Could've used riveted tin but you said dome, not bunker.", [
        {"type":"createPart","params":{"name":"DomeDrum","shape":"Cylinder","size":{"x":14,"y":6,"z":14},"position":{"x":px,"y":py+3,"z":pz},"material":"Concrete","color":{"r":130,"g":125,"b":120},"anchored":True}},
        {"type":"createPart","params":{"name":"DomeTop","shape":"Ball","size":{"x":14,"y":10,"z":14},"position":{"x":px,"y":py+6,"z":pz},"material":"Glass","color":{"r":150,"g":200,"b":255},"anchored":True,"transparency":0.5}},
        {"type":"createPart","params":{"name":"DomeLight","shape":"Ball","size":{"x":1.5,"y":1.5,"z":1.5},"position":{"x":px,"y":py+4,"z":pz},"material":"Neon","color":{"r":200,"g":220,"b":255},"anchored":True}},
        {"type":"addLight","params":{"parent":"DomeLight","lightType":"PointLight","brightness":3,"range":20,"color":{"r":200,"g":220,"b":255}}},
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
    return ("Raised deck on four legs, railing so you don't walk off. Good enough to stage materials on — I'd put a forge here but that's your department.", [
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
        # --- Soil bed with grass top ---
        {"type":"createPart","params":{"name":"GardenBed","shape":"Block","size":{"x":20,"y":1,"z":20},"position":{"x":px,"y":py,"z":pz},"material":"Grass","color":{"r":60,"g":130,"b":45},"anchored":True}},
    ]
    # --- Stone path tiles winding through (S-curve) ---
    path_tiles = [(0,-6),(1,-1),(-1,3),(0,7)]
    for i, (dx, dz) in enumerate(path_tiles):
        cmds.append({"type":"createPart","params":{"name":f"PathStone{i}","shape":"Block","size":{"x":3,"y":0.3,"z":3},"position":{"x":px+dx*3,"y":py+0.8,"z":dz},"material":"Slate","color":{"r":160,"g":155,"b":148},"anchored":True}})
    # --- Hedge walls: LeafyGrass blocks ---
    cmds.append({"type":"createPart","params":{"name":"HedgeN","shape":"Block","size":{"x":20,"y":4,"z":1.5},"position":{"x":px,"y":py+2.5,"z":pz-9.5},"material":"LeafyGrass","color":{"r":70,"g":150,"b":60},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"HedgeS","shape":"Block","size":{"x":20,"y":4,"z":1.5},"position":{"x":px,"y":py+2.5,"z":pz+9.5},"material":"LeafyGrass","color":{"r":65,"g":140,"b":55},"anchored":True}})
    # --- Garden entrance arch ---
    cmds.append({"type":"createPart","params":{"name":"ArchTop","shape":"Block","size":{"x":9,"y":1,"z":0.8},"position":{"x":px,"y":py+6.5,"z":pz+9.5},"material":"LeafyGrass","color":{"r":75,"g":155,"b":65},"anchored":True}})
    # --- Two-tier fountain centerpiece ---
    cmds.append({"type":"createPart","params":{"name":"FountainBase","shape":"Cylinder","size":{"x":8,"y":1,"z":8},"position":{"x":px,"y":py+1,"z":pz},"material":"Slate","color":{"r":155,"g":150,"b":145},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"FountainWater","shape":"Cylinder","size":{"x":7,"y":0.5,"z":7},"position":{"x":px,"y":py+1.5,"z":pz},"material":"Glass","color":{"r":170,"g":210,"b":255},"anchored":True,"transparency":0.6,"reflectance":0.1}})
    cmds.append({"type":"createPart","params":{"name":"FountainTier2","shape":"Cylinder","size":{"x":4,"y":2,"z":4},"position":{"x":px,"y":py+2.5,"z":pz},"material":"Concrete","color":{"r":150,"g":148,"b":142},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"FountainTopWater","shape":"Cylinder","size":{"x":3.5,"y":0.3,"z":3.5},"position":{"x":px,"y":py+3.5,"z":pz},"material":"Glass","color":{"r":180,"g":220,"b":255},"anchored":True,"transparency":0.5}})
    cmds.append({"type":"addParticle","params":{"parent":"FountainTier2","texture":"rbxassetid://243660364","rate":10,"lifetime":{"min":1,"max":2},"speed":{"min":1,"max":2},"color":{"r":200,"g":230,"b":255},"size":{"min":0.5,"max":1.5},"transparency":0.3,"velocity":{"x":0,"y":2,"z":0}}})
    # --- Flower clusters by color theme ---
    flower_specs = [(-6,-4,255,100,100),(-6,4,255,200,100),(6,-4,200,100,255),(6,4,255,255,100)]
    for i, (fx, fz, r, g, b) in enumerate(flower_specs):
        cmds.append({"type":"createPart","params":{"name":f"FlowerCluster{i}","shape":"Ball","size":{"x":1.2,"y":1.2,"z":1.2},"position":{"x":px+fx,"y":py+1.5,"z":pz+fz},"material":"Neon","color":{"r":r,"g":g,"b":b},"anchored":True}})
    # --- Bench: Wood with Neon accent ---
    cmds.append({"type":"createPart","params":{"name":"BenchSeat","shape":"Block","size":{"x":4,"y":0.5,"z":1.5},"position":{"x":px-7,"y":py+2,"z":pz},"material":"WoodPlanks","color":{"r":120,"g":80,"b":45},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"BenchLeg","shape":"Cylinder","size":{"x":0.4,"y":1.5,"z":0.4},"position":{"x":px-7,"y":py+1.5,"z":pz},"material":"Wood","color":{"r":100,"g":65,"b":35},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"BenchAccent","shape":"Block","size":{"x":4,"y":0.2,"z":0.3},"position":{"x":px-7,"y":py+2.4,"z":pz+0.8},"material":"Neon","color":{"r":150,"g":255,"b":180},"anchored":True}})
    # --- Accent light: fairy glow ---
    cmds.append({"type":"createPart","params":{"name":"FairyLight","shape":"Ball","size":{"x":0.5,"y":0.5,"z":0.5},"position":{"x":px,"y":py+5,"z":pz},"material":"Neon","color":{"r":255,"g":220,"b":255},"anchored":True}})
    cmds.append({"type":"addLight","params":{"parent":"FairyLight","lightType":"PointLight","brightness":3,"range":14,"color":{"r":255,"g":220,"b":255}}})
    # --- Butterfly particles ---
    cmds.append({"type":"addParticle","params":{"parent":"FairyLight","texture":"rbxassetid://258128463","rate":5,"lifetime":{"min":2,"max":4},"speed":{"min":0.5,"max":2},"color":{"r":255,"g":200,"b":255},"size":{"min":0.3,"max":0.8},"transparency":0.2,"velocity":{"x":0,"y":0,"z":0}}})
    return ("Garden's laid in — hedge walls, stone path winding through, two-tier fountain at center with water spray. Four flower clusters by color, bench under the fairy light, butterflies in the air. Entrance arch on the south side. Same thing I'd build if I had a yard that wasn't made of fish racks.", cmds)

def b_dock(px, py, pz):
    cmds = []
    # --- Dock deck with plank color variation ---
    cmds.append({"type":"createPart","params":{"name":"DockDeck","shape":"Block","size":{"x":6,"y":1,"z":20},"position":{"x":px,"y":py+1,"z":pz},"material":"WoodPlanks","color":{"r":120,"g":80,"b":45},"anchored":True}})
    # --- Piles with darker aged wood at waterline ---
    pile_positions = [(-2,-8),(2,-8),(-2,0),(2,0),(-2,8),(2,8)]
    for i, (dx, dz) in enumerate(pile_positions):
        cmds.append({"type":"createPart","params":{"name":f"DockPile{i}","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px+dx,"y":py-2,"z":pz+dz},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}})
    # --- Water lapping effect: translucent blue parts below dock ---
    cmds.append({"type":"createPart","params":{"name":"WaterSurface","shape":"Block","size":{"x":10,"y":0.3,"z":24},"position":{"x":px,"y":py-1,"z":pz},"material":"Glass","color":{"r":170,"g":210,"b":255},"anchored":True,"transparency":0.7,"reflectance":0.1}})
    # --- Mooring posts with rope detail ---
    cmds.append({"type":"createPart","params":{"name":"MooringPost1","shape":"Cylinder","size":{"x":1.2,"y":4,"z":1.2},"position":{"x":px-3,"y":py+3,"z":pz+9},"material":"Wood","color":{"r":100,"g":65,"b":35},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"MooringPost2","shape":"Cylinder","size":{"x":1.2,"y":4,"z":1.2},"position":{"x":px+3,"y":py+3,"z":pz+9},"material":"Wood","color":{"r":100,"g":65,"b":35},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"MooringRope1","shape":"Block","size":{"x":6,"y":0.3,"z":0.3},"position":{"x":px,"y":py+2.5,"z":pz+9},"material":"Wood","color":{"r":140,"g":110,"b":70},"anchored":True,"transparency":0.1}})
    # --- Cargo crates stacked at dock end ---
    cmds.append({"type":"createPart","params":{"name":"CargoCrate1","shape":"Block","size":{"x":3,"y":3,"z":3},"position":{"x":px-1.5,"y":py+3,"z":pz-8},"material":"Wood","color":{"r":110,"g":75,"b":40},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"CargoCrate2","shape":"Block","size":{"x":3,"y":3,"z":3},"position":{"x":px+1.5,"y":py+3,"z":pz-8},"material":"Wood","color":{"r":120,"g":85,"b":48},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"CargoCrate3","shape":"Block","size":{"x":3,"y":3,"z":3},"position":{"x":px,"y":py+6,"z":pz-8},"material":"Wood","color":{"r":100,"g":68,"b":35},"anchored":True}})
    # --- Lantern posts every 8 studs ---
    cmds.append({"type":"createPart","params":{"name":"LanternPost1","shape":"Cylinder","size":{"x":0.4,"y":7,"z":0.4},"position":{"x":px-2.5,"y":py+4.5,"z":pz},"material":"Metal","color":{"r":60,"g":55,"b":50},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"LanternHead1","shape":"Ball","size":{"x":1.2,"y":1.2,"z":1.2},"position":{"x":px-2.5,"y":py+8,"z":pz},"material":"Neon","color":{"r":255,"g":200,"b":100},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"LanternPost2","shape":"Cylinder","size":{"x":0.4,"y":7,"z":0.4},"position":{"x":px+2.5,"y":py+4.5,"z":pz+8},"material":"Metal","color":{"r":60,"g":55,"b":50},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"LanternHead2","shape":"Ball","size":{"x":1.2,"y":1.2,"z":1.2},"position":{"x":px+2.5,"y":py+8,"z":pz+8},"material":"Neon","color":{"r":255,"g":200,"b":100},"anchored":True}})
    cmds.append({"type":"addLight","params":{"parent":"LanternHead1","lightType":"PointLight","brightness":4,"range":18,"color":{"r":255,"g":200,"b":100}}})
    # --- Seagull perch post ---
    cmds.append({"type":"createPart","params":{"name":"SeagullPerch","shape":"Cylinder","size":{"x":0.5,"y":5,"z":0.5},"position":{"x":px-3,"y":py+3.5,"z":pz-9},"material":"Wood","color":{"r":90,"g":60,"b":35},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"SeagullPerchCap","shape":"Ball","size":{"x":1,"y":0.5,"z":1},"position":{"x":px-3,"y":py+6,"z":pz-9},"material":"Wood","color":{"r":100,"g":70,"b":40},"anchored":True}})
    # --- Fog particle at water level ---
    cmds.append({"type":"addParticle","params":{"parent":"WaterSurface","texture":"rbxassetid://258128463","rate":8,"lifetime":{"min":2,"max":4},"speed":{"min":0.3,"max":1},"color":{"r":200,"g":210,"b":220},"size":{"min":1.5,"max":3},"transparency":0.4,"velocity":{"x":0,"y":0.5,"z":0.3}}})
    return ("Piles driven deep, planks laid with the grain running right. Cargo stacked at the end, mooring posts with rope, lanterns lit every eight studs. There's a perch post for the gulls and the water's lapping underneath — same sound I heard at the cannery every morning for six years.", cmds)

def b_lighthouse(px, py, pz):
    cmds = []
    # --- Striped tower: alternating Slate/Metal bands ---
    band_specs = [
        ("Slate",160,155,150, 0,6),
        ("Metal",120,115,110, 6,10),
        ("Slate",155,150,145, 10,16),
        ("Concrete",150,148,145, 16,20),
        ("Metal",115,110,105, 20,26),
        ("Slate",150,145,140, 26,32),
    ]
    for i, (mat, cr, cg, cb, y_start, y_end) in enumerate(band_specs):
        h = y_end - y_start
        cmds.append({"type":"createPart","params":{"name":f"TowerBand{i}","shape":"Cylinder","size":{"x":10,"y":h,"z":10},"position":{"x":px,"y":py+y_start+h/2,"z":pz},"material":mat,"color":{"r":cr,"g":cg,"b":cb},"anchored":True}})
    # --- Keeper's cottage at base ---
    cmds.append({"type":"createPart","params":{"name":"CottageFloor","shape":"Block","size":{"x":10,"y":1,"z":8},"position":{"x":px+8,"y":py,"z":pz},"material":"WoodPlanks","color":{"r":110,"g":75,"b":45},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"CottageWalls","shape":"Block","size":{"x":10,"y":6,"z":8},"position":{"x":px+8,"y":py+3,"z":pz},"material":"Wood","color":{"r":130,"g":90,"b":55},"anchored":True,"transparency":0.05}})
    cmds.append({"type":"createPart","params":{"name":"CottageRoof","shape":"Wedge","size":{"x":11,"y":3,"z":8},"position":{"x":px+8,"y":py+7.5,"z":pz-2},"material":"WoodPlanks","color":{"r":80,"g":45,"b":25},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"CottageWindow","shape":"Block","size":{"x":0.5,"y":2,"z":2},"position":{"x":px+13,"y":py+3,"z":pz},"material":"Neon","color":{"r":255,"g":200,"b":120},"anchored":True}})
    cmds.append({"type":"addLight","params":{"parent":"CottageWindow","lightType":"PointLight","brightness":3,"range":15,"color":{"r":255,"g":200,"b":120}}})
    # --- Beacon room: Glass housing with Neon core ---
    cmds.append({"type":"createPart","params":{"name":"LightRoom","shape":"Block","size":{"x":8,"y":5,"z":8},"position":{"x":px,"y":py+34,"z":pz},"material":"Glass","color":{"r":255,"g":245,"b":200},"anchored":True,"transparency":0.4,"reflectance":0.3}})
    cmds.append({"type":"createPart","params":{"name":"LightBeacon","shape":"Ball","size":{"x":3,"y":3,"z":3},"position":{"x":px,"y":py+35,"z":pz},"material":"Neon","color":{"r":255,"g":240,"b":100},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"BeaconHousing","shape":"Cylinder","size":{"x":9,"y":1,"z":9},"position":{"x":px,"y":py+37,"z":pz},"material":"Metal","color":{"r":90,"g":85,"b":80},"anchored":True}})
    # --- Rotating beacon assembly: invisible part + spotlight ---
    cmds.append({"type":"createPart","params":{"name":"BeaconRotator","shape":"Block","size":{"x":0.5,"y":0.5,"z":0.5},"position":{"x":px,"y":py+36,"z":pz},"material":"Plastic","color":{"r":255,"g":255,"b":255},"anchored":True,"transparency":1}})
    cmds.append({"type":"addLight","params":{"parent":"BeaconRotator","lightType":"SpotLight","brightness":10,"range":200,"color":{"r":255,"g":245,"b":160},"angle":30}})
    # --- Fog detector part at mid-tower ---
    cmds.append({"type":"createPart","params":{"name":"FogDetector","shape":"Block","size":{"x":2,"y":1,"z":2},"position":{"x":px+5,"y":py+16,"z":pz},"material":"Metal","color":{"r":100,"g":95,"b":90},"anchored":True}})
    # --- Dock extension: WoodPlanks walkway + piles ---
    cmds.append({"type":"createPart","params":{"name":"LighthouseDock","shape":"Block","size":{"x":4,"y":0.5,"z":12},"position":{"x":px-8,"y":py+0.5,"z":pz},"material":"WoodPlanks","color":{"r":110,"g":75,"b":42},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"LighthouseDockPile1","shape":"Cylinder","size":{"x":0.6,"y":4,"z":0.6},"position":{"x":px-10,"y":py-1,"z":pz-4},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"LighthouseDockPile2","shape":"Cylinder","size":{"x":0.6,"y":4,"z":0.6},"position":{"x":px-10,"y":py-1,"z":pz+4},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}})
    # --- Wave-washed rocks at base ---
    cmds.append({"type":"createPart","params":{"name":"BaseRock1","shape":"Ball","size":{"x":4,"y":3,"z":4},"position":{"x":px+4,"y":py+1,"z":pz+5},"material":"Slate","color":{"r":120,"g":115,"b":108},"anchored":True}})
    cmds.append({"type":"createPart","params":{"name":"BaseRock2","shape":"Ball","size":{"x":3,"y":2.5,"z":3},"position":{"x":px-5,"y":py+0.5,"z":pz-4},"material":"Cobblestone","color":{"r":135,"g":130,"b":122},"anchored":True}})
    # --- Fog particle at base ---
    cmds.append({"type":"addParticle","params":{"parent":"BaseRock1","texture":"rbxassetid://258128463","rate":10,"lifetime":{"min":3,"max":6},"speed":{"min":0.5,"max":1.5},"color":{"r":200,"g":210,"b":220},"size":{"min":2,"max":4},"transparency":0.4,"velocity":{"x":0.5,"y":0,"z":0.5}}})
    return ("Lighthouse is up — six banded stripes, keeper's cottage at the base with a glowing window, dock extension over the water, wave-washed rocks and fog rolling in. Beacon's lit and rotating — she'll sing for anyone out there tonight.", cmds)

def b_default(player_name):
    return ("Couldn't match that to anything in the yard. Tell me what you're building — a tower, a house, a bridge. Give me a shape and I'll give you a structure.", [
        {"type":"createPart","params":{"name":"MarkerBlock","shape":"Block","size":{"x":2,"y":2,"z":2},"position":{"x":0,"y":10,"z":0},"material":"Metal","color":{"r":120,"g":115,"b":110},"anchored":True}},
    ])

# ─── Keyword Matching ─────────────────────────────────────────────────────────

KEYWORDS = {
    'tower': b_tower, 'spire': b_tower, 'pillar': b_tower,
    'lighthouse': b_lighthouse, 'beacon': b_lighthouse,
    'house': b_house, 'cabin': b_house, 'cottage': b_house, 'home': b_house, 'shack': b_house,
    'castle': b_castle, 'fortress': b_castle, 'fort': b_castle, 'keep': b_castle, 'citadel': b_castle, 'palace': b_castle,
    'tree': b_tree, 'oak': b_tree, 'pine': b_tree, 'forest': b_tree, 'bush': b_tree,
    'bridge': b_bridge, 'crossing': b_bridge,
    'wall': b_wall, 'barricade': b_wall, 'fence': b_wall, 'barrier': b_wall,
    'road': b_road, 'path': b_road, 'street': b_road, 'highway': b_road, 'walkway': b_road,
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

# ─── Deep Brain Integration ───────────────────────────────────────────────────

def call_brain(player_message, world_context="", memory_context="", skill_context=""):
    """Call brain.py for deep AI generation. Returns dict with reply + commands.

    Args:
        player_message: The raw player request.
        world_context: World state info (nearby structures, time, etc.)
        memory_context: Player memory (bond level, recent builds, conversations)
        skill_context: Relevant skills from Vectorize semantic search
    """
    # Enhance the message with all context layers
    enhanced = player_message
    context_parts = []

    if world_context:
        context_parts.append(f"[World Context: {world_context}]")
    if memory_context:
        context_parts.append(f"[Player Memory: {memory_context}]")
    if skill_context:
        context_parts.append(f"[Skill Library: {skill_context}]")

    if context_parts:
        enhanced = f"{player_message}\n\n" + "\n".join(context_parts)

    log(f"  Brain context layers: world={'yes' if world_context else 'no'}, "
        f"memory={'yes' if memory_context else 'no'}, "
        f"skills={'yes' if skill_context else 'no'}")

    try:
        result = subprocess.run(
            ['python3', BRAIN_SCRIPT, '--verbose', enhanced],
            capture_output=True, text=True, timeout=DEEP_TIMEOUT,
            cwd=os.path.dirname(BRAIN_SCRIPT)
        )
        if result.returncode != 0:
            log(f"Brain stderr: {result.stderr[-500:]}", "WARN")
            # Try fast mode as fallback
            log("Retrying brain in fast mode...", "WARN")
            result = subprocess.run(
                ['python3', BRAIN_SCRIPT, '--fast', enhanced],
                capture_output=True, text=True, timeout=60,
                cwd=os.path.dirname(BRAIN_SCRIPT)
            )

        if result.returncode == 0 and result.stdout.strip():
            parsed = json.loads(result.stdout)
            if parsed.get("reply") and parsed.get("commands"):
                return parsed
            else:
                log(f"Brain returned incomplete: {str(parsed)[:200]}", "WARN")
                return None
        else:
            log(f"Brain failed: rc={result.returncode}, stderr={result.stderr[-300:]}", "ERROR")
            return None
    except subprocess.TimeoutExpired:
        log(f"Brain timed out after {DEEP_TIMEOUT}s", "ERROR")
        return None
    except json.JSONDecodeError as e:
        log(f"Brain output not JSON: {e}", "ERROR")
        return None
    except Exception as e:
        log(f"Brain call failed: {e}", "ERROR")
        return None

# ─── Job Processing ───────────────────────────────────────────────────────────

def process_job(job, force_deep=False):
    job_id = job.get('id', '')
    player_name = job.get('playerName', 'friend')
    message = job.get('message', '')
    session_id = job.get('sessionId', '')

    # Extract player position
    ps = job.get('playerState') or {}
    pos = ps.get('position') or {}
    px = int(float(pos.get('x', 0)))
    py = int(float(pos.get('y', 0)))
    pz = int(float(pos.get('z', 0)))

    log(f"Processing {job_id[:8]} | {player_name} | \"{message}\" | pos=({px},{py},{pz})")

    # ─── 1. Log the player's incoming message to memory ───
    if session_id and session_id != "mock-session":
        log_conversation(session_id, player_name, "player", message)

    # ─── 2. Get world context ───
    world_ctx = get_world_context(session_id)
    if world_ctx:
        log(f"  World context: {world_ctx[:100]}")

    # ─── 3. Recall player memory (profile, builds, conversations) ───
    memory_ctx = ""
    if session_id and session_id != "mock-session":
        player_ctx = get_player_context(player_name, session_id)
        memory_ctx = player_ctx.get("context", "")
        if memory_ctx:
            log(f"  Memory recall: {memory_ctx[:120]}...")
    else:
        # Mock mode — still try profile + builds for testing
        player_ctx = get_player_context(player_name, "")
        memory_ctx = player_ctx.get("context", "")

    # ─── 4. Search Vectorize for relevant skills ───
    skills = search_skills(message, top_k=3)
    skill_ctx = format_skill_context(skills)

    # ─── 5. Try fast path: keyword match ───
    reply = None
    commands = None
    used_path = None

    if not force_deep:
        builder = match_keyword(message)
        if builder:
            reply, commands = builder(px, py, pz)
            used_path = "template"
            log(f"  → Template match: {builder.__name__} → {len(commands)} commands")

    # ─── 6. Deep path: brain.py with all context ───
    if not reply:
        used_path = "deep-brain"
        log(f"  → Deep brain pipeline...")
        brain_result = call_brain(
            player_message=message,
            world_context=world_ctx,
            memory_context=memory_ctx,
            skill_context=skill_ctx,
        )
        if brain_result:
            reply = brain_result.get("reply", "")
            commands = brain_result.get("commands", [])
            pipeline = brain_result.get("_pipeline", {})
            log(f"  → Brain done: {len(commands)} commands in {pipeline.get('total_time_s', '?')}s")
        else:
            # Ultimate fallback
            reply, commands = b_default(player_name)
            used_path = "fallback"

    # ─── 7. Post result to Worker ───
    success = False
    try:
        result = api_post(f"/api/job/{job_id}/result", {
            "reply": reply,
            "commands": commands
        })
        log(f"  ✓ Complete via {used_path} ({len(commands)} commands)")
        success = True
    except Exception as e:
        log(f"  ✗ Failed to post result: {e}", "ERROR")

    # ─── 8. Save to memory (build + conversation + profile) ───
    # Always save, even for mock sessions (helps test the full pipeline)
    save_to_memory(
        job_id=job_id,
        session_id=session_id,
        player_name=player_name,
        message=message,
        reply=reply,
        commands=commands,
        px=px, py=py, pz=pz,
        used_path=used_path,
    )

    return success


def save_to_memory(job_id, session_id, player_name, message, reply, commands,
                   px, py, pz, used_path):
    """Persist build, conversation, and profile to D1 memory after job completion."""

    # Determine build type description from the reply or message
    build_desc = message[:100]  # Use the player's original request as description

    # 1. Upsert player profile FIRST — build_history has a FK to player_profiles
    upsert_player_profile(player_name, session_id)

    # 2. Log the build (now the player row exists for the FK)
    log_build(
        session_id=session_id or "unknown",
        player_name=player_name,
        description=build_desc,
        command_count=len(commands) if commands else 0,
        position={"x": px, "y": py, "z": pz},
    )

    # 3. Log Lucineer's reply as assistant conversation
    if session_id and session_id != "mock-session":
        log_conversation(session_id, player_name, "assistant", reply)


# ─── Main Loops ───────────────────────────────────────────────────────────────

def run_once(force_deep=False):
    data = api_get("/api/jobs/pending")
    jobs = data.get("jobs", [])
    if not jobs:
        return 0

    log(f"Found {len(jobs)} pending job(s)")
    count = 0
    for job in jobs:
        try:
            if process_job(job, force_deep=force_deep):
                count += 1
        except Exception as e:
            log(f"Job {job.get('id','?')[:8]} crashed: {e}", "ERROR")
            traceback.print_exc()
    return count

def get_rss_mb():
    """Return current process RSS in megabytes."""
    try:
        # ru_maxrss is in KB on Linux, KB on macOS
        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return rss_kb / 1024.0
    except Exception:
        return 0.0


def run_loop(interval=2, force_deep=False):
    log("=== Lucineer Processor v2 — Hybrid Intelligence + Memory ===")
    log(f"  Worker:  {WORKER_URL}")
    log(f"  Memory:  {MEMORY_URL}")
    log(f"  Vector:  {VECTOR_URL}")
    log(f"  Brain:   {BRAIN_SCRIPT}")
    log(f"  Mode:    {'DEEP-ONLY' if force_deep else 'HYBRID (template→brain)'}")
    log(f"  Poll:    every {interval}s")
    log(f"  Circuit breaker: {CIRCUIT_BREAKER_THRESHOLD} consecutive failures")
    log(f"  Heartbeat: every {HEARTBEAT_INTERVAL}s idle")
    log(f"  Memory guard: {MEMORY_LIMIT_MB}MB RSS warning")

    running = True
    consecutive_failures = 0
    last_heartbeat = time.time()

    def handle_signal(signum, frame):
        nonlocal running
        log(f"Signal {signum} received, shutting down...")
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    while running:
        try:
            jobs_processed = run_once(force_deep=force_deep)

            # Reset failure counter on any successful poll cycle
            if jobs_processed > 0:
                consecutive_failures = 0
            else:
                # Idle — emit heartbeat if enough time has passed
                now = time.time()
                if now - last_heartbeat >= HEARTBEAT_INTERVAL:
                    log("Heartbeat: OK (0 pending jobs)")
                    last_heartbeat = now

                    # Memory leak guard — check RSS on each heartbeat
                    rss_mb = get_rss_mb()
                    if rss_mb > MEMORY_LIMIT_MB:
                        log(f"Memory warning: RSS={rss_mb:.1f}MB exceeds {MEMORY_LIMIT_MB}MB limit", "WARN")

        except Exception as e:
            consecutive_failures += 1
            log(f"Loop error ({consecutive_failures}/{CIRCUIT_BREAKER_THRESHOLD}): {e}", "ERROR")
            traceback.print_exc()

            if consecutive_failures >= CIRCUIT_BREAKER_THRESHOLD:
                log(f"CIRCUIT BREAKER TRIPPED: {consecutive_failures} consecutive failures. "
                    f"Logging critical and continuing — will retry next cycle.", "CRITICAL")
                # Don't crash — reset counter so we don't spam CRITICAL every iteration
                # Keep counting; next success resets to 0
        time.sleep(interval)

    log("Processor stopped.")

# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Lucineer Processor v2 — Memory-Integrated")
    parser.add_argument("--loop", action="store_true", help="Continuous polling mode")
    parser.add_argument("--once", action="store_true", help="Single poll (default)")
    parser.add_argument("--deep", action="store_true", help="Force deep brain on all jobs")
    parser.add_argument("--mock", type=str, help="Inject a mock job with given message")
    parser.add_argument("--interval", type=int, default=2, help="Poll interval in seconds")
    args = parser.parse_args()

    if args.mock:
        mock = {
            "id": f"mock_{int(time.time())}",
            "playerName": "Casey",
            "message": args.mock,
            "sessionId": "mock-session",
            "playerState": {"position": {"x": 10, "y": 5, "z": -20}}
        }
        process_job(mock, force_deep=args.deep)
    elif args.loop:
        run_loop(interval=args.interval, force_deep=args.deep)
    else:
        count = run_once(force_deep=args.deep)
        if count == 0:
            log("No pending jobs.")
