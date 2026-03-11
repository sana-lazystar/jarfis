#!/bin/bash
# JARFIS Recent Meetings — 최근 미팅 N개를 JSON으로 출력
# work.md Phase 0에서 미팅 선택 AskUserQuestion에 사용.
#
# Usage:
#   jarfis-recent-meetings.sh [count]
#
# Args:
#   count  — 조회 개수 (기본값: 3)
#
# Output: JSON array (stdout)
# [
#   {"path":"meetings/20260310-결제-시스템-리뉴얼","name":"결제-시스템-리뉴얼","date":"2026-03-10","summary":"..."},
#   ...
# ]
# Empty result: []

set -eo pipefail

COUNT="${1:-3}"

# ── Workspace dir resolution ──
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

MEETINGS_DIR="$JARFIS_WORKSPACE_DIR/meetings"

# ── No meetings directory ──
if [ ! -d "$MEETINGS_DIR" ]; then
  echo "[]"
  exit 0
fi

# ── Find meeting directories with summary.md, sorted by modification time ──
MEETING_DIRS=$(find "$MEETINGS_DIR" -mindepth 1 -maxdepth 1 -type d -exec test -f '{}/summary.md' \; -print 2>/dev/null \
  | while read d; do stat -f "%m %N" "$d" 2>/dev/null || stat -c "%Y %n" "$d" 2>/dev/null; done \
  | sort -rn | head -n "$COUNT" | awk '{print $2}')

if [ -z "$MEETING_DIRS" ]; then
  echo "[]"
  exit 0
fi

# ── Parse summary.md YAML frontmatter and build JSON ──
python3 -c "
import os, json, re, sys

dirs = '''$MEETING_DIRS'''.strip().split('\n')
workspace = '$JARFIS_WORKSPACE_DIR'
results = []

for d in dirs:
    d = d.strip()
    if not d:
        continue
    summary_path = os.path.join(d, 'summary.md')
    if not os.path.isfile(summary_path):
        continue

    dirname = os.path.basename(d)
    # Extract name: remove YYYYMMDD- prefix
    name = re.sub(r'^\d{8}-', '', dirname)

    # Parse YAML frontmatter
    date_val = ''
    summary_val = ''
    idea_val = ''
    try:
        with open(summary_path, 'r') as f:
            content = f.read()
        # Extract frontmatter between --- markers
        fm_match = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        if fm_match:
            fm = fm_match.group(1)
            for line in fm.split('\n'):
                line = line.strip()
                if line.startswith('date:'):
                    date_val = line.split(':', 1)[1].strip().strip('\"').strip(\"'\")
                elif line.startswith('idea:'):
                    idea_val = line.split(':', 1)[1].strip().strip('\"').strip(\"'\")
                elif line.startswith('meeting_name:') and not name:
                    name = line.split(':', 1)[1].strip().strip('\"').strip(\"'\")

        # If no date from frontmatter, extract from dirname
        if not date_val:
            date_match = re.match(r'^(\d{4})(\d{2})(\d{2})', dirname)
            if date_match:
                date_val = f'{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}'

        # Use idea as summary, fallback to first non-frontmatter line
        summary_val = idea_val
        if not summary_val:
            lines = content.split('---')
            if len(lines) >= 3:
                body = lines[2].strip()
                first_line = body.split('\n')[0].strip().lstrip('#').strip() if body else ''
                summary_val = first_line[:80]
    except Exception:
        pass

    rel_path = 'meetings/' + dirname
    results.append({
        'path': rel_path,
        'name': name,
        'date': date_val,
        'summary': summary_val
    })

print(json.dumps(results, ensure_ascii=False))
"
