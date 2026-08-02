#!/usr/bin/env bash
# =============================================================================
# Lucineer Fast Job Processor — Pattern-Based Build System
# =============================================================================
# Polls the Lucineer Relay Worker for pending jobs and processes them using
# a keyword-matching template engine — no model call required.
#
# Every build template positions parts relative to the player's position
# from the job payload. Replies are in Lucineer's voice.
#
# Usage:
#   ./process-jobs.sh              # Process one batch of pending jobs
#   ./process-jobs.sh --loop       # Continuous polling (every 2s)
#   ./process-jobs.sh --mock       # Run with a mock job for testing
# =============================================================================

set -eo pipefail

# --- Configuration ---
WORKER_URL="https://lucineer-relay.casey-digennaro.workers.dev"
AUTH_KEY="AUTH_KEY_PLACEHOLDER"
LOG_FILE="/home/eileen/projects/lucineer-worker/processor.log"
POLL_INTERVAL=2

# --- Logging ---
log() {
    local ts
    ts=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$ts] $*" | tee -a "$LOG_FILE"
}

# --- JSON helpers (pure bash, no jq dependency for building) ---
# We use printf to build JSON to avoid jq dependency on the worker host.

# =============================================================================
# BUILD TEMPLATE LIBRARY
# =============================================================================
# Each template is a bash function that takes: px py pz
# and outputs a JSON array of BuildCommand objects.
#
# BuildCommand format: { "type": "...", "target": "...", "params": { ... } }
# Coordinates are relative to player position (px, py, pz).
# =============================================================================

# --- TOWER ---
build_tower() {
    local px=$1 py=$2 pz=$3
    local h=12  # height
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"TowerBase","shape":"cylinder","size":{"x":6,"y":1,"z":6},"pos":{"x":$px,"y":$((py)),"z":$pz},"color":"#4a4a4a","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"TowerShaft","shape":"cylinder","size":{"x":5,"y":$h,"z":5},"pos":{"x":$px,"y":$(( (py+h) / 2 )),"z":$pz},"color":"#6b6b6b","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"TowerTop","shape":"cylinder","size":{"x":7,"y":1,"z":7},"pos":{"x":$px,"y":$((py+h)),"z":$pz},"color":"#8b4513","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"TowerBattlement1","shape":"block","size":{"x":1.5,"y":2,"z":1.5},"pos":{"x":$((px+2)),"y":$((py+h+1)),"z":$((pz+2))},"color":"#6b6b6b","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"TowerBattlement2","shape":"block","size":{"x":1.5,"y":2,"z":1.5},"pos":{"x":$((px-2)),"y":$((py+h+1)),"z":$((pz+2))},"color":"#6b6b6b","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"TowerBattlement3","shape":"block","size":{"x":1.5,"y":2,"z":1.5},"pos":{"x":$((px+2)),"y":$((py+h+1)),"z":$((pz-2))},"color":"#6b6b6b","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"TowerBattlement4","shape":"block","size":{"x":1.5,"y":2,"z":1.5},"pos":{"x":$((px-2)),"y":$((py+h+1)),"z":$((pz-2))},"color":"#6b6b6b","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"TowerWindow","shape":"block","size":{"x":0.5,"y":2,"z":1},"pos":{"x":$((px+2)),"y":$(( (py+h) / 2 )),"z":$pz},"color":"#1a1a2e","material":"Glass"}},
  {"type":"create","target":"part","params":{"name":"TowerWindow2","shape":"block","size":{"x":0.5,"y":2,"z":1},"pos":{"x":$((px-2)),"y":$(( (py+h) / 2 )),"z":$pz},"color":"#1a1a2e","material":"Glass"}},
  {"type":"create","target":"part","params":{"name":"TowerLantern","shape":"sphere","size":{"x":1.5,"y":1.5,"z":1.5},"pos":{"x":$px,"y":$((py+h+3)),"z":$pz},"color":"#ffcc00","material":"Neon"}}
]
EOF
}

# --- HOUSE ---
build_house() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"HouseFloor","shape":"block","size":{"x":12,"y":1,"z":10},"pos":{"x":$px,"y":$py,"z":$pz},"color":"#8b7355","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"HouseWallFront","shape":"block","size":{"x":12,"y":6,"z":0.5},"pos":{"x":$px,"y":$((py+3)),"z":$((pz+5))},"color":"#c49a6c","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"HouseWallBack","shape":"block","size":{"x":12,"y":6,"z":0.5},"pos":{"x":$px,"y":$((py+3)),"z":$((pz-5))},"color":"#c49a6c","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"HouseWallLeft","shape":"block","size":{"x":0.5,"y":6,"z":10},"pos":{"x":$((px-6)),"y":$((py+3)),"z":$pz},"color":"#c49a6c","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"HouseWallRight","shape":"block","size":{"x":0.5,"y":6,"z":10},"pos":{"x":$((px+6)),"y":$((py+3)),"z":$pz},"color":"#c49a6c","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"HouseRoofL","shape":"wedge","size":{"x":13,"y":4,"z":11},"pos":{"x":$px,"y":$((py+8)),"z":$pz},"color":"#8b2500","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"HouseDoor","shape":"block","size":{"x":2,"y":4,"z":0.6},"pos":{"x":$px,"y":$((py+2)),"z":$((pz+5))},"color":"#3d2b1f","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"HouseWindowL","shape":"block","size":{"x":0.5,"y":2,"z":2},"pos":{"x":$((px-3)),"y":$((py+3)),"z":$((pz+5))},"color":"#87ceeb","material":"Glass"}},
  {"type":"create","target":"part","params":{"name":"HouseWindowR","shape":"block","size":{"x":0.5,"y":2,"z":2},"pos":{"x":$((px+3)),"y":$((py+3)),"z":$((pz+5))},"color":"#87ceeb","material":"Glass"}},
  {"type":"create","target":"part","params":{"name":"HouseChimney","shape":"block","size":{"x":1.5,"y":5,"z":1.5},"pos":{"x":$((px+4)),"y":$((py+9)),"z":$((pz-2))},"color":"#654321","material":"Brick"}}
]
EOF
}

