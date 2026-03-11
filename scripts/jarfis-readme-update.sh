#!/bin/bash
# JARFIS README Update wrapper — delegates to Python sync --readme-only
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$SCRIPT_DIR/jarfis_cli.py" sync --readme-only "$@"
