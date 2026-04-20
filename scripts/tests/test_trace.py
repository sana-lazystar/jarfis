"""Tests for jarfis.trace module.

v4.0.5 N-2: trace is gated by JARFIS_TRACE. Every test explicitly opts in or out.
Previous tests that relied on an implicit "always on" behaviour have been updated
to set JARFIS_TRACE=1 via monkeypatch; the new `TestGatedBehaviour` class covers
the no-op path when the gate is off and the exception-shield contract.
"""

import json
import os
import time

import pytest

from jarfis.trace import is_enabled, log_event, trace_agent, trace_phase


@pytest.fixture
def trace_on(monkeypatch):
    monkeypatch.setenv("JARFIS_TRACE", "1")


@pytest.fixture
def trace_off(monkeypatch):
    monkeypatch.setenv("JARFIS_TRACE", "0")


class TestTraceAgent:
    def test_basic_trace(self, tmp_path, trace_on):
        path = str(tmp_path / "traces.jsonl")
        with trace_agent(path, "run-001", 4, "frontend-developer", ["react"]) as span_id:
            assert span_id.startswith("agent-frontend-developer-")

        lines = open(path).readlines()
        assert len(lines) == 1
        span = json.loads(lines[0])
        assert span["traceId"] == "run-001"
        assert span["type"] == "agent"
        assert span["persona"] == "frontend-developer"
        assert span["skills"] == ["react"]
        assert span["parentSpanId"] == "phase-4"
        assert "duration_ms" in span
        assert "startTime" in span

    def test_unique_span_ids(self, tmp_path, trace_on):
        """W1-12: span_id should use uuid4 to avoid collisions."""
        path = str(tmp_path / "traces.jsonl")
        ids = []
        for _ in range(5):
            with trace_agent(path, "run-001", 4, "fe", []) as span_id:
                ids.append(span_id)
        assert len(set(ids)) == 5  # All unique

    def test_duration_measurement(self, tmp_path, trace_on):
        path = str(tmp_path / "traces.jsonl")
        with trace_agent(path, "run-001", 4, "fe", []):
            time.sleep(0.05)  # 50ms

        span = json.loads(open(path).readline())
        assert span["duration_ms"] >= 40  # Allow some tolerance

    def test_creates_file(self, tmp_path, trace_on):
        path = str(tmp_path / "traces.jsonl")
        assert not os.path.exists(path)
        with trace_agent(path, "run-001", 1, "po", []):
            pass
        assert os.path.exists(path)


class TestTracePhase:
    def test_basic_phase_trace(self, tmp_path, trace_on):
        path = str(tmp_path / "traces.jsonl")
        trace_phase(path, "run-001", 4, 5000)

        span = json.loads(open(path).readline())
        assert span["traceId"] == "run-001"
        assert span["spanId"] == "phase-4"
        assert span["type"] == "phase"
        assert span["phase"] == 4
        assert span["duration_ms"] == 5000

    def test_multiple_phases(self, tmp_path, trace_on):
        path = str(tmp_path / "traces.jsonl")
        trace_phase(path, "run-001", 0, 1000)
        trace_phase(path, "run-001", 1, 2000)
        trace_phase(path, "run-001", 4, 5000)

        lines = open(path).readlines()
        assert len(lines) == 3


