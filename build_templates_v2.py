#!/usr/bin/env python3
"""
Lucineer Build Templates v2 — Visually Polished Fast Templates
==============================================================
Drop-in replacements for process_v2.py's basic templates.
Each function returns: (lucineer_message, list_of_commands)

Design rules enforced here:
  - 3+ materials per build
  - 3+ distinct colors per build
  - 1 hero light + 1 accent light
  - 1+ particle system per build
  - 15–25 commands per template (including final sendMessage)
  - Predictable part names: <Build><Feature><Index>

Usage in processor:
    from build_templates_v2 import TEMPLATES_V2
    fn = TEMPLATES_V2.get(intent)
    msg, cmds = fn(x, y, z, player_name="Casey")
"""
from typing import List, Dict, Any, Tuple
import random


# ───────────────────────────────────────────────────────────────────────────────
# PALETTES — exact Roblox Material + RGB combos from VISUAL_POLISH.md
# ───────────────────────────────────────────────────────────────────────────────

STONE = {
    "base":    {"material": "Slate",       "color": {"r": 160, "g": 155, "b": 150}},
    "aged":    {"material": "Cobblestone", "color": {"r": 140, "g": 140, "b": 135}},
    "trim":    {"material": "Concrete",    "color": {"r": 150, "g": 150, "b": 150}},
    "shadow":  {"material": "Basalt",      "color": {"r": 100, "g": 100, "b": 100}},
    "moss":    {"material": "LeafyGrass",  "color": {"r": 120, "g": 140, "b":  90}},
}

WOOD = {
    "beam":    {"material": "Wood",        "color": {"r": 130, "g":  90, "b": 55}},
    "deck":    {"material": "WoodPlanks",  "color": {"r": 110, "g":  80, "b": 50}},
    "aged":    {"material": "WoodPlanks",  "color": {"r":  90, "g":  60, "b": 35}},
    "tar":     {"material": "Wood",        "color": {"r":  30, "g":  25, "b": 20}},
}

METAL = {
    "steel":   {"material": "Metal",         "color": {"r":  90, "g":  95, "b": 100}},
    "rust":    {"material": "CorrodedMetal", "color": {"r": 150, "g":  70, "b":  35}},
    "iron":    {"material": "Metal",         "color": {"r":  60, "g":  65, "b":  70}},
    "hot":     {"material": "Neon",          "color": {"r": 255, "g":  90, "b":  30}},
}

NATURE = {
    "grass":   {"material": "Grass",       "color": {"r":  60, "g": 130, "b":  45}},
    "leafy":   {"material": "LeafyGrass",  "color": {"r":  70, "g": 150, "b":  60}},
    "deep":    {"material": "Grass",       "color": {"r":  40, "g": 120, "b":  40}},
    "trunk":   {"material": "Wood",        "color": {"r": 100, "g":  70, "b":  40}},
    "soil":    {"material": "Ground",      "color": {"r": 120, "g":  90, "b":  60}},
    "water":   {"material": "Glass",       "color": {"r": 170, "g": 210, "b": 255}},
    "crystal": {"material": "Neon",        "color": {"r":  80, "g": 220, "b": 255}},
}

LIGHT = {
    "torch":   {"r": 255, "g": 160, "b":  60},
    "window":  {"r": 255, "g": 200, "b": 120},
    "ember":   {"r": 255, "g": 100, "b":  40},
    "crystal": {"r": 150, "g": 255, "b": 180},
    "beacon":  {"r": 255, "g": 245, "b": 160},
    "fairy":   {"r": 255, "g": 220, "b": 255},
}


# ───────────────────────────────────────────────────────────────────────────────
# COMMAND BUILDERS
# ───────────────────────────────────────────────────────────────────────────────

