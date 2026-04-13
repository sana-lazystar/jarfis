"""JARFIS Audit — append-only event log for workflow observability.

Hybrid state model (Ratchet R2):
- state.json: direct write, immediate current-state lookup (unchanged)
- audit.jsonl: append-only audit log, for debugging/Monitor App

Note (P9): audit.jsonl is not a recovery source. Missing/corrupt files have no functional impact.
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
