#!/usr/bin/env python3
"""JARFIS CLI dispatcher — routes subcommands to Python modules.

Usage:
    jarfis_cli.py <command> [args...]

Commands:
    state            State CRUD (.jarfis-state.json)
    gate-check       Gate 1/2/3 prerequisite validation (v4 top-level)
    phase-check      Phase-start prerequisite validation (v4 top-level)
    phase-verify     Per-phase output verification (v4)
    pattern-detect   Review round pattern detection (v4)
    detect           Project framework/language detection
    measure          Prompt file token measurement
    preflight        Pre-flight validation
    meetings         Recent meetings list
    version          Version bump
    sync             Repo sync + README update
    quality-gate     Run lint/typecheck on edited file
    validate         Workflow state + artifact validation
    org              Organization management (init/scan/info)
    wiki             Wiki ops (index/search/status/rebuild-index) — rebuild-index is M6 (auto INDEX.md regen)
    search           Semantic search (all/meetings/works/wiki)
    domain           Domain pack management (list/detect/agents/compose/validate/scaffold/install)
    compose          Compose agent invocation (persona + skills + context) [v4 — M2]
    work-args        Parse /jarfis:work $ARGUMENTS for --domain / --scope-domain overrides [v4.1 — M3]
    implement        sys-implement deliverables workspace (init/state/log/resume/list/archive) [v4.2 — ADR-0003]
    agent            Skill+persona registry CRUD (skill list/add/update/remove, persona list) [v4.5 — agent-skill-system-v1]
    ia               IA snapshot/validate/merge/list-pages/probe (manifest.json + pages/{slug}.md + shared.json) [ia-as-po-ssot-v2-spine]
    register         Event Stream — register a workflow in ~/.jarfis/active.json [event-stream-v1]
    unregister       Event Stream — remove a workflow from ~/.jarfis/active.json [event-stream-v1]
    emit             Event Stream — append a single event to {docs_dir}/events.jsonl [event-stream-v1]
    status           Event Stream — list active workflows + event counts [event-stream-v1]
    tail             Event Stream — tail N events of a workflow (or all -a) [event-stream-v1]
    bind-session     Event Stream — statusline auto-bind helper (D9) [event-stream-v1]
"""

import os
import sys

# Ensure jarfis package is importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

VENV_DIR = os.path.join(os.path.expanduser("~"), ".claude", ".jarfis-venv")

# Commands that require sentence-transformers venv
VENV_COMMANDS = {"wiki", "search"}


def _needs_venv_reexec(venv_dir=None):
    """Check if we need to re-exec in JARFIS venv.

    Returns True if venv exists but we're not running in it.
    Uses site-packages presence in sys.path instead of realpath comparison,
    because homebrew symlinks can make system python and venv python
    resolve to the same binary.
    """
    if venv_dir is None:
        venv_dir = VENV_DIR
    venv_python = os.path.join(venv_dir, "bin", "python3")
    if not os.path.isfile(venv_python):
        return False
    # Check if any venv site-packages directory is in sys.path
    venv_lib = os.path.join(venv_dir, "lib")
    for p in sys.path:
        if p.startswith(venv_lib) and "site-packages" in p:
            return False
    return True


def _maybe_reexec_in_venv(command):
    """For wiki/search commands, re-execute in JARFIS venv if available."""
    if command not in VENV_COMMANDS:
        return
    if not _needs_venv_reexec():
        return
    venv_python = os.path.join(VENV_DIR, "bin", "python3")
    os.execv(venv_python, [venv_python] + sys.argv)


def main():
    if len(sys.argv) < 2:
        print(
            '{"error":"Usage: jarfis <state|detect|measure|preflight|meetings|version|sync|quality-gate|validate|org|wiki|search|implement> [args...]"}',
            file=sys.stderr,
        )
        sys.exit(1)

    command = sys.argv[1]

    if command in ("--help", "-h", "help"):
        print(__doc__)
        sys.exit(0)

    args = sys.argv[2:]

    commands = {
        "state": "jarfis.state",
        "gate-check": "jarfis.verify",
        "phase-check": "jarfis.verify",
        "phase-verify": "jarfis.verify",
        "pattern-detect": "jarfis.verify",
        "detect": "jarfis.detect",
        "measure": "jarfis.measure",
        "preflight": "jarfis.preflight",
        "meetings": "jarfis.meetings",
        "version": "jarfis.version",
        "sync": "jarfis.sync",
        "quality-gate": "jarfis.quality_gate",
        "validate": "jarfis.validate",
        "org": "jarfis.organization",
        "wiki": "jarfis.wiki_search",
        "search": "jarfis.wiki_search",
        "domain": "jarfis.domain",
        "compose": "jarfis.compose.__main__",
        "work-args": "jarfis.work_args",
        "implement": "jarfis.implement",
        # v4.4 — ADR org-root data-source restructure: data layout migrator.
        "migrate": "jarfis.migrate",
        # v4.5 — agent-skill-system-v1: skill+persona CRUD module.
        "agent": "jarfis.agent_admin",
        # ia-as-po-ssot-v2-spine — Stage 1: IA snapshot/validate/merge module.
        "ia": "jarfis.ia",
        # event-stream-v1 — D8/D10 lockdown: active registry + emit + statusline support.
        "register": "jarfis.cli",
        "unregister": "jarfis.cli",
        "emit": "jarfis.cli",
        "status": "jarfis.cli",
        "tail": "jarfis.cli",
        "bind-session": "jarfis.cli",
        "render-statusline": "jarfis.cli",
    }

    if command not in commands:
        print(
            f'{{"error":"Unknown command: {command}. Available: {", ".join(sorted(commands))}."}}',
            file=sys.stderr,
        )
        sys.exit(1)

    _maybe_reexec_in_venv(command)

    module = __import__(commands[command], fromlist=["main"])

    if command == "search":
        module.search_main(args)
    elif command in ("gate-check", "phase-check", "phase-verify", "pattern-detect"):
        # verify.main expects the subcommand name as args[0]
        module.main([command] + args)
    elif command in (
        "register",
        "unregister",
        "emit",
        "status",
        "tail",
        "bind-session",
        "render-statusline",
    ):
        # cli.main argparse expects the subcommand as args[0]
        module.main([command] + args)
    else:
        module.main(args)


if __name__ == "__main__":
    main()