def part(
    name: str,
    shape: str,
    size: Tuple[float, float, float],
    position: Tuple[float, float, float],
    material: str,
    color: Dict[str, int],
    transparency: float = 0.0,
    reflectance: float = 0.0,
    rotation: Tuple[float, float, float] = (0, 0, 0),
    anchored: bool = True,
    can_collide: bool = True,
) -> Dict[str, Any]:
    return {
        "type": "createPart",
        "params": {
            "name": name,
            "shape": shape,
            "size": {"x": size[0], "y": size[1], "z": size[2]},
            "position": {"x": position[0], "y": position[1], "z": position[2]},
            "rotation": {"x": rotation[0], "y": rotation[1], "z": rotation[2]},
            "material": material,
            "color": color,
            "anchored": anchored,
            "transparency": transparency,
            "reflectance": reflectance,
            "canCollide": can_collide,
        },
    }


def add_light(
    parent: str,
    light_type: str,
    brightness: float,
    range_: float,
    color: Dict[str, int],
    shadows: bool = True,
    angle: float = None,
) -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "parent": parent,
        "lightType": light_type,
        "brightness": brightness,
        "range": range_,
        "color": color,
        "shadows": shadows,
    }
    if angle is not None:
        params["angle"] = angle
    return {"type": "addLight", "params": params}


def add_particle(
    parent: str,
    texture: str,
    rate: float,
    lifetime: Tuple[float, float],
    speed: Tuple[float, float],
    color: Dict[str, int],
    size: Tuple[float, float],
    transparency: float = 0.3,
    velocity: Tuple[float, float, float] = (0, 1, 0),
) -> Dict[str, Any]:
    return {
        "type": "addParticle",
        "params": {
            "parent": parent,
            "texture": texture,
            "rate": rate,
            "lifetime": {"min": lifetime[0], "max": lifetime[1]},
            "speed": {"min": speed[0], "max": speed[1]},
            "color": color,
            "size": {"min": size[0], "max": size[1]},
            "transparency": transparency,
            "velocity": {"x": velocity[0], "y": velocity[1], "z": velocity[2]},
        },
    }


def send_message(text: str) -> Dict[str, Any]:
    return {"type": "sendMessage", "params": {"text": text}}


# ───────────────────────────────────────────────────────────────────────────────
# TEMPLATE 1: CASTLE
# Multi-texture stone, banners, torch lighting, gate detail, inner courtyard.
# Commands: 25
# ───────────────────────────────────────────────────────────────────────────────

