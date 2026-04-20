"""JARFIS Trace — performance tracing for agent invocations.

Primary data source for Monitor App. Separated concerns from audit.jsonl:
- audit.jsonl = workflow events (Phase transitions, gate results)
- traces.jsonl = performance metrics (token counts, elapsed time, per-agent details)

v4.0.5 N-2: controlled by the `JARFIS_TRACE` environment variable.
  JARFIS_TRACE unset OR "0"  → every entry point is a no-op.
  JARFIS_TRACE non-"0"        → spans are written to the caller-supplied path.

All I/O and serialization paths are wrapped in try/except so a trace failure
never flips a Phase outcome. See adr/v4.0.5-trace-design.md.

Note (P9): traces.jsonl is not a recovery source. Missing/corrupt files have
no functional impact.
"""

import json
import os
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


def is_enabled() -> bool:
    """Return True when JARFIS_TRACE is set to anything other than "0"."""
    return os.getenv("JARFIS_TRACE", "0") != "0"


_DEFAULT_TRACE_PATH = "/tmp/jarfis-trace.jsonl"


def _safe_append(trace_path, payload):
    """Append one JSON line to `trace_path`. Any failure is swallowed silently.

    Kept private so instrumentation sites don't each re-implement the shield.
    Callers that want to know about failures should check `is_enabled()` and
    do their own I/O; this helper's contract is "best effort, never raises".
    """
    try:
        with open(trace_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _resolve_trace_path(path):
    """Path precedence: explicit arg → $JARFIS_TRACE_PATH → _DEFAULT_TRACE_PATH."""
    if path:
        return path
    return os.getenv("JARFIS_TRACE_PATH") or _DEFAULT_TRACE_PATH


def log_event(event, attrs=None, path=None):
    """Append one JSONL event to the trace file.

    No-op when `JARFIS_TRACE` is unset or "0". Intended for entry/exit
    instrumentation on hot paths (5b) — keep attrs small (counts, ids,
    durations) so the file stays readable by hand during post-mortem.

    Args:
        event: short snake_case event name (e.g. "compose_start").
        attrs: optional dict of simple JSON-serializable attributes.
        path:  optional override. If omitted, $JARFIS_TRACE_PATH is used,
               else /tmp/jarfis-trace.jsonl.
    """
    if not is_enabled():
        return

    try:
        payload = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "attrs": attrs or {},
        }
    except Exception:
        return
    _safe_append(_resolve_trace_path(path), payload)


@contextmanager
def trace_agent(trace_path, trace_id, phase, persona, skills):
    """Trace an agent invocation as a context manager.

    Usage:
        with trace_agent("traces.jsonl", "run-001", 4, "frontend-developer", ["react"]) as span_id:
            # agent execution happens here
            pass

    When JARFIS_TRACE is off, yields an identifiable no-op span_id and skips
    the write entirely (no file created).

    Args:
        trace_path: Path to traces.jsonl file.
        trace_id: Unique workflow trace ID.
        phase: Current phase number.
        persona: Persona name being used.
        skills: List of skill names loaded.

    Yields:
        span_id: Unique span identifier for this agent invocation, or a
        deterministic "<persona>-disabled" sentinel when tracing is off.
    """
    if not is_enabled():
        yield f"agent-{persona}-disabled"
        return

    try:
        span_id = f"agent-{persona}-{uuid.uuid4().hex[:8]}"
        start = time.monotonic()
        start_ts = datetime.now(timezone.utc).isoformat()
    except Exception:
        # setup itself failed — yield a sentinel and skip recording
        yield f"agent-{persona}-disabled"
        return

    yield span_id

    try:
        duration_ms = int((time.monotonic() - start) * 1000)
        span = {
            "traceId": trace_id,
            "spanId": span_id,
            "parentSpanId": f"phase-{phase}",
            "type": "agent",
            "persona": persona,
            "skills": skills,
            "startTime": start_ts,
            "duration_ms": duration_ms,
        }
    except Exception:
        return
    _safe_append(trace_path, span)


def trace_phase(trace_path, trace_id, phase, duration_ms):
    """Record a phase completion trace.

    No-op when JARFIS_TRACE is off.

    Args:
        trace_path: Path to traces.jsonl file.
        trace_id: Unique workflow trace ID.
        phase: Phase number that completed.
        duration_ms: Duration of the phase in milliseconds.
    """
    if not is_enabled():
        return

    span = {
        "traceId": trace_id,
        "spanId": f"phase-{phase}",
        "type": "phase",
        "phase": phase,
        "duration_ms": duration_ms,
    }
    _safe_append(trace_path, span)
