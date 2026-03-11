#!/bin/bash
# JARFIS Detect Project wrapper — delegates to Python
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/jarfis_cli.py" detect "$@"
