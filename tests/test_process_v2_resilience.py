#!/usr/bin/env python3
"""
Tests for process_v2.py resilience and circuit breaker functions.

Covers:
  1. _check_auth_failure — auth rejection surfacing (the silent-failure guard)
  2. scheduler_circuit_state / record_scheduler_success / record_scheduler_failure
  3. _is_valid_build_command edge cases
  4. _filter_valid_commands with mixed/empty/None inputs
  5. match_keyword — negation handling, verb requirement, scoring
"""

import json
import pytest
import sys
import importlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

spec = importlib.util.spec_from_file_location(
    "process_v2",
    str(Path(__file__).parent.parent / "process_v2.py"),
)
process_v2 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(process_v2)

_check_auth_failure = process_v2._check_auth_failure
_is_valid_build_command = process_v2._is_valid_build_command
_filter_valid_commands = process_v2._filter_valid_commands
match_keyword = process_v2.match_keyword
scheduler_circuit_state = process_v2.scheduler_circuit_state
record_scheduler_success = process_v2.record_scheduler_success
record_scheduler_failure = process_v2.record_scheduler_failure


# ─── Auth Failure Detection ─────────────────────────────────────────────────

class TestCheckAuthFailure:
    """The guard that catches silent auth failures — a historic outage cause."""

    def test_unauthorized_dict_returns_true(self):
        """When relay returns {'error': 'Unauthorized'}, must surface it."""
        result = _check_auth_failure("/api/jobs/pending", {"error": "Unauthorized"})
        assert result is True

    def test_normal_response_returns_false(self):
        """A normal jobs response should not trigger auth failure."""
        result = _check_auth_failure("/api/jobs/pending", {"jobs": []})
        assert result is False

    def test_empty_dict_returns_false(self):
        """Empty dict (network failure fallback) should not trigger auth failure."""
        result = _check_auth_failure("/api/jobs/pending", {})
        assert result is False

    def test_non_dict_returns_false(self):
        """Non-dict inputs should not crash."""
        assert _check_auth_failure("/api/test", None) is False
        assert _check_auth_failure("/api/test", "string") is False
        assert _check_auth_failure("/api/test", []) is False
        assert _check_auth_failure("/api/test", 42) is False

    def test_different_error_string_returns_false(self):
        """Only exact 'Unauthorized' triggers — not other error strings."""
        assert _check_auth_failure("/api/test", {"error": "Forbidden"}) is False
        assert _check_auth_failure("/api/test", {"error": "Rate limited"}) is False

    def test_job_response_with_error_field_does_not_trigger(self):
        """A job with an 'error' field (normal) should not trigger auth alert."""
        job_with_error = {"id": "abc", "error": "model timeout"}
        assert _check_auth_failure("/api/job/abc", job_with_error) is False


# ─── Circuit Breaker ────────────────────────────────────────────────────────

class TestCircuitBreaker:
    """The scheduler circuit breaker prevents cascading failures."""

    def setup_method(self):
        """Reset circuit breaker state before each test."""
        record_scheduler_success()

    def test_circuit_starts_closed(self):
        """Circuit should start in closed state."""
        is_open, should_probe = scheduler_circuit_state()
        assert is_open is False

    def test_circuit_opens_after_threshold(self):
        """After SCHEDULER_CB_THRESHOLD failures, circuit opens."""
        threshold = process_v2.SCHEDULER_CB_THRESHOLD
        for _ in range(threshold):
            record_scheduler_failure()
        is_open, should_probe = scheduler_circuit_state()
        assert is_open is True

    def test_circuit_resets_on_success(self):
        """A single success closes the circuit."""
        threshold = process_v2.SCHEDULER_CB_THRESHOLD
        for _ in range(threshold):
            record_scheduler_failure()
        is_open, _ = scheduler_circuit_state()
        assert is_open is True

        record_scheduler_success()
        is_open, _ = scheduler_circuit_state()
        assert is_open is False

    def test_below_threshold_stays_closed(self):
        """One fewer than threshold should not open the circuit."""
        threshold = process_v2.SCHEDULER_CB_THRESHOLD
        for _ in range(threshold - 1):
            record_scheduler_failure()
        is_open, _ = scheduler_circuit_state()
        assert is_open is False

    def test_circuit_does_not_double_open(self):
        """Recording more failures after open doesn't re-trigger open log."""
        threshold = process_v2.SCHEDULER_CB_THRESHOLD
        for _ in range(threshold + 5):
            record_scheduler_failure()
        is_open, _ = scheduler_circuit_state()
        assert is_open is True


# ─── Build Command Validation ───────────────────────────────────────────────

