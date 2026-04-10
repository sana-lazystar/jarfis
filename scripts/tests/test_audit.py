"""Tests for jarfis.audit module."""

import json
import os

import pytest

from jarfis.audit import append_event, read_events, EVENT_TYPES


class TestAppendEvent:
    def test_basic_append(self, tmp_path):
        path = str(tmp_path / "audit.jsonl")
        event = append_event(path, "WorkflowStarted", workflow="test-001")
        assert event["type"] == "WorkflowStarted"
        assert event["workflow"] == "test-001"
        assert "ts" in event

    def test_creates_file(self, tmp_path):
        path = str(tmp_path / "audit.jsonl")
        assert not os.path.exists(path)
        append_event(path, "PhaseStarted", phase=0)
        assert os.path.exists(path)

    def test_append_multiple(self, tmp_path):
        path = str(tmp_path / "audit.jsonl")
        append_event(path, "PhaseStarted", phase=0)
        append_event(path, "PhaseCompleted", phase=0)
        lines = open(path).readlines()
        assert len(lines) == 2

    def test_invalid_event_type(self, tmp_path):
        path = str(tmp_path / "audit.jsonl")
        with pytest.raises(ValueError, match="Unknown event type"):
            append_event(path, "InvalidType")

    def test_all_event_types_valid(self, tmp_path):
        path = str(tmp_path / "audit.jsonl")
        for et in EVENT_TYPES:
            event = append_event(path, et)
            assert event["type"] == et

    def test_unicode_content(self, tmp_path):
        path = str(tmp_path / "audit.jsonl")
        append_event(path, "AutoCommit", message="jarfis(FE-1): 한글 커밋")
        events = read_events(path)
        assert events[0]["message"] == "jarfis(FE-1): 한글 커밋"


class TestReadEvents:
    def test_empty_file(self, tmp_path):
        path = str(tmp_path / "audit.jsonl")
        open(path, "w").close()
        assert read_events(path) == []

    def test_nonexistent_file(self, tmp_path):
        path = str(tmp_path / "nonexistent.jsonl")
        assert read_events(path) == []

    def test_corrupted_line_skipped(self, tmp_path):
        """W1-4: Corrupted lines should be silently skipped."""
        path = str(tmp_path / "audit.jsonl")
        with open(path, "w") as f:
            f.write('{"type": "PhaseStarted", "phase": 0}\n')
            f.write('{"type": "Trunca\n')  # Corrupted
            f.write('{"type": "PhaseCompleted", "phase": 0}\n')
        events = read_events(path)
        assert len(events) == 2
        assert events[0]["type"] == "PhaseStarted"
        assert events[1]["type"] == "PhaseCompleted"

    def test_blank_lines_skipped(self, tmp_path):
        path = str(tmp_path / "audit.jsonl")
        with open(path, "w") as f:
            f.write('{"type": "PhaseStarted"}\n')
            f.write('\n')
            f.write('   \n')
            f.write('{"type": "PhaseCompleted"}\n')
        events = read_events(path)
        assert len(events) == 2
