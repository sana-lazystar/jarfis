"""JARFIS Event Stream — emit() + EventType + atomic JSONL append.

Design SSOT: ~/repos/jarfis/.personal/meetings/20260513-jarfis-eventstream/
             design-output-formats.md (D4~D10 lockdown 2026-05-13)

Constraints (from SSOT):
  - 10 EventType members (M-3 lockdown, design-output-formats.md:280-296)
  - 4 Level → ANSI colors (D5)
  - summary: ≤80 chars, no emoji, no trailing period
  - JSONL append is atomic (POSIX O_APPEND, write ≤ PIPE_BUF)
  - emit() returns the dict; never raises on disk full (caller's job)
"""

import json
import os
import unicodedata
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterable

MAX_SUMMARY_LEN = 80
PROTECTED_FIELDS = frozenset({"ts", "type", "level", "summary"})


class EventType(str, Enum):
    """v1.0 EventType enum — 10 members, locked per M-3 (2026-05-13).

    Re-litigating this set requires a new sys-implement run with explicit
    design-output-formats.md amendment. v2 candidates listed in SSOT:300-308.
    """

    PHASE_START = "phase.start"
    PHASE_END = "phase.end"
    PHASE_ABORT = "phase.abort"
    CHECKPOINT = "checkpoint"
    AGENT_SPAWN = "agent.spawn"
    AGENT_DONE = "agent.done"
    TOOL = "tool"
    NOTE = "note"
    ERROR = "error"
    DIALECTIC_UNRESOLVED = "dialectic.unresolved"


class Level(str, Enum):
    """4-color rule (D5). dialectic also rendered purple via [STUCK] text."""

    HIGHLIGHT = "highlight"
    INFO = "info"
    ERROR = "error"
    DEBUG = "debug"


DEFAULT_LEVEL: dict[EventType, Level] = {
    EventType.PHASE_START: Level.HIGHLIGHT,
    EventType.PHASE_END: Level.HIGHLIGHT,
    EventType.PHASE_ABORT: Level.HIGHLIGHT,
    EventType.CHECKPOINT: Level.HIGHLIGHT,
    EventType.DIALECTIC_UNRESOLVED: Level.HIGHLIGHT,
    EventType.AGENT_SPAWN: Level.INFO,
    EventType.AGENT_DONE: Level.INFO,
    EventType.TOOL: Level.INFO,
    EventType.NOTE: Level.INFO,
    EventType.ERROR: Level.ERROR,
}

GLYPH: dict[EventType, str] = {
    EventType.PHASE_START: "▶",
    EventType.PHASE_END: "✓",
    EventType.PHASE_ABORT: "✗",
    EventType.CHECKPOINT: "●",
    EventType.DIALECTIC_UNRESOLVED: "⚠",
    EventType.ERROR: "✗",
    EventType.AGENT_SPAWN: "",
    EventType.AGENT_DONE: "",
    EventType.TOOL: "",
    EventType.NOTE: "",
}

ANSI: dict[Level, str] = {
    Level.HIGHLIGHT: "\033[35m\033[1m",
    Level.INFO: "\033[97m",
    Level.ERROR: "\033[31m\033[1m",
    Level.DEBUG: "\033[90m\033[2m",
}
ANSI_RESET = "\033[0m"

# Re-export for cli.py convenience.
__all__ = [
    "ANSI",
    "ANSI_RESET",
    "DEFAULT_LEVEL",
    "GLYPH",
    "MAX_SUMMARY_LEN",
    "EmitError",
    "EventType",
    "Level",
    "emit",
    "render_line",
    "tail_events",
]


class EmitError(ValueError):
    """Raised when emit() input violates SSOT constraints."""