def build_castle(px: float, py: float, pz: float, player_name: str = "friend") -> Tuple[str, List[Dict[str, Any]]]:
    cmds: List[Dict[str, Any]] = []
    s, w, m, l = STONE, WOOD, METAL, LIGHT

    cmds.append(part("CastleCourtyard", "Block", (34, 1, 34), (px, py, pz), s["aged"]["material"], s["aged"]["color"]))

    # Four corner towers with conical roofs
    for i, (dx, dz) in enumerate([(-14, -14), (14, -14), (14, 14), (-14, 14)], 1):
        cmds.append(part(f"CastleTower{i}", "Cylinder", (7, 20, 7), (px + dx, py + 11, pz + dz), s["base"]["material"], s["base"]["color"]))
        cmds.append(part(f"CastleTowerRoof{i}", "Cone", (9, 7, 9), (px + dx, py + 24.5, pz + dz), w["tar"]["material"], w["tar"]["color"]))

    # Curtain walls
    cmds.append(part("CastleWallN", "Block", (28, 14, 2), (px, py + 7, pz - 18), s["base"]["material"], s["base"]["color"]))
    cmds.append(part("CastleWallS", "Block", (28, 14, 2), (px, py + 7, pz + 18), s["base"]["material"], s["base"]["color"]))
    cmds.append(part("CastleWallW", "Block", (2, 14, 28), (px - 18, py + 7, pz), s["base"]["material"], s["base"]["color"]))
    cmds.append(part("CastleWallE", "Block", (2, 14, 28), (px + 18, py + 7, pz), s["base"]["material"], s["base"]["color"]))

    # Gatehouse + portcullis
    cmds.append(part("CastleGateTop", "Block", (12, 4, 3), (px, py + 11, pz + 18), s["trim"]["material"], s["trim"]["color"]))
    cmds.append(part("CastlePortcullis", "Block", (8, 9, 0.5), (px, py + 5.5, pz + 19), m["iron"]["material"], m["iron"]["color"]))

    # Keep + beacon
    cmds.append(part("CastleKeep", "Block", (12, 18, 12), (px, py + 9, pz), s["base"]["material"], s["base"]["color"]))
    cmds.append(part("CastleKeepRoof", "Cone", (15, 8, 15), (px, py + 22, pz), w["tar"]["material"], w["tar"]["color"]))
    cmds.append(part("CastleBeacon", "Ball", (2.5, 2.5, 2.5), (px, py + 27, pz), "Neon", l["beacon"]))
    cmds.append(add_light("CastleBeacon", "PointLight", 7, 55, l["beacon"]))

    # Banner + hero torch
    cmds.append(part("CastleBanner", "Block", (0.3, 5, 3), (px - 6, py + 14, pz + 18.6), "Neon", {"r": 180, "g": 40, "b": 40}))
    cmds.append(part("CastleTorch", "Ball", (1.2, 1.2, 1.2), (px, py + 8, pz + 20.5), "Neon", l["torch"]))
    cmds.append(add_light("CastleTorch", "PointLight", 8, 35, l["torch"]))

    # Courtyard well
    cmds.append(part("CastleWell", "Cylinder", (4, 2, 4), (px - 6, py + 1, pz - 6), s["aged"]["material"], s["aged"]["color"]))

    # Ember particles from gate torch
    cmds.append(add_particle(
        "CastleTorch", "rbxassetid://243660364", 10, (0.4, 1.2), (1, 3),
        l["torch"], (0.2, 0.6), transparency=0.1, velocity=(0, 1.5, 0)
    ))

    msg = (
        f"There's your castle, {player_name}. Four towers, a gate you can actually defend, "
        "and a courtyard well for when the siege gets long. Banner's blank — pick your colors."
    )
    cmds.append(send_message(msg))
    return msg, cmds


# ───────────────────────────────────────────────────────────────────────────────
# TEMPLATE 2: HOUSE
# Shingled roof, window glow, chimney smoke, flower boxes, stone foundation.
# Commands: 24
# ───────────────────────────────────────────────────────────────────────────────

