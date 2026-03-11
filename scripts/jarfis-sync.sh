#!/bin/bash
# JARFIS Sync wrapper — delegates to Python
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/jarfis_cli.py" sync "$@"
