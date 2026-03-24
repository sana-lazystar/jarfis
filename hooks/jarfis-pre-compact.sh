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

# Personal directory resolution
PERSONAL_DIR_FILE="$HOME/.claude/.jarfis-personal-dir"
if [ -f "$PERSONAL_DIR_FILE" ]; then
  JARFIS_PERSONAL_DIR=$(cat "$PERSONAL_DIR_FILE" | tr -d '[:space:]')
else
  SOURCE_FILE="$HOME/.claude/.jarfis-source"
  if [ -f "$SOURCE_FILE" ]; then
    JARFIS_PERSONAL_DIR="$(cat "$SOURCE_FILE" | tr -d '[:space:]')/.personal"
  else
    JARFIS_PERSONAL_DIR="$HOME/repos/jarfis/.personal"
  fi
fi

ORGS_DIR="$JARFIS_PERSONAL_DIR/orgs"

# 1. Back up jarfis-state.json (scan all org workspaces)
STATE_FILE=""
if [ -d "$ORGS_DIR" ]; then
  STATE_FILE=$(find "$ORGS_DIR" -path "*/works/*/.jarfis-state.json" -maxdepth 4 2>/dev/null | head -1)
fi

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

# 2. Back up in-progress meeting notes (scan all org workspaces)
MEETING_DIR=""
if [ -d "$ORGS_DIR" ]; then
  MEETING_DIR=$(find "$ORGS_DIR" -path "*/meetings/*" -mindepth 3 -maxdepth 3 -type d 2>/dev/null | while read d; do
    if [ -f "$d/summary.md" ]; then
      echo "$d"
    fi
  done | tail -1)
fi

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