class TestIsValidBuildCommand:
    """Build command validation — the last gate before commands reach Roblox."""

    def test_valid_create_part(self):
        cmd = {"type": "createPart", "params": {"name": "Wall"}}
        assert _is_valid_build_command(cmd) is True

    def test_valid_add_light(self):
        cmd = {"type": "addLight", "params": {"position": {"x": 0, "y": 5, "z": 0}}}
        assert _is_valid_build_command(cmd) is True

    def test_valid_add_particle(self):
        cmd = {"type": "addParticle", "params": {}}
        assert _is_valid_build_command(cmd) is True

    def test_invalid_type(self):
        cmd = {"type": "deletePart", "params": {}}
        assert _is_valid_build_command(cmd) is False

    def test_missing_type(self):
        cmd = {"params": {}}
        assert _is_valid_build_command(cmd) is False

    def test_empty_type(self):
        cmd = {"type": "", "params": {}}
        assert _is_valid_build_command(cmd) is False

    def test_non_dict_returns_false(self):
        assert _is_valid_build_command(None) is False
        assert _is_valid_build_command("string") is False
        assert _is_valid_build_command(42) is False
        assert _is_valid_build_command([]) is False


class TestFilterValidCommands:
    """Filtering mixed valid/invalid commands from model output."""

    def test_all_valid(self):
        cmds = [
            {"type": "createPart", "params": {}},
            {"type": "addLight", "params": {}},
        ]
        result = _filter_valid_commands(cmds)
        assert len(result) == 2

    def test_all_invalid(self):
        cmds = [
            {"type": "deletePart", "params": {}},
            {"type": "movePart", "params": {}},
        ]
        result = _filter_valid_commands(cmds)
        assert result == []

    def test_mixed(self):
        cmds = [
            {"type": "createPart", "params": {}},
            {"type": "badType", "params": {}},
            {"type": "addLight", "params": {}},
            {"type": "addParticle", "params": {}},
            {"not": "even a command"},
        ]
        result = _filter_valid_commands(cmds)
        assert len(result) == 3

    def test_empty_list(self):
        assert _filter_valid_commands([]) == []

    def test_none_input(self):
        assert _filter_valid_commands(None) == []

    def test_non_list_input(self):
        assert _filter_valid_commands("not a list") == []
        assert _filter_valid_commands({"type": "createPart"}) == []

    def test_preserves_order(self):
        cmds = [
            {"type": "addParticle", "params": {"n": 3}},
            {"type": "createPart", "params": {"n": 1}},
            {"type": "addLight", "params": {"n": 2}},
        ]
        result = _filter_valid_commands(cmds)
        assert result[0]["params"]["n"] == 3
        assert result[1]["params"]["n"] == 1
        assert result[2]["params"]["n"] == 2


# ─── match_keyword edge cases ──────────────────────────────────────────────

class TestMatchKeywordEdgeCases:
    """Additional edge case coverage for the fast-path router."""

    def test_empty_message_returns_none(self):
        assert match_keyword("") is None

    def test_no_build_verb_returns_none(self):
        """Messages without a build verb route to deep path."""
        assert match_keyword("a nice castle over there") is None

    def test_negation_blocks_match(self):
        """'don't build a wall' should not match."""
        result = match_keyword("don't build a wall")
        assert result is None or len(result) == 0

    def test_build_castle_matches(self):
        result = match_keyword("build a castle")
        assert result is not None
        assert callable(result)

    def test_case_insensitive(self):
        lower = match_keyword("build a castle")
        upper = match_keyword("BUILD A CASTLE")
        assert lower is not None
        assert upper is not None
        # Both should produce the same builder function
        assert lower == upper


# ─── _strip_build_json_from_text edge cases ────────────────────────────────

class TestStripBuildJson:
    """Test JSON fragment stripping from model replies."""

    def test_text_without_json_unchanged(self):
        text = "Castle's up. Four tower walls."
        result = process_v2._strip_build_json_from_text(text)
        assert result == text

    def test_embedded_createpart_stripped(self):
        text = 'Castle\'s up. {"type": "createPart", "params": {"name": "X"}}'
        result = process_v2._strip_build_json_from_text(text)
        assert "createPart" not in result
        assert "Castle" in result

    def test_multiple_fragments_stripped(self):
        text = (
            'Done. {"type": "createPart", "params": {}} '
            'and {"type": "addLight", "params": {}}'
        )
        result = process_v2._strip_build_json_from_text(text)
        assert "createPart" not in result
        assert "addLight" not in result
        assert "Done" in result

    def test_empty_string(self):
        assert process_v2._strip_build_json_from_text("") == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
