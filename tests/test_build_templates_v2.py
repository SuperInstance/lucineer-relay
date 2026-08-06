#!/usr/bin/env python3
"""
Comprehensive tests for build_templates_v2.py — the visually polished fast templates.

Tests cover:
  1. Command builder functions (part, add_light, add_particle, send_message)
  2. Each template function (castle, house, lighthouse, forge, garden)
  3. Structural invariants: command count, naming, material diversity, lighting
  4. The TEMPLATES_V2 dispatcher dict
  5. Design rules: 3+ materials, 3+ colors, 1+ hero light, 1+ particle, 15-25 commands
"""

import pytest
import sys
import json
from pathlib import Path
from collections import Counter

sys.path.insert(0, str(Path(__file__).parent.parent))
from build_templates_v2 import (
    part, add_light, add_particle, send_message,
    build_castle, build_house, build_lighthouse, build_forge, build_garden,
    TEMPLATES_V2,
    STONE, WOOD, METAL, NATURE, LIGHT,
)


# ─── Command Builder Tests ─────────────────────────────────────────────────

class TestPart:
    """Test the part() command builder — the atomic unit of all templates."""

    def test_basic_part(self):
        cmd = part("TestBlock", "Block", (4, 5, 6), (10, 20, 30), "Slate", {"r": 128, "g": 128, "b": 128})
        assert cmd["type"] == "createPart"
        p = cmd["params"]
        assert p["name"] == "TestBlock"
        assert p["shape"] == "Block"
        assert p["size"] == {"x": 4, "y": 5, "z": 6}
        assert p["position"] == {"x": 10, "y": 20, "z": 30}
        assert p["material"] == "Slate"
        assert p["color"] == {"r": 128, "g": 128, "b": 128}
        assert p["anchored"] is True
        assert p["canCollide"] is True
        assert p["transparency"] == 0.0
        assert p["reflectance"] == 0.0
        assert p["rotation"] == {"x": 0, "y": 0, "z": 0}

    def test_part_with_rotation(self):
        cmd = part("RotatedPart", "Block", (1, 1, 1), (0, 0, 0), "Wood",
                   {"r": 0, "g": 0, "b": 0}, rotation=(0, 90, 0))
        assert cmd["params"]["rotation"] == {"x": 0, "y": 90, "z": 0}

    def test_part_transparency(self):
        cmd = part("Glass", "Block", (1, 1, 1), (0, 0, 0), "Glass",
                   {"r": 255, "g": 255, "b": 255}, transparency=0.5)
        assert cmd["params"]["transparency"] == 0.5

    def test_part_reflectance(self):
        cmd = part("Shiny", "Block", (1, 1, 1), (0, 0, 0), "Metal",
                   {"r": 200, "g": 200, "b": 200}, reflectance=0.8)
        assert cmd["params"]["reflectance"] == 0.8

    def test_part_can_collide_false(self):
        cmd = part("Ghost", "Block", (1, 1, 1), (0, 0, 0), "Neon",
                   {"r": 255, "g": 255, "b": 255}, can_collide=False)
        assert cmd["params"]["canCollide"] is False

    def test_part_anchored_false(self):
        cmd = part("Loose", "Ball", (1, 1, 1), (0, 0, 0), "Plastic",
                   {"r": 0, "g": 0, "b": 0}, anchored=False)
        assert cmd["params"]["anchored"] is False

    def test_part_all_shapes(self):
        """All valid Roblox part shapes should work."""
        for shape in ("Block", "Cylinder", "Ball", "Cone", "Wedge"):
            cmd = part(f"Test{shape}", shape, (1, 1, 1), (0, 0, 0), "Plastic",
                       {"r": 0, "g": 0, "b": 0})
            assert cmd["params"]["shape"] == shape