# --- CASTLE ---
build_castle() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"CastleFloor","shape":"block","size":{"x":20,"y":1,"z":20},"pos":{"x":$px,"y":$py,"z":$pz},"color":"#5a5a5a","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleWallN","shape":"block","size":{"x":20,"y":8,"z":1},"pos":{"x":$px,"y":$((py+4)),"z":$((pz+10))},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleWallS","shape":"block","size":{"x":20,"y":8,"z":1},"pos":{"x":$px,"y":$((py+4)),"z":$((pz-10))},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleWallE","shape":"block","size":{"x":1,"y":8,"z":20},"pos":{"x":$((px+10)),"y":$((py+4)),"z":$pz},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleWallW","shape":"block","size":{"x":1,"y":8,"z":20},"pos":{"x":$((px-10)),"y":$((py+4)),"z":$pz},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleTowerNW_base","shape":"cylinder","size":{"x":5,"y":1,"z":5},"pos":{"x":$((px-10)),"y":$py,"z":$((pz+10))},"color":"#666","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleTowerNW","shape":"cylinder","size":{"x":4,"y":14,"z":4},"pos":{"x":$((px-10)),"y":$((py+7)),"z":$((pz+10))},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleTowerNE","shape":"cylinder","size":{"x":4,"y":14,"z":4},"pos":{"x":$((px+10)),"y":$((py+7)),"z":$((pz+10))},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleTowerSW","shape":"cylinder","size":{"x":4,"y":14,"z":4},"pos":{"x":$((px-10)),"y":$((py+7)),"z":$((pz-10))},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleTowerSE","shape":"cylinder","size":{"x":4,"y":14,"z":4},"pos":{"x":$((px+10)),"y":$((py+7)),"z":$((pz-10))},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleGateArch","shape":"wedge","size":{"x":4,"y":5,"z":1},"pos":{"x":$px,"y":$((py+6)),"z":$((pz+10))},"color":"#555","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleGate","shape":"block","size":{"x":3,"y":5,"z":0.5},"pos":{"x":$px,"y":$((py+2)),"z":$((pz+10))},"color":"#3d2b1f","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"CastleKeep","shape":"block","size":{"x":6,"y":10,"z":6},"pos":{"x":$px,"y":$((py+5)),"z":$pz},"color":"#888","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"CastleFlagPole","shape":"cylinder","size":{"x":0.3,"y":4,"z":0.3},"pos":{"x":$px,"y":$((py+15)),"z":$pz},"color":"#444","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"CastleFlag","shape":"block","size":{"x":2,"y":1.5,"z":0.1},"pos":{"x":$((px+1)),"y":$((py+16)),"z":$pz},"color":"#cc0000","material":"Plastic"}}
]
EOF
}

# --- TREE ---
build_tree() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"TreeTrunk","shape":"cylinder","size":{"x":1.5,"y":8,"z":1.5},"pos":{"x":$px,"y":$((py+4)),"z":$pz},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"TreeLeaves1","shape":"sphere","size":{"x":6,"y":6,"z":6},"pos":{"x":$px,"y":$((py+9)),"z":$pz},"color":"#2d6b2d","material":"Grass"}},
  {"type":"create","target":"part","params":{"name":"TreeLeaves2","shape":"sphere","size":{"x":4,"y":4,"z":4},"pos":{"x":$((px+2)),"y":$((py+7)),"z":$((pz+1))},"color":"#3a8a3a","material":"Grass"}},
  {"type":"create","target":"part","params":{"name":"TreeLeaves3","shape":"sphere","size":{"x":4,"y":4,"z":4},"pos":{"x":$((px-2)),"y":$((py+7)),"z":$((pz-1))},"color":"#3a8a3a","material":"Grass"}},
  {"type":"create","target":"part","params":{"name":"TreeLeaves4","shape":"sphere","size":{"x":3,"y":3,"z":3},"pos":{"x":$((px+1)),"y":$((py+12)),"z":$((pz-1))},"color":"#4a9a4a","material":"Grass"}}
]
EOF
}