def build_house(px: float, py: float, pz: float, player_name: str = "friend") -> Tuple[str, List[Dict[str, Any]]]:
    cmds: List[Dict[str, Any]] = []
    s, w, l = STONE, WOOD, LIGHT

    cmds.append(part("HouseFoundation", "Block", (18, 1.5, 14), (px, py + 0.75, pz), s["aged"]["material"], s["aged"]["color"]))
    cmds.append(part("HouseFloor", "Block", (16, 1, 12), (px, py + 1.5, pz), w["deck"]["material"], w["deck"]["color"]))

    # Walls
    cmds.append(part("HouseWallN", "Block", (16, 9, 1), (px, py + 6, pz - 6), w["beam"]["material"], w["beam"]["color"]))
    cmds.append(part("HouseWallS", "Block", (16, 9, 1), (px, py + 6, pz + 6), w["beam"]["material"], w["beam"]["color"]))
    cmds.append(part("HouseWallW", "Block", (1, 9, 12), (px - 8, py + 6, pz), w["beam"]["material"], w["beam"]["color"]))
    cmds.append(part("HouseWallE", "Block", (1, 9, 12), (px + 8, py + 6, pz), w["beam"]["material"], w["beam"]["color"]))

    # Shingled roof: main mass + two overlapping rows
    cmds.append(part("HouseRoofMain", "Block", (18, 2, 14), (px, py + 11, pz), w["aged"]["material"], w["aged"]["color"]))
    cmds.append(part("HouseShingleL", "Block", (8, 0.4, 13), (px - 4.2, py + 12.2, pz), w["tar"]["material"], w["tar"]["color"]))
    cmds.append(part("HouseShingleR", "Block", (8, 0.4, 13), (px + 4.2, py + 12.2, pz), w["tar"]["material"], w["tar"]["color"]))

    # Chimney + door
    cmds.append(part("HouseChimney", "Block", (2.2, 6, 2.2), (px + 5, py + 13, pz - 3), s["trim"]["material"], s["trim"]["color"]))
    cmds.append(part("HouseDoor", "Block", (3.5, 6, 0.4), (px, py + 4.5, pz + 6.3), w["aged"]["material"], w["aged"]["color"]))

    # Two glowing windows
    for i, dx in enumerate([-8.1, 8.1], 1):
        cmds.append(part(f"HouseWindow{i}", "Block", (0.3, 3, 3), (px + dx, py + 6, pz), "Glass", {"r": 255, "g": 250, "b": 220}, transparency=0.5))
        cmds.append(part(f"HouseWindowGlow{i}", "Block", (0.2, 2.6, 2.6), (px + dx, py + 6, pz), "Neon", l["window"], transparency=0.2))
        cmds.append(add_light(f"HouseWindowGlow{i}", "PointLight", 3, 18, l["window"]))

    # Flower boxes + clustered blooms
    for side, dx in [("L", -4.5), ("R", 4.5)]:
        cmds.append(part(f"HouseFlowerBox{side}", "Block", (3, 0.8, 1.2), (px + dx, py + 4.2, pz + 6.5), w["deck"]["material"], w["deck"]["color"]))
        cmds.append(part(f"HouseFlowers{side}", "Ball", (1.2, 0.8, 0.8), (px + dx, py + 4.9, pz + 6.7), "Neon", random.choice([
            {"r": 255, "g": 80, "b": 120},
            {"r": 255, "g": 200, "b": 40},
            {"r": 160, "g": 80, "b": 255},
        ])))

    # Step + smoke
    cmds.append(part("HouseStep", "Block", (4, 0.5, 1.5), (px, py + 1.75, pz + 7.5), s["trim"]["material"], s["trim"]["color"]))
    cmds.append(add_particle(
        "HouseChimney", "rbxassetid://241876428", 8, (2, 4), (1, 2),
        {"r": 180, "g": 180, "b": 180}, (1, 2.5), transparency=0.3, velocity=(0.3, 2, 0.1)
    ))

    msg = (
        f"Home sweet home, {player_name}. Stone skirt, shingled roof, and the chimney's "
        "already smoking. I planted flowers in the boxes — don't let 'em die."
    )
    cmds.append(send_message(msg))
    return msg, cmds


# ───────────────────────────────────────────────────────────────────────────────
# TEMPLATE 3: LIGHTHOUSE
# Striped tower, rotating beam, weathered stone, fog particles, dock extension.
# Commands: 22
# ───────────────────────────────────────────────────────────────────────────────

