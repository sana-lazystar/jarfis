#!/bin/bash
# JARFIS Measure — 프롬프트 파일 토큰 측정 + 구조 진단
# distill D-0/D-1/D-4에서 사용. LLM이 파일을 읽지 않고 측정 결과만 받음.
#
# Usage:
#   jarfis-measure.sh [options] [dir1 dir2 ...]
#
# Options:
#   --exclude file1,file2   측정에서 제외할 파일명 (콤마 구분)
#   --index path            인덱스 파일 경로 (불일치 검증용)
#   --verbose               상세 출력 (stderr)
#   --diagnostics           D-1 진단 정보 포함 (코드블록, 헤더, 프롬프트 패턴)
#
# Output: JSON (stdout)

set -eo pipefail

# ── Args parsing ──
EXCLUDE=""
INDEX_PATH=""
VERBOSE=false
DIAGNOSTICS=false
DIRS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --exclude) EXCLUDE="$2"; shift 2 ;;
    --index) INDEX_PATH="$2"; shift 2 ;;
    --verbose) VERBOSE=true; shift ;;
    --diagnostics) DIAGNOSTICS=true; shift ;;
    *) DIRS+=("$1"); shift ;;
  esac
done

# Default dirs if none provided
if [ ${#DIRS[@]} -eq 0 ]; then
  DIRS=(
    "$HOME/.claude/commands/jarfis"
    "$HOME/.claude/agents/jarfis"
  )
  # Also include the main jarfis.md
  EXTRA_FILES=("$HOME/.claude/commands/jarfis.md")
else
  EXTRA_FILES=()
fi

log() {
  if $VERBOSE; then echo "[measure] $*" >&2; fi
}

# ── Exclude list to array ──
EXCLUDE_ARR=()
if [ -n "$EXCLUDE" ]; then
  IFS=',' read -ra EXCLUDE_ARR <<< "$EXCLUDE"
fi
is_excluded() {
  local fname="$1"
  [ ${#EXCLUDE_ARR[@]} -eq 0 ] && return 1
  for ex in "${EXCLUDE_ARR[@]}"; do
    [ -z "$ex" ] && continue
    if [ "$(basename "$fname")" = "$ex" ]; then
      return 0
    fi
  done
  return 1
}

# ── Collect target files ──
FILES=()
for dir in "${DIRS[@]}"; do
  if [ -f "$dir" ]; then
    FILES+=("$dir")
  elif [ -d "$dir" ]; then
    while IFS= read -r f; do
      FILES+=("$f")
    done < <(find "$dir" -name "*.md" -not -path "*/.distill-backup/*" 2>/dev/null | sort)
  fi
done

if [ ${#EXTRA_FILES[@]} -gt 0 ]; then
  for f in "${EXTRA_FILES[@]}"; do
    [ -f "$f" ] && FILES+=("$f")
  done
fi

# ── Measure each file ──
TOTAL_LINES=0
TOTAL_CHARS=0
TOTAL_TOKENS=0
FILE_COUNT=0

# Start JSON array
echo '{"files":['

FIRST=true
for filepath in "${FILES[@]}"; do
  fname=$(basename "$filepath")

  if is_excluded "$fname"; then
    log "Excluded: $fname"
    continue
  fi

  if [ ! -f "$filepath" ]; then
    log "Not found: $filepath"
    continue
  fi

  lines=$(wc -l < "$filepath" | tr -d ' ')
  chars=$(wc -c < "$filepath" | tr -d ' ')
  tokens_est=$((chars / 4))

  # Relative path from ~/.claude/
  rel_path="${filepath#$HOME/.claude/}"

  TOTAL_LINES=$((TOTAL_LINES + lines))
  TOTAL_CHARS=$((TOTAL_CHARS + chars))
  TOTAL_TOKENS=$((TOTAL_TOKENS + tokens_est))
  FILE_COUNT=$((FILE_COUNT + 1))

  # ── Diagnostics (D-1) ──
  DIAG_JSON=""
  if $DIAGNOSTICS; then
    # 1. Codeblock analysis: count lines inside ``` blocks
    cb_lines=$(awk '/^```/{toggle=!toggle; next} toggle{c++} END{print c+0}' "$filepath")
    cb_ratio=$(awk -v cb="$cb_lines" -v total="$lines" 'BEGIN{if(total>0) printf "%.2f", cb/total; else print "0.00"}')

    # 2. Header extraction (## level) — pipefail-safe
    headers=""
    while IFS= read -r line; do
      linenum=$(echo "$line" | cut -d: -f1)
      content=$(echo "$line" | cut -d: -f2- | sed 's/^ *//' | sed 's/\\/\\\\/g' | sed 's/"/\\"/g')
      [ -n "$headers" ] && headers="$headers,"
      headers="$headers{\"line\":$linenum,\"text\":\"$content\"}"
    done < <(grep -n '^##' "$filepath" 2>/dev/null | head -30 || true)

    # 3. Prompt pattern detection — pipefail-safe
    prompts=""
    while IFS= read -r line; do
      [ -z "$line" ] && continue
      linenum=$(echo "$line" | cut -d: -f1)
      content=$(echo "$line" | cut -d: -f2- | sed 's/^ *//' | sed 's/\\/\\\\/g' | sed 's/"/\\"/g')
      [ -n "$prompts" ] && prompts="$prompts,"
      prompts="$prompts{\"line\":$linenum,\"text\":\"$content\"}"
    done < <(grep -n '📄 프롬프트:\|📄 템플릿:\|Task prompt:\|prompt:' "$filepath" 2>/dev/null | head -20 || true)

    DIAG_JSON=$(cat <<DIAGEOF
,"diagnostics":{"codeblock_lines":$cb_lines,"codeblock_ratio":$cb_ratio,"headers":[${headers:-}],"prompt_patterns":[${prompts:-}]}
DIAGEOF
)
  fi

  # Output file entry
  if $FIRST; then FIRST=false; else echo ","; fi
  echo "{\"path\":\"$rel_path\",\"name\":\"$fname\",\"lines\":$lines,\"chars\":$chars,\"tokens_est\":$tokens_est${DIAG_JSON}}"

  log "Measured: $fname ($lines lines, ~${tokens_est}tok)"
done

echo '],'

# ── Index mismatch check ──
MISMATCH_JSON=""
if [ -n "$INDEX_PATH" ] && [ -f "$INDEX_PATH" ]; then
  # Extract file paths from index (lines matching ├── or └── patterns)
  index_files=$(grep -oE '[a-zA-Z0-9_-]+\.md' "$INDEX_PATH" 2>/dev/null | sort -u)

  # Get actual files on disk
  disk_files=""
  for dir in "${DIRS[@]}"; do
    [ -d "$dir" ] && disk_files="$disk_files $(find "$dir" -name "*.md" -not -path "*/.distill-backup/*" -exec basename {} \; 2>/dev/null)"
  done
  disk_files=$(echo "$disk_files" | tr ' ' '\n' | sort -u | grep -v '^$')

  # Find mismatches
  missing_on_disk=$(comm -23 <(echo "$index_files") <(echo "$disk_files") | head -10)
  not_in_index=$(comm -13 <(echo "$index_files") <(echo "$disk_files") | head -10)

  missing_arr=""
  for m in $missing_on_disk; do
    [ -n "$missing_arr" ] && missing_arr="$missing_arr,"
    missing_arr="$missing_arr\"missing_on_disk:$m\""
  done
  for n in $not_in_index; do
    [ -n "$missing_arr" ] && missing_arr="$missing_arr,"
    missing_arr="$missing_arr\"not_in_index:$n\""
  done

  MISMATCH_JSON="\"index_mismatches\":[${missing_arr}],"
fi

# ── Total ──
echo "${MISMATCH_JSON}\"total\":{\"files\":$FILE_COUNT,\"lines\":$TOTAL_LINES,\"chars\":$TOTAL_CHARS,\"tokens_est\":$TOTAL_TOKENS}}"
