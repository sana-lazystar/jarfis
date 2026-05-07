"""JARFIS Implement — sys-implement deliverables workspace management.

ADR-0003 synthesis (Saga + LangGraph + Command + Clean Architecture).
Workspace location: {JARFIS_SOURCE}/.personal/sys-implements/{plan-name}/.

Subcommands:
    init <plan-name> "<request>"        Create workspace (manifest + state + log/ + artifacts/)
    state <plan-name> --get <key>       Read state.json (dotted nested key supported)
    state <plan-name> --set k=v         Write top-level key to state.json
    state <plan-name> --set-nested k v  Write nested key (e.g. steps.step0.status completed)
    log <plan-name> append <json>       Append-only event log entry
    resume <plan-name>                  Print resume info (currentState, user_gates_pending, nextAction)
    list [--status pending|in_progress|completed|failed|aborted|all]
                                        List all plans grouped by status
    archive <plan-name>                 Move to _archive/{YYYYMMDD}-{plan-name}/
"""

from __future__ import annotations

import errno
import fcntl
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from .utils import (
    get_personal_dir,
    get_source_path,
    json_error,
    json_output,
    parse_json_value,
)


# ── Constants (ADR-0003) ────────────────────────────────────────────

PLAN_NAME_RE = re.compile(r"^[a-z][a-z0-9-]*$")
PLAN_NAME_MAX_LEN = 40

MANIFEST_SCHEMA_VERSION = "sys-implement-manifest-v1"
STATE_SCHEMA_VERSION = "sys-implement-state-v1"
WORKSPACE_VERSION = "0.1.0"

# §2.2 manifest plannedSteps (default — Step 0~5 + injected 1.5/1.7/4.5)
DEFAULT_PLANNED_STEPS = [
    "step0",
    "step1",
    "step1.5",
    "step1.7",
    "step2",
    "step3",
    "step3.5",
    "step4",
    "step4.5",
    "step5",
]

# §2.5 status enum
STATUS_PENDING = "pending"
STATUS_IN_PROGRESS = "in_progress"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
STATUS_ABORTED = "aborted"
STATUS_SKIPPED = "skipped"
VALID_STATUSES = frozenset({
    STATUS_PENDING,
    STATUS_IN_PROGRESS,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_ABORTED,
    STATUS_SKIPPED,
})


# ── Custom exceptions ───────────────────────────────────────────────


class InvalidPlanNameError(ValueError):
    """plan-name does not match kebab-case regex or exceeds max length."""


class WorkspaceLockedError(RuntimeError):
    """Another process holds the workspace lock."""


class WorkspaceNotFoundError(FileNotFoundError):
    """Plan workspace directory does not exist."""


class LogAppendOnlyViolation(RuntimeError):
    """Attempted to overwrite an existing log entry."""


# ── Path helpers ────────────────────────────────────────────────────


def get_implements_dir():
    """Return {JARFIS_SOURCE}/.personal/sys-implements/ (the parent of all plans)."""
    return os.path.join(get_personal_dir(), "sys-implements")


def get_plan_dir(plan_name: str) -> str:
    """Return path to a plan workspace (does not check existence)."""
    return os.path.join(get_implements_dir(), plan_name)


def get_archive_dir() -> str:
    """Return {implements_dir}/_archive/."""
    return os.path.join(get_implements_dir(), "_archive")


# ── Validation ──────────────────────────────────────────────────────


def _validate_plan_name(plan_name: str) -> None:
    """Raise InvalidPlanNameError if plan_name is invalid."""
    if not plan_name:
        raise InvalidPlanNameError("plan-name cannot be empty")
    if len(plan_name) > PLAN_NAME_MAX_LEN:
        raise InvalidPlanNameError(
            f"plan-name length {len(plan_name)} exceeds max {PLAN_NAME_MAX_LEN}"
        )
    if not PLAN_NAME_RE.match(plan_name):
        raise InvalidPlanNameError(
            f"plan-name '{plan_name}' must match {PLAN_NAME_RE.pattern} (kebab-case)"
        )


