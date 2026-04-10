"""Tests for jarfis.trace module."""

import json
import os
import time

import pytest

from jarfis.trace import trace_agent, trace_phase


class TestTraceAgent:
    def test_basic_trace(self, tmp_path):
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

    def test_unique_span_ids(self, tmp_path):
        """W1-12: span_id should use uuid4 to avoid collisions."""
        path = str(tmp_path / "traces.jsonl")
        ids = []
        for _ in range(5):
            with trace_agent(path, "run-001", 4, "fe", []) as span_id:
                ids.append(span_id)
        assert len(set(ids)) == 5  # All unique

    def test_duration_measurement(self, tmp_path):
        path = str(tmp_path / "traces.jsonl")
        with trace_agent(path, "run-001", 4, "fe", []):
            time.sleep(0.05)  # 50ms

        span = json.loads(open(path).readline())
        assert span["duration_ms"] >= 40  # Allow some tolerance

    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "traces.jsonl")
        assert not os.path.exists(path)
        with trace_agent(path, "run-001", 1, "po", []):
            pass
        assert os.path.exists(path)


class TestTracePhase:
    def test_basic_phase_trace(self, tmp_path):
        path = str(tmp_path / "traces.jsonl")
        trace_phase(path, "run-001", 4, 5000)

        span = json.loads(open(path).readline())
        assert span["traceId"] == "run-001"
        assert span["spanId"] == "phase-4"
        assert span["type"] == "phase"
        assert span["phase"] == 4
        assert span["duration_ms"] == 5000

    def test_multiple_phases(self, tmp_path):
        path = str(tmp_path / "traces.jsonl")
        trace_phase(path, "run-001", 0, 1000)
        trace_phase(path, "run-001", 1, 2000)
        trace_phase(path, "run-001", 4, 5000)

        lines = open(path).readlines()
        assert len(lines) == 3