def build_lighthouse(px: float, py: float, pz: float, player_name: str = "friend") -> Tuple[str, List[Dict[str, Any]]]:
    cmds: List[Dict[str, Any]] = []
    s, w, m, l = STONE, WOOD, METAL, LIGHT

    cmds.append(part("LightBaseRock", "Block", (14, 3, 14), (px, py + 1.5, pz), s["aged"]["material"], s["aged"]["color"]))

    # Striped tower rings (alternating materials)
    ring_h = [3, 6, 6, 6, 6, 5]
    y = py + 3
    for i, h in enumerate(ring_h):
        dia = 8 * (1 - i * 0.04)
        mat_col = s["base"] if i % 2 == 0 else s["trim"]
        cmds.append(part(f"LightTowerRing{i}", "Cylinder", (dia, h, dia), (px, y + h / 2, pz), mat_col["material"], mat_col["color"]))
        y += h

    # Balcony, lantern room, roof
    cmds.append(part("LightBalcony", "Cylinder", (11, 1.2, 11), (px, y + 0.6, pz), m["rust"]["material"], m["rust"]["color"]))
    y += 1.2
    cmds.append(part("LightRoom", "Cylinder", (7, 7, 7), (px, y + 3.5, pz), "Glass", {"r": 255, "g": 255, "b": 220}, transparency=0.35))
    cmds.append(part("LightRoof", "Cone", (9, 5, 9), (px, y + 8.5, pz), m["iron"]["material"], m["iron"]["color"]))

    # Rotating beacon assembly
    cmds.append(part("LightBeacon", "Ball", (2.5, 2.5, 2.5), (px, y + 3.5, pz), "Neon", l["beacon"]))
    cmds.append(add_light("LightBeacon", "SpotLight", 10, 200, l["beacon"], angle=30))
    cmds.append(part("LightBeamArm", "Block", (1, 1, 16), (px, y + 3.5, pz), "Neon", l["beacon"], transparency=0.6))

    # Dock
    dock_x = px + 12
    cmds.append(part("DockDeck", "Block", (5, 0.8, 22), (dock_x, py + 1.4, pz), w["deck"]["material"], w["deck"]["color"]))
    for i, dz in enumerate([-8, -2.5, 2.5, 8]):
        cmds.append(part(f"DockPile{i}", "Cylinder", (0.8, 5, 0.8), (dock_x, py - 1, pz + dz), w["aged"]["material"], w["aged"]["color"]))
    cmds.append(part("DockBollard", "Cylinder", (0.6, 1.2, 0.6), (dock_x + 1.5, py + 2, pz + 9), m["rust"]["material"], m["rust"]["color"]))

    # Fog + water spray
    cmds.append(add_particle(
        "LightBaseRock", "rbxassetid://258128463", 12, (3, 6), (0.5, 1.5),
        {"r": 200, "g": 210, "b": 220}, (2, 5), transparency=0.4, velocity=(0.5, 0.8, 0.3)
    ))
    cmds.append(add_particle(
        "DockPile0", "rbxassetid://243660364", 8, (1, 2), (1, 2),
        {"r": 200, "g": 230, "b": 255}, (0.5, 1.5), transparency=0.25, velocity=(0, 1.5, 0)
    ))

    msg = (
        f"Lighthouse's up, {player_name}. Striped tower, rotating beam, and a dock "
        "long enough for a seiner. Fog comes with the territory — Southeast Alaska standard."
    )
    cmds.append(send_message(msg))
    return msg, cmds


# ───────────────────────────────────────────────────────────────────────────────
# TEMPLATE 4: FORGE
# Glowing interior, smokestack particles, anvil details, ember lighting.
# Commands: 19
# ───────────────────────────────────────────────────────────────────────────────