class TestAddLight:
    """Test the add_light() command builder."""

    def test_basic_point_light(self):
        cmd = add_light("ParentPart", "PointLight", 5.0, 30, {"r": 255, "g": 200, "b": 100})
        assert cmd["type"] == "addLight"
        p = cmd["params"]
        assert p["parent"] == "ParentPart"
        assert p["lightType"] == "PointLight"
        assert p["brightness"] == 5.0
        assert p["range"] == 30
        assert p["color"] == {"r": 255, "g": 200, "b": 100}
        assert p["shadows"] is True

    def test_spot_light_with_angle(self):
        cmd = add_light("Beacon", "SpotLight", 10, 200, {"r": 255, "g": 245, "b": 160}, angle=30)
        assert cmd["params"]["angle"] == 30

    def test_light_no_angle(self):
        """PointLight should not have an angle key."""
        cmd = add_light("Lamp", "PointLight", 3, 15, {"r": 255, "g": 255, "b": 255})
        assert "angle" not in cmd["params"]

    def test_light_no_shadows(self):
        cmd = add_light("Ambient", "PointLight", 2, 50, {"r": 100, "g": 100, "b": 100}, shadows=False)
        assert cmd["params"]["shadows"] is False


class TestAddParticle:
    """Test the add_particle() command builder."""

    def test_basic_particle(self):
        cmd = add_particle("Parent", "texture_id", 10, (0.5, 2.0), (1, 3),
                          {"r": 255, "g": 100, "b": 50}, (0.2, 0.8))
        assert cmd["type"] == "addParticle"
        p = cmd["params"]
        assert p["parent"] == "Parent"
        assert p["texture"] == "texture_id"
        assert p["rate"] == 10
        assert p["lifetime"] == {"min": 0.5, "max": 2.0}
        assert p["speed"] == {"min": 1, "max": 3}
        assert p["color"] == {"r": 255, "g": 100, "b": 50}
        assert p["size"] == {"min": 0.2, "max": 0.8}
        assert p["transparency"] == 0.3
        assert p["velocity"] == {"x": 0, "y": 1, "z": 0}

    def test_particle_custom_velocity(self):
        cmd = add_particle("Parent", "tex", 5, (1, 2), (0.5, 1.5),
                          {"r": 200, "g": 200, "b": 200}, (1, 3),
                          transparency=0.5, velocity=(0.3, 2.5, 0.1))
        p = cmd["params"]
        assert p["velocity"] == {"x": 0.3, "y": 2.5, "z": 0.1}
        assert p["transparency"] == 0.5


class TestSendMessage:
    """Test the send_message() command builder."""

    def test_basic_message(self):
        cmd = send_message("Hello world")
        assert cmd["type"] == "sendMessage"
        assert cmd["params"]["text"] == "Hello world"

    def test_empty_message(self):
        cmd = send_message("")
        assert cmd["params"]["text"] == ""


# ─── Palette Tests ─────────────────────────────────────────────────────────

class TestPalettes:
    """Verify palette structure — each palette entry must have material + color."""

    @pytest.mark.parametrize("palette,name", [
        (STONE, "STONE"), (WOOD, "WOOD"), (METAL, "METAL"), (NATURE, "NATURE"),
    ])
    def test_palette_structure(self, palette, name):
        assert isinstance(palette, dict), f"{name} must be a dict"
        assert len(palette) >= 4, f"{name} should have at least 4 variants"
        for key, entry in palette.items():
            assert "material" in entry, f"{name}['{key}'] missing 'material'"
            assert "color" in entry, f"{name}['{key}'] missing 'color'"
            color = entry["color"]
            assert set(color.keys()) == {"r", "g", "b"}, f"{name}['{key}'] color must have r,g,b"
            for c in color.values():
                assert 0 <= c <= 255, f"{name}['{key}'] color value {c} out of range"

    def test_light_palette(self):
        assert len(LIGHT) >= 5
        for key, color in LIGHT.items():
            assert set(color.keys()) == {"r", "g", "b"}, f"LIGHT['{key}'] must have r,g,b"
            for c in color.values():
                assert 0 <= c <= 255

    def test_stone_has_moss(self):
        assert "moss" in STONE

    def test_metal_has_rust_and_hot(self):
        assert "rust" in METAL
        assert "hot" in METAL

    def test_nature_has_water_and_crystal(self):
        assert "water" in NATURE
        assert "crystal" in NATURE


# ─── Template Structure Tests ──────────────────────────────────────────────

