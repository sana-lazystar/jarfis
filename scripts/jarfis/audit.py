"""JARFIS Audit — append-only event log for workflow observability.

Hybrid state model (래칫 R2):
- state.json: 직접 기록, 현재 상태 즉시 조회 (기존 유지)
- audit.jsonl: append-only 감사 로그, 디버깅/Monitor App용

Note (P9): audit.jsonl은 복구 소스가 아님. 누락/손상 시 기능 영향 없음.
"""

import json
from datetime import datetime, timezone

EVENT_TYPES = [
    "WorkflowStarted", "WorkflowCompleted", "WorkflowAborted",
    "PhaseStarted", "PhaseCompleted",
    "AgentInvoked", "AgentCompleted", "AgentFailed",
    "QualityGateEvaluated", "GateApproved",
    "RatchetChecked",
    "AutoCommit",
    "FallbackTriggered", "CircuitBreakerChanged",
]


def append_event(audit_path, event_type, **data):
    """Append an event to the audit log.

    Args:
        audit_path: Path to audit.jsonl file.
        event_type: One of EVENT_TYPES.
        **data: Additional event data.

    Returns:
        The event dict that was written.

    Raises:
        ValueError: If event_type is not recognized.
    """
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type: {event_type}")

    event = {
        "type": event_type,
        "ts": datetime.now(timezone.utc).isoformat(),
        **data,
    }

    with open(audit_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")

    return event


def read_events(audit_path):
    """Read all events from the audit log.

    Corrupted lines are silently skipped (W1-4: process kill can leave
    partial JSON lines). This is acceptable because audit.jsonl is not
    a recovery source (P9).

    Args:
        audit_path: Path to audit.jsonl file.

    Returns:
        List of event dicts.
    """
    import os
    if not os.path.exists(audit_path):
        return []

    events = []
    with open(audit_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue  # Skip corrupted lines
    return events
