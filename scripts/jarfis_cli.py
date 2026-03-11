#!/usr/bin/env python3
"""JARFIS CLI dispatcher — routes subcommands to Python modules.

Usage:
    jarfis_cli.py <command> [args...]

Commands:
    state       State CRUD (.jarfis-state.json)
    detect      Project framework/language detection
    measure     Prompt file token measurement
    preflight   Pre-flight validation
    meetings    Recent meetings list
    version     Version bump
    sync        Repo sync + README update
"""

import os
import sys

# Ensure jarfis package is importable
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def main():
    if len(sys.argv) < 2:
        print(
            '{"error":"Usage: jarfis <state|detect|measure|preflight|meetings|version|sync> [args...]"}',
            file=sys.stderr,
        )
        sys.exit(1)

    command = sys.argv[1]
    args = sys.argv[2:]

    commands = {
        "state": "jarfis.state",
        "detect": "jarfis.detect",
        "measure": "jarfis.measure",
        "preflight": "jarfis.preflight",
        "meetings": "jarfis.meetings",
        "version": "jarfis.version",
        "sync": "jarfis.sync",
    }

    if command not in commands:
        print(
            f'{{"error":"Unknown command: {command}. Available: {", ".join(sorted(commands))}."}}',
            file=sys.stderr,
        )
        sys.exit(1)

    module = __import__(commands[command], fromlist=["main"])
    module.main(args)


if __name__ == "__main__":
    main()