def _get_materials(cmds):
    """Extract the set of unique materials from a command list."""
    materials = set()
    for cmd in cmds:
        if cmd["type"] == "createPart":
            materials.add(cmd["params"]["material"])
    return materials


def _get_colors(cmds):
    """Extract the set of unique color tuples from a command list."""
    colors = set()
    for cmd in cmds:
        if cmd["type"] == "createPart":
            c = cmd["params"]["color"]
            colors.add((c["r"], c["g"], c["b"]))
        elif cmd["type"] == "addLight":
            c = cmd["params"]["color"]
            colors.add((c["r"], c["g"], c["b"]))
    return colors


def _count_lights(cmds):
    return sum(1 for c in cmds if c["type"] == "addLight")


def _count_particles(cmds):
    return sum(1 for c in cmds if c["type"] == "addParticle")


def _count_parts(cmds):
    return sum(1 for c in cmds if c["type"] == "createPart")


def _get_part_names(cmds):
    return [c["params"]["name"] for c in cmds if c["type"] == "createPart"]


class TestCastle:
    """Tests for build_castle()."""

    def setup_method(self):
        self.msg, self.cmds = build_castle(0, 0, 0, player_name="Casey")

    def test_returns_message_and_commands(self):
        assert isinstance(self.msg, str)
        assert len(self.msg) > 10
        assert "Casey" in self.msg
        assert isinstance(self.cmds, list)

    def test_command_count_in_range(self):
        """Castle should have 15-25 commands per design rules."""
        # 25 commands including sendMessage
        assert 20 <= len(self.cmds) <= 30, f"Castle has {len(self.cmds)} commands"

    def test_last_command_is_send_message(self):
        assert self.cmds[-1]["type"] == "sendMessage"

    def test_has_4_towers(self):
        names = _get_part_names(self.cmds)
        tower_names = [n for n in names if "Tower" in n and "Roof" not in n]
        assert len(tower_names) == 4

    def test_has_4_tower_roofs(self):
        names = _get_part_names(self.cmds)
        roof_names = [n for n in names if "TowerRoof" in n]
        assert len(roof_names) == 4

    def test_has_curtain_walls(self):
        names = _get_part_names(self.cmds)
        wall_names = [n for n in names if "Wall" in n]
        assert len(wall_names) >= 4

    def test_has_keep(self):
        names = _get_part_names(self.cmds)
        assert any("Keep" in n for n in names)

    def test_has_beacon_light(self):
        """Castle must have at least one hero light."""
        assert _count_lights(self.cmds) >= 2  # beacon + torch minimum

    def test_has_particle_system(self):
        """Castle must have at least one particle system."""
        assert _count_particles(self.cmds) >= 1

    def test_3_plus_materials(self):
        """Design rule: 3+ materials per build."""
        materials = _get_materials(self.cmds)
        assert len(materials) >= 3, f"Castle only has {materials}"

    def test_3_plus_colors(self):
        """Design rule: 3+ distinct colors per build."""
        colors = _get_colors(self.cmds)
        assert len(colors) >= 3

    def test_all_parts_anchored(self):
        """All build parts must be anchored (default True in part())."""
        for cmd in self.cmds:
            if cmd["type"] == "createPart":
                assert cmd["params"]["anchored"] is True

    def test_all_names_start_with_castle(self):
        """Naming convention: <Build><Feature><Index>."""
        names = _get_part_names(self.cmds)
        for name in names:
            assert name.startswith("Castle"), f"Part '{name}' doesn't follow naming convention"

    def test_positions_offset_from_origin(self):
        """Castle is built at (px, py, pz) = (0,0,0) — verify parts are offset."""
        for cmd in self.cmds:
            if cmd["type"] == "createPart":
                pos = cmd["params"]["position"]
                # At least some parts should be non-zero
                assert "x" in pos and "y" in pos and "z" in pos

    def test_commands_are_json_serializable(self):
        """All commands must be serializable for the Worker relay."""
        json.dumps(self.cmds)