def _ensure_workspace_exists(plan_dir: str) -> None:
    """Raise WorkspaceNotFoundError if plan_dir does not exist."""
    if not os.path.isdir(plan_dir):
        raise WorkspaceNotFoundError(
            f"Workspace not found: {plan_dir}. "
            f"Run `jarfis_cli.py implement init <plan-name> \"<request>\"` first."
        )


# ── Lock file (concurrency guard) ───────────────────────────────────


def _lock_path(plan_dir: str) -> str:
    return os.path.join(plan_dir, ".lock")


def _acquire_lock(plan_dir: str) -> int:
    """Acquire exclusive lock on {plan_dir}/.lock. Raises WorkspaceLockedError if held."""
    lock_file = _lock_path(plan_dir)
    fd = os.open(lock_file, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        os.close(fd)
        if exc.errno in (errno.EWOULDBLOCK, errno.EAGAIN):
            raise WorkspaceLockedError(
                f"Workspace {plan_dir} is locked by another process"
            ) from exc
        raise
    return fd


def _release_lock(fd: int, plan_dir: str) -> None:
    """Release the lock and remove the .lock file."""
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
    finally:
        os.close(fd)
        try:
            os.remove(_lock_path(plan_dir))
        except FileNotFoundError:
            pass


# ── Atomic write helpers ────────────────────────────────────────────


def _atomic_write_json(path: str, data) -> None:
    """Atomic JSON write via tmp + rename (POSIX guarantee)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _atomic_write_text(path: str, text: str) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _now_iso() -> str:
    # Microsecond precision so back-to-back updates produce distinct timestamps.
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ── Log helpers (append-only) ───────────────────────────────────────


def _next_log_id(plan_dir: str) -> str:
    """Return next 4-digit log ID by scanning log/ directory."""
    log_dir = os.path.join(plan_dir, "log")
    if not os.path.isdir(log_dir):
        return "0000"
    max_id = -1
    for fname in os.listdir(log_dir):
        if fname.endswith(".json") and len(fname) >= 4 and fname[:4].isdigit():
            max_id = max(max_id, int(fname[:4]))
    return f"{max_id + 1:04d}"


def _log_filename(log_id: str, step: str | None, event: str) -> str:
    """Return canonical log filename: {NNNN}-{step}-{event}.json or {NNNN}-{event}.json."""
    safe_event = re.sub(r"[^a-z0-9-]+", "-", event.lower()).strip("-") or "event"
    if step:
        safe_step = re.sub(r"[^a-z0-9.]+", "-", step.lower()).strip("-")
        return f"{log_id}-{safe_step}-{safe_event}.json"
    return f"{log_id}-{safe_event}.json"


def _write_log_entry(plan_dir: str, entry: dict) -> str:
    """Write a log entry. Refuses to overwrite (append-only)."""
    log_dir = os.path.join(plan_dir, "log")
    os.makedirs(log_dir, exist_ok=True)
    log_id = entry.get("id") or _next_log_id(plan_dir)
    entry["id"] = log_id
    if "ts" not in entry:
        entry["ts"] = _now_iso()
    fname = _log_filename(log_id, entry.get("step"), entry.get("event", "event"))
    path = os.path.join(log_dir, fname)

    # Append-only: if a file with this ID prefix already exists, refuse.
    for existing in os.listdir(log_dir):
        if existing.startswith(f"{log_id}-"):
            raise LogAppendOnlyViolation(
                f"Log entry {log_id} already exists at {existing}; append-only."
            )
    _atomic_write_json(path, entry)
    return path


# ── State checkpoint helper (mirror log entry into state.checkpoints[]) ─────


def _append_checkpoint(state: dict, log_entry: dict) -> None:
    """Mirror the log entry's id/ts/event/step into state.checkpoints[]."""
    cp = {
        "id": log_entry["id"],
        "ts": log_entry["ts"],
        "event": log_entry["event"],
    }
    if "step" in log_entry and log_entry["step"]:
        cp["step"] = log_entry["step"]
    state.setdefault("checkpoints", []).append(cp)


# ── Git state snapshot ──────────────────────────────────────────────


def _git_state_at_start() -> dict:
    """Capture JARFIS repo state for manifest. Best-effort."""
    repo = get_source_path()
    out = {"jarfis_repo": repo, "branch": None, "headSha": None}
    try:
        out["branch"] = subprocess.check_output(
            ["git", "-C", repo, "branch", "--show-current"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    try:
        out["headSha"] = subprocess.check_output(
            ["git", "-C", repo, "rev-parse", "HEAD"],
            text=True, stderr=subprocess.DEVNULL,
        ).strip() or None
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return out


def _read_jarfis_version() -> str:
    """Read ~/.claude/.jarfis-version, fallback unknown."""
    from .utils import get_claude_dir
    path = os.path.join(get_claude_dir(), ".jarfis-version")
    try:
        with open(path) as f:
            return f.read().strip()
    except (FileNotFoundError, OSError):
        return "unknown"


# ── §2.2 manifest + §2.3 state initial documents ────────────────────


def _build_initial_manifest(plan_name: str, request: str) -> dict:
    return {
        "version": WORKSPACE_VERSION,
        "schemaVersion": MANIFEST_SCHEMA_VERSION,
        "planName": plan_name,
        "request": request,
        "createdAt": _now_iso(),
        "createdBy": "main-session",
        "executionMode": None,
        "orchestrator": "main",
        "plannedSteps": list(DEFAULT_PLANNED_STEPS),
        "git_state_at_start": _git_state_at_start(),
        "jarfis_version_at_start": _read_jarfis_version(),
    }


def _build_initial_state(plan_name: str) -> dict:
    now = _now_iso()
    steps = {step: {"status": STATUS_PENDING} for step in DEFAULT_PLANNED_STEPS}
    steps["step0"]["status"] = STATUS_IN_PROGRESS
    steps["step0"]["startedAt"] = now
    return {
        "version": WORKSPACE_VERSION,
        "schemaVersion": STATE_SCHEMA_VERSION,
        "planName": plan_name,
        "lastUpdated": now,
        "lastUpdatedBy": "main-session",
        "currentState": "step0",
        "currentStateLabel": "Assess System State",
        "nextStateHint": "step1",
        "executionMode": None,
        "steps": steps,
        "blockers": [],
        "user_gates_pending": [],
        "checkpoints": [],
    }


def _resume_md_body(plan_name: str) -> str:
    return (
        f"# RESUME — sys-implement workspace `{plan_name}`\n\n"
        f"> 새 Claude Code 세션 / 컨텍스트 compact 후 — **이 파일 먼저 읽고** 따라하세요.\n\n"
        f"## §1. Boot 3 단계\n\n"
        f"1. `cat state.json` — 현 위치 1줄 (currentState, user_gates_pending, blockers)\n"
        f"2. `cat manifest.json` — 작업 정의 (request, plannedSteps, executionMode)\n"
        f"3. `ls log/` — 마지막 entry 확인 (event sequence)\n\n"
        f"## §2. 진입 직후 체크리스트\n\n"
        f"- [ ] `state.json.user_gates_pending` 비어있는지 확인\n"
        f"- [ ] `state.json.blockers` 비어있는지 확인\n"
        f"- [ ] `state.json.currentState` 부터 재개\n\n"
        f"## §3. CLI\n\n"
        f"```bash\n"
        f"# resume info\n"
        f"jarfis_cli.py implement resume {plan_name}\n\n"
        f"# state CRUD\n"
        f"jarfis_cli.py implement state {plan_name} --get currentState\n"
        f"jarfis_cli.py implement state {plan_name} --set-nested steps.step1.status completed\n\n"
        f"# log append\n"
        f"jarfis_cli.py implement log {plan_name} append '{{\"event\":\"step.completed\",\"step\":\"step1\"}}'\n"
        f"```\n"
    )


def _readme_body(plan_name: str, request: str) -> str:
    return (
        f"# {plan_name}\n\n"
        f"**Request**: {request}\n\n"
        f"## Layout (ADR-0003 §2.1)\n\n"
        f"```\n"
        f"{plan_name}/\n"
        f"├── manifest.json      # immutable after init\n"
        f"├── state.json         # mutable — current state machine instance\n"
        f"├── RESUME.md          # boot procedure\n"
        f"├── README.md          # this file\n"
        f"├── log/               # append-only event log\n"
        f"│   └── NNNN-{{step}}-{{event}}.json\n"
        f"├── artifacts/         # step deliverables\n"
        f"│   └── step{{N}}/...\n"
        f"└── compensation/      # rollback (optional)\n"
        f"```\n\n"
        f"## CLI\n\n"
        f"See `RESUME.md §3`.\n"
    )


# ── cmd_init ────────────────────────────────────────────────────────


def cmd_init(args):
    if len(args) < 2:
        json_error("Usage: jarfis_cli.py implement init <plan-name> \"<request>\"")
    plan_name, request = args[0], args[1]
    _validate_plan_name(plan_name)

    plan_dir = get_plan_dir(plan_name)
    if os.path.isdir(plan_dir):
        json_error(
            f"Workspace already exists: {plan_dir}. "
            f"Use `implement resume {plan_name}` to continue, or pick a new plan-name (e.g. {plan_name}-v2).",
            path=plan_dir,
        )

    # Create directory tree
    os.makedirs(plan_dir, exist_ok=False)
    for sub in ("log", "artifacts", "compensation"):
        os.makedirs(os.path.join(plan_dir, sub), exist_ok=True)
    # Pre-create per-step artifact directories
    for step in DEFAULT_PLANNED_STEPS:
        os.makedirs(os.path.join(plan_dir, "artifacts", step), exist_ok=True)

    # Write top-level files atomically
    manifest = _build_initial_manifest(plan_name, request)
    state = _build_initial_state(plan_name)
    _atomic_write_json(os.path.join(plan_dir, "manifest.json"), manifest)
    _atomic_write_text(os.path.join(plan_dir, "RESUME.md"), _resume_md_body(plan_name))
    _atomic_write_text(os.path.join(plan_dir, "README.md"), _readme_body(plan_name, request))

    # Initial log entry — this also seeds checkpoints in state
    init_entry = {
        "id": "0000",
        "ts": _now_iso(),
        "event": "init",
        "step": None,
        "actor": "main-session",
        "details": {
            "request": request,
            "plannedSteps": list(DEFAULT_PLANNED_STEPS),
        },
    }
    _write_log_entry(plan_dir, init_entry)
    _append_checkpoint(state, init_entry)
    _atomic_write_json(os.path.join(plan_dir, "state.json"), state)

    json_output({
        "success": True,
        "planName": plan_name,
        "planDir": plan_dir,
        "currentState": "step0",
    })


# ── cmd_state — read / write top-level / write nested ───────────────


def _read_state(plan_name: str) -> tuple[str, dict]:
    plan_dir = get_plan_dir(plan_name)
    _ensure_workspace_exists(plan_dir)
    state_path = os.path.join(plan_dir, "state.json")
    with open(state_path) as f:
        return state_path, json.load(f)


def _set_nested_key(d: dict, dotted: str, value) -> None:
    # Greedy longest-prefix match honors literal dotted keys (e.g. "step1.5")
    # that already exist in the dict, while still creating fresh nesting for
    # paths that don't collide.
    parts = dotted.split(".")
    cur = d
    i = 0
    while i < len(parts):
        matched = False
        for j in range(len(parts), i, -1):
            candidate = ".".join(parts[i:j])
            if candidate in cur:
                if j == len(parts):
                    cur[candidate] = value
                    return
                if isinstance(cur[candidate], dict):
                    cur = cur[candidate]
                    i = j
                    matched = True
                    break
        if matched:
            continue
        part = parts[i]
        if i == len(parts) - 1:
            cur[part] = value
            return
        if part not in cur or not isinstance(cur[part], dict):
            cur[part] = {}
        cur = cur[part]
        i += 1


def _get_nested_key(d, dotted: str):
    parts = dotted.split(".")
    cur = d
    i = 0
    while i < len(parts):
        if not isinstance(cur, dict):
            return None
        matched = False
        for j in range(len(parts), i, -1):
            candidate = ".".join(parts[i:j])
            if candidate in cur:
                if j == len(parts):
                    return cur[candidate]
                cur = cur[candidate]
                i = j
                matched = True
                break
        if not matched:
            return None
    return cur


def cmd_state(args):
    """state <plan-name> --get k | --set k=v | --set-nested k v"""
    if not args:
        json_error("Usage: jarfis_cli.py implement state <plan-name> --get|--set|--set-nested ...")
    plan_name = args[0]
    rest = args[1:]
    if not rest:
        json_error("state requires --get / --set / --set-nested")

    state_path, state = _read_state(plan_name)

    if rest[0] == "--get":
        if len(rest) < 2:
            json_error("--get requires a key")
        key = rest[1]
        val = state.get(key) if "." not in key else _get_nested_key(state, key)
        print(json.dumps(val, ensure_ascii=False))
        return

    if rest[0] == "--set":
        if len(rest) < 2:
            json_error("--set requires key=value")
        kv = rest[1]
        if "=" not in kv:
            json_error("--set value must be key=value")
        key, raw = kv.split("=", 1)
        state[key] = parse_json_value(raw)
        state["lastUpdated"] = _now_iso()
        _atomic_write_json(state_path, state)
        json_output({"success": True, "key": key, "value": state[key]})
        return

    if rest[0] == "--set-nested":
        if len(rest) < 3:
            json_error("--set-nested requires <dotted.key> <value>")
        dotted, raw = rest[1], rest[2]
        _set_nested_key(state, dotted, parse_json_value(raw))
        state["lastUpdated"] = _now_iso()
        _atomic_write_json(state_path, state)
        json_output({"success": True, "key": dotted, "value": _get_nested_key(state, dotted)})
        return

    json_error(f"Unknown state op: {rest[0]}")


# ── cmd_log append ──────────────────────────────────────────────────


def cmd_log(args):
    """log <plan-name> append <json>"""
    if len(args) < 3 or args[1] != "append":
        json_error("Usage: jarfis_cli.py implement log <plan-name> append '<json>'")
    plan_name, _, payload_json = args[0], args[1], args[2]
    plan_dir = get_plan_dir(plan_name)
    _ensure_workspace_exists(plan_dir)
    try:
        entry = json.loads(payload_json)
    except json.JSONDecodeError as exc:
        json_error(f"Invalid JSON: {exc}")
    if not isinstance(entry, dict):
        json_error("log entry must be a JSON object")
    entry.setdefault("event", "event")
    entry.setdefault("actor", "main-session")
    path = _write_log_entry(plan_dir, entry)

    # Mirror into state.checkpoints
    state_path, state = _read_state(plan_name)
    _append_checkpoint(state, entry)
    state["lastUpdated"] = _now_iso()
    _atomic_write_json(state_path, state)

    json_output({"success": True, "logFile": path, "id": entry["id"]})


# ── cmd_resume ──────────────────────────────────────────────────────


def cmd_resume(args):
    """resume <plan-name>"""
    if not args:
        json_error("Usage: jarfis_cli.py implement resume <plan-name>")
    plan_name = args[0]
    _, state = _read_state(plan_name)

    next_action = (
        "사용자 답변 대기 — user_gates_pending 의 question 다시 띄우기"
        if state.get("user_gates_pending")
        else f"{state.get('currentState')} 부터 재개"
    )
    json_output({
        "planName": plan_name,
        "currentState": state.get("currentState"),
        "currentStateLabel": state.get("currentStateLabel"),
        "executionMode": state.get("executionMode"),
        "blockers": state.get("blockers", []),
        "user_gates_pending": state.get("user_gates_pending", []),
        "lastUpdated": state.get("lastUpdated"),
        "nextAction": next_action,
    })


# ── cmd_list ────────────────────────────────────────────────────────


def cmd_list(args):
    """list [--status pending|in_progress|completed|failed|aborted|all]"""
    status_filter = "all"
    if args and args[0] == "--status":
        if len(args) < 2:
            json_error("--status requires a value")
        status_filter = args[1]

    impl_dir = get_implements_dir()
    if not os.path.isdir(impl_dir):
        json_output({})
        return

    grouped: dict[str, list] = {}
    for entry in sorted(os.listdir(impl_dir)):
        if entry.startswith("_") or entry.startswith("."):
            continue
        plan_dir = os.path.join(impl_dir, entry)
        state_path = os.path.join(plan_dir, "state.json")
        if not os.path.isfile(state_path):
            continue
        try:
            with open(state_path) as f:
                state = json.load(f)
        except (json.JSONDecodeError, OSError):
            continue

        # Determine plan-level status: if all steps completed → completed,
        # else in_progress (presence of currentState != skipped means active)
        steps = state.get("steps", {})
        statuses = {s.get("status") for s in steps.values() if isinstance(s, dict)}
        if statuses == {STATUS_COMPLETED} or statuses == {STATUS_COMPLETED, STATUS_SKIPPED}:
            plan_status = STATUS_COMPLETED
        elif STATUS_FAILED in statuses:
            plan_status = STATUS_FAILED
        elif STATUS_ABORTED in statuses:
            plan_status = STATUS_ABORTED
        elif STATUS_IN_PROGRESS in statuses:
            plan_status = STATUS_IN_PROGRESS
        else:
            plan_status = STATUS_PENDING

        if status_filter not in ("all", plan_status):
            continue

        grouped.setdefault(plan_status, []).append({
            "planName": state.get("planName", entry),
            "currentState": state.get("currentState"),
            "lastUpdated": state.get("lastUpdated"),
            "executionMode": state.get("executionMode"),
        })

    json_output(grouped)


# ── cmd_archive ─────────────────────────────────────────────────────


def cmd_archive(args):
    """archive <plan-name>"""
    if not args:
        json_error("Usage: jarfis_cli.py implement archive <plan-name>")
    plan_name = args[0]
    plan_dir = get_plan_dir(plan_name)
    _ensure_workspace_exists(plan_dir)
    archive_root = get_archive_dir()
    os.makedirs(archive_root, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    target = os.path.join(archive_root, f"{stamp}-{plan_name}")
    # Avoid clobber: append -N if collision
    suffix = 1
    while os.path.exists(target):
        target = os.path.join(archive_root, f"{stamp}-{plan_name}-{suffix}")
        suffix += 1
    shutil.move(plan_dir, target)
    json_output({"success": True, "archivedTo": target})


# ── main entry point ────────────────────────────────────────────────


SUBCOMMANDS = {
    "init": cmd_init,
    "state": cmd_state,
    "log": cmd_log,
    "resume": cmd_resume,
    "list": cmd_list,
    "archive": cmd_archive,
}


# ── ADR-0005 — Dialectic evidence policy (validate_citations + classify_verdict) ──

from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass
class Citation:
    """A `path:LNN` (or `path:N-M`) reference parsed from advocate/critic output."""
    path: str
    line_start: int
    line_end: int
    status: str  # "valid" | "invalid_path" | "invalid_line"
    text: Optional[str] = None
    raw: str = ""


@dataclass
class Verdict:
    """Outcome of a one-round Force-acknowledge dialectic."""
    status: str  # "ACKNOWLEDGED-advocate-wins" | "ACKNOWLEDGED-critic-wins" | "UNRESOLVED"
    reason: str
    advocate_citations: List[Citation] = field(default_factory=list)
    critic_citations: List[Citation] = field(default_factory=list)


# Backtick-wrapped `path:LNN` or `path:N-M`. Path must contain a slash so we
# don't catch ordinary inline code like `int:5`.
_CITATION_RE = re.compile(r"`(~?/?[^`\s:]+/[^`\s:]+):(\d+)(?:-(\d+))?`")


def validate_citations(text: str) -> List[Citation]:
    """Parse and validate `path:LNN[-M]` citations from agent output.

    For each match:
    - Expand ~ via os.path.expanduser
    - status="invalid_path" if file missing
    - status="invalid_line" if line range out of bounds
    - status="valid" if both pass — `text` field holds the cited content
    """
    cites: List[Citation] = []
    for match in _CITATION_RE.finditer(text):
        raw = match.group(0)
        path = os.path.expanduser(match.group(1))
        line_start = int(match.group(2))
        line_end = int(match.group(3)) if match.group(3) else line_start

        if not os.path.isfile(path):
            cites.append(Citation(path=path, line_start=line_start, line_end=line_end,
                                  status="invalid_path", raw=raw))
            continue

        try:
            with open(path, encoding="utf-8") as f:
                lines = f.readlines()
        except (OSError, UnicodeDecodeError):
            cites.append(Citation(path=path, line_start=line_start, line_end=line_end,
                                  status="invalid_path", raw=raw))
            continue

        if line_start < 1 or line_end > len(lines) or line_start > line_end:
            cites.append(Citation(path=path, line_start=line_start, line_end=line_end,
                                  status="invalid_line", raw=raw))
            continue

        cited_text = "".join(lines[line_start - 1:line_end])
        cites.append(Citation(path=path, line_start=line_start, line_end=line_end,
                              status="valid", text=cited_text, raw=raw))
    return cites


def classify_verdict(advocate_out: str, critic_out: str, advocate_rebuttal: str = "") -> Verdict:
    """Force-acknowledge classifier (ADR-0005 §2.3).

    Rules:
    - critic has NO valid citation → automatic loss for critic → ACKNOWLEDGED-advocate-wins
    - critic valid, advocate (any turn) has NO valid citation → ACKNOWLEDGED-critic-wins
    - both valid → UNRESOLVED (orchestrator does NOT judge content; defer to user)
    """
    adv_cites = validate_citations(advocate_out + "\n" + advocate_rebuttal)
    crit_cites = validate_citations(critic_out)
    valid_adv = [c for c in adv_cites if c.status == "valid"]
    valid_crit = [c for c in crit_cites if c.status == "valid"]

    if not valid_crit:
        return Verdict(
            status="ACKNOWLEDGED-advocate-wins",
            reason="Critic has no valid file:line citation — formal violation, automatic loss.",
            advocate_citations=adv_cites,
            critic_citations=crit_cites,
        )
    if not valid_adv:
        return Verdict(
            status="ACKNOWLEDGED-critic-wins",
            reason="Advocate has no valid file:line citation in either turn — concession by absence.",
            advocate_citations=adv_cites,
            critic_citations=crit_cites,
        )
    return Verdict(
        status="UNRESOLVED",
        reason=(
            f"Both sides supplied valid citations "
            f"(advocate {len(valid_adv)}, critic {len(valid_crit)}). "
            f"Orchestrator does not judge content — user Confirm required."
        ),
        advocate_citations=adv_cites,
        critic_citations=crit_cites,
    )


# ── ADR-0004 — execution mode dispatch (recommend_execution_mode) ──


_TMUX_CHANGE_TYPES = frozenset({"structural", "new-command", "agent-prompt", "agent-role"})


def recommend_execution_mode(impact_scope: dict) -> Tuple[str, str]:
    """Recommend `single` or `tmux` based on impact scope.

    Inputs (impact_scope dict):
        files_affected: List[str]   relative file paths
        change_type:    str         "content" | "structural" | "new-command" | "agent-prompt" | "agent-role" | ...

    Returns (mode, reason) per ADR-0004 §2.2.
    """
    files = impact_scope.get("files_affected", []) or []
    change_type = impact_scope.get("change_type", "content")
    file_count = len(files)
    has_python = any(
        f.startswith("scripts/jarfis/") and f.endswith(".py") for f in files
    )

    # Force tmux: large file count or structural change
    if file_count >= 6:
        return ("tmux", f"파일 {file_count}개 영향 (≥6) — 메인 컨텍스트 폭발 방지를 위해 tmux 강제")
    if change_type == "structural":
        return ("tmux", "structural 변경 — 다수 파일 cross-cutting, tmux 격리 권장")

    # Strong tmux preference
    if file_count >= 4:
        return ("tmux", f"파일 {file_count}개 영향 — tmux 권장 (메인 ~40K 절감)")
    if has_python:
        return ("tmux", "scripts/jarfis/*.py 변경 — Python TDD 비용 큼, tmux 권장")
    if change_type in _TMUX_CHANGE_TYPES:
        return ("tmux", f"{change_type} 변경 — 다수 reference 갱신 필요, tmux 권장")

    # Single mode is fine
    if file_count <= 2 and change_type == "content":
        return ("single", f"파일 {file_count}개 콘텐츠 변경 — 단일 모드 충분")

    return ("single", "보더라인 — 단일 모드 기본 (사용자 override 가능)")


# ── ADR-0002 §2.4 — Step 4.5 RAG auto-update support (M6) ──────────


def extract_changed_files(plan_dir: str) -> List[str]:
    """Parse `{plan_dir}/artifacts/step2/diff.patch` and return changed file paths.

    Path conventions:
    - Stripped of leading `a/` and `b/` (git diff prefixes).
    - Both old (`---`) and new (`+++`) paths are collected so renames and
      deletions appear (RAG needs the OLD path to remove stale chunks).
    - `/dev/null` markers are excluded.
    - Result is deduplicated, order preserved by first appearance.
    """
    diff_path = os.path.join(plan_dir, "artifacts", "step2", "diff.patch")
    if not os.path.isfile(diff_path):
        return []
    try:
        with open(diff_path, encoding="utf-8") as f:
            content = f.read()
    except (OSError, UnicodeDecodeError):
        return []

    seen = set()
    out: List[str] = []
    for line in content.splitlines():
        # Headers we accept:
        #   --- a/<path>
        #   +++ b/<path>
        #   rename from <path>
        #   rename to <path>
        path = None
        if line.startswith("--- "):
            path = line[4:].strip()
        elif line.startswith("+++ "):
            path = line[4:].strip()
        elif line.startswith("rename from ") or line.startswith("rename to "):
            path = line.split(" ", 2)[2].strip() if line.count(" ") >= 2 else None

        if not path:
            continue
        if path == "/dev/null":
            continue
        # Strip the conventional a/ or b/ prefix
        if path.startswith("a/") or path.startswith("b/"):
            path = path[2:]
        # Skip empty after stripping
        if not path:
            continue

        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def main(args):
    if not args:
        json_error(
            "Usage: jarfis_cli.py implement <init|state|log|resume|list|archive> ..."
        )
    sub = args[0]
    if sub not in SUBCOMMANDS:
        json_error(
            f"Unknown subcommand: {sub}. Available: {', '.join(sorted(SUBCOMMANDS))}"
        )
    SUBCOMMANDS[sub](args[1:])


if __name__ == "__main__":
    main(sys.argv[1:])
