"""JARFIS State — .jarfis-state.json CRUD

Subcommands:
    read <state_file> [key]
    write <state_file> <json_string>
    set <state_file> <key> <value>
    set-nested <state_file> <path.to.key> <value>
    init <state_file> <project_name> <work_name> <docs_dir>
    validate <state_file>
    list-workflows <org_dir> [--completed-only]
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone

from .utils import get_all_workspaces, json_error, json_output, parse_json_value

# Lazy import to avoid circular dependency; audit is optional.
_audit_module = None


def _try_audit(audit_path, event_type, **data):
    """Best-effort audit logging. Failures are silently ignored (P9)."""
    if not audit_path:
        return
    try:
        global _audit_module
        if _audit_module is None:
            from . import audit as _mod
            _audit_module = _mod
        _audit_module.append_event(audit_path, event_type, **data)
    except Exception:
        pass  # Audit is not a recovery source — never block state ops


def cmd_read(args):
    state_file = args[0] if args else ""
    if not state_file:
        json_error("Usage: jarfis state read <state_file> [key]")
    if not os.path.isfile(state_file):
        json_error("State file not found", path=state_file)

    key = args[1] if len(args) > 1 else ""
    if not key:
        # Raw file output
        with open(state_file) as f:
            sys.stdout.write(f.read())
        return

    with open(state_file) as f:
        data = json.load(f)
    keys = key.split(".")
    val = data
    for k in keys:
        if isinstance(val, dict) and k in val:
            val = val[k]
        else:
            print(json.dumps(None, ensure_ascii=False))
            return
    print(json.dumps(val, ensure_ascii=False))


def cmd_write(args):
    state_file = args[0] if args else ""
    json_string = args[1] if len(args) > 1 else ""
    if not state_file:
        json_error("Usage: jarfis state write <state_file> <json_string>")
    if not json_string:
        json_error("write requires a JSON string argument")

    data = json.loads(json_string)
    with open(state_file, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    json_output({"success": True, "path": state_file})


def cmd_set(args, audit_path=None):
    state_file = args[0] if args else ""
    key = args[1] if len(args) > 1 else ""
    value = args[2] if len(args) > 2 else ""
    if not key:
        json_error("set requires key and value arguments")
    if not os.path.isfile(state_file):
        json_error("State file not found", path=state_file)

    with open(state_file) as f:
        data = json.load(f)

    data[key] = parse_json_value(value)

    with open(state_file, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    _try_audit(audit_path, "PhaseCompleted", key=key)
    json_output({"success": True, "key": key})


def cmd_set_nested(args, audit_path=None):
    state_file = args[0] if args else ""
    key_path = args[1] if len(args) > 1 else ""
    value = args[2] if len(args) > 2 else ""
    if not key_path:
        json_error("set-nested requires path.to.key and value arguments")
    if not os.path.isfile(state_file):
        json_error("State file not found", path=state_file)

    with open(state_file) as f:
        data = json.load(f)

    keys = key_path.split(".")
    parsed_value = parse_json_value(value)

    obj = data
    for k in keys[:-1]:
        if k not in obj or not isinstance(obj[k], dict):
            obj[k] = {}
        obj = obj[k]
    obj[keys[-1]] = parsed_value

    with open(state_file, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    _try_audit(audit_path, "PhaseCompleted", key_path=key_path)
    json_output({"success": True, "key_path": key_path})


def cmd_init(args):
    state_file = args[0] if args else ""
    project_name = args[1] if len(args) > 1 else ""
    work_name = args[2] if len(args) > 2 else ""
    docs_dir = args[3] if len(args) > 3 else ""

    if not project_name or not work_name or not docs_dir:
        json_error("init requires project_name, work_name, and docs_dir")

    os.makedirs(os.path.dirname(state_file), exist_ok=True)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    session_key = "jf-" + uuid.uuid4().hex[:8]

    # v4.1 (M2.11, ADR-0002): emit v4 nested shape only.
    # work-legacy.md is gone, so v3 flat keys (project_name / work_name /
    # work_input / docs_dir / branch / branches / source_meeting) no
    # longer have a consumer and are dropped. The remaining top-level
    # keys (status / started_at / current_phase / phases /
    # key_decisions / workspace / required_roles / gate_results /
    # last_checkpoint) are part of the v4 schema and consumed by
    # phase prompts + work.md.
    state = {
        # v4 identity / orchestration block
        "sessionKey": session_key,
        "locale": None,
        "org": None,
        "domain": None,
        "design": {"mode": None, "figmaPages": []},
        "responsive": None,
        "api": {"mode": None},
        "devops": False,
        "po_extras": [],
        "work": {
            "name": work_name,
            "input": "",
            "docsDir": docs_dir,
            "startedAt": now,
            "meetings": [],
            # ``project_name`` migrates from a v3 top-level key to a
            # nested label under ``work`` so ``cmd_list_workflows`` and
            # the audit log keep human-readable context.
            "projectName": project_name,
        },
        # v4 lifecycle keys (top-level — consumed by phase prompts)
        "started_at": now,
        "status": "in-progress",
        "key_decisions": [],
        "current_phase": 0,
        "workspace": {},
        "phases": {
            "0": {"status": "in_progress"},
            "1": {"status": "pending"},
            "2": {"status": "pending"},
            "3": {"status": "pending"},
            "4": {"status": "pending"},
            "4.5": {"status": "pending"},
            "5": {"status": "pending"},
            "6": {"status": "pending"},
        },
        "required_roles": {},
        "gate_results": {},
        "last_checkpoint": {
            "timestamp": now,
            "phase": 0,
            "summary": "Initialized",
        },
    }
    with open(state_file, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    json_output({
        "success": True,
        "path": state_file,
        "work_name": work_name,
        "sessionKey": session_key,
    })


def cmd_list_workflows(args):
    completed_only = "--completed-only" in args
    remaining = [a for a in args if a != "--completed-only"]
    org_dir = remaining[0] if remaining else ""

    # Collect works directories to scan
    works_dirs = []
    if org_dir:
        # Explicit workspace: scan its works/ subdir (backward compat)
        wd = os.path.join(org_dir, "works")
        if os.path.isdir(wd):
            works_dirs.append(wd)
    else:
        # No arg: scan all org workspaces
        for ws in get_all_workspaces():
            wd = os.path.join(ws, "works")
            if os.path.isdir(wd):
                works_dirs.append(wd)

    if not works_dirs:
        json_output({"workflows": [], "count": 0})
        return

    results = []
    for works_dir in works_dirs:
        for root, dirs, files in os.walk(works_dir):
            if ".jarfis-state.json" in files:
                sf = os.path.join(root, ".jarfis-state.json")
                try:
                    with open(sf) as f:
                        data = json.load(f)
                    cp = data.get("current_phase", "")
                    phases = data.get("phases", {})
                    status = data.get("status", "")
                    key_decisions = data.get("key_decisions", [])
                    is_done = (
                        status == "completed"
                        or str(cp) == "done"
                        or phases.get("6", {}).get("status") == "completed"
                    )
                    if completed_only and not is_done:
                        continue
                    # v4 nested ``work`` block is preferred; v3 flat
                    # keys remain accepted as fallback for older state files.
                    work_block = data.get("work") or {}
                    results.append({
                        "path": os.path.dirname(sf),
                        "state_file": sf,
                        "project_name": (
                            work_block.get("projectName")
                            or data.get("project_name", "")
                        ),
                        "work_name": (
                            work_block.get("name")
                            or data.get("work_name", "")
                        ),
                        "current_phase": cp,
                        "status": status,
                        "key_decisions": key_decisions,
                        "is_completed": is_done,
                        "started_at": (
                            work_block.get("startedAt")
                            or data.get("started_at", "")
                        ),
                        "docs_dir": (
                            work_block.get("docsDir")
                            or data.get("docs_dir", "")
                        ),
                    })
                except Exception:
                    pass

    results.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    json_output({"workflows": results, "count": len(results)})


def cmd_validate(args):
    """Validate .jarfis-state.json structure against required schema."""
    state_file = args[0] if args else ""
    if not state_file:
        json_error("Usage: jarfis state validate <state_file>")
    if not os.path.isfile(state_file):
        json_error("State file not found", path=state_file)

    with open(state_file) as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            json_error(f"Invalid JSON: {e}")
            return

    errors = []

    # v4 (post-M2.11) requires the nested ``work`` block with name/docsDir.
    # Legacy v3 flat keys (project_name / work_name / docs_dir) are still
    # accepted as a fallback so pre-existing state files continue to
    # validate during the v4.0 → v4.1 transition.
    work_block = data.get("work")
    if isinstance(work_block, dict):
        for nested_field, label in (
            ("name", "work.name"),
            ("docsDir", "work.docsDir"),
        ):
            if nested_field not in work_block:
                errors.append(f"Missing required field: {label}")
            elif not isinstance(work_block[nested_field], str):
                errors.append(
                    f"{label} must be string, got "
                    f"{type(work_block[nested_field]).__name__}"
                )
    else:
        # Backward compat: accept v3 flat keys when ``work`` block absent.
        for field in ("project_name", "work_name", "docs_dir"):
            if field not in data:
                errors.append(f"Missing required field: work.{field.replace('_', 'D').replace('docsD', 'docsD')} or {field}")
            elif not isinstance(data[field], str):
                errors.append(f"{field} must be string, got {type(data[field]).__name__}")

    # ``started_at`` remains a top-level v4 key (consumed by phase prompts).
    if "started_at" not in data:
        errors.append("Missing required field: started_at")
    elif not isinstance(data["started_at"], str):
        errors.append(
            f"started_at must be string, got {type(data['started_at']).__name__}"
        )

    # status: top-level workflow status
    status = data.get("status")
    if status is not None:
        valid_top_statuses = {"in-progress", "completed", "aborted"}
        if not isinstance(status, str):
            errors.append(f"status must be string, got {type(status).__name__}")
        elif status not in valid_top_statuses:
            errors.append(f"status invalid: {status}. Valid: {', '.join(sorted(valid_top_statuses))}")

    # key_decisions: list of strings
    kd = data.get("key_decisions")
    if kd is not None and not isinstance(kd, list):
        errors.append(f"key_decisions must be list, got {type(kd).__name__}")

    # current_phase: int, float, or "done"
    cp = data.get("current_phase")
    if cp is None:
        errors.append("Missing required field: current_phase")
    elif not isinstance(cp, (int, float, str)):
        errors.append(f"current_phase must be int/float/string, got {type(cp).__name__}")

    # phases: dict with known keys
    phases = data.get("phases")
    if phases is None:
        errors.append("Missing required field: phases")
    elif not isinstance(phases, dict):
        errors.append(f"phases must be dict, got {type(phases).__name__}")
    else:
        valid_statuses = {"pending", "in_progress", "completed", "skipped"}
        for phase_key, phase_val in phases.items():
            if isinstance(phase_val, dict):
                status = phase_val.get("status", "")
                if status and status not in valid_statuses:
                    errors.append(f"phases.{phase_key}.status invalid: {status}")

    # required_roles: dict of booleans
    roles = data.get("required_roles")
    if roles is not None and not isinstance(roles, dict):
        errors.append(f"required_roles must be dict, got {type(roles).__name__}")

    # gate_results: dict
    gates = data.get("gate_results")
    if gates is not None and not isinstance(gates, dict):
        errors.append(f"gate_results must be dict, got {type(gates).__name__}")

    # last_checkpoint: dict with timestamp
    lc = data.get("last_checkpoint")
    if lc is not None:
        if not isinstance(lc, dict):
            errors.append(f"last_checkpoint must be dict, got {type(lc).__name__}")
        elif "timestamp" not in lc:
            errors.append("last_checkpoint missing timestamp")

    if errors:
        json_output({"valid": False, "errors": errors, "error_count": len(errors)})
    else:
        json_output({"valid": True, "errors": [], "error_count": 0})


def main(args):
    if not args:
        json_error("Usage: jarfis state <read|write|set|set-nested|init|validate|list-workflows> <state_file> [args...]")

    action = args[0]
    rest = args[1:]

    commands = {
        "read": cmd_read,
        "write": cmd_write,
        "set": cmd_set,
        "set-nested": cmd_set_nested,
        "init": cmd_init,
        "validate": cmd_validate,
        "list-workflows": cmd_list_workflows,
    }

    if action not in commands:
        json_error(f"Unknown action: {action}. Use read|write|set|set-nested|init|validate|list-workflows.")

    commands[action](rest)
