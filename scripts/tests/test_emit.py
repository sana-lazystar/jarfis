"""Tests for jarfis.emit — event-stream-v1 (D4~D10 lockdown).

Coverage:
  - EventType enum (10 members per M-3 lockdown)
  - Level enum (4 members per D5)
  - emit() atomic JSONL append + validation rules
  - render_line() display layer (HH:MM:SS, [type], glyph, ANSI 4-color)
  - tail_events() last-N + level filter
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

from jarfis.emit import (
    ANSI,
    ANSI_RESET,
    DEFAULT_LEVEL,
    GLYPH,
    MAX_SUMMARY_LEN,
    EmitError,
    EventType,
    Level,
    emit,
    render_line,
    tail_events,
)


# ---------------------------------------------------------------- enum lockdowns


class TestEventTypeEnum:
    def test_has_exactly_10_members(self):
        # M-3 lockdown — design-output-formats.md:280-296
        assert len(list(EventType)) == 10

    def test_all_expected_values(self):
        expected = {
            "phase.start",
            "phase.end",
            "phase.abort",
            "checkpoint",
            "agent.spawn",
            "agent.done",
            "tool",
            "note",
            "error",
            "dialectic.unresolved",
        }
        assert {e.value for e in EventType} == expected

    def test_lookup_from_string(self):
        assert EventType("phase.start") == EventType.PHASE_START
        assert EventType("dialectic.unresolved") == EventType.DIALECTIC_UNRESOLVED

    def test_unknown_value_rejected(self):
        with pytest.raises(ValueError):
            EventType("phase.unknown")


class TestLevelEnum:
    def test_has_exactly_4_members(self):
        # D5 — 4-color rule
        assert len(list(Level)) == 4

    def test_all_expected_values(self):
        assert {l.value for l in Level} == {"highlight", "info", "error", "debug"}


class TestDefaultLevel:
    def test_phase_events_are_highlight(self):
        for et in (
            EventType.PHASE_START,
            EventType.PHASE_END,
            EventType.PHASE_ABORT,
            EventType.CHECKPOINT,
            EventType.DIALECTIC_UNRESOLVED,
        ):
            assert DEFAULT_LEVEL[et] == Level.HIGHLIGHT

    def test_agent_tool_note_are_info(self):
        for et in (
            EventType.AGENT_SPAWN,
            EventType.AGENT_DONE,
            EventType.TOOL,
            EventType.NOTE,
        ):
            assert DEFAULT_LEVEL[et] == Level.INFO

    def test_error_is_error(self):
        assert DEFAULT_LEVEL[EventType.ERROR] == Level.ERROR

    def test_every_type_has_default_level(self):
        for et in EventType:
            assert et in DEFAULT_LEVEL


class TestGlyphMapping:
    def test_phase_start_is_triangle(self):
        assert GLYPH[EventType.PHASE_START] == "▶"

    def test_phase_end_is_check(self):
        assert GLYPH[EventType.PHASE_END] == "✓"

    def test_phase_abort_is_x(self):
        assert GLYPH[EventType.PHASE_ABORT] == "✗"

    def test_checkpoint_is_dot(self):
        assert GLYPH[EventType.CHECKPOINT] == "●"

    def test_dialectic_is_warning(self):
        assert GLYPH[EventType.DIALECTIC_UNRESOLVED] == "⚠"

    def test_error_is_x(self):
        assert GLYPH[EventType.ERROR] == "✗"

    def test_info_types_have_no_glyph(self):
        for et in (EventType.AGENT_SPAWN, EventType.AGENT_DONE, EventType.TOOL, EventType.NOTE):
            assert GLYPH[et] == ""


class TestANSI:
    def test_4_colors_present(self):
        assert ANSI[Level.HIGHLIGHT] == "\033[35m\033[1m"
        assert ANSI[Level.INFO] == "\033[97m"
        assert ANSI[Level.ERROR] == "\033[31m\033[1m"
        assert ANSI[Level.DEBUG] == "\033[90m\033[2m"

    def test_reset_defined(self):
        assert ANSI_RESET == "\033[0m"


# ---------------------------------------------------------------- emit() core


class TestEmitWritesEvent:
    def test_writes_single_jsonl_line(self, tmp_path):
        events = tmp_path / "events.jsonl"
        emit(events, EventType.PHASE_START, "Workflow xyz 시작")
        content = events.read_text(encoding="utf-8")
        assert content.count("\n") == 1
        # Each event is a single self-contained JSON object
        line = content.strip()
        ev = json.loads(line)
        assert ev["type"] == "phase.start"
        assert ev["summary"] == "Workflow xyz 시작"
        assert ev["level"] == "highlight"
        assert "ts" in ev

    def test_returns_event_dict(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.NOTE, "test")
        assert isinstance(ev, dict)
        assert ev["type"] == "note"
        assert ev["summary"] == "test"

    def test_accepts_string_type(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", "tool", "Edit foo.py")
        assert ev["type"] == "tool"

    def test_accepts_string_level_override(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", "note", "debug detail", level="debug")
        assert ev["level"] == "debug"

    def test_default_level_picked_from_type(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.CHECKPOINT, "PO ready")
        assert ev["level"] == "highlight"

    def test_extras_merged_into_event(self, tmp_path):
        ev = emit(
            tmp_path / "events.jsonl",
            EventType.AGENT_SPAWN,
            "spawn jarfis-engineer",
            extras={"agent": "jarfis-engineer", "task": "BE-impl"},
        )
        assert ev["agent"] == "jarfis-engineer"
        assert ev["task"] == "BE-impl"

    def test_extras_cannot_override_protected_fields(self, tmp_path):
        # ts/type/level/summary should not be silently overridden by extras
        with pytest.raises(EmitError):
            emit(
                tmp_path / "events.jsonl",
                EventType.NOTE,
                "x",
                extras={"type": "phase.end"},
            )

    def test_explicit_timestamp_used(self, tmp_path):
        ts = datetime(2026, 5, 13, 14, 21, 38, tzinfo=timezone.utc)
        ev = emit(tmp_path / "events.jsonl", EventType.PHASE_START, "boot", timestamp=ts)
        assert ev["ts"] == "2026-05-13T14:21:38+00:00"

    def test_default_timestamp_is_utc_iso(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.NOTE, "now")
        # Should parse as ISO8601 with timezone
        parsed = datetime.fromisoformat(ev["ts"])
        assert parsed.tzinfo is not None

    def test_creates_parent_dir_if_missing(self, tmp_path):
        events = tmp_path / "deep" / "nest" / "events.jsonl"
        emit(events, EventType.NOTE, "first")
        assert events.exists()

    def test_multiple_calls_append(self, tmp_path):
        events = tmp_path / "events.jsonl"
        emit(events, EventType.PHASE_START, "a")
        emit(events, EventType.NOTE, "b")
        emit(events, EventType.PHASE_END, "c")
        lines = events.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 3
        assert json.loads(lines[0])["type"] == "phase.start"
        assert json.loads(lines[1])["type"] == "note"
        assert json.loads(lines[2])["type"] == "phase.end"


class TestSummaryValidation:
    def test_rejects_empty_summary(self, tmp_path):
        with pytest.raises(EmitError):
            emit(tmp_path / "events.jsonl", EventType.NOTE, "")

    def test_rejects_summary_over_80_chars(self, tmp_path):
        long = "x" * (MAX_SUMMARY_LEN + 1)
        with pytest.raises(EmitError):
            emit(tmp_path / "events.jsonl", EventType.NOTE, long)

    def test_accepts_summary_at_80_chars(self, tmp_path):
        eighty = "x" * MAX_SUMMARY_LEN
        ev = emit(tmp_path / "events.jsonl", EventType.NOTE, eighty)
        assert ev["summary"] == eighty

    def test_rejects_period_terminator(self, tmp_path):
        with pytest.raises(EmitError):
            emit(tmp_path / "events.jsonl", EventType.NOTE, "ends with period.")

    def test_rejects_korean_period_terminator(self, tmp_path):
        with pytest.raises(EmitError):
            emit(tmp_path / "events.jsonl", EventType.NOTE, "한국어 마침표。")

    def test_rejects_emoji(self, tmp_path):
        with pytest.raises(EmitError):
            emit(tmp_path / "events.jsonl", EventType.NOTE, "no 🎉 emojis")

    def test_allows_korean_text(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.NOTE, "한국어 OK")
        assert ev["summary"] == "한국어 OK"

    def test_allows_punctuation_inside(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.NOTE, "a, b, c — d")
        assert ev["summary"] == "a, b, c — d"


class TestEmitErrorContract:
    def test_unknown_type_raises(self, tmp_path):
        with pytest.raises((EmitError, ValueError)):
            emit(tmp_path / "events.jsonl", "phase.bogus", "x")

    def test_unknown_level_raises(self, tmp_path):
        with pytest.raises((EmitError, ValueError)):
            emit(tmp_path / "events.jsonl", EventType.NOTE, "x", level="purple")


class TestAtomicAppend:
    def test_100_sequential_writes_produce_100_valid_lines(self, tmp_path):
        events = tmp_path / "events.jsonl"
        for i in range(100):
            emit(events, EventType.TOOL, f"step-{i:03d}")
        lines = events.read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) == 100
        # Each line must be parseable as a complete JSON object (no torn writes)
        parsed = [json.loads(line) for line in lines]
        assert [p["summary"] for p in parsed] == [f"step-{i:03d}" for i in range(100)]


# ---------------------------------------------------------------- render_line()


class TestRenderLine:
    def test_includes_hhmmss_and_type(self, tmp_path, monkeypatch):
        import time
        monkeypatch.setenv("TZ", "UTC")
        time.tzset()
        events = tmp_path / "events.jsonl"
        ts = datetime(2026, 5, 13, 14, 21, 38, tzinfo=timezone.utc)
        ev = emit(events, EventType.PHASE_START, "boot", timestamp=ts)
        line = render_line(ev, color=False)
        assert "14:21:38" in line
        assert "[phase.start]" in line
        assert "boot" in line

    def test_render_line_converts_to_local_timezone(self, tmp_path, monkeypatch):
        """Fix E — ts stored as UTC; render_line displays in machine local TZ."""
        import time
        monkeypatch.setenv("TZ", "Asia/Seoul")
        time.tzset()
        events = tmp_path / "events.jsonl"
        # 07:00 UTC = 16:00 KST
        ts = datetime(2026, 5, 13, 7, 0, 0, tzinfo=timezone.utc)
        ev = emit(events, EventType.PHASE_START, "boot", timestamp=ts)
        line = render_line(ev, color=False)
        assert "16:00:00" in line, f"expected KST 16:00:00, got: {line}"

    def test_render_line_fallback_on_malformed_ts(self, tmp_path):
        """Fix E safety — malformed ts must not crash; fall back to raw slice."""
        ev = {
            "type": "phase.start",
            "summary": "x",
            "ts": "not-a-valid-ts",
            "level": "highlight",
        }
        line = render_line(ev, color=False)
        # Just verify it doesn't crash and includes the slice fallback
        assert "phase.start" in line
        assert "x" in line

    def test_includes_glyph_for_typed_events(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.PHASE_START, "boot")
        line = render_line(ev, color=False)
        assert "▶" in line

    def test_no_glyph_prefix_for_info_types(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.TOOL, "Edit foo.py")
        line = render_line(ev, color=False)
        # Glyph chars should NOT appear
        for g in ("▶", "✓", "✗", "●", "⚠"):
            assert g not in line

    def test_color_wraps_in_ansi(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.PHASE_START, "x")
        line = render_line(ev, color=True)
        assert line.startswith(ANSI[Level.HIGHLIGHT])
        assert line.endswith(ANSI_RESET)

    def test_color_false_omits_ansi(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.NOTE, "x")
        line = render_line(ev, color=False)
        assert "\033[" not in line

    def test_error_uses_red_when_color(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.ERROR, "pytest 실패")
        line = render_line(ev, color=True)
        assert line.startswith(ANSI[Level.ERROR])

    def test_debug_event_uses_gray(self, tmp_path):
        ev = emit(tmp_path / "events.jsonl", EventType.TOOL, "Read x", level="debug")
        line = render_line(ev, color=True)
        assert line.startswith(ANSI[Level.DEBUG])


# ---------------------------------------------------------------- tail_events()


class TestTailEvents:
    def test_returns_empty_when_file_missing(self, tmp_path):
        assert tail_events(tmp_path / "missing.jsonl") == []

    def test_returns_last_n(self, tmp_path):
        events = tmp_path / "events.jsonl"
        for i in range(10):
            emit(events, EventType.TOOL, f"step-{i}")
        last3 = tail_events(events, n=3)
        assert len(last3) == 3
        assert [e["summary"] for e in last3] == ["step-7", "step-8", "step-9"]

    def test_returns_all_when_n_exceeds_total(self, tmp_path):
        events = tmp_path / "events.jsonl"
        for i in range(2):
            emit(events, EventType.NOTE, f"x{i}")
        result = tail_events(events, n=10)
        assert len(result) == 2

    def test_filters_by_level_set(self, tmp_path):
        events = tmp_path / "events.jsonl"
        emit(events, EventType.PHASE_START, "p-start")  # highlight
        emit(events, EventType.TOOL, "t1")  # info
        emit(events, EventType.TOOL, "t2", level="debug")  # debug
        emit(events, EventType.PHASE_END, "p-end")  # highlight

        # Statusline shows highlight + info, hides debug
        result = tail_events(events, n=10, levels={Level.HIGHLIGHT, Level.INFO})
        assert len(result) == 3
        assert all(e["level"] in ("highlight", "info") for e in result)

    def test_filter_with_string_levels(self, tmp_path):
        events = tmp_path / "events.jsonl"
        emit(events, EventType.PHASE_START, "p")
        emit(events, EventType.TOOL, "t")
        result = tail_events(events, n=10, levels={"highlight"})
        assert len(result) == 1
        assert result[0]["type"] == "phase.start"

    def test_skips_blank_and_corrupt_lines(self, tmp_path):
        events = tmp_path / "events.jsonl"
        emit(events, EventType.NOTE, "real-1")
        # Manually inject corruption
        with events.open("a", encoding="utf-8") as f:
            f.write("\n")  # blank
            f.write("not-json{\n")  # corrupt
        emit(events, EventType.NOTE, "real-2")
        result = tail_events(events, n=10)
        # Corrupt + blank lines silently skipped
        summaries = [e["summary"] for e in result]
        assert "real-1" in summaries
        assert "real-2" in summaries
