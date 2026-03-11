#!/bin/bash
# JARFIS Repo Sync Script
# ~/.claude/ → {repo_path}/ 단방향 동기화
# Usage: bash jarfis-sync.sh [repo_path]

set -euo pipefail

REPO_PATH="${1:-}"

# repo 경로 결정: 인자 > .jarfis-source > 기본값
if [ -z "$REPO_PATH" ]; then
  SOURCE_FILE="$HOME/.claude/.jarfis-source"
  if [ -f "$SOURCE_FILE" ]; then
    REPO_PATH="$(cat "$SOURCE_FILE")"
  else
    REPO_PATH="$HOME/repos/jarfis"
  fi
fi

if [ ! -d "$REPO_PATH" ]; then
  echo "ERROR: repo not found at $REPO_PATH"
  exit 1
fi

CLAUDE_DIR="$HOME/.claude"
SYNCED=0
CHANGES=""

# 동기화 함수: src → dst
sync_file() {
  local src="$1"
  local dst="$2"
  if [ ! -f "$src" ]; then
    return
  fi
  mkdir -p "$(dirname "$dst")"
  if [ ! -f "$dst" ] || ! diff -q "$src" "$dst" > /dev/null 2>&1; then
    cp "$src" "$dst"
    local rel_src="${src#$CLAUDE_DIR/}"
    CHANGES="${CHANGES}\n  ✅ ${rel_src}"
    SYNCED=$((SYNCED + 1))
  fi
}

# 1. commands/jarfis.md
sync_file "$CLAUDE_DIR/commands/jarfis.md" "$REPO_PATH/commands/jarfis.md"

# 2. commands/jarfis/* (재귀, .distill-backup 제외)
if [ -d "$CLAUDE_DIR/commands/jarfis" ]; then
  while IFS= read -r f; do
    rel="${f#$CLAUDE_DIR/commands/jarfis/}"
    sync_file "$f" "$REPO_PATH/commands/jarfis/$rel"
  done < <(find "$CLAUDE_DIR/commands/jarfis" -name "*.md" -not -path "*/.distill-backup/*")
fi

# 3. agents/jarfis/*
if [ -d "$CLAUDE_DIR/agents/jarfis" ]; then
  while IFS= read -r f; do
    rel="${f#$CLAUDE_DIR/agents/jarfis/}"
    sync_file "$f" "$REPO_PATH/agents/jarfis/$rel"
  done < <(find "$CLAUDE_DIR/agents/jarfis" -name "*.md")
fi

# 4. hooks/* (jarfis- 접두사만)
if [ -d "$CLAUDE_DIR/hooks" ]; then
  while IFS= read -r f; do
    rel="${f#$CLAUDE_DIR/hooks/}"
    sync_file "$f" "$REPO_PATH/hooks/$rel"
  done < <(find "$CLAUDE_DIR/hooks" -type f -name "jarfis-*")
fi

# 5. scripts/* (jarfis- 접두사 + claude-cleanup.sh)
if [ -d "$CLAUDE_DIR/scripts" ]; then
  while IFS= read -r f; do
    rel="${f#$CLAUDE_DIR/scripts/}"
    sync_file "$f" "$REPO_PATH/scripts/$rel"
  done < <(find "$CLAUDE_DIR/scripts" -type f \( -name "jarfis-*" -o -name "claude-cleanup.sh" \))
fi

# 6. statusline-command.sh
sync_file "$CLAUDE_DIR/statusline-command.sh" "$REPO_PATH/statusline-command.sh"

# 7. README.md 자동 갱신
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/jarfis-readme-update.sh" ]; then
  README_RESULT=$(bash "$SCRIPT_DIR/jarfis-readme-update.sh" "$REPO_PATH" 2>&1) || true
  CHANGES="${CHANGES}\n  ${README_RESULT}"
fi

# 결과 보고
if [ $SYNCED -gt 0 ]; then
  echo "🔄 Repo 동기화: ${SYNCED}개 파일 → ${REPO_PATH}"
  echo -e "$CHANGES"
else
  echo "✅ Repo 동기화: 이미 최신 (변경 없음)"
  echo -e "$CHANGES"
fi
