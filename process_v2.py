#!/usr/bin/env python3
"""
Lucineer Job Processor v2 — Hybrid Intelligence
================================================
Two-speed brain:
  FAST: Pattern-matched templates (instant, no model call)
  DEEP: brain.py 3-stage pipeline (Seed → Planner → Coder) for complex requests

Processor flow:
  1. Poll Worker for pending jobs
  2. Check world state for context (what's already built nearby)
  3. Try keyword match → fast template
  4. If no match → call brain.py for deep generation
  5. Post result back to Worker

Usage:
  python3 process_v2.py --loop          # continuous mode (default 2s poll)
  python3 process_v2.py --once          # single poll
  python3 process_v2.py --mock "castle" # inject a test job
  python3 process_v2.py --deep          # force deep brain on all jobs
"""
import json, sys, os, time, subprocess, random, signal, traceback
from datetime import datetime
from pathlib import Path

# ─── Config ───────────────────────────────────────────────────────────────────

WORKER_URL = "https://lucineer-relay.casey-digennaro.workers.dev"
AUTH_KEY = "feba836ba409a7e959d957c7c4051fa6243a3436367073e52c567f979f49c9a7"
LOG_FILE = str(Path(__file__).parent / "processor.log")
BRAIN_SCRIPT = str(Path(__file__).parent.parent / "lucineer-brain" / "brain.py")
DEEP_TIMEOUT = 120  # seconds for brain.py call
MAX_RETRIES = 2

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
    return ("Four walls and a roof — proper brick, planks on the floor, chimney flue. Window's glowing but I didn't build the door yet. Your call on the style.", [
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
    return ("Castle's up — walls, corner towers, keep, the works. Gate's in but I left the portcullis mechanism for you. Even a foreman needs something to do.", cmds)

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
    return ("Bed's in, fence's up, six flowers and a tree at center. Didn't lay the paths — wanted you to pick where they go.", cmds)

def b_dock(px, py, pz):
    return ("Piles driven, planks across, lantern at the end. Reminds me of the tenders in Southeast — except those have crab pots. You could add some.", [
        {"type":"createPart","params":{"name":"DockDeck","shape":"Block","size":{"x":6,"y":1,"z":20},"position":{"x":px,"y":py+1,"z":pz},"material":"WoodPlanks","color":{"r":120,"g":80,"b":45},"anchored":True}},
        {"type":"createPart","params":{"name":"DockPile1","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px-2,"y":py-2,"z":pz-8},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"DockPile2","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px+2,"y":py-2,"z":pz-8},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"DockPile3","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px-2,"y":py-2,"z":pz+8},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"DockPile4","shape":"Cylinder","size":{"x":1,"y":6,"z":1},"position":{"x":px+2,"y":py-2,"z":pz+8},"material":"Wood","color":{"r":85,"g":55,"b":30},"anchored":True}},
        {"type":"createPart","params":{"name":"DockLantern","shape":"Ball","size":{"x":1.5,"y":1.5,"z":1.5},"position":{"x":px,"y":py+4,"z":pz+8},"material":"Neon","color":{"r":255,"g":200,"b":100},"anchored":True}},
        {"type":"addLight","params":{"parent":"DockLantern","lightType":"PointLight","brightness":4,"range":20,"color":{"r":255,"g":200,"b":100}}},
    ])

def b_lighthouse(px, py, pz):
    return ("Concrete shaft, beacon room on top, spotlight that reaches. Like the ones at the cannery — except those smell like fish and this one doesn't.", [
        {"type":"createPart","params":{"name":"LightBase","shape":"Cylinder","size":{"x":10,"y":30,"z":10},"position":{"x":px,"y":py+15,"z":pz},"material":"Concrete","color":{"r":200,"g":200,"b":195},"anchored":True}},
        {"type":"createPart","params":{"name":"LightTop","shape":"Cylinder","size":{"x":12,"y":4,"z":12},"position":{"x":px,"y":py+32,"z":pz},"material":"Metal","color":{"r":100,"g":100,"b":95},"anchored":True}},
        {"type":"createPart","params":{"name":"LightRoom","shape":"Block","size":{"x":8,"y":6,"z":8},"position":{"x":px,"y":py+36,"z":pz},"material":"Glass","color":{"r":255,"g":255,"b":200},"anchored":True,"transparency":0.3}},
        {"type":"createPart","params":{"name":"LightBeacon","shape":"Ball","size":{"x":3,"y":3,"z":3},"position":{"x":px,"y":py+36,"z":pz},"material":"Neon","color":{"r":255,"g":240,"b":100},"anchored":True}},
        {"type":"addLight","params":{"parent":"LightBeacon","lightType":"SpotLight","brightness":10,"range":200,"color":{"r":255,"g":240,"b":100}}},
    ])

def b_default(player_name):
    return (f"Couldn't match that to anything in the yard, {player_name}. Tower, house, castle, bridge, "
            "tree, wall, road, lamp, pyramid, dome, arch, platform, stairs, garden, dock, lighthouse — "
            "pick one and I'll get to work.", [
        {"type":"createPart","params":{"name":"CreativeBlock","shape":"Block","size":{"x":4,"y":4,"z":4},"position":{"x":0,"y":10,"z":0},"material":"Neon","color":{"r":100,"g":255,"b":200},"anchored":True}},
    ])

# ─── Keyword Matching ─────────────────────────────────────────────────────────

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

# ─── Deep Brain Integration ───────────────────────────────────────────────────

def call_brain(player_message, world_context=""):
    """Call brain.py for deep AI generation. Returns dict with reply + commands."""
    # Enhance the message with world context
    enhanced = player_message
    if world_context:
        enhanced = f"{player_message}\n\n[World Context: {world_context}]"

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

    # Get world context for deep brain
    world_ctx = get_world_context(session_id)
    if world_ctx:
        log(f"  World context: {world_ctx[:100]}")

    reply = None
    commands = None
    used_path = None

    # Fast path: keyword match
    if not force_deep:
        builder = match_keyword(message)
        if builder:
            reply, commands = builder(px, py, pz)
            used_path = "template"
            log(f"  → Template match: {builder.__name__} → {len(commands)} commands")

    # Deep path: brain.py
    if not reply:
        used_path = "deep-brain"
        log(f"  → Deep brain pipeline...")
        brain_result = call_brain(message, world_ctx)
        if brain_result:
            reply = brain_result.get("reply", "")
            commands = brain_result.get("commands", [])
            pipeline = brain_result.get("_pipeline", {})
            log(f"  → Brain done: {len(commands)} commands in {pipeline.get('total_time_s', '?')}s")
        else:
            # Ultimate fallback
            reply, commands = b_default(player_name)
            used_path = "fallback"

    # Post result
    try:
        result = api_post(f"/api/job/{job_id}/result", {
            "reply": reply,
            "commands": commands
        })
        log(f"  ✓ Complete via {used_path} ({len(commands)} commands)")
        return True
    except Exception as e:
        log(f"  ✗ Failed to post result: {e}", "ERROR")
        return False

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

def run_loop(interval=2, force_deep=False):
    log("=== Lucineer Processor v2 — Hybrid Intelligence ===")
    log(f"  Worker: {WORKER_URL}")
    log(f"  Brain:  {BRAIN_SCRIPT}")
    log(f"  Mode:   {'DEEP-ONLY' if force_deep else 'HYBRID (template→brain)'}")
    log(f"  Poll:   every {interval}s")

    running = True
    def handle_signal(signum, frame):
        nonlocal running
        log(f"Signal {signum} received, shutting down...")
        running = False

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    while running:
        try:
            run_once(force_deep=force_deep)
        except Exception as e:
            log(f"Loop error: {e}", "ERROR")
            traceback.print_exc()
        time.sleep(interval)

    log("Processor stopped.")

# ─── CLI ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Lucineer Processor v2")
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
