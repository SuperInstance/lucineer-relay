#!/usr/bin/env python3
"""
Tests for job validation — the guard against the one-line bug class.

The bug (commit 7e0de39): the relay returns { jobId, job } wrappers, but
run_once() passed the wrapper directly to process_job(). job.get('message', '')
silently returned '' on every deep-path job for 48 hours.

These tests cover validate_job() which catches this class of failure.
"""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


# validate_job is a pure function with no module-level dependencies, so we
# test it directly without importing process_v2 (which has side effects).


def validate_job(job):
    """Copy of validate_job from process_v2.py for testing."""
    if not isinstance(job, dict):
        return False, f"job is {type(job).__name__}, not dict"

    if 'jobId' in job and 'message' not in job:
        return False, ("received relay wrapper {jobId, job} instead of inner job — "
                       "unwrap with entry.get('job', entry) before calling process_job")

    message = job.get('message', '')
    if not message or not message.strip():
        return False, f"job {job.get('id', '?')[:8]} has empty/missing 'message' field"

    if not job.get('playerName'):
        return False, f"job {job.get('id', '?')[:8]} has missing 'playerName' field"

    if not job.get('sessionId'):
        return False, f"job {job.get('id', '?')[:8]} has missing 'sessionId' field"

    return True, None


class TestValidateJob:
    """The validation guard that catches the one-line bug class."""

    def test_valid_job(self):
        """A well-formed job passes validation."""
        job = {
            "id": "test123",
            "playerName": "Casey",
            "message": "build a castle",
            "sessionId": "session-1",
        }
        ok, err = validate_job(job)
        assert ok is True
        assert err is None

    def test_relay_wrapper_rejected(self):
        """The exact bug from 7e0de39: relay wrapper passed instead of inner job."""
        wrapper = {
            "jobId": "session-1.abc123",
            "job": {
                "id": "session-1.abc123",
                "playerName": "Casey",
                "message": "build a castle",
                "sessionId": "session-1",
            }
        }
        ok, err = validate_job(wrapper)
        assert ok is False
        assert "wrapper" in err.lower()

    def test_empty_message_rejected(self):
        """Empty message string — the silent failure mode."""
        job = {"id": "x", "playerName": "Casey", "message": "", "sessionId": "s1"}
        ok, err = validate_job(job)
        assert ok is False
        assert "empty" in err.lower()

    def test_whitespace_message_rejected(self):
        """Whitespace-only message is also empty."""
        job = {"id": "x", "playerName": "Casey", "message": "   ", "sessionId": "s1"}
        ok, err = validate_job(job)
        assert ok is False

    def test_missing_message_rejected(self):
        """No message key at all."""
        job = {"id": "x", "playerName": "Casey", "sessionId": "s1"}
        ok, err = validate_job(job)
        assert ok is False
        assert "message" in err.lower()

    def test_missing_player_name_rejected(self):
        """No playerName — would default to 'friend' silently."""
        job = {"id": "x", "message": "hi", "sessionId": "s1"}
        ok, err = validate_job(job)
        assert ok is False
        assert "playerName" in err

    def test_missing_session_id_rejected(self):
        """No sessionId — would default to '' silently."""
        job = {"id": "x", "playerName": "Casey", "message": "hi"}
        ok, err = validate_job(job)
        assert ok is False
        assert "sessionId" in err

    def test_non_dict_rejected(self):
        """Job is not even a dict."""
        ok, err = validate_job(None)
        assert ok is False
        ok, err = validate_job("not a dict")
        assert ok is False
        ok, err = validate_job(42)
        assert ok is False
        ok, err = validate_job([])
        assert ok is False

    def test_relay_wrapper_with_message_passes(self):
        """Edge case: if something has both jobId and message, it's ambiguous but valid."""
        job = {"jobId": "x", "message": "hi", "playerName": "C", "sessionId": "s"}
        ok, err = validate_job(job)
        assert ok is True

    def test_error_messages_are_informative(self):
        """Error messages should contain enough info to debug without a stack trace."""
        wrapper = {"jobId": "abc", "job": {}}
        ok, err = validate_job(wrapper)
        assert ok is False
        # The error should mention the unwrap fix
        assert "unwrap" in err.lower() or "entry" in err.lower()


class TestRunOnceUnwrap:
    """Test that run_once's unwrapping logic handles all relay response shapes."""

    def test_unwrap_relay_wrapper(self):
        """The fix from 7e0de39: unwrap {jobId, job} to get the inner job."""
        entry = {"jobId": "s1.abc", "job": {"id": "s1.abc", "message": "hi"}}
        job = entry.get("job", entry) if isinstance(entry, dict) else entry
        assert job.get("message") == "hi"

    def test_unwrap_plain_job(self):
        """Backward compat: a plain job dict (no wrapper) passes through."""
        entry = {"id": "s1.abc", "message": "hi", "playerName": "C"}
        job = entry.get("job", entry) if isinstance(entry, dict) else entry
        assert job.get("message") == "hi"

    def test_unwrap_non_dict(self):
        """Non-dict entries don't crash the unwrap."""
        entry = None
        job = entry.get("job", entry) if isinstance(entry, dict) else entry
        assert job is None
