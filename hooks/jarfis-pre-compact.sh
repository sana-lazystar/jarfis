#!/bin/bash
# JARFIS PreCompact Hook
# auto-compact 직전에 JARFIS 워크플로우 상태를 백업한다.
# Claude Code가 stdin으로 JSON을 전달하며, trigger(manual/auto)와 cwd를 포함한다.

INPUT=$(cat)
TRIGGER=$(echo "$INPUT" | jq -r '.trigger // "unknown"')
CWD=$(echo "$INPUT" | jq -r '.cwd // "."')
SESSION_ID=$(echo "$INPUT" | jq -r '.session_id // "unknown"')
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 1. jarfis-state.json 백업 (work 워크플로우용)
#    $CWD/.jarfis/ 하위에서 가장 최근 .jarfis-state.json을 찾는다.
STATE_FILE=$(find "$CWD/.jarfis" -name ".jarfis-state.json" -maxdepth 3 2>/dev/null | head -1)

if [ -n "$STATE_FILE" ]; then
  STATE_DIR=$(dirname "$STATE_FILE")
  BACKUP_DIR="$STATE_DIR/.compact-backups"
  mkdir -p "$BACKUP_DIR"

  # 상태 파일 백업
  cp "$STATE_FILE" "$BACKUP_DIR/state_${TIMESTAMP}.json"

  # 오래된 백업 정리 (최근 10개만 유지)
  ls -t "$BACKUP_DIR"/state_*.json 2>/dev/null | tail -n +11 | xargs rm -f 2>/dev/null

  # 백업 메타데이터 기록
  echo "{\"trigger\":\"$TRIGGER\",\"session_id\":\"$SESSION_ID\",\"timestamp\":\"$TIMESTAMP\",\"state_file\":\"$STATE_FILE\"}" \
    > "$BACKUP_DIR/last_compact.json"
fi

# 2. meeting 진행 중 임시 노트 백업
#    ./.jarfis/meetings/ 하위에서 최근 수정된 디렉토리 확인
MEETING_DIR=$(find "$CWD/.jarfis/meetings" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | while read d; do
  if [ -f "$d/summary.md" ]; then
    echo "$d"
  fi
done | tail -1)

if [ -n "$MEETING_DIR" ]; then
  MEETING_BACKUP="$MEETING_DIR/.compact-backups"
  mkdir -p "$MEETING_BACKUP"

  # meeting 파일들 백업
  for f in summary.md meeting-notes.md decisions.md tech-research.md; do
    [ -f "$MEETING_DIR/$f" ] && cp "$MEETING_DIR/$f" "$MEETING_BACKUP/${f%.md}_${TIMESTAMP}.md"
  done

  # 오래된 백업 정리
  ls -t "$MEETING_BACKUP"/*_*.md 2>/dev/null | tail -n +21 | xargs rm -f 2>/dev/null
fi

exit 0
