#!/usr/bin/env python3
"""
Lucineer Bond Scoring
=====================
Turns `player_profiles.bond_level` from a dead column into the relationship arc
described in CHARACTER_BIBLE.md §4.

Bond advances on COLLABORATION, not conversation. A player who talks for an hour
and builds nothing stays at Tier 0. See CHARACTER_BIBLE.md Appendix, note 3.

Tier thresholds (CHARACTER_BIBLE.md §4):
    Tier 0  Hired               bond   0- 9
    Tier 1  Working Together    bond  10-29
    Tier 2  Trusted             bond  30-69
    Tier 3  Crew                bond  70-149
    Tier 4  The Yard            bond 150+
"""

from typing import Literal

BondEvent = Literal[
    "session_first_build",      # showing up
    "finished_hook",            # player completed something Lucineer left open — the core loop
    "manual_build",             # player built something themselves, unprompted
    "modify_not_replace",       # asked to change a build rather than tear it down
    "won_argument",             # gave a reason that changed his mind
    "returned",                 # came back after >24h away
    "blind_delete",             # deleted a build without inspecting it
]

# Base values from CHARACTER_BIBLE.md §4.
BOND_POINTS: dict[str, int] = {
    "session_first_build": 1,
    "finished_hook":       5,
    "manual_build":        3,
    "modify_not_replace":  2,
    "won_argument":        4,
    "returned":            2,
    "blind_delete":       -1,
}

TIER_THRESHOLDS = (0, 10, 30, 70, 150)


def tier_for(bond_level: int) -> int:
    """Map a raw bond score to a tier index 0-4."""
    tier = 0
    for i, threshold in enumerate(TIER_THRESHOLDS):
        if bond_level >= threshold:
            tier = i
    return tier


def award_bond(
    current_bond: int,
    event: BondEvent,
    events_this_session: dict[str, int],
) -> int:
    """
    Return the player's NEW bond level after `event`.

    Args:
        current_bond:        the player's bond_level from D1
        event:               which BondEvent just fired
        events_this_session: count of each event already fired this session,
                             e.g. {"manual_build": 4, "finished_hook": 1}

    Returns:
        The new bond level. Must never drop the player below their current
        tier's floor — see CHARACTER_BIBLE.md §4, "Bond decay: None."

    TODO(casey): implement the scoring policy.

    The raw table in BOND_POINTS is a starting point, not a finished design.
    The open questions are about PACING, and they're yours:

      - Diminishing returns? A player who builds 40 things manually in one
        session earning 120 bond would hit Tier 3 on day one. Halving after
        the 3rd occurrence of an event keeps grinding from outrunning the
        relationship — but it also punishes a genuinely productive session.

      - Per-session cap? A hard ceiling (say 25/session) guarantees the arc
        takes at least ~6 sessions to reach Tier 3, which makes "we" mean
        something. It also means a player can hit the cap and stop earning,
        which feels bad if they notice.

      - Should `finished_hook` ignore both of the above? It's the one event
        that represents the thing the whole character is built around.

    Whatever you pick, enforce the floor: bond may never fall below
    TIER_THRESHOLDS[tier_for(current_bond)].
    """
    raise NotImplementedError("see TODO above")
