"""JARFIS State — .jarfis-state.json CRUD

Subcommands:
    read <state_file> [key]
    write <state_file> <json_string>
    set <state_file> <key> <value>
    set-nested <state_file> <path.to.key> <value>
    init <state_file> <project_name> <work_name> <docs_dir>
    list-workflows <workspace_dir> [--completed-only]
"""

import json
import os
import sys
from datetime import datetime, timezone

from .utils import json_error, json_output, parse_json_value


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
            print(json.dumps(None))
            return
    print(json.dumps(val))


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


def cmd_set(args):
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
    json_output({"success": True, "key": key})


def cmd_set_nested(args):
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
    state = {
        "project_name": project_name,
        "work_name": work_name,
        "work_input": "",
        "docs_dir": docs_dir,
        "branch": work_name,
        "branches": {},
        "source_meeting": None,
        "started_at": now,
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
    json_output({"success": True, "path": state_file, "work_name": work_name})


def cmd_list_workflows(args):
    workspace_dir = args[0] if args else ""
    completed_only = "--completed-only" in args

    if not workspace_dir:
        json_error("list-workflows requires workspace_dir")

    works_dir = os.path.join(workspace_dir, "works")
    if not os.path.isdir(works_dir):
        json_output({"workflows": [], "count": 0})
        return

    results = []
    for root, dirs, files in os.walk(works_dir):
        if ".jarfis-state.json" in files:
            sf = os.path.join(root, ".jarfis-state.json")
            try:
                with open(sf) as f:
                    data = json.load(f)
                cp = data.get("current_phase", "")
                phases = data.get("phases", {})
                is_done = str(cp) == "done" or phases.get("6", {}).get("status") == "completed"
                if completed_only and not is_done:
                    continue
                results.append({
                    "path": os.path.dirname(sf),
                    "state_file": sf,
                    "project_name": data.get("project_name", ""),
                    "work_name": data.get("work_name", ""),
                    "current_phase": cp,
                    "is_completed": is_done,
                    "started_at": data.get("started_at", ""),
                    "docs_dir": data.get("docs_dir", ""),
                })
            except Exception:
                pass

    results.sort(key=lambda x: x.get("started_at", ""), reverse=True)
    json_output({"workflows": results, "count": len(results)})


def main(args):
    if not args:
        json_error("Usage: jarfis state <read|write|set|set-nested|init|list-workflows> <state_file> [args...]")

    action = args[0]
    rest = args[1:]

    commands = {
        "read": cmd_read,
        "write": cmd_write,
        "set": cmd_set,
        "set-nested": cmd_set_nested,
        "init": cmd_init,
        "list-workflows": cmd_list_workflows,
    }

    if action not in commands:
        json_error(f"Unknown action: {action}. Use read|write|set|set-nested|init|list-workflows.")

    commands[action](rest)
