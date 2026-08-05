#!/usr/bin/env python3
"""
Tests for Lucineer Bond Scoring.

Tests cover tier_for(), data structure consistency, and boundary conditions.
The award_bond() function is currently a stub (NotImplementedError) pending
Casey's scoring policy decisions — tests for it are marked skip.

When award_bond is implemented, remove the skip markers.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from bond import (
    BOND_POINTS,
    TIER_THRESHOLDS,
    BondEvent,
    tier_for,
    award_bond,
)


# ─── tier_for ────────────────────────────────────────────────────────────────

class TestTierFor:
    """The tier mapping is the core relationship gate. It must be exact."""

    @pytest.mark.parametrize("bond,expected_tier", [
        # Tier 0: Hired (0-9)
        (0, 0),
        (1, 0),
        (5, 0),
        (9, 0),
        # Tier 1: Working Together (10-29)
        (10, 1),
        (15, 1),
        (29, 1),
        # Tier 2: Trusted (30-69)
        (30, 2),
        (45, 2),
        (69, 2),
        # Tier 3: Crew (70-149)
        (70, 3),
        (100, 3),
        (149, 3),
        # Tier 4: The Yard (150+)
        (150, 4),
        (200, 4),
        (500, 4),
        (9999, 4),
    ])
    def test_tier_mapping(self, bond, expected_tier):
        assert tier_for(bond) == expected_tier

    def test_tier_boundaries(self):
        """Each tier threshold should be the inclusive lower bound."""
        for i, threshold in enumerate(TIER_THRESHOLDS):
            assert tier_for(threshold) == i, f"Threshold {threshold} should map to tier {i}"

    def test_below_first_threshold(self):
        """Bond 0 is valid and maps to tier 0."""
        assert tier_for(0) == 0

    def test_negative_bond(self):
        """Negative bond should map to tier 0 (floor)."""
        assert tier_for(-5) == 0
        assert tier_for(-100) == 0

    def test_all_tiers_reachable(self):
        """Every tier 0-4 should be reachable."""
        tiers_found = set()
        for bond in range(0, 300):
            tiers_found.add(tier_for(bond))
        assert tiers_found == {0, 1, 2, 3, 4}


# ─── TIER_THRESHOLDS consistency ─────────────────────────────────────────────

class TestTierThresholds:
    def test_thresholds_ascending(self):
        """Each threshold must be strictly greater than the last."""
        for i in range(1, len(TIER_THRESHOLDS)):
            assert TIER_THRESHOLDS[i] > TIER_THRESHOLDS[i - 1], \
                f"Threshold {i} ({TIER_THRESHOLDS[i]}) not > {i-1} ({TIER_THRESHOLDS[i-1]})"

    def test_five_tiers(self):
        """There should be exactly 5 tiers (0-4)."""
        assert len(TIER_THRESHOLDS) == 5

    def test_first_threshold_is_zero(self):
        """Tier 0 starts at bond level 0."""
        assert TIER_THRESHOLDS[0] == 0

    def test_tier_4_at_150(self):
        """Tier 4 (The Yard) starts at 150 per CHARACTER_BIBLE.md."""
        assert TIER_THRESHOLDS[4] == 150


# ─── BOND_POINTS consistency ─────────────────────────────────────────────────

class TestBondPoints:
    def test_all_events_have_points(self):
        """Every event must have a defined point value."""
        for event in BOND_POINTS:
            assert isinstance(BOND_POINTS[event], int), f"{event} points not int"
            assert BOND_POINTS[event] != 0 or event == "blind_delete", \
                f"{event} has 0 points (only blind_delete can be 0-penalty)"

    def test_finished_hook_is_highest_positive(self):
        """finished_hook is the core loop — it should be worth the most."""
        positive = {k: v for k, v in BOND_POINTS.items() if v > 0}
        max_event = max(positive, key=positive.get)
        assert max_event == "finished_hook", \
            f"{max_event} ({positive[max_event]}) should be highest, not finished_hook ({positive.get('finished_hook')})"
        assert positive["finished_hook"] == max(positive.values())

    def test_blind_delete_is_negative(self):
        """blind_delete is the only penalty — it should be negative."""
        assert BOND_POINTS["blind_delete"] < 0

    def test_won_argument_worth_more_than_manual_build(self):
        """Winning an argument (giving a reason that changed his mind) is rarer
        and more meaningful than just building something manually."""
        assert BOND_POINTS["won_argument"] >= BOND_POINTS["manual_build"], \
            "won_argument should be >= manual_build"

    def test_returned_is_positive(self):
        """Coming back after 24h+ should reward."""
        assert BOND_POINTS["returned"] > 0

    def test_modify_not_replace_is_positive(self):
        """Asking to modify rather than teardown shows investment."""
        assert BOND_POINTS["modify_not_replace"] > 0

    def test_session_first_build_exists(self):
        """The 'showing up' event must exist."""
        assert "session_first_build" in BOND_POINTS

    def test_session_first_build_is_small(self):
        """First build of a session is a small reward — just showing up."""
        assert BOND_POINTS["session_first_build"] <= 2

    def test_all_keys_are_valid_events(self):
        """Every key in BOND_POINTS should be a known event."""
        valid_events = {
            "session_first_build", "finished_hook", "manual_build",
            "modify_not_replace", "won_argument", "returned", "blind_delete",
        }
        for key in BOND_POINTS:
            assert key in valid_events, f"Unknown event: {key}"


# ─── award_bond (currently stub) ─────────────────────────────────────────────

class TestAwardBondStub:
    """award_bond is a stub. These tests verify the contract for when it's implemented."""

    @pytest.mark.skip(reason="award_bond is NotImplementedError until Casey designs the policy")
    def test_returns_int(self):
        result = award_bond(0, "session_first_build", {})
        assert isinstance(result, int)

    @pytest.mark.skip(reason="award_bond is NotImplementedError until Casey designs the policy")
    def test_session_first_build_adds_points(self):
        new = award_bond(0, "session_first_build", {})
        assert new >= 1

    @pytest.mark.skip(reason="award_bond is NotImplementedError until Casey designs the policy")
    def test_blind_delete_never_drops_below_tier_floor(self):
        """Bond decay is not allowed — see CHARACTER_BIBLE.md §4."""
        # Player at tier 2 floor (30)
        new = award_bond(30, "blind_delete", {"blind_delete": 0})
        assert new >= 30  # cannot drop below current tier floor

    @pytest.mark.skip(reason="award_bond is NotImplementedError until Casey designs the policy")
    def test_blind_delete_at_tier_0_can_lose(self):
        """At tier 0, bond CAN go negative (or at least decrease) — no floor protection below 0... 
        actually, the spec says 'never below current tier floor'. Tier 0 floor is 0."""
        new = award_bond(5, "blind_delete", {})
        assert new >= 0  # floor for tier 0 is 0

    @pytest.mark.skip(reason="award_bond is NotImplementedError until Casey designs the policy")
    def test_finished_hook_ignores_diminishing_returns(self):
        """Per the TODO, finished_hook may ignore diminishing returns."""
        # Build 10 finished_hooks in one session
        events = {"finished_hook": 9}
        before = award_bond(0, "finished_hook", {"finished_hook": 0})
        after_many = award_bond(before, "finished_hook", events)
        # Each finished_hook should add the full 5 points (no diminishing)
        # This test encodes the desired behavior from the TODO
        assert after_many >= before + 5

    @pytest.mark.skip(reason="award_bond is NotImplementedError until Casey designs the policy")
    def test_unknown_event_raises(self):
        with pytest.raises((KeyError, ValueError)):
            award_bond(0, "not_a_real_event", {})

    @pytest.mark.skip(reason="award_bond is NotImplementedError until Casey designs the policy")
    def test_result_always_positive_or_zero(self):
        """Bond should never go negative (tier 0 floor)."""
        for event in BOND_POINTS:
            result = award_bond(0, event, {})
            assert result >= 0, f"award_bond(0, {event}, {{}}) = {result} < 0"


