#!/bin/bash
# JARFIS Recent Meetings wrapper — delegates to Python
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/jarfis_cli.py" meetings "$@"