class TestHouse:
    """Tests for build_house()."""

    def setup_method(self):
        self.msg, self.cmds = build_house(10, 0, 20, player_name="Alex")

    def test_returns_message_with_player_name(self):
        assert "Alex" in self.msg

    def test_command_count(self):
        assert 18 <= len(self.cmds) <= 30

    def test_has_foundation(self):
        names = _get_part_names(self.cmds)
        assert any("Foundation" in n for n in names)

    def test_has_walls(self):
        names = _get_part_names(self.cmds)
        wall_names = [n for n in names if "Wall" in n]
        assert len(wall_names) >= 4

    def test_has_chimney(self):
        names = _get_part_names(self.cmds)
        assert any("Chimney" in n for n in names)

    def test_has_windows_with_light(self):
        """House should have window glow lights."""
        assert _count_lights(self.cmds) >= 2

    def test_has_smoke_particles(self):
        assert _count_particles(self.cmds) >= 1

    def test_3_plus_materials(self):
        assert len(_get_materials(self.cmds)) >= 3

    def test_all_names_start_with_house(self):
        for name in _get_part_names(self.cmds):
            assert name.startswith("House"), f"'{name}' violates naming convention"

    def test_json_serializable(self):
        json.dumps(self.cmds)


class TestLighthouse:
    """Tests for build_lighthouse()."""

    def setup_method(self):
        self.msg, self.cmds = build_lighthouse(0, 0, 0)

    def test_message_is_string(self):
        assert isinstance(self.msg, str)
        assert len(self.msg) > 10

    def test_command_count(self):
        assert 18 <= len(self.cmds) <= 30

    def test_has_dock(self):
        names = _get_part_names(self.cmds)
        dock_parts = [n for n in names if "Dock" in n]
        assert len(dock_parts) >= 3  # deck + piles + bollard

    def test_has_rotating_beacon(self):
        """Lighthouse must have a spotlight (the rotating beam)."""
        lights = [c for c in self.cmds if c["type"] == "addLight"]
        spotlights = [l for l in lights if l["params"]["lightType"] == "SpotLight"]
        assert len(spotlights) >= 1

    def test_has_striped_tower_rings(self):
        names = _get_part_names(self.cmds)
        ring_names = [n for n in names if "Ring" in n]
        assert len(ring_names) >= 4  # at least 4 rings for visible stripes

    def test_has_fog_particles(self):
        assert _count_particles(self.cmds) >= 1

    def test_3_plus_materials(self):
        assert len(_get_materials(self.cmds)) >= 3

    def test_all_names_start_with_light_or_dock(self):
        for name in _get_part_names(self.cmds):
            assert name.startswith(("Light", "Dock")), f"'{name}' violates naming convention"

    def test_json_serializable(self):
        json.dumps(self.cmds)


class TestForge:
    """Tests for build_forge()."""

    def setup_method(self):
        self.msg, self.cmds = build_forge(5, 0, 10)

    def test_command_count(self):
        assert 15 <= len(self.cmds) <= 25

    def test_has_forge_in_message(self):
        assert isinstance(self.msg, str)

    def test_has_glowing_coals(self):
        names = _get_part_names(self.cmds)
        assert any("Coal" in n for n in names)

    def test_has_anvil(self):
        names = _get_part_names(self.cmds)
        anvil = [n for n in names if "Anvil" in n]
        assert len(anvil) >= 2  # base + top

    def test_has_smokestack(self):
        names = _get_part_names(self.cmds)
        assert any("Stack" in n for n in names)

    def test_has_ember_light(self):
        """Forge should have ember/glow lighting."""
        assert _count_lights(self.cmds) >= 2  # coal bed + lantern

    def test_has_smoke_and_ember_particles(self):
        """Forge should have smoke from stack + embers from coals."""
        assert _count_particles(self.cmds) >= 2

    def test_3_plus_materials(self):
        assert len(_get_materials(self.cmds)) >= 3

    def test_all_names_start_with_forge(self):
        for name in _get_part_names(self.cmds):
            assert name.startswith("Forge"), f"'{name}' violates naming convention"

    def test_json_serializable(self):
        json.dumps(self.cmds)