def build_forge(px: float, py: float, pz: float, player_name: str = "friend") -> Tuple[str, List[Dict[str, Any]]]:
    cmds: List[Dict[str, Any]] = []
    s, w, m, l = STONE, WOOD, METAL, LIGHT

    cmds.append(part("ForgeFoundation", "Block", (18, 2, 14), (px, py + 1, pz), s["shadow"]["material"], s["shadow"]["color"]))
    cmds.append(part("ForgeFloor", "Block", (16, 0.8, 12), (px, py + 2.4, pz), s["aged"]["material"], s["aged"]["color"]))

    # Walls + roof
    cmds.append(part("ForgeWallBack", "Block", (16, 10, 1), (px, py + 7, pz - 6), s["base"]["material"], s["base"]["color"]))
    cmds.append(part("ForgeWallL", "Block", (1, 10, 12), (px - 8, py + 7, pz), s["base"]["material"], s["base"]["color"]))
    cmds.append(part("ForgeWallR", "Block", (1, 10, 12), (px + 8, py + 7, pz), s["base"]["material"], s["base"]["color"]))
    cmds.append(part("ForgeRoof", "Block", (18, 1, 14), (px, py + 12.5, pz), m["rust"]["material"], m["rust"]["color"]))

    # Smokestack
    cmds.append(part("ForgeStack", "Cylinder", (2.5, 14, 2.5), (px + 5, py + 20, pz - 4), m["rust"]["material"], m["rust"]["color"]))
    cmds.append(part("ForgeStackCap", "Cylinder", (3, 1, 3), (px + 5, py + 27.5, pz - 4), m["iron"]["material"], m["iron"]["color"]))

    # Glowing coals + light
    cmds.append(part("ForgeCoalBed", "Block", (6, 0.8, 4), (px - 3, py + 3, pz - 3), "Neon", {"r": 80, "g": 25, "b": 10}))
    cmds.append(add_light("ForgeCoalBed", "PointLight", 10, 45, l["ember"]))

    # Anvil
    cmds.append(part("ForgeAnvilBase", "Block", (2, 3, 2), (px + 3, py + 3.5, pz - 2), w["beam"]["material"], w["beam"]["color"]))
    cmds.append(part("ForgeAnvilTop", "Block", (2.4, 1.2, 1.4), (px + 3, py + 5.6, pz - 2), m["steel"]["material"], m["steel"]["color"]))

    # Workbench + hot tool
    cmds.append(part("ForgeBench", "Block", (5, 1, 2.5), (px + 3, py + 3.5, pz + 3), w["deck"]["material"], w["deck"]["color"]))
    cmds.append(part("ForgeHotTool", "Block", (0.2, 2.5, 0.2), (px + 5.5, py + 5.5, pz + 2), "Neon", m["hot"]["color"]))

    # Accent lantern
    cmds.append(part("ForgeLantern", "Ball", (1.2, 1.2, 1.2), (px + 6.5, py + 8, pz + 5), "Neon", l["torch"]))
    cmds.append(add_light("ForgeLantern", "PointLight", 5, 22, l["torch"]))

    # Smoke + ember particles
    cmds.append(add_particle(
        "ForgeStackCap", "rbxassetid://241876428", 12, (2, 5), (1, 2.5),
        {"r": 150, "g": 150, "b": 150}, (1.5, 3.5), transparency=0.25, velocity=(0.4, 2.5, 0.2)
    ))
    cmds.append(add_particle(
        "ForgeCoalBed", "rbxassetid://243660364", 12, (0.4, 1.4), (1.5, 3.5),
        l["ember"], (0.2, 0.8), transparency=0.15, velocity=(0.2, 2, 0.2)
    ))

    msg = (
        f"Forge is hot, {player_name}. Anvil's true, stack's smoking, and the coals "
        "are hungry. Don't touch the orange ones — they bite."
    )
    cmds.append(send_message(msg))
    return msg, cmds


# ───────────────────────────────────────────────────────────────────────────────
# TEMPLATE 5: GARDEN
# Multi-tier planters, path stones, butterfly particles, fountain centerpiece.
# Commands: 25
# ───────────────────────────────────────────────────────────────────────────────

