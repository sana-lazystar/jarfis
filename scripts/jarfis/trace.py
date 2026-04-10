"""JARFIS Trace — performance tracing for agent invocations.

Monitor App의 주요 데이터 소스. audit.jsonl과 관심사 분리:
- audit.jsonl = 워크플로우 이벤트 (Phase 전환, 게이트 결과)
- traces.jsonl = 성능 메트릭 (토큰 수, 소요 시간, 에이전트별 상세)

Note (P9): traces.jsonl은 복구 소스가 아님. 누락/손상 시 기능 영향 없음.
"""

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


@contextmanager
def trace_agent(trace_path, trace_id, phase, persona, skills):
    """Trace an agent invocation as a context manager.

    Usage:
        with trace_agent("traces.jsonl", "run-001", 4, "frontend-developer", ["react"]) as span_id:
            # agent execution happens here
            pass

    Args:
        trace_path: Path to traces.jsonl file.
        trace_id: Unique workflow trace ID.
        phase: Current phase number.
        persona: Persona name being used.
        skills: List of skill names loaded.

    Yields:
        span_id: Unique span identifier for this agent invocation.
    """
    span_id = f"agent-{persona}-{uuid.uuid4().hex[:8]}"
    start = time.monotonic()
    start_ts = datetime.now(timezone.utc).isoformat()

    yield span_id

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

    with open(trace_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(span, ensure_ascii=False) + "\n")


def trace_phase(trace_path, trace_id, phase, duration_ms):
    """Record a phase completion trace.

    Args:
        trace_path: Path to traces.jsonl file.
        trace_id: Unique workflow trace ID.
        phase: Phase number that completed.
        duration_ms: Duration of the phase in milliseconds.
    """
    span = {
        "traceId": trace_id,
        "spanId": f"phase-{phase}",
        "type": "phase",
        "phase": phase,
        "duration_ms": duration_ms,
    }

    with open(trace_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(span, ensure_ascii=False) + "\n")