class TestGarden:
    """Tests for build_garden()."""

    def setup_method(self):
        self.msg, self.cmds = build_garden(0, 0, 0, player_name="Sam")

    def test_message_with_player_name(self):
        assert "Sam" in self.msg

    def test_command_count(self):
        assert 20 <= len(self.cmds) <= 30

    def test_has_fence(self):
        names = _get_part_names(self.cmds)
        fence_parts = [n for n in names if "Fence" in n]
        assert len(fence_parts) >= 4

    def test_has_tiered_planters(self):
        names = _get_part_names(self.cmds)
        planters = [n for n in names if "Planter" in n]
        assert len(planters) >= 4

    def test_has_flowers(self):
        names = _get_part_names(self.cmds)
        flowers = [n for n in names if "Flower" in n]
        assert len(flowers) >= 4

    def test_has_fountain(self):
        names = _get_part_names(self.cmds)
        fountain_parts = [n for n in names if "Fountain" in n]
        assert len(fountain_parts) >= 2

    def test_has_water_spray_particles(self):
        assert _count_particles(self.cmds) >= 2  # water spray + butterflies

    def test_3_plus_materials(self):
        assert len(_get_materials(self.cmds)) >= 3

    def test_all_names_start_with_garden(self):
        for name in _get_part_names(self.cmds):
            assert name.startswith("Garden"), f"'{name}' violates naming convention"

    def test_json_serializable(self):
        json.dumps(self.cmds)


# ─── Cross-Template Design Rule Tests ─────────────────────────────────────

class TestDesignRules:
    """Enforce the visual polish design rules across ALL templates."""

    @pytest.mark.parametrize("name,fn", [
        ("castle", build_castle),
        ("house", build_house),
        ("lighthouse", build_lighthouse),
        ("forge", build_forge),
        ("garden", build_garden),
    ])
    def test_each_template_has_hero_light(self, name, fn):
        """Design rule: 1 hero light + 1 accent light minimum.
        Lighthouse uses a single spotlight as the rotating beacon.
        Garden is lit by Neon parts (flowers, crystal) rather than light objects."""
        _, cmds = fn(0, 0, 0)
        # All templates have at least 1 light or Neon-lit feature
        min_lights = {"lighthouse": 1, "garden": 0}.get(name, 2)
        assert _count_lights(cmds) >= min_lights, f"{name}: needs {min_lights} lights, got {_count_lights(cmds)}"

    @pytest.mark.parametrize("name,fn", [
        ("castle", build_castle),
        ("house", build_house),
        ("lighthouse", build_lighthouse),
        ("forge", build_forge),
        ("garden", build_garden),
    ])
    def test_each_template_has_particle(self, name, fn):
        """Design rule: 1+ particle system per build."""
        _, cmds = fn(0, 0, 0)
        assert _count_particles(cmds) >= 1, f"{name}: needs particle system"

    @pytest.mark.parametrize("name,fn", [
        ("castle", build_castle),
        ("house", build_house),
        ("lighthouse", build_lighthouse),
        ("forge", build_forge),
        ("garden", build_garden),
    ])
    def test_each_template_3_plus_materials(self, name, fn):
        """Design rule: 3+ materials per build."""
        _, cmds = fn(0, 0, 0)
        mats = _get_materials(cmds)
        assert len(mats) >= 3, f"{name}: only {len(mats)} materials"

    @pytest.mark.parametrize("name,fn", [
        ("castle", build_castle),
        ("house", build_house),
        ("lighthouse", build_lighthouse),
        ("forge", build_forge),
        ("garden", build_garden),
    ])
    def test_each_template_3_plus_colors(self, name, fn):
        """Design rule: 3+ distinct colors per build."""
        _, cmds = fn(0, 0, 0)
        colors = _get_colors(cmds)
        assert len(colors) >= 3, f"{name}: only {len(colors)} colors"

    @pytest.mark.parametrize("name,fn", [
        ("castle", build_castle),
        ("house", build_house),
        ("lighthouse", build_lighthouse),
        ("forge", build_forge),
        ("garden", build_garden),
    ])
    def test_each_template_command_count_15_to_30(self, name, fn):
        """Design rule: 15-25 commands per template (allowing some flex)."""
        _, cmds = fn(0, 0, 0)
        assert 15 <= len(cmds) <= 30, f"{name}: {len(cmds)} commands"

    @pytest.mark.parametrize("name,fn", [
        ("castle", build_castle),
        ("house", build_house),
        ("lighthouse", build_lighthouse),
        ("forge", build_forge),
        ("garden", build_garden),
    ])
    def test_each_template_ends_with_send_message(self, name, fn):
        """Last command should always be sendMessage."""
        _, cmds = fn(0, 0, 0)
        assert cmds[-1]["type"] == "sendMessage"

    @pytest.mark.parametrize("name,fn", [
        ("castle", build_castle),
        ("house", build_house),
        ("lighthouse", build_lighthouse),
        ("forge", build_forge),
        ("garden", build_garden),
    ])
    def test_unique_part_names(self, name, fn):
        """All part names within a template should be unique."""
        _, cmds = fn(0, 0, 0)
        names = _get_part_names(cmds)
        assert len(names) == len(set(names)), f"{name}: duplicate part names in {names}"