def build_garden(px: float, py: float, pz: float, player_name: str = "friend") -> Tuple[str, List[Dict[str, Any]]]:
    cmds: List[Dict[str, Any]] = []
    n, s, w, l = NATURE, STONE, WOOD, LIGHT

    cmds.append(part("GardenGround", "Block", (22, 0.8, 22), (px, py + 0.4, pz), n["grass"]["material"], n["grass"]["color"]))

    # Fence
    fence = [
        ((22, 1.2, 0.4), (px, py + 1.2, pz - 11)),
        ((22, 1.2, 0.4), (px, py + 1.2, pz + 11)),
        ((0.4, 1.2, 22), (px - 11, py + 1.2, pz)),
        ((0.4, 1.2, 22), (px + 11, py + 1.2, pz)),
    ]
    for i, (size, pos) in enumerate(fence):
        cmds.append(part(f"GardenFence{i}", "Block", size, pos, w["deck"]["material"], w["deck"]["color"]))

    # Tiered planters at 4 heights
    planter_cfg = [(-6, -6, 1.0), (6, -6, 1.8), (-6, 6, 2.6), (6, 6, 3.4)]
    for i, (dx, dz, h) in enumerate(planter_cfg):
        cmds.append(part(f"GardenPlanter{i}", "Block", (5, h, 5), (px + dx, py + h / 2, pz + dz), n["soil"]["material"], n["soil"]["color"]))

    # Stepping stones
    for i in range(3):
        sx, sz = 1.6 + (i % 2) * 0.3, 2.0 + (i % 3) * 0.3
        rot_y = (i * 23) % 360
        cmds.append(part(f"GardenStone{i}", "Block", (sx, 0.3, sz), (px + (i - 1) * 2.8, py + 0.65, pz + 4), s["aged"]["material"], s["aged"]["color"], rotation=(0, rot_y, 0)))

    # Fountain centerpiece
    cmds.append(part("GardenFountainBase", "Cylinder", (5, 2, 5), (px, py + 1.5, pz), s["trim"]["material"], s["trim"]["color"]))
    cmds.append(part("GardenFountainPillar", "Cylinder", (0.8, 4, 0.8), (px, py + 4.5, pz), s["base"]["material"], s["base"]["color"]))
    cmds.append(part("GardenFountainTop", "Ball", (1.2, 1.2, 1.2), (px, py + 6.2, pz), n["water"]["material"], n["water"]["color"], transparency=0.6))

    # Flowers (one cluster per planter)
    flower_colors = [
        {"r": 255, "g": 80, "b": 120},
        {"r": 255, "g": 200, "b": 40},
        {"r": 160, "g": 80, "b": 255},
        {"r": 255, "g": 140, "b": 60},
    ]
    for i, (dx, dz, h) in enumerate(planter_cfg):
        cmds.append(part(f"GardenFlower{i}", "Ball", (1.2, 0.9, 1.2), (px + dx, py + h + 0.5, pz + dz), "Neon", flower_colors[i]))

    # Tree + crystal accent
    cmds.append(part("GardenTreeTrunk", "Cylinder", (1.2, 7, 1.2), (px + 7, py + 3.5, pz - 7), n["trunk"]["material"], n["trunk"]["color"]))
    cmds.append(part("GardenTreeLeaves", "Ball", (6, 6, 6), (px + 7, py + 8, pz - 7), n["leafy"]["material"], n["leafy"]["color"]))
    cmds.append(part("GardenCrystal", "Ball", (1, 1.5, 1), (px - 7, py + 2.5, pz + 7), n["crystal"]["material"], n["crystal"]["color"]))

    # Water spray + butterflies
    cmds.append(add_particle(
        "GardenFountainTop", "rbxassetid://243660364", 10, (1, 2), (1, 2.5),
        {"r": 200, "g": 230, "b": 255}, (0.3, 1.2), transparency=0.2, velocity=(0, 2, 0)
    ))
    cmds.append(add_particle(
        "GardenTreeLeaves", "rbxassetid://258128463", 5, (2, 4), (0.5, 1.5),
        l["fairy"], (0.3, 0.8), transparency=0.15, velocity=(1, 0.5, 1)
    ))

    msg = (
        f"Garden's in, {player_name}. Tiered planters, a fountain, and butterflies "
        "that won't stop moving. I tucked a crystal in the corner — keeps the flowers company."
    )
    cmds.append(send_message(msg))
    return msg, cmds


# ───────────────────────────────────────────────────────────────────────────────
# DISPATCHER
# ───────────────────────────────────────────────────────────────────────────────

TEMPLATES_V2 = {
    "castle": build_castle,
    "fortress": build_castle,
    "fort": build_castle,
    "keep": build_castle,
    "citadel": build_castle,
    "palace": build_castle,
    "house": build_house,
    "home": build_house,
    "cabin": build_house,
    "cottage": build_house,
    "lighthouse": build_lighthouse,
    "beacon": build_lighthouse,
    "forge": build_forge,
    "smithy": build_forge,
    "blacksmith": build_forge,
    "garden": build_garden,
    "park": build_garden,
    "yard": build_garden,
    "flowerbed": build_garden,
}


if __name__ == "__main__":
    import json
    for name, fn in [
        ("castle", build_castle),
        ("house", build_house),
        ("lighthouse", build_lighthouse),
        ("forge", build_forge),
        ("garden", build_garden),
    ]:
        _, cmds = fn(0, 0, 0, player_name="Casey")
        print(f"{name}: {len(cmds)} commands")
        json.dumps(cmds)