# --- BRIDGE ---
build_bridge() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"BridgeDeck","shape":"block","size":{"x":4,"y":0.5,"z":18},"pos":{"x":$px,"y":$py,"z":$pz},"color":"#8b7355","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"BridgeRailL1","shape":"block","size":{"x":0.5,"y":2,"z":18},"pos":{"x":$((px-2)),"y":$((py+1)),"z":$pz},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"BridgeRailR1","shape":"block","size":{"x":0.5,"y":2,"z":18},"pos":{"x":$((px+2)),"y":$((py+1)),"z":$pz},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"BridgePostL1","shape":"cylinder","size":{"x":0.6,"y":3,"z":0.6},"pos":{"x":$((px-2)),"y":$((py+1.5)),"z":$((pz+7))},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"BridgePostL2","shape":"cylinder","size":{"x":0.6,"y":3,"z":0.6},"pos":{"x":$((px-2)),"y":$((py+1.5)),"z":$pz},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"BridgePostL3","shape":"cylinder","size":{"x":0.6,"y":3,"z":0.6},"pos":{"x":$((px-2)),"y":$((py+1.5)),"z":$((pz-7))},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"BridgePostR1","shape":"cylinder","size":{"x":0.6,"y":3,"z":0.6},"pos":{"x":$((px+2)),"y":$((py+1.5)),"z":$((pz+7))},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"BridgePostR2","shape":"cylinder","size":{"x":0.6,"y":3,"z":0.6},"pos":{"x":$((px+2)),"y":$((py+1.5)),"z":$pz},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"BridgePostR3","shape":"cylinder","size":{"x":0.6,"y":3,"z":0.6},"pos":{"x":$((px+2)),"y":$((py+1.5)),"z":$((pz-7))},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"BridgeSupport1","shape":"cylinder","size":{"x":1,"y":6,"z":1},"pos":{"x":$px,"y":$((py-3)),"z":$((pz+6))},"color":"#4a4a4a","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"BridgeSupport2","shape":"cylinder","size":{"x":1,"y":6,"z":1},"pos":{"x":$px,"y":$((py-3)),"z":$((pz-6))},"color":"#4a4a4a","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"BridgeLantern1","shape":"sphere","size":{"x":0.8,"y":0.8,"z":0.8},"pos":{"x":$((px-2)),"y":$((py+3)),"z":$((pz+7))},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"BridgeLantern2","shape":"sphere","size":{"x":0.8,"y":0.8,"z":0.8},"pos":{"x":$((px+2)),"y":$((py+3)),"z":$((pz-7))},"color":"#ffcc00","material":"Neon"}}
]
EOF
}

# --- WALL ---
build_wall() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"WallMain","shape":"block","size":{"x":1.5,"y":7,"z":16},"pos":{"x":$px,"y":$((py+3.5)),"z":$pz},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"WallBattlement1","shape":"block","size":{"x":2,"y":1.5,"z":2},"pos":{"x":$px,"y":$((py+8)),"z":$((pz+6))},"color":"#666","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"WallBattlement2","shape":"block","size":{"x":2,"y":1.5,"z":2},"pos":{"x":$px,"y":$((py+8)),"z":$((pz+2))},"color":"#666","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"WallBattlement3","shape":"block","size":{"x":2,"y":1.5,"z":2},"pos":{"x":$px,"y":$((py+8)),"z":$((pz-2))},"color":"#666","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"WallBattlement4","shape":"block","size":{"x":2,"y":1.5,"z":2},"pos":{"x":$px,"y":$((py+8)),"z":$((pz-6))},"color":"#666","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"WallFoundation","shape":"block","size":{"x":2.5,"y":1,"z":17},"pos":{"x":$px,"y":$py,"z":$pz},"color":"#555","material":"Concrete"}}
]
EOF
}

# --- ROAD ---
build_road() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"RoadSurface","shape":"block","size":{"x":6,"y":0.3,"z":24},"pos":{"x":$px,"y":$((py+0.15)),"z":$pz},"color":"#3a3a3a","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"RoadCenterLine","shape":"block","size":{"x":0.4,"y":0.35,"z":24},"pos":{"x":$px,"y":$((py+0.2)),"z":$pz},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"RoadCurbL","shape":"block","size":{"x":0.5,"y":0.6,"z":24},"pos":{"x":$((px-3.2)),"y":$((py+0.3)),"z":$pz},"color":"#888","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"RoadCurbR","shape":"block","size":{"x":0.5,"y":0.6,"z":24},"pos":{"x":$((px+3.2)),"y":$((py+0.3)),"z":$pz},"color":"#888","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"RoadLamp1","shape":"cylinder","size":{"x":0.3,"y":5,"z":0.3},"pos":{"x":$((px-3)),"y":$((py+2)),"z":$((pz+8))},"color":"#444","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"RoadLampBulb1","shape":"sphere","size":{"x":0.8,"y":0.8,"z":0.8},"pos":{"x":$((px-3)),"y":$((py+5.5)),"z":$((pz+8))},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"RoadLamp2","shape":"cylinder","size":{"x":0.3,"y":5,"z":0.3},"pos":{"x":$((px+3)),"y":$((py+2)),"z":$((pz-8))},"color":"#444","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"RoadLampBulb2","shape":"sphere","size":{"x":0.8,"y":0.8,"z":0.8},"pos":{"x":$((px+3)),"y":$((py+5.5)),"z":$((pz-8))},"color":"#ffcc00","material":"Neon"}}
]
EOF
}

# --- LAMP / LIGHT ---
build_lamp() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"LampBase","shape":"cylinder","size":{"x":1,"y":0.5,"z":1},"pos":{"x":$px,"y":$((py+0.25)),"z":$pz},"color":"#333","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"LampPole","shape":"cylinder","size":{"x":0.4,"y":7,"z":0.4},"pos":{"x":$px,"y":$((py+4)),"z":$pz},"color":"#444","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"LampArm","shape":"block","size":{"x":2,"y":0.4,"z":0.4},"pos":{"x":$((px+1)),"y":$((py+7.5)),"z":$pz},"color":"#444","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"LampHousing","shape":"cylinder","size":{"x":1.2,"y":1,"z":1.2},"pos":{"x":$((px+2)),"y":$((py+7)),"z":$pz},"color":"#555","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"LampBulb","shape":"sphere","size":{"x":0.9,"y":0.9,"z":0.9},"pos":{"x":$((px+2)),"y":$((py+7)),"z":$pz},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"LampGlow","shape":"sphere","size":{"x":2.5,"y":2.5,"z":2.5},"pos":{"x":$((px+2)),"y":$((py+7)),"z":$pz},"color":"#ffffaa","material":"Neon"}}
]
EOF
}