def _validate_summary(summary: Any) -> str:
    if not isinstance(summary, str):
        raise EmitError(f"summary must be str, got {type(summary).__name__}")
    if not summary:
        raise EmitError("summary must not be empty")
    if len(summary) > MAX_SUMMARY_LEN:
        raise EmitError(
            f"summary exceeds {MAX_SUMMARY_LEN} chars (got {len(summary)})"
        )
    if summary[-1] in (".", "。"):
        raise EmitError("summary must not end with a period")
    for ch in summary:
        cat = unicodedata.category(ch)
        # Symbol/Other (So) covers most pictographic emoji.
        # Glyph chars (▶ ✓ ✗ ● ⚠) belong to category So too — stripped here
        # because they are display-layer concerns, prepended by render_line().
        if cat == "So":
            raise EmitError(f"summary must not contain emoji/symbol char: {ch!r}")
    return summary


def emit(
    events_path: Path | str,
    type_: EventType | str,
    summary: str,
    *,
    level: Level | str | None = None,
    extras: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Append a single event to events.jsonl atomically.

    Args:
        events_path: Path to events.jsonl (created if missing, parents auto-mkdir).
        type_: EventType or its string value.
        summary: ≤80 chars, no emoji, no trailing period.
        level: Optional override; default derived from type via DEFAULT_LEVEL.
        extras: Optional dict merged into event; cannot override protected fields.
        timestamp: Optional explicit ts; default = datetime.now(timezone.utc).

    Returns:
        The event dict (also written to disk).

    Raises:
        EmitError: on validation failure.
    """
    et = EventType(type_) if not isinstance(type_, EventType) else type_
    summary = _validate_summary(summary)
    if level is None:
        lv = DEFAULT_LEVEL[et]
    else:
        lv = Level(level) if not isinstance(level, Level) else level
    ts = timestamp or datetime.now(timezone.utc)

    event: dict[str, Any] = {
        "ts": ts.isoformat(),
        "type": et.value,
        "level": lv.value,
        "summary": summary,
    }
    if extras:
        clash = PROTECTED_FIELDS & set(extras.keys())
        if clash:
            raise EmitError(
                f"extras cannot override protected fields: {sorted(clash)}"
            )
        event.update(extras)

    path = Path(events_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n"

    # POSIX O_APPEND atomic for writes ≤ PIPE_BUF (typically 4096).
    # An event line is far smaller; concurrent appenders cannot interleave bytes.
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        os.write(fd, line.encode("utf-8"))
    finally:
        os.close(fd)
    return event


def render_line(event: dict[str, Any], *, color: bool = True) -> str:
    """Render a single event for statusline display.

    Format: `  HH:MM:SS  [type]            (glyph) summary`

    The leading 2-space indent matches the multi-line statusline body
    convention (D6). Type column is left-padded to 16 chars.
    """
    et = EventType(event["type"])
    lv_value = event.get("level") or DEFAULT_LEVEL[et].value
    lv = Level(lv_value)
    glyph = GLYPH[et]
    ts = event["ts"]
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(ts)
        time_part = dt.astimezone().strftime("%H:%M:%S")
    except (ValueError, TypeError):
        if "T" in ts:
            time_part = ts.split("T")[1][:8]
        else:
            time_part = ts[:8]
    type_col = f"[{et.value}]".ljust(16)
    body = f"{glyph} {event['summary']}" if glyph else event["summary"]
    line = f"  {time_part}  {type_col} {body}"
    if color:
        return f"{ANSI[lv]}{line}{ANSI_RESET}"
    return line


def tail_events(
    events_path: Path | str,
    n: int = 5,
    *,
    levels: Iterable[Level | str] | None = None,
) -> list[dict[str, Any]]:
    """Read last N events from events.jsonl, optionally filtered by level.

    Returns [] if file missing. Corrupt/blank lines are silently skipped
    (statusline must never crash on a half-written line).
    """
    path = Path(events_path)
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if not raw:
                continue
            try:
                events.append(json.loads(raw))
            except json.JSONDecodeError:
                continue
    if levels:
        wanted = {l.value if isinstance(l, Level) else l for l in levels}
        events = [e for e in events if e.get("level") in wanted]
    return events[-n:]