# ─── Integration: tier arc ───────────────────────────────────────────────────

class TestTierArc:
    """The tier arc should take roughly 6+ sessions to reach Tier 3."""

    def test_tier_3_not_reachable_in_one_session_of_moderate_play(self):
        """If a player does 10 manual builds + 3 finished hooks + 1 won argument
        in a single session (without diminishing returns that's 10*3 + 3*5 + 4 = 49),
        they should reach at most tier 1 or 2, not tier 3 (70)."""
        moderate_points = (
            10 * BOND_POINTS["manual_build"]
            + 3 * BOND_POINTS["finished_hook"]
            + 1 * BOND_POINTS["won_argument"]
            + 1 * BOND_POINTS["session_first_build"]
            + 1 * BOND_POINTS["returned"]
        )
        # Without diminishing returns, this gives 10*3 + 3*5 + 1*4 + 1 + 2 = 52
        # That's tier 2 (30-69), not tier 3 (70+). Good.
        tier = tier_for(moderate_points)
        assert tier <= 2, \
            f"Moderate session ({moderate_points} points) reaches tier {tier}, should be <= 2"

    def test_tier_4_takes_many_sessions(self):
        """150 points requires sustained play over multiple sessions."""
        # If each session averages ~25 points (with diminishing returns),
        # reaching 150 takes ~6 sessions minimum
        avg_per_session = 25
        sessions_for_tier_4 = TIER_THRESHOLDS[4] / avg_per_session
        assert sessions_for_tier_4 >= 5, \
            f"Tier 4 reachable in {sessions_for_tier_4:.1f} sessions — too fast"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
