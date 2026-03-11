#!/bin/bash
# JARFIS README Auto-Update Script
# jarfis-index.md + CHANGELOG.md → README.md 섹션 자동 갱신
# Usage: bash jarfis-readme-update.sh [repo_path]

set -euo pipefail

REPO_PATH="${1:-}"

# repo 경로 결정
if [ -z "$REPO_PATH" ]; then
  SOURCE_FILE="$HOME/.claude/.jarfis-source"
  if [ -f "$SOURCE_FILE" ]; then
    REPO_PATH="$(cat "$SOURCE_FILE")"
  else
    REPO_PATH="$HOME/repos/jarfis"
  fi
fi

README="$REPO_PATH/README.md"
INDEX="$HOME/.claude/commands/jarfis/jarfis-index.md"
CHANGELOG="$REPO_PATH/CHANGELOG.md"

if [ ! -f "$README" ]; then
  echo "ERROR: README.md not found at $README"
  exit 1
fi

UPDATED=0

# ── 헬퍼: 마커 사이 내용 교체 ──
# replace_section <file> <start_marker> <end_marker> <content_file>
replace_section() {
  local file="$1"
  local start="$2"
  local end="$3"
  local content_file="$4"
  local tmpfile
  tmpfile=$(mktemp)

  awk -v start="$start" -v end="$end" -v cfile="$content_file" '
    $0 == start {
      print
      while ((getline line < cfile) > 0) print line
      close(cfile)
      skip=1
      next
    }
    $0 == end { skip=0; print; next }
    !skip { print }
  ' "$file" > "$tmpfile"

  if ! diff -q "$file" "$tmpfile" > /dev/null 2>&1; then
    cp "$tmpfile" "$file"
    UPDATED=$((UPDATED + 1))
  fi
  rm -f "$tmpfile"
}

# ── 1. Commands 섹션 갱신 ──
if [ -f "$INDEX" ]; then
  CMD_TMP=$(mktemp)
  awk '
    /^## 명령어 매핑/ { found=1; next }
    found && /^\|.*\|.*\|.*\|/ {
      if ($0 ~ /^[|] *명령어/ || $0 ~ /^[|]-/) next
      split($0, cols, "|")
      gsub(/^[ \t]+|[ \t]+$/, "", cols[2])
      gsub(/^[ \t]+|[ \t]+$/, "", cols[4])
      if (cols[2] != "" && cols[4] != "") {
        cmds[++n] = cols[2]
        descs[n] = cols[4]
      }
    }
    found && /^$/ { found=0 }
    found && /^##/ { found=0 }
    END {
      maxcmd = 24; maxdesc = 31
      for (i=1; i<=n; i++) {
        if (length(cmds[i]) > maxcmd) maxcmd = length(cmds[i])
        if (length(descs[i]) > maxdesc) maxdesc = length(descs[i])
      }
      printf "## Commands\n\n"
      printf "| %-*s | %-*s |\n", maxcmd, "Command", maxdesc, "Description"
      printf "| "
      for (i=1; i<=maxcmd; i++) printf "-"
      printf " | "
      for (i=1; i<=maxdesc; i++) printf "-"
      printf " |\n"
      for (i=1; i<=n; i++) {
        printf "| %-*s | %-*s |\n", maxcmd, cmds[i], maxdesc, descs[i]
      }
    }
  ' "$INDEX" > "$CMD_TMP"

  if [ -s "$CMD_TMP" ]; then
    replace_section "$README" \
      "<!-- JARFIS-COMMANDS-START -->" \
      "<!-- JARFIS-COMMANDS-END -->" \
      "$CMD_TMP"
  fi
  rm -f "$CMD_TMP"
fi

# ── 2. Architecture 섹션 갱신 ──
if [ -f "$INDEX" ]; then
  ARCH_TMP=$(mktemp)
  awk '
    /^## 파일 구조/ { found=1; next }
    found && /^```$/ && !in_block { in_block=1; next }
    found && /^```$/ && in_block { in_block=0; found=0; next }
    found && in_block {
      line = $0
      gsub(/ *\([0-9]+줄[^)]*\)/, "", line)
      gsub(/ *\[NEW\]/, "", line)
      gsub(/[ \t]+$/, "", line)
      lines[++n] = line
    }
    END {
      printf "## Architecture\n\n```\n"
      for (i=1; i<=n; i++) print lines[i]
      printf "```\n\n"
      printf "**설계 원칙**:\n\n"
      printf "- **워크플로우 흐름**은 `work.md`에, **에이전트 프롬프트**는 `prompts/`에, **산출물 양식**은 `templates/`에 분리\n"
      printf "- 에이전트 역할 프롬프트(`agents/`)와 워크플로우 프롬프트(`prompts/`)는 별개 — 역할은 고정, 태스크는 Phase마다 다름\n"
      printf "- 학습 데이터는 로컬에만 존재 (Git repo에 포함되지 않음)"
    }
  ' "$INDEX" > "$ARCH_TMP"

  if [ -s "$ARCH_TMP" ]; then
    replace_section "$README" \
      "<!-- JARFIS-ARCHITECTURE-START -->" \
      "<!-- JARFIS-ARCHITECTURE-END -->" \
      "$ARCH_TMP"
  fi
  rm -f "$ARCH_TMP"
fi

# ── 3. Latest Changes 섹션 갱신 ──
if [ -f "$CHANGELOG" ]; then
  CL_TMP=$(mktemp)
  awk '
    /^## \[[0-9]+\.[0-9]+\.[0-9]+\]/ {
      if (found) exit
      found=1
    }
    found { lines[++n] = $0 }
    END {
      if (n == 0) exit
      # 끝 빈 줄 제거
      while (n > 0 && lines[n] == "") n--
      printf "## Latest Changes\n\n"
      printf "> 전체 변경 이력은 [CHANGELOG.md](./CHANGELOG.md)를 참조하세요.\n\n"
      for (i=1; i<=n; i++) print lines[i]
    }
  ' "$CHANGELOG" > "$CL_TMP"

  if [ -s "$CL_TMP" ]; then
    replace_section "$README" \
      "<!-- JARFIS-LATEST-CHANGES-START -->" \
      "<!-- JARFIS-LATEST-CHANGES-END -->" \
      "$CL_TMP"
  fi
  rm -f "$CL_TMP"
fi

# 결과 보고
if [ $UPDATED -gt 0 ]; then
  echo "📝 README.md: ${UPDATED}개 섹션 갱신"
else
  echo "📝 README.md: 이미 최신 (변경 없음)"
fi