class TestGatedBehaviour:
    """v4.0.5 N-2: env gate + exception shield."""

    def test_is_enabled_default_off(self, monkeypatch):
        monkeypatch.delenv("JARFIS_TRACE", raising=False)
        assert is_enabled() is False

    def test_is_enabled_explicit_zero(self, trace_off):
        assert is_enabled() is False

    def test_is_enabled_one(self, trace_on):
        assert is_enabled() is True

    def test_is_enabled_any_nonzero_truthy(self, monkeypatch):
        monkeypatch.setenv("JARFIS_TRACE", "verbose")
        assert is_enabled() is True

    def test_trace_agent_noop_when_disabled(self, tmp_path, trace_off):
        path = str(tmp_path / "traces.jsonl")
        with trace_agent(path, "run-001", 4, "fe", ["react"]) as span_id:
            assert span_id == "agent-fe-disabled"
        assert not os.path.exists(path), "no file should be written when off"

    def test_trace_agent_noop_when_env_unset(self, tmp_path, monkeypatch):
        monkeypatch.delenv("JARFIS_TRACE", raising=False)
        path = str(tmp_path / "traces.jsonl")
        with trace_agent(path, "run-001", 4, "fe", []) as span_id:
            assert span_id.endswith("-disabled")
        assert not os.path.exists(path)

    def test_trace_phase_noop_when_disabled(self, tmp_path, trace_off):
        path = str(tmp_path / "traces.jsonl")
        trace_phase(path, "run-001", 4, 5000)
        assert not os.path.exists(path)

    def test_trace_agent_swallows_write_failure(self, tmp_path, trace_on, monkeypatch):
        """A write error must never propagate to the caller."""
        # Point at a path whose parent doesn't exist AND cannot be created.
        bogus = str(tmp_path / "nope" / "deep" / "traces.jsonl")
        # Remove parent so open() will fail
        try:
            with trace_agent(bogus, "run-001", 4, "fe", []) as span_id:
                pass  # body ran cleanly
            assert span_id.startswith("agent-fe-")
        except Exception as exc:  # pragma: no cover — defensive
            pytest.fail(f"trace_agent should swallow write errors, got: {exc}")
        assert not os.path.exists(bogus)

    def test_trace_phase_swallows_write_failure(self, tmp_path, trace_on):
        bogus = str(tmp_path / "missing-dir" / "traces.jsonl")
        # No raise expected
        trace_phase(bogus, "run-001", 4, 1000)
        assert not os.path.exists(bogus)

    def test_trace_agent_yields_even_when_write_fails(self, tmp_path, trace_on):
        """The caller's body must run even if recording the span fails."""
        bogus = str(tmp_path / "nope" / "traces.jsonl")
        ran = []
        with trace_agent(bogus, "run-001", 4, "fe", []):
            ran.append(True)
        assert ran == [True]


class TestLogEvent:
    """v4.0.5b: free-form event entry point for hot-path instrumentation."""

    def test_writes_event_with_attrs(self, tmp_path, trace_on):
        path = str(tmp_path / "trace.jsonl")
        log_event("compose_start", {"agent": "backend-developer"}, path=path)
        lines = open(path).readlines()
        assert len(lines) == 1
        rec = json.loads(lines[0])
        assert rec["event"] == "compose_start"
        assert rec["attrs"] == {"agent": "backend-developer"}
        assert "ts" in rec

    def test_attrs_optional(self, tmp_path, trace_on):
        path = str(tmp_path / "trace.jsonl")
        log_event("phase_verify_end", path=path)
        rec = json.loads(open(path).readline())
        assert rec["attrs"] == {}

    def test_noop_when_disabled(self, tmp_path, trace_off):
        path = str(tmp_path / "trace.jsonl")
        log_event("compose_start", {"x": 1}, path=path)
        assert not os.path.exists(path)

    def test_env_path_override(self, tmp_path, trace_on, monkeypatch):
        env_path = str(tmp_path / "from-env.jsonl")
        monkeypatch.setenv("JARFIS_TRACE_PATH", env_path)
        # no explicit path → should use env
        log_event("session_start", {"name": "jf-xx"})
        assert os.path.exists(env_path)
        rec = json.loads(open(env_path).readline())
        assert rec["event"] == "session_start"

    def test_explicit_path_wins_over_env(self, tmp_path, trace_on, monkeypatch):
        env_path = str(tmp_path / "from-env.jsonl")
        explicit = str(tmp_path / "explicit.jsonl")
        monkeypatch.setenv("JARFIS_TRACE_PATH", env_path)
        log_event("e", path=explicit)
        assert os.path.exists(explicit)
        assert not os.path.exists(env_path)

    def test_swallows_write_failure(self, tmp_path, trace_on):
        bogus = str(tmp_path / "missing-dir" / "trace.jsonl")
        # must not raise
        log_event("compose_start", {"a": 1}, path=bogus)
        assert not os.path.exists(bogus)