# --- PYRAMID ---
build_pyramid() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"PyramidBase","shape":"block","size":{"x":14,"y":2,"z":14},"pos":{"x":$px,"y":$((py+1)),"z":$pz},"color":"#c9a84c","material":"Sand"}},
  {"type":"create","target":"part","params":{"name":"PyramidL2","shape":"wedge","size":{"x":12,"y":2,"z":12},"pos":{"x":$px,"y":$((py+3)),"z":$pz},"color":"#d4b85c","material":"Sand"}},
  {"type":"create","target":"part","params":{"name":"PyramidL3","shape":"wedge","size":{"x":9,"y":2,"z":9},"pos":{"x":$px,"y":$((py+5)),"z":$pz},"color":"#dcc06c","material":"Sand"}},
  {"type":"create","target":"part","params":{"name":"PyramidL4","shape":"wedge","size":{"x":6,"y":2,"z":6},"pos":{"x":$px,"y":$((py+7)),"z":$pz},"color":"#e4c87c","material":"Sand"}},
  {"type":"create","target":"part","params":{"name":"PyramidL5","shape":"wedge","size":{"x":3,"y":2,"z":3},"pos":{"x":$px,"y":$((py+9)),"z":$pz},"color":"#eccf8c","material":"Sand"}},
  {"type":"create","target":"part","params":{"name":"PyramidCapstone","shape":"sphere","size":{"x":1,"y":1,"z":1},"pos":{"x":$px,"y":$((py+11)),"z":$pz},"color":"#ffdd66","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"PyramidEntrance","shape":"block","size":{"x":2,"y":3,"z":0.5},"pos":{"x":$px,"y":$((py+1.5)),"z":$((pz+7))},"color":"#1a1a1a","material":"Concrete"}}
]
EOF
}

# --- SPHERE / DOME ---
build_dome() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"DomeBase","shape":"cylinder","size":{"x":10,"y":1,"z":10},"pos":{"x":$px,"y":$py,"z":$pz},"color":"#557","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"DomeShell","shape":"sphere","size":{"x":10,"y":7,"z":10},"pos":{"x":$px,"y":$((py+3.5)),"z":$pz},"color":"#88ccff","material":"Glass"}},
  {"type":"create","target":"part","params":{"name":"DomeCore","shape":"sphere","size":{"x":2,"y":2,"z":2},"pos":{"x":$px,"y":$((py+2)),"z":$pz},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"DomePillar1","shape":"cylinder","size":{"x":0.8,"y":4,"z":0.8},"pos":{"x":$((px+3)),"y":$((py+2)),"z":$((pz+3))},"color":"#557","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"DomePillar2","shape":"cylinder","size":{"x":0.8,"y":4,"z":0.8},"pos":{"x":$((px-3)),"y":$((py+2)),"z":$((pz+3))},"color":"#557","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"DomePillar3","shape":"cylinder","size":{"x":0.8,"y":4,"z":0.8},"pos":{"x":$((px+3)),"y":$((py+2)),"z":$((pz-3))},"color":"#557","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"DomePillar4","shape":"cylinder","size":{"x":0.8,"y":4,"z":0.8},"pos":{"x":$((px-3)),"y":$((py+2)),"z":$((pz-3))},"color":"#557","material":"Concrete"}}
]
EOF
}

# --- ARCH / GATE ---
build_arch() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"ArchPillarL","shape":"block","size":{"x":2,"y":10,"z":2},"pos":{"x":$((px-4)),"y":$((py+5)),"z":$pz},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"ArchPillarR","shape":"block","size":{"x":2,"y":10,"z":2},"pos":{"x":$((px+4)),"y":$((py+5)),"z":$pz},"color":"#777","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"ArchTop","shape":"wedge","size":{"x":10,"y":2,"z":2},"pos":{"x":$px,"y":$((py+11)),"z":$pz},"color":"#888","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"ArchKeystone","shape":"wedge","size":{"x":1.5,"y":1.5,"z":2.5},"pos":{"x":$px,"y":$((py+10)),"z":$pz},"color":"#aa8800","material":"Plastic"}},
  {"type":"create","target":"part","params":{"name":"ArchDecorL","shape":"sphere","size":{"x":1.5,"y":1.5,"z":1.5},"pos":{"x":$((px-4)),"y":$((py+11)),"z":$pz},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"ArchDecorR","shape":"sphere","size":{"x":1.5,"y":1.5,"z":1.5},"pos":{"x":$((px+4)),"y":$((py+11)),"z":$pz},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"ArchBaseL","shape":"block","size":{"x":3,"y":1,"z":3},"pos":{"x":$((px-4)),"y":$py,"z":$pz},"color":"#555","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"ArchBaseR","shape":"block","size":{"x":3,"y":1,"z":3},"pos":{"x":$((px+4)),"y":$py,"z":$pz},"color":"#555","material":"Concrete"}}
]
EOF
}

