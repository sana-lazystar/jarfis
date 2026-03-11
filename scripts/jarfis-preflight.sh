#!/bin/bash
# JARFIS Pre-flight — work/continue/meeting 사전 검증
# 프로젝트 프로필, learnings, project-context, git 상태를 확인하고 JSON으로 출력.
#
# Usage:
#   jarfis-preflight.sh [options] [project_dir]
#
# Options:
#   --workspace-dir path   워크스페이스 디렉토리 (기본: {JARFIS_SOURCE}/.local/workspace)
#   --check-meetings       미팅 디렉토리 존재 여부도 확인
#   --verbose              상세 출력 (stderr)
#
# Output: JSON (stdout)
# {
#   "project_dir": "/path/to/project",
#   "profile_path": ".jarfis/project-profile.md" or null,
#   "has_profile": true/false,
#   "has_learnings": true/false,
#   "learnings_path": "{JARFIS_SOURCE}/.local/jarfis-learnings.md" or null,
#   "has_context": true/false,
#   "context_path": ".jarfis/project-context.md" or null,
#   "git_available": true/false,
#   "branch": "main" or null,
#   "uncommitted": 0,
#   "has_uncommitted": false,
#   "workspace_dir": "/path/to/workspace",
#   "has_meetings": true/false,
#   "warnings": ["msg1", ...]
# }

set -eo pipefail

# ── Args parsing ──
PROJECT_DIR=""
WORKSPACE_DIR=""
CHECK_MEETINGS=false
VERBOSE=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --workspace-dir) WORKSPACE_DIR="$2"; shift 2 ;;
    --check-meetings) CHECK_MEETINGS=true; shift ;;
    --verbose) VERBOSE=true; shift ;;
    *) PROJECT_DIR="$1"; shift ;;
  esac
done

log() {
  if $VERBOSE; then echo "[preflight] $*" >&2; fi
}

# ── Defaults ──
if [ -z "$PROJECT_DIR" ]; then
  PROJECT_DIR="$(pwd)"
fi

if [ -z "$WORKSPACE_DIR" ]; then
  WORKS_DIR_FILE="$HOME/.claude/.jarfis-works-dir"
  if [ -f "$WORKS_DIR_FILE" ]; then
    WORKSPACE_DIR="$(cat "$WORKS_DIR_FILE" | tr -d '[:space:]')"
  else
    SOURCE_FILE="$HOME/.claude/.jarfis-source"
    if [ -f "$SOURCE_FILE" ]; then
      WORKSPACE_DIR="$(cat "$SOURCE_FILE" | tr -d '[:space:]')/.local/workspace"
    else
      WORKSPACE_DIR="$HOME/repos/jarfis/.local/workspace"
    fi
  fi
fi

WARNINGS=()

# ── Profile check ──
PROFILE_PATH="$PROJECT_DIR/.jarfis/project-profile.md"
HAS_PROFILE=false
PROFILE_JSON="null"
if [ -f "$PROFILE_PATH" ]; then
  HAS_PROFILE=true
  PROFILE_JSON="\"$PROFILE_PATH\""
  log "Profile found: $PROFILE_PATH"
else
  WARNINGS+=("프로젝트 프로필이 없습니다. /jarfis:project-init으로 생성하세요.")
  log "Profile not found"
fi

# ── Learnings check ──
SOURCE_FILE_L="$HOME/.claude/.jarfis-source"
if [ -f "$SOURCE_FILE_L" ]; then
  LEARNINGS_PATH="$(cat "$SOURCE_FILE_L" | tr -d '[:space:]')/.local/jarfis-learnings.md"
else
  LEARNINGS_PATH="$HOME/repos/jarfis/.local/jarfis-learnings.md"
fi
HAS_LEARNINGS=false
LEARNINGS_JSON="null"
if [ -f "$LEARNINGS_PATH" ]; then
  HAS_LEARNINGS=true
  LEARNINGS_JSON="\"$LEARNINGS_PATH\""
  log "Learnings found: $LEARNINGS_PATH"
else
  log "Learnings not found"
fi

# ── Project context check ──
CONTEXT_PATH="$PROJECT_DIR/.jarfis/project-context.md"
HAS_CONTEXT=false
CONTEXT_JSON="null"
if [ -f "$CONTEXT_PATH" ]; then
  HAS_CONTEXT=true
  CONTEXT_JSON="\"$CONTEXT_PATH\""
  log "Context found: $CONTEXT_PATH"
else
  log "Context not found"
fi

# ── Git check ──
GIT_AVAILABLE=false
BRANCH="null"
UNCOMMITTED=0
HAS_UNCOMMITTED=false

if [ -d "$PROJECT_DIR/.git" ] || git -C "$PROJECT_DIR" rev-parse --git-dir >/dev/null 2>&1; then
  GIT_AVAILABLE=true
  BRANCH_RAW=$(git -C "$PROJECT_DIR" branch --show-current 2>/dev/null || echo "")
  if [ -n "$BRANCH_RAW" ]; then
    BRANCH="\"$BRANCH_RAW\""
  fi
  UNCOMMITTED=$(git -C "$PROJECT_DIR" status --porcelain 2>/dev/null | wc -l | tr -d ' ')
  if [ "$UNCOMMITTED" -gt 0 ]; then
    HAS_UNCOMMITTED=true
    WARNINGS+=("커밋되지 않은 변경 ${UNCOMMITTED}개가 있습니다.")
  fi
  log "Git: branch=$BRANCH_RAW, uncommitted=$UNCOMMITTED"
else
  WARNINGS+=("Git 저장소가 아닙니다.")
  log "Git not available"
fi

# ── Meetings check ──
HAS_MEETINGS=false
if $CHECK_MEETINGS; then
  MEETINGS_DIR="$PROJECT_DIR/.jarfis/meetings"
  if [ -d "$MEETINGS_DIR" ]; then
    MEETING_COUNT=$(find "$MEETINGS_DIR" -name "summary.md" -type f 2>/dev/null | wc -l | tr -d ' ')
    if [ "$MEETING_COUNT" -gt 0 ]; then
      HAS_MEETINGS=true
    fi
  fi
  log "Meetings: $HAS_MEETINGS"
fi

# ── Build warnings JSON array ──
WARNINGS_JSON="["
FIRST=true
for w in "${WARNINGS[@]}"; do
  if $FIRST; then FIRST=false; else WARNINGS_JSON="$WARNINGS_JSON,"; fi
  # Escape quotes in warning message
  w_escaped=$(echo "$w" | sed 's/"/\\"/g')
  WARNINGS_JSON="$WARNINGS_JSON\"$w_escaped\""
done
WARNINGS_JSON="$WARNINGS_JSON]"

# ── Output JSON ──
cat <<EOF
{"project_dir":"$PROJECT_DIR","profile_path":$PROFILE_JSON,"has_profile":$HAS_PROFILE,"has_learnings":$HAS_LEARNINGS,"learnings_path":$LEARNINGS_JSON,"has_context":$HAS_CONTEXT,"context_path":$CONTEXT_JSON,"git_available":$GIT_AVAILABLE,"branch":$BRANCH,"uncommitted":$UNCOMMITTED,"has_uncommitted":$HAS_UNCOMMITTED,"workspace_dir":"$WORKSPACE_DIR","has_meetings":$HAS_MEETINGS,"warnings":$WARNINGS_JSON}
EOF
