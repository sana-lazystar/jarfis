#!/bin/bash
# JARFIS PreCompact Hook
# Backs up JARFIS workflow state before auto-compact.
# Claude Code passes JSON via stdin with trigger(manual/auto) and cwd.

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

TRIGGER=$(_json_get "$INPUT" "trigger" "unknown")
CWD=$(_json_get "$INPUT" "cwd" ".")
SESSION_ID=$(_json_get "$INPUT" "session_id" "unknown")
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Workspace directory resolution
WORKS_DIR_FILE="$HOME/.claude/.jarfis-works-dir"
if [ -f "$WORKS_DIR_FILE" ]; then
  JARFIS_WORKSPACE_DIR=$(cat "$WORKS_DIR_FILE" | tr -d '[:space:]')
else
  SOURCE_FILE="$HOME/.claude/.jarfis-source"
  if [ -f "$SOURCE_FILE" ]; then
    JARFIS_WORKSPACE_DIR="$(cat "$SOURCE_FILE" | tr -d '[:space:]')/.local/workspace"
  else
    JARFIS_WORKSPACE_DIR="$HOME/repos/jarfis/.local/workspace"
  fi
fi

# 1. Back up jarfis-state.json (for work workflows)
#    Find the most recent .jarfis-state.json under $JARFIS_WORKSPACE_DIR/works/.
STATE_FILE=$(find "$JARFIS_WORKSPACE_DIR/works" -name ".jarfis-state.json" -maxdepth 2 2>/dev/null | head -1)

if [ -n "$STATE_FILE" ]; then
  STATE_DIR=$(dirname "$STATE_FILE")
  BACKUP_DIR="$STATE_DIR/.compact-backups"
  mkdir -p "$BACKUP_DIR"

  # Back up state file
  cp "$STATE_FILE" "$BACKUP_DIR/state_${TIMESTAMP}.json"

  # Clean old backups (keep only latest 10)
  ls -t "$BACKUP_DIR"/state_*.json 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null

  # Record backup metadata
  echo "{\"trigger\":\"$TRIGGER\",\"session_id\":\"$SESSION_ID\",\"timestamp\":\"$TIMESTAMP\",\"state_file\":\"$STATE_FILE\"}" \
    > "$BACKUP_DIR/last_compact.json"
fi

# 2. Back up in-progress meeting notes
#    Check recently modified directories under $JARFIS_WORKSPACE_DIR/meetings/
MEETING_DIR=$(find "$JARFIS_WORKSPACE_DIR/meetings" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | while read d; do
  if [ -f "$d/summary.md" ]; then
    echo "$d"
  fi
done | tail -1)

if [ -n "$MEETING_DIR" ]; then
  MEETING_BACKUP="$MEETING_DIR/.compact-backups"
  mkdir -p "$MEETING_BACKUP"

  # Back up meeting files
  for f in summary.md meeting-notes.md decisions.md tech-research.md; do
    [ -f "$MEETING_DIR/$f" ] && cp "$MEETING_DIR/$f" "$MEETING_BACKUP/${f%.md}_${TIMESTAMP}.md"
  done

  # Clean old backups
  ls -t "$MEETING_BACKUP"/*_*.md 2>/dev/null | tail -n +21 | xargs rm -f 2>/dev/null
fi

exit 0