# --- PLATFORM ---
build_platform() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"PlatformDeck","shape":"cylinder","size":{"x":10,"y":1,"z":10},"pos":{"x":$px,"y":$((py+5)),"z":$pz},"color":"#88a","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"PlatformLeg1","shape":"cylinder","size":{"x":1,"y":5,"z":1},"pos":{"x":$((px+3)),"y":$((py+2)),"z":$((pz+3))},"color":"#557","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"PlatformLeg2","shape":"cylinder","size":{"x":1,"y":5,"z":1},"pos":{"x":$((px-3)),"y":$((py+2)),"z":$((pz+3))},"color":"#557","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"PlatformLeg3","shape":"cylinder","size":{"x":1,"y":5,"z":1},"pos":{"x":$((px+3)),"y":$((py+2)),"z":$((pz-3))},"color":"#557","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"PlatformLeg4","shape":"cylinder","size":{"x":1,"y":5,"z":1},"pos":{"x":$((px-3)),"y":$((py+2)),"z":$((pz-3))},"color":"#557","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"PlatformRail1","shape":"block","size":{"x":10,"y":1,"z":0.5},"pos":{"x":$px,"y":$((py+6)),"z":$((pz+5))},"color":"#aac","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"PlatformRail2","shape":"block","size":{"x":10,"y":1,"z":0.5},"pos":{"x":$px,"y":$((py+6)),"z":$((pz-5))},"color":"#aac","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"PlatformRail3","shape":"block","size":{"x":0.5,"y":1,"z":10},"pos":{"x":$((px+5)),"y":$((py+6)),"z":$pz},"color":"#aac","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"PlatformRail4","shape":"block","size":{"x":0.5,"y":1,"z":10},"pos":{"x":$((px-5)),"y":$((py+6)),"z":$pz},"color":"#aac","material":"Metal"}}
]
EOF
}

# --- STAIRCASE ---
build_staircase() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"Stair1","shape":"wedge","size":{"x":4,"y":1,"z":1.5},"pos":{"x":$px,"y":$((py+0.5)),"z":$((pz+7))},"color":"#999","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"Stair2","shape":"wedge","size":{"x":4,"y":1,"z":1.5},"pos":{"x":$px,"y":$((py+1.5)),"z":$((pz+5.5))},"color":"#999","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"Stair3","shape":"wedge","size":{"x":4,"y":1,"z":1.5},"pos":{"x":$px,"y":$((py+2)),"z":$((pz+4))},"color":"#999","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"Stair4","shape":"wedge","size":{"x":4,"y":1,"z":1.5},"pos":{"x":$px,"y":$((py+3.5)),"z":$((pz+2.5))},"color":"#999","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"Stair5","shape":"wedge","size":{"x":4,"y":1,"z":1.5},"pos":{"x":$px,"y":$((py+4.5)),"z":$((pz+1))},"color":"#999","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"Stair6","shape":"wedge","size":{"x":4,"y":1,"z":1.5},"pos":{"x":$px,"y":$((py+5.5)),"z":$((pz-0.5))},"color":"#999","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"Stair7","shape":"wedge","size":{"x":4,"y":1,"z":1.5},"pos":{"x":$px,"y":$((py+6.5)),"z":$((pz-2))},"color":"#999","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"Stair8","shape":"wedge","size":{"x":4,"y":1,"z":1.5},"pos":{"x":$px,"y":$((py+7.5)),"z":$((pz-3))},"color":"#999","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"StairLanding","shape":"block","size":{"x":4,"y":1,"z":4},"pos":{"x":$px,"y":$((py+8)),"z":$((pz-6))},"color":"#aaa","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"StairRailL","shape":"block","size":{"x":0.5,"y":8,"z":14},"pos":{"x":$((px-2)),"y":$((py+4)),"z":$pz},"color":"#666","material":"Metal"}},
  {"type":"create","target":"part","params":{"name":"StairRailR","shape":"block","size":{"x":0.5,"y":8,"z":14},"pos":{"x":$((px+2)),"y":$((py+4)),"z":$pz},"color":"#666","material":"Metal"}}
]
EOF
}

