"""JARFIS Event Stream — CLI subcommands.

Subcommands:
    register     skill markdown entry → add workflow to active.json
    unregister   skill markdown exit  → remove workflow from active.json
    emit         append a single event to {workflow.docs_dir}/events.jsonl
    status       list active workflows + per-workflow event count + last event
    tail         tail N events of a workflow (or all -a) with ANSI color
    bind-session statusline auto-bind helper (D9) — bind cwd-matched workflow

Active registry SSOT: ~/.jarfis/active.json (D8).
events.jsonl location: $DOCS_DIR/events.jsonl (D1).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jarfis.emit import (
    EmitError,
    EventType,
    Level,
    emit as emit_event,
    render_line,
    tail_events,
)


def _active_path() -> Path:
    """Resolve ~/.jarfis/active.json (override via $JARFIS_ACTIVE_PATH for tests)."""
    override = os.environ.get("JARFIS_ACTIVE_PATH")
    if override:
        return Path(override)
    return Path(os.path.expanduser("~")) / ".jarfis" / "active.json"


def _read_active() -> dict[str, Any]:
    """Read active.json. Returns {'workflows': []} on missing/corrupt file."""
    path = _active_path()
    if not path.exists():
        return {"workflows": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"workflows": []}
    if not isinstance(data, dict) or "workflows" not in data:
        return {"workflows": []}
    return data


def _write_active(data: dict[str, Any]) -> None:
    """Atomic write via tmp+rename."""
    path = _active_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(path))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _find_workflow(workflow_id: str) -> dict[str, Any] | None:
    for wf in _read_active()["workflows"]:
        if wf.get("workflow_id") == workflow_id:
            return wf
    return None


def _realpath(p: str) -> str:
    """Resolve symlinks defensively. macOS /tmp → /private/tmp must match."""
    try:
        return os.path.realpath(p)
    except OSError:
        return os.path.abspath(p)


def find_by_cwd_ancestor(cwd: str) -> dict[str, Any] | None:
    """Return the workflow whose docs_dir is an ancestor of cwd (or cwd itself)."""
    cwd_real = _realpath(cwd)
    for wf in _read_active()["workflows"]:
        docs = wf.get("docs_dir")
        if not docs:
            continue
        docs_real = _realpath(docs)
        try:
            common = os.path.commonpath([cwd_real, docs_real])
        except ValueError:
            continue
        if common == docs_real:
            return wf
    return None


def find_by_session_id(session_id: str) -> dict[str, Any] | None:
    for wf in _read_active()["workflows"]:
        if wf.get("session_id") == session_id:
            return wf
    return None


def _err(msg: str, code: int = 1) -> None:
    print(json.dumps({"error": msg}, ensure_ascii=False), file=sys.stderr)
    sys.exit(code)


# ---------------------------------------------------------------- subcommands


def _resolve_session_id(ns: argparse.Namespace) -> str | None:
    """Pick session_id with priority: --session-id arg > $CLAUDE_CODE_SESSION_ID > None.

    Empty strings (from either source) normalize to None so the entry stores a
    real value or nothing — never `""`.
    """
    arg_val = getattr(ns, "session_id", None)
    if arg_val:  # non-empty string wins
        return arg_val
    env_val = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    return env_val or None


def cmd_register(ns: argparse.Namespace) -> int:
    """Register a workflow in active.json.

    Fix A — session_id is bound at register time when available:
      priority = --session-id arg > $CLAUDE_CODE_SESSION_ID env > None.
    On dedupe replace, if the new invocation supplies a session_id but the
    prior entry had none, the new value wins (update). If neither side has
    a value, session_id stays None — left for statusline auto-bind (D9 step 2).
    """
    resolved_session = _resolve_session_id(ns)

    data = _read_active()
    # Carry forward an existing session_id only when the new register call
    # didn't supply one (resolved_session is None). When both exist, new wins.
    prior = next(
        (w for w in data["workflows"] if w.get("workflow_id") == ns.workflow_id),
        None,
    )
    if resolved_session is None and prior is not None and prior.get("session_id"):
        resolved_session = prior["session_id"]

    data["workflows"] = [
        w for w in data["workflows"] if w.get("workflow_id") != ns.workflow_id
    ]
    data["workflows"].append(
        {
            "workflow_id": ns.workflow_id,
            "skill": ns.skill,
            "docs_dir": str(Path(ns.docs_dir).expanduser().resolve()),
            "session_id": resolved_session,
            "tmux_session": ns.tmux_session,
            "started_at": _now_iso(),
            "show_tools": bool(getattr(ns, "show_tools", False)),
        }
    )
    _write_active(data)
    print(
        json.dumps(
            {"success": True, "workflow_id": ns.workflow_id, "skill": ns.skill},
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 0


def cmd_unregister(ns: argparse.Namespace) -> int:
    data = _read_active()
    before = len(data["workflows"])
    data["workflows"] = [
        w for w in data["workflows"] if w.get("workflow_id") != ns.workflow_id
    ]
    _write_active(data)
    removed = before - len(data["workflows"])
    print(
        json.dumps(
            {"success": True, "workflow_id": ns.workflow_id, "removed": removed},
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 0


def _resolve_workflow_id(ns: argparse.Namespace) -> str:
    if getattr(ns, "workflow_id", None):
        return ns.workflow_id
    env_id = os.environ.get("JARFIS_WORKFLOW")
    if env_id:
        return env_id
    _err("workflow_id not provided (use --workflow-id or set $JARFIS_WORKFLOW)")
    raise AssertionError("unreachable")  # _err exits


def _parse_extras(pairs: list[str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for pair in pairs or []:
        if "=" not in pair:
            _err(f"--extra must be key=value, got: {pair!r}")
        k, v = pair.split("=", 1)
        out[k.strip()] = v
    return out


def cmd_emit(ns: argparse.Namespace) -> int:
    workflow_id = _resolve_workflow_id(ns)
    wf = _find_workflow(workflow_id)
    if wf is None:
        _err(f"unknown workflow_id: {workflow_id!r} (not in active.json)")
    docs_dir = Path(wf["docs_dir"])
    events_path = docs_dir / "events.jsonl"
    extras = _parse_extras(ns.extra)
    extras["workflow_id"] = workflow_id
    try:
        ev = emit_event(
            events_path,
            ns.type,
            ns.summary,
            level=ns.level,
            extras=extras,
        )
    except EmitError as e:
        _err(f"emit failed: {e}")
        raise
    print(
        json.dumps({"success": True, "event": ev}, ensure_ascii=False),
        file=sys.stderr,
    )
    return 0


def cmd_status(ns: argparse.Namespace) -> int:
    data = _read_active()
    enriched: list[dict[str, Any]] = []
    for wf in data["workflows"]:
        events_path = Path(wf["docs_dir"]) / "events.jsonl"
        if events_path.exists():
            all_events = tail_events(events_path, n=10**9)
            count = len(all_events)
            last = all_events[-1] if all_events else None
        else:
            count = 0
            last = None
        enriched.append(
            {
                **wf,
                "event_count": count,
                "last_event": last,
            }
        )
    out = {"workflows": enriched}
    if ns.json:
        print(json.dumps(out, ensure_ascii=False))
    else:
        if not enriched:
            print("No active workflows")
        else:
            for wf in enriched:
                last = wf["last_event"]
                last_str = (
                    f" · last={last['type']}/{last['summary'][:40]}" if last else ""
                )
                print(
                    f"- {wf['workflow_id']} ({wf['skill']}) · "
                    f"{wf['event_count']} events{last_str}"
                )
    return 0


def cmd_tail(ns: argparse.Namespace) -> int:
    color = sys.stdout.isatty() and not ns.no_color
    if ns.all:
        data = _read_active()
        if not data["workflows"]:
            print("No active workflows")
            return 0
        # Multiplex: interleave events from all workflows by ts, take last N total.
        merged: list[tuple[str, dict[str, Any], str]] = []
        for wf in data["workflows"]:
            ev_path = Path(wf["docs_dir"]) / "events.jsonl"
            for ev in tail_events(ev_path, n=10**9):
                merged.append((ev.get("ts", ""), ev, wf["workflow_id"]))
        merged.sort(key=lambda t: t[0])
        for _, ev, wid in merged[-ns.n :]:
            print(f"[{wid}] {render_line(ev, color=color)}")
        return 0

    if not ns.workflow_id:
        _err("workflow_id required (or use -a for all)")
    wf = _find_workflow(ns.workflow_id)
    if wf is None:
        _err(f"unknown workflow_id: {ns.workflow_id!r}")
    events_path = Path(wf["docs_dir"]) / "events.jsonl"
    for ev in tail_events(events_path, n=ns.n):
        print(render_line(ev, color=color))
    return 0


def _format_elapsed(started_at: str) -> str:
    """`14m23s` for <1h, `2h05m` for ≥1h, `?` on parse error."""
    try:
        started = datetime.fromisoformat(started_at)
    except (ValueError, TypeError):
        return "?"
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    diff = int((datetime.now(timezone.utc) - started).total_seconds())
    if diff < 0:
        diff = 0
    h, rem = divmod(diff, 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m"
    return f"{m}m{s:02d}s"


def cmd_render_statusline(ns: argparse.Namespace) -> int:
    """Multi-line 6-row statusline render (D6).

    Reads stdin JSON, returns 6 lines (header + 5 body) on stdout when a JARFIS
    workflow matches the session_id (or auto-binds via cwd). Otherwise prints
    "FALLBACK" on a single line — the shell shim then defers to the original
    statusline-command.sh.

    Side effect: on first match via cwd, binds session_id to the workflow
    entry (D9 — "1회 박음").
    """
    from jarfis.emit import ANSI, ANSI_RESET, Level  # local import to keep top-level minimal

    raw = sys.stdin.read()
    try:
        stdin_data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        print("FALLBACK")
        return 0

    session_id = stdin_data.get("session_id") or ""
    cwd = (stdin_data.get("workspace") or {}).get("current_dir") or stdin_data.get("cwd") or ""

    data = _read_active()
    if not data["workflows"]:
        print("FALLBACK")
        return 0

    # 1. session_id match (preferred — survives cwd drift, D9 step 3)
    matched: dict[str, Any] | None = None
    if session_id:
        for wf in data["workflows"]:
            if wf.get("session_id") == session_id:
                matched = wf
                break

    # 2. cwd ancestor match (auto-bind, D9 step 2)
    if matched is None and cwd:
        wf = find_by_cwd_ancestor(cwd)
        if wf is not None and not wf.get("session_id") and session_id:
            # Atomic 1회 박음
            data2 = _read_active()
            for entry in data2["workflows"]:
                if entry["workflow_id"] == wf["workflow_id"]:
                    entry["session_id"] = session_id
                    break
            _write_active(data2)
            matched = wf
            matched["session_id"] = session_id
        elif wf is not None:
            matched = wf

    # Neither session_id nor cwd matched → this session is not an owner of any
    # active workflow. Silence (FALLBACK) rather than showing a `· drift` marker
    # to other sessions — Fix A (register-time session_id bind via
    # $CLAUDE_CODE_SESSION_ID) ensures the owner session always matches.
    if matched is None:
        print("FALLBACK")
        return 0

    # Header — purple bold (statusline pipe path: force color, isatty() is False
    # under Claude Code TUI but ANSI is rendered correctly)
    active_count = len(data["workflows"])
    elapsed = _format_elapsed(matched.get("started_at", ""))
    header = (
        f"JARFIS · {active_count} active · ←{matched['workflow_id']} · {elapsed}"
    )
    use_color = not getattr(ns, "no_color", False)
    if use_color:
        print(f"{ANSI[Level.HIGHLIGHT]}{header}{ANSI_RESET}")
    else:
        print(header)

    # Body — last 5 highlight+info events; pad to 5 lines
    events_path = Path(matched["docs_dir"]) / "events.jsonl"
    events = tail_events(
        events_path, n=5, levels=({Level.HIGHLIGHT, Level.INFO, Level.DEBUG}
                              if matched.get("show_tools")
                              else {Level.HIGHLIGHT, Level.INFO})
    )
    for ev in events:
        print(render_line(ev, color=use_color))
    # Pad with single-space lines so total = 6 (terminal renders blank;
    # plain "" would be trailing-newline-stripped by callers like
    # `out.rstrip("\n").split("\n")`).
    for _ in range(5 - len(events)):
        print(" ")
    return 0


def cmd_bind_session(ns: argparse.Namespace) -> int:
    """D9 step 2 — auto-bind statusline cwd → workflow.session_id (1회 박음)."""
    wf = find_by_cwd_ancestor(ns.cwd)
    if wf is None:
        print(
            json.dumps({"success": False, "reason": "no_match"}, ensure_ascii=False),
            file=sys.stderr,
        )
        return 0
    if wf.get("session_id"):
        print(
            json.dumps(
                {"success": True, "already_bound": True, "session_id": wf["session_id"]},
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 0
    data = _read_active()
    for entry in data["workflows"]:
        if entry["workflow_id"] == wf["workflow_id"]:
            entry["session_id"] = ns.session_id
            break
    _write_active(data)
    print(
        json.dumps(
            {
                "success": True,
                "bound": True,
                "workflow_id": wf["workflow_id"],
                "session_id": ns.session_id,
            },
            ensure_ascii=False,
        ),
        file=sys.stderr,
    )
    return 0


# ---------------------------------------------------------------- argparse


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="jarfis-cli", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("register", help="Register a workflow in active.json")
    pr.add_argument("--workflow-id", required=True)
    pr.add_argument("--skill", required=True, help="work / work-meeting / sys-implement / ...")
    pr.add_argument("--docs-dir", required=True, help="Workflow docs dir (events.jsonl parent)")
    pr.add_argument("--tmux-session", default=None)
    pr.add_argument(
        "--session-id",
        default=None,
        help="Bind Claude Code session id at register time (Fix A — event-stream-v2). "
             "Fallback: $CLAUDE_CODE_SESSION_ID env. Empty → None.",
    )
    pr.add_argument(
        "--show-tools",
        action="store_true",
        help="Show tool events in statusline body (event-stream-v4). "
             "Default: False — TOOL is DEBUG and filtered out. "
             "Tool events are always recorded in events.jsonl regardless (tail -a still works).",
    )
    pr.set_defaults(func=cmd_register)

    pu = sub.add_parser("unregister", help="Remove a workflow from active.json")
    pu.add_argument("--workflow-id", required=True)
    pu.set_defaults(func=cmd_unregister)

    pe = sub.add_parser("emit", help="Append an event to a workflow's events.jsonl")
    pe.add_argument("--workflow-id", default=None, help="Default: $JARFIS_WORKFLOW")
    pe.add_argument("--type", required=True, help="EventType value (e.g. phase.start)")
    pe.add_argument("--summary", required=True, help="≤80 chars, no emoji, no period")
    pe.add_argument("--level", default=None, help="highlight|info|error|debug")
    pe.add_argument("--extra", action="append", help="key=value (repeatable)")
    pe.set_defaults(func=cmd_emit)

    ps = sub.add_parser("status", help="List active workflows + counts")
    ps.add_argument("--json", action="store_true")
    ps.set_defaults(func=cmd_status)

    pt = sub.add_parser("tail", help="Show last N events of a workflow")
    pt.add_argument("workflow_id", nargs="?", default=None)
    pt.add_argument("-n", type=int, default=5, dest="n")
    pt.add_argument("-a", "--all", action="store_true", help="Multiplex all active workflows")
    pt.add_argument("--no-color", action="store_true")
    pt.set_defaults(func=cmd_tail)

    pb = sub.add_parser(
        "bind-session", help="D9 statusline helper — bind cwd-matched workflow"
    )
    pb.add_argument("--cwd", required=True)
    pb.add_argument("--session-id", required=True)
    pb.set_defaults(func=cmd_bind_session)

    pr = sub.add_parser(
        "render-statusline",
        help="D6 multi-line statusline render (stdin JSON → 6-line stdout or FALLBACK)",
    )
    pr.add_argument("--no-color", action="store_true")
    pr.set_defaults(func=cmd_render_statusline)

    return p


def main(args: list[str] | None = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(args)
    return ns.func(ns)


if __name__ == "__main__":
    sys.exit(main())