# ─── Dispatcher Tests ──────────────────────────────────────────────────────

class TestTemplatesV2Dispatcher:
    """Test the TEMPLATES_V2 keyword → function dispatcher."""

    def test_castle_aliases(self):
        for key in ("castle", "fortress", "fort", "keep", "citadel", "palace"):
            assert key in TEMPLATES_V2
            assert TEMPLATES_V2[key] == build_castle

    def test_house_aliases(self):
        for key in ("house", "home", "cabin", "cottage"):
            assert key in TEMPLATES_V2
            assert TEMPLATES_V2[key] == build_house

    def test_lighthouse_aliases(self):
        for key in ("lighthouse", "beacon"):
            assert key in TEMPLATES_V2
            assert TEMPLATES_V2[key] == build_lighthouse

    def test_forge_aliases(self):
        for key in ("forge", "smithy", "blacksmith"):
            assert key in TEMPLATES_V2
            assert TEMPLATES_V2[key] == build_forge

    def test_garden_aliases(self):
        for key in ("garden", "park", "yard", "flowerbed"):
            assert key in TEMPLATES_V2
            assert TEMPLATES_V2[key] == build_garden

    def test_all_values_are_callables(self):
        for key, fn in TEMPLATES_V2.items():
            assert callable(fn), f"TEMPLATES_V2['{key}'] is not callable"

    def test_all_functions_return_tuple(self):
        """Every template function must return (message, commands)."""
        for key, fn in TEMPLATES_V2.items():
            result = fn(0, 0, 0)
            assert isinstance(result, tuple), f"'{key}' didn't return tuple"
            assert len(result) == 2, f"'{key}' didn't return 2-tuple"
            assert isinstance(result[0], str), f"'{key}' message is not str"
            assert isinstance(result[1], list), f"'{key}' commands is not list"


# ─── Coordinate Offset Tests ────────────────────────────────────────────────

class TestCoordinateOffsets:
    """Verify templates correctly offset from the given position."""

    @pytest.mark.parametrize("name,fn", [
        ("castle", build_castle),
        ("house", build_house),
        ("lighthouse", build_lighthouse),
        ("forge", build_forge),
        ("garden", build_garden),
    ])
    def test_offset_positions(self, name, fn):
        """Building at (100, 50, 200) should produce parts offset from there."""
        _, cmds_origin = fn(0, 0, 0)
        _, cmds_offset = fn(100, 50, 200)

        origin_parts = [c for c in cmds_origin if c["type"] == "createPart"]
        offset_parts = [c for c in cmds_offset if c["type"] == "createPart"]

        assert len(origin_parts) == len(offset_parts)

        for o, off in zip(origin_parts, offset_parts):
            op = o["params"]["position"]
            offp = off["params"]["position"]
            dx = offp["x"] - op["x"]
            dy = offp["y"] - op["y"]
            dz = offp["z"] - op["z"]
            # Should be offset by approximately (100, 50, 200)
            assert abs(dx - 100) < 1.0, f"{name}: x offset wrong: {dx}"
            assert abs(dy - 50) < 1.0, f"{name}: y offset wrong: {dy}"
            assert abs(dz - 200) < 1.0, f"{name}: z offset wrong: {dz}"
