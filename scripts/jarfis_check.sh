#!/bin/bash
# JARFIS Structure Check — grep-based prompt structure validation
# Usage: bash jarfis_check.sh
# Checks JARFIS file integrity without API calls.

set -euo pipefail

CLAUDE_DIR="${HOME}/.claude"
COMMANDS_DIR="${CLAUDE_DIR}/commands/jarfis"
AGENTS_DIR="${CLAUDE_DIR}/agents/jarfis"
SCRIPTS_DIR="${CLAUDE_DIR}/scripts"

SOURCE_FILE="${CLAUDE_DIR}/.jarfis-source"
if [ -f "$SOURCE_FILE" ]; then
  REPO_DIR=$(cat "$SOURCE_FILE" | tr -d '[:space:]')
else
  REPO_DIR="${HOME}/repos/jarfis"
fi

PASS=0
FAIL=0
WARN=0

pass() { echo "  [PASS] $1"; PASS=$((PASS + 1)); }
fail() { echo "  [FAIL] $1"; FAIL=$((FAIL + 1)); }
warn() { echo "  [WARN] $1"; WARN=$((WARN + 1)); }

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  JARFIS Structure Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. work.md Phase headings
echo "1. work.md Phase headings:"
WORK_FILE="${COMMANDS_DIR}/work.md"
if [ -f "$WORK_FILE" ]; then
  for phase in "Phase T" "Phase 0" "Phase 1" "Phase 2" "Phase 4:" "Phase 4.5" "Phase 5" "Phase 6"; do
    if grep -q "## $phase" "$WORK_FILE"; then
      pass "$phase"
    else
      fail "$phase not found in work.md"
    fi
  done
else
  fail "work.md not found"
fi
echo ""

# 2. Required prompt files
echo "2. Required prompt files:"
for pf in phase1.md phase2.md phase4.md phase4-5.md phase5.md phase6.md continue-extend.md; do
  if [ -f "${COMMANDS_DIR}/prompts/$pf" ]; then
    pass "prompts/$pf"
  else
    fail "prompts/$pf missing"
  fi
done
echo ""

# 3. VERSION consistency
echo "3. VERSION consistency:"
VERSION_FILE="${REPO_DIR}/VERSION"
INIT_FILE="${SCRIPTS_DIR}/jarfis/__init__.py"
if [ -f "$VERSION_FILE" ] && [ -f "$INIT_FILE" ]; then
  REPO_VER=$(cat "$VERSION_FILE" | tr -d '[:space:]')
  INIT_VER=$(grep '__version__' "$INIT_FILE" | sed 's/.*"\(.*\)".*/\1/')
  if [ "$REPO_VER" = "$INIT_VER" ]; then
    pass "VERSION ($REPO_VER) == __init__.py ($INIT_VER)"
  else
    fail "VERSION ($REPO_VER) != __init__.py ($INIT_VER)"
  fi
else
  [ ! -f "$VERSION_FILE" ] && fail "VERSION file not found"
  [ ! -f "$INIT_FILE" ] && fail "__init__.py not found"
fi
echo ""

# 4. Agent model consistency (work.md Agent Mapping vs frontmatter)
echo "4. Agent model consistency:"
if [ -f "$WORK_FILE" ]; then
  # Extract agent mapping from work.md (format: | Role | agent-name | model |)
  while IFS='|' read -r _ role agent model _; do
    agent=$(echo "$agent" | tr -d ' ')
    model=$(echo "$model" | tr -d ' ')
    [ -z "$agent" ] && continue
    [[ "$agent" == "Agent"* ]] && continue
    [[ "$agent" == "---"* ]] && continue

    agent_file="${AGENTS_DIR}/${agent}.md"
    if [ -f "$agent_file" ]; then
      fm_model=$(grep '^model:' "$agent_file" | head -1 | awk '{print $2}')
      if [ "$fm_model" = "$model" ]; then
        pass "$agent: $model"
      else
        fail "$agent: work.md=$model, frontmatter=$fm_model"
      fi
    fi
  done < <(grep -A 12 '### Agent Mapping' "$WORK_FILE" | grep '|.*|.*|.*|' | tail -n +3)
else
  fail "work.md not found for agent mapping check"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Results: $PASS passed, $FAIL failed, $WARN warnings"
if [ $FAIL -eq 0 ]; then
  echo "  Status: ALL CHECKS PASSED"
else
  echo "  Status: $FAIL CHECK(S) FAILED"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

exit $FAIL
