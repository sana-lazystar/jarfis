#!/bin/bash
# JARFIS PostToolUse Quality Gate Hook
# Runs lint/typecheck on files after Edit/Write/MultiEdit.
# Never blocks (PostToolUse always exit 0) — warnings only via stderr.
#
# Kill switch: JARFIS_QUALITY_GATE=0

# Kill switch
if [[ "${JARFIS_QUALITY_GATE:-1}" == "0" ]]; then
  exit 0
fi

INPUT=$(cat)

# JSON parsing: jq if available, python3 fallback
_json_get() {
  local json="$1" key="$2" default="$3"
  if command -v jq >/dev/null 2>&1; then
    echo "$json" | jq -r ".$key // \"$default\""
  elif command -v python3 >/dev/null 2>&1; then
    echo "$json" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('$key','$default'))"
  else
    echo "$default"
  fi
}

TOOL_NAME=$(_json_get "$INPUT" "tool_name" "")

# Only process Edit, Write, MultiEdit
case "$TOOL_NAME" in
  Edit|Write|MultiEdit) ;;
  *) exit 0 ;;
esac

# Extract file_path from tool_input
if command -v jq >/dev/null 2>&1; then
  FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""')
elif command -v python3 >/dev/null 2>&1; then
  FILE_PATH=$(echo "$INPUT" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(d.get('tool_input', {}).get('file_path', ''))
")
else
  exit 0
fi

if [[ -z "$FILE_PATH" ]]; then
  exit 0
fi

# Resolve JARFIS scripts directory
SCRIPTS_DIR="$HOME/.claude/scripts"
if [[ ! -f "$SCRIPTS_DIR/jarfis_cli.py" ]]; then
  # Fallback: try source path
  SOURCE_FILE="$HOME/.claude/.jarfis-source"
  if [[ -f "$SOURCE_FILE" ]]; then
    SCRIPTS_DIR="$(cat "$SOURCE_FILE" | tr -d '[:space:]')/scripts"
  fi
fi

# Run quality gate via Python module
if command -v python3 >/dev/null 2>&1 && [[ -f "$SCRIPTS_DIR/jarfis_cli.py" ]]; then
  OUTPUT=$(python3 "$SCRIPTS_DIR/jarfis_cli.py" quality-gate "$FILE_PATH" 2>&1)
  EXIT_CODE=$?

  # Check if skipped
  if echo "$OUTPUT" | grep -q '"status".*"skipped"'; then
    echo "[quality-gate] skipped: $(basename "$FILE_PATH")"
    exit 0
  fi

  # Print warnings to stderr (PostToolUse — never block)
  if echo "$OUTPUT" | grep -q '"status".*"warn"'; then
    echo "$OUTPUT" | grep -E 'FAIL' >&2
    echo "[quality-gate] warnings found for: $(basename "$FILE_PATH")" >&2
  else
    echo "[quality-gate] OK: $(basename "$FILE_PATH")"
  fi
else
  echo "[quality-gate] skipped (python3 or jarfis_cli.py not found)"
fi

# PostToolUse hooks must NEVER block
exit 0