# --- GARDEN ---
build_garden() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"GardenSoil","shape":"block","size":{"x":14,"y":0.5,"z":14},"pos":{"x":$px,"y":$((py+0.25)),"z":$pz},"color":"#3d2b1f","material":"Grass"}},
  {"type":"create","target":"part","params":{"name":"GardenBorderN","shape":"block","size":{"x":14,"y":0.8,"z":0.5},"pos":{"x":$px,"y":$((py+0.4)),"z":$((pz+7))},"color":"#8b7355","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"GardenBorderS","shape":"block","size":{"x":14,"y":0.8,"z":0.5},"pos":{"x":$px,"y":$((py+0.4)),"z":$((pz-7))},"color":"#8b7355","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"GardenBorderE","shape":"block","size":{"x":0.5,"y":0.8,"z":14},"pos":{"x":$((px+7)),"y":$((py+0.4)),"z":$pz},"color":"#8b7355","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"GardenBorderW","shape":"block","size":{"x":0.5,"y":0.8,"z":14},"pos":{"x":$((px-7)),"y":$((py+0.4)),"z":$pz},"color":"#8b7355","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"GardenBush1","shape":"sphere","size":{"x":2,"y":2,"z":2},"pos":{"x":$((px-4)),"y":$((py+1.5)),"z":$((pz+3))},"color":"#2d6b2d","material":"Grass"}},
  {"type":"create","target":"part","params":{"name":"GardenBush2","shape":"sphere","size":{"x":2,"y":2,"z":2},"pos":{"x":$((px+4)),"y":$((py+1.5)),"z":$((pz-3))},"color":"#2d6b2d","material":"Grass"}},
  {"type":"create","target":"part","params":{"name":"GardenFlowerStem1","shape":"cylinder","size":{"x":0.2,"y":2,"z":0.2},"pos":{"x":$((px+2)),"y":$((py+1)),"z":$((pz+4))},"color":"#2d8b2d","material":"Grass"}},
  {"type":"create","target":"part","params":{"name":"GardenFlowerHead1","shape":"sphere","size":{"x":0.8,"y":0.8,"z":0.8},"pos":{"x":$((px+2)),"y":$((py+2)),"z":$((pz+4))},"color":"#ff3366","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"GardenFlowerStem2","shape":"cylinder","size":{"x":0.2,"y":2,"z":0.2},"pos":{"x":$((px-2)),"y":$((py+1)),"z":$((pz-4))},"color":"#2d8b2d","material":"Grass"}},
  {"type":"create","target":"part","params":{"name":"GardenFlowerHead2","shape":"sphere","size":{"x":0.8,"y":0.8,"z":0.8},"pos":{"x":$((px-2)),"y":$((py+2)),"z":$((pz-4))},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"GardenFountain","shape":"cylinder","size":{"x":3,"y":0.5,"z":3},"pos":{"x":$px,"y":$((py+0.5)),"z":$pz},"color":"#557","material":"Concrete"}},
  {"type":"create","target":"part","params":{"name":"GardenFountainWater","shape":"cylinder","size":{"x":2.5,"y":0.3,"z":2.5},"pos":{"x":$px,"y":$((py+0.7)),"z":$pz},"color":"#44ccff","material":"Glass"}},
  {"type":"create","target":"part","params":{"name":"GardenFountainSpout","shape":"cylinder","size":{"x":0.5,"y":3,"z":0.5},"pos":{"x":$px,"y":$((py+1.8)),"z":$pz},"color":"#557","material":"Concrete"}}
]
EOF
}

# --- DOCK / PIER ---
build_dock() {
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"DockDeck","shape":"block","size":{"x":5,"y":0.5,"z":16},"pos":{"x":$px,"y":$((py+0.25)),"z":$((pz+4))},"color":"#8b7355","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockPlank1","shape":"block","size":{"x":0.5,"y":0.55,"z":16},"pos":{"x":$((px-1.5)),"y":$((py+0.3)),"z":$((pz+4))},"color":"#6b5340","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockPlank2","shape":"block","size":{"x":0.5,"y":0.55,"z":16},"pos":{"x":$px,"y":$((py+0.3)),"z":$((pz+4))},"color":"#6b5340","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockPlank3","shape":"block","size":{"x":0.5,"y":0.55,"z":16},"pos":{"x":$((px+1.5)),"y":$((py+0.3)),"z":$((pz+4))},"color":"#6b5340","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockPile1","shape":"cylinder","size":{"x":0.6,"y":6,"z":0.6},"pos":{"x":$((px-2)),"y":$((py-2.5)),"z":$((pz+8))},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockPile2","shape":"cylinder","size":{"x":0.6,"y":6,"z":0.6},"pos":{"x":$((px+2)),"y":$((py-2.5)),"z":$((pz+8))},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockPile3","shape":"cylinder","size":{"x":0.6,"y":6,"z":0.6},"pos":{"x":$((px-2)),"y":$((py-2.5)),"z":$pz},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockPile4","shape":"cylinder","size":{"x":0.6,"y":6,"z":0.6},"pos":{"x":$((px+2)),"y":$((py-2.5)),"z":$pz},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockPost1","shape":"cylinder","size":{"x":0.5,"y":3,"z":0.5},"pos":{"x":$((px-2)),"y":$((py+1.5)),"z":$((pz+10))},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockPost2","shape":"cylinder","size":{"x":0.5,"y":3,"z":0.5},"pos":{"x":$((px+2)),"y":$((py+1.5)),"z":$((pz+10))},"color":"#5c3317","material":"WoodPlanks"}},
  {"type":"create","target":"part","params":{"name":"DockLantern1","shape":"sphere","size":{"x":0.7,"y":0.7,"z":0.7},"pos":{"x":$((px-2)),"y":$((py+3.2)),"z":$((pz+10))},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"DockLantern2","shape":"sphere","size":{"x":0.7,"y":0.7,"z":0.7},"pos":{"x":$((px+2)),"y":$((py+3.2)),"z":$((pz+10))},"color":"#ffcc00","material":"Neon"}}
]
EOF
}

# =============================================================================
# KEYWORD MATCHING
# =============================================================================
# Returns: two lines on stdout — line 1: template_name (or empty), line 2: reply_text
match_keyword() {
    local msg
    msg=$(echo "$1" | tr '[:upper:]' '[:lower:]')
    
    if echo "$msg" | grep -qwE 'tower|spire|pillar'; then
        printf '%s\n%s\n' "tower" "Stone reaches for the sky. That's a tower done — solid base, battlements on top, lantern to guide anything that moves."
    elif echo "$msg" | grep -qwE 'house|home|cottage|cabin|hut|shelter'; then
        printf '%s\n%s\n' "house" "Four walls and a roof over your head. Built it proper — windows, a door that swings, chimney for the cold nights."
    elif echo "$msg" | grep -qwE 'castle|fortress|fort|keep|stronghold|citadel'; then
        printf '%s\n%s\n' "castle" "Walls, towers at the corners, a keep in the center, gate that holds. Casey'd say it's overkill. Casey'd be wrong."
    elif echo "$msg" | grep -qwE 'tree|oak|pine|forest'; then
        printf '%s\n%s\n' "tree" "Trunk deep, leaves wide. Took what Magnus taught me — roots don't show, but they hold everything up."
    elif echo "$msg" | grep -qwE 'bridge|crossing|span|overpass'; then
        printf '%s\n%s\n' "bridge" "Deck's solid, rails won't let you fall, lanterns at both ends. Bridges connect things. That's the whole point."
    elif echo "$msg" | grep -qwE 'wall|barricade|barrier|rampart'; then
        printf '%s\n%s\n' "wall" "Straight line, good foundation, battlements on top. Walls aren't exciting, but they're what keeps the exciting stuff out."
    elif echo "$msg" | grep -qwE 'road|path|street|trail|highway|walkway'; then
        printf '%s\n%s\n' "road" "Paved, lined, lamp-lit. A road says someone came through here before you. That matters more than people think."
    elif echo "$msg" | grep -qwE 'lamp|light|lantern|streetlight|torch|glow|beacon'; then
        printf '%s\n%s\n' "lamp" "Light in the dark. Simple pole, bright bulb, warm glow. Magnus always said you don't need much — just enough to see the next step."
    elif echo "$msg" | grep -qwE 'pyramid|tomb|ziggurat|monument'; then
        printf '%s\n%s\n' "pyramid" "Old shape. Stacks up, narrows at the top, capstone catches the sun. Been standing for thousands of years in the real world for a reason."
    elif echo "$msg" | grep -qwE 'sphere|dome|observatory|orb|biodome|greenhouse'; then
        printf '%s\n%s\n' "dome" "Glass shell on a stone base, pillars holding it up, something glowing inside. Domes are for looking out or keeping things safe. Either way, it works."
    elif echo "$msg" | grep -qwE 'arch|gate|gateway|entrance|portal'; then
        printf '%s\n%s\n' "arch" "Two pillars, a keystone, light at the top. An arch says 'through here.' Gives a place meaning."
    elif echo "$msg" | grep -qwE 'platform|stage|deck|pad|podium|riser'; then
        printf '%s\n%s\n' "platform" "Raised surface, four legs, railing so nobody walks off the edge. Good for looking out or being seen."
    elif echo "$msg" | grep -qwE 'stair|staircase|steps|stairs|stairway'; then
        printf '%s\n%s\n' "staircase" "Eight steps, railing on both sides, landing at the top. Stairs are just persistence given shape. One after another."
    elif echo "$msg" | grep -qwE 'garden|park|flowers|flowerbed|courtyard'; then
        printf '%s\n%s\n' "garden" "Soil bed, border walls, a fountain in the middle, flowers that actually bloom. Beauty's not waste — Casey taught me that."
    elif echo "$msg" | grep -qwE 'dock|pier|wharf|quay|jetty|boardwalk'; then
        printf '%s\n%s\n' "dock" "Piled into the water, planks laid straight, lanterns at the end. A dock says the adventure's not over — it's just on the water."
    else
        printf '\n'
    fi
}

# =============================================================================
# DEFAULT (no match) RESPONSE
# =============================================================================
default_commands() {
    # A small creative block — a placeholder sculpture
    local px=$1 py=$2 pz=$3
    cat <<EOF
[
  {"type":"create","target":"part","params":{"name":"IdeaBlock","shape":"block","size":{"x":2,"y":2,"z":2},"pos":{"x":$px,"y":$((py+1)),"z":$pz},"color":"#ffcc00","material":"Neon"}},
  {"type":"create","target":"part","params":{"name":"IdeaBase","shape":"cylinder","size":{"x":4,"y":0.5,"z":4},"pos":{"x":$px,"y":$((py+0.25)),"z":$pz},"color":"#555","material":"Concrete"}}
]
EOF
}

default_reply() {
    local player=$1
    cat <<EOF
Not sure what you're after, $player. I've got towers, houses, castles, bridges, trees, walls, roads, lamps, pyramids, domes, arches, platforms, stairs, gardens, docks — name one and I'll build it. Magnus says the scrapyard's got everything if you know what you're looking for.
EOF
}

# =============================================================================
# JOB PROCESSING
# =============================================================================

# Extract player position from job JSON (uses python3 if available, else fallback)
get_player_pos() {
    local json="$1"
    local pos
    
    # Try to extract from playerState.position
    pos=$(echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    p = d.get('playerState', {}).get('position', {})
    x = p.get('x', 0)
    y = p.get('y', 0)
    z = p.get('z', 0)
    print(f'{x} {y} {z}')
except:
    print('0 0 0')
" 2>/dev/null)
    
    if [ -z "$pos" ]; then
        pos="0 0 0"
    fi
    echo "$pos"
}

# Extract a field from JSON string
json_field() {
    local json="$1"
    local field="$2"
    echo "$json" | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    val = d.get('$field', '')
    if isinstance(val, str):
        print(val)
    else:
        print(json.dumps(val))
except:
    print('')
" 2>/dev/null
}

# Process a single job
process_job() {
    local job_json="$1"
    
    local job_id=$(echo "$job_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('id',''))" 2>/dev/null)
    local player_name=$(echo "$job_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('playerName','friend'))" 2>/dev/null)
    local message=$(echo "$job_json" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('message',''))" 2>/dev/null)
    
    if [ -z "$job_id" ]; then
        log "ERROR: Could not parse job ID from: ${job_json:0:200}"
        return 1
    fi
    
    log "Processing job $job_id | Player: $player_name | Message: \"$message\""
    
    # Get player position
    local pos=$(get_player_pos "$job_json")
    local px=$(echo "$pos" | cut -d' ' -f1)
    local py=$(echo "$pos" | cut -d' ' -f2)
    local pz=$(echo "$pos" | cut -d' ' -f3)
    
    # Round to integers for arithmetic
    px=$(printf '%.0f' "$px" 2>/dev/null || echo "0")
    py=$(printf '%.0f' "$py" 2>/dev/null || echo "0")
    pz=$(printf '%.0f' "$pz" 2>/dev/null || echo "0")
    
    log "  Player position: ($px, $py, $pz)"
    
    # Match keyword — line 1: template name, line 2: reply text
    local match_result
    match_result=$(match_keyword "$message")
    local template
    local reply_text
    template=$(echo "$match_result" | sed -n '1p')
    reply_text=$(echo "$match_result" | sed -n '2p')
    
    local commands_json
    
    if [ -n "$template" ]; then
        log "  Matched template: $template"
        case "$template" in
            tower)      commands_json=$(build_tower "$px" "$py" "$pz") ;;
            house)      commands_json=$(build_house "$px" "$py" "$pz") ;;
            castle)     commands_json=$(build_castle "$px" "$py" "$pz") ;;
            tree)       commands_json=$(build_tree "$px" "$py" "$pz") ;;
            bridge)     commands_json=$(build_bridge "$px" "$py" "$pz") ;;
            wall)       commands_json=$(build_wall "$px" "$py" "$pz") ;;
            road)       commands_json=$(build_road "$px" "$py" "$pz") ;;
            lamp)       commands_json=$(build_lamp "$px" "$py" "$pz") ;;
            pyramid)    commands_json=$(build_pyramid "$px" "$py" "$pz") ;;
            dome)       commands_json=$(build_dome "$px" "$py" "$pz") ;;
            arch)       commands_json=$(build_arch "$px" "$py" "$pz") ;;
            platform)   commands_json=$(build_platform "$px" "$py" "$pz") ;;
            staircase)  commands_json=$(build_staircase "$px" "$py" "$pz") ;;
            garden)     commands_json=$(build_garden "$px" "$py" "$pz") ;;
            dock)       commands_json=$(build_dock "$px" "$py" "$pz") ;;
        esac
    else
        log "  No keyword match — using default creative block"
        commands_json=$(default_commands "$px" "$py" "$pz")
        reply_text=$(default_reply "$player_name")
    fi
    
    # Build the result payload using python3 for reliable JSON construction
    local result_payload
    result_payload=$(python3 -c "
import json, sys
reply = '''$reply_text'''
commands = json.loads('''$commands_json''')
payload = {'reply': reply.strip(), 'commands': commands}
print(json.dumps(payload))
" 2>/dev/null)
    
    if [ -z "$result_payload" ]; then
        log "ERROR: Failed to build result payload for job $job_id"
        return 1
    fi
    
    # POST result back to worker
    local post_url="${WORKER_URL}/api/job/${job_id}/result"
    local http_code
    http_code=$(curl -s -o /dev/null -w '%{http_code}' \
        -X POST \
        -H "X-Lucineer-Key: ${AUTH_KEY}" \
        -H "Content-Type: application/json" \
        -d "$result_payload" \
        "$post_url")
    
    if [ "$http_code" = "200" ]; then
        log "  ✓ Job $job_id completed successfully (HTTP $http_code)"
    else
        log "  ✗ Job $job_id failed to post result (HTTP $http_code)"
        log "  Response payload (first 500 chars): ${result_payload:0:500}"
        return 1
    fi
}

