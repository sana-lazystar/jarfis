#!/usr/bin/env bash
# JARFIS multi-line statusline shim (event-stream-v1, D6).
#
# - Reads Claude Code statusline stdin JSON.
# - Delegates rendering to `jarfis_cli.py render-statusline`.
#   - On JARFIS workflow match → 6-line multi-line output (header + 5 events).
#   - On no match → prints "FALLBACK" → this shim invokes statusline-command.sh
#     so non-JARFIS sessions keep their original 1-line look. Zero impact when
#     no workflow is registered.
#
# Activated via settings.json statusLine.command = "bash /…/statusline-jarfis.sh"
# Refresh: refreshInterval = 1 (D6 — 1Hz polling on top of event-driven debounce).

set -u

input=$(cat)

JARFIS_CLI="$HOME/.claude/scripts/jarfis_cli.py"
ORIG_STATUSLINE="$HOME/.claude/statusline-command.sh"

if ! command -v python3 >/dev/null 2>&1 || [ ! -f "$JARFIS_CLI" ]; then
  printf '%s' "$input" | bash "$ORIG_STATUSLINE"
  exit $?
fi

output=$(printf '%s' "$input" | python3 "$JARFIS_CLI" render-statusline 2>/dev/null)

if [ -z "$output" ] || [ "$(printf '%s' "$output" | head -1)" = "FALLBACK" ]; then
  printf '%s' "$input" | bash "$ORIG_STATUSLINE"
  exit $?
fi

printf '%s' "$output"
