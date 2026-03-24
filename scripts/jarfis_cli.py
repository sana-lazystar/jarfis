#!/usr/bin/env python3
"""JARFIS CLI dispatcher — routes subcommands to Python modules.

Usage:
    jarfis_cli.py <command> [args...]

Commands:
    state         State CRUD (.jarfis-state.json)
    detect        Project framework/language detection
    measure       Prompt file token measurement
    preflight     Pre-flight validation
    meetings      Recent meetings list
    version       Version bump
    sync          Repo sync + README update
    quality-gate  Run lint/typecheck on edited file
    validate      Workflow state + artifact validation
    org           Organization management (init/scan/info)
    wiki          Wiki semantic search (index/search/status)
"""

import os
import sys

# Ensure jarfis package is importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

VENV_DIR = os.path.join(os.path.expanduser("~"), ".claude", ".jarfis-venv")


def _maybe_reexec_in_venv(command):
    """For wiki command, re-execute in JARFIS venv if available."""
    if command != "wiki":
        return
    venv_python = os.path.join(VENV_DIR, "bin", "python3")
    if not os.path.isfile(venv_python):
        return
    # Already running in venv — skip
    if os.path.realpath(sys.executable) == os.path.realpath(venv_python):
        return
    # Re-exec with venv python
    os.execv(venv_python, [venv_python] + sys.argv)


def main():
    if len(sys.argv) < 2:
        print(
            '{"error":"Usage: jarfis <state|detect|measure|preflight|meetings|version|sync|quality-gate|validate|org|wiki> [args...]"}',
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
    }

    if command not in commands:
        print(
            f'{{"error":"Unknown command: {command}. Available: {", ".join(sorted(commands))}."}}',
            file=sys.stderr,
        )
        sys.exit(1)

    _maybe_reexec_in_venv(command)

    module = __import__(commands[command], fromlist=["main"])
    module.main(args)


if __name__ == "__main__":
    main()