# =============================================================================
# MAIN LOOP
# =============================================================================

main() {
    local mode="${1:---once}"
    
    log "=== Lucineer Job Processor starting (mode: $mode) ==="
    
    if [ "$mode" = "--mock" ]; then
        # Create a mock job for testing
        log "Creating mock job for testing..."
        
        local mock_job='{"id":"mock_test_001","sessionId":"test-session","playerName":"Casey","message":"build me a castle","status":"processing","createdAt":'$(date +%s)'000,"playerState":{"position":{"x":10,"y":5,"z":-20}}}'
        
        log "Mock job: $mock_job"
        process_job "$mock_job"
        log "=== Mock test complete ==="
        return 0
    fi
    
    if [ "$mode" = "--loop" ]; then
        log "Entering continuous polling mode (interval: ${POLL_INTERVAL}s)"
        while true; do
            local response
            response=$(curl -s -H "X-Lucineer-Key: ${AUTH_KEY}" "${WORKER_URL}/api/jobs/pending" 2>/dev/null || echo '{"jobs":[]}')
            
            local job_count
            job_count=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('jobs',[])))" 2>/dev/null || echo "0")
            
            if [ "$job_count" -gt 0 ]; then
                log "Found $job_count pending job(s)"
                
                # Process each job
                echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for job in d.get('jobs', []):
    print(json.dumps(job))
" 2>/dev/null | while IFS= read -r job; do
                    process_job "$job" || true
                done
            fi
            
            sleep "$POLL_INTERVAL"
        done
    else
        # Single polling run
        local response
        response=$(curl -s -H "X-Lucineer-Key: ${AUTH_KEY}" "${WORKER_URL}/api/jobs/pending" 2>/dev/null || echo '{"jobs":[]}')
        
        local job_count
        job_count=$(echo "$response" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('jobs',[])))" 2>/dev/null || echo "0")
        
        if [ "$job_count" = "0" ]; then
            log "No pending jobs."
            return 0
        fi
        
        log "Found $job_count pending job(s)"
        
        # Process each job
        echo "$response" | python3 -c "
import sys, json
d = json.load(sys.stdin)
for job in d.get('jobs', []):
    print(json.dumps(job))
" 2>/dev/null | while IFS= read -r job; do
            process_job "$job" || true
        done
        
        log "=== Batch complete ==="
    fi
}

main "$@"
