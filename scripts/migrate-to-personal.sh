#!/bin/bash
set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   JARFIS Migration: .local → .personal/orgs/Medistream
#   One-time script for migrating existing Medistream data
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"

OLD_BASE="$REPO_DIR/.local"
OLD_WORKS="$OLD_BASE/workspace/works"
OLD_MEETINGS="$OLD_BASE/workspace/meetings"
OLD_LEARNINGS="$OLD_BASE/jarfis-learnings.md"

NEW_BASE="$REPO_DIR/.personal"
ORG_NAME="Medistream"
ORG_ROOT="/Users/sanhalee/Integration/Medistream/Projects/Bitbucket"
ORG_DIR="$NEW_BASE/orgs/$ORG_NAME"
NEW_WORKS="$ORG_DIR/works"
NEW_MEETINGS="$ORG_DIR/meetings"
NEW_LEARNINGS="$ORG_DIR/learnings.md"
ORGS_JSON="$NEW_BASE/orgs/orgs.json"

# Parse --dry-run flag
DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  JARFIS Migration → .personal/orgs/$ORG_NAME"
if [[ "$DRY_RUN" == "true" ]]; then
  echo "  [DRY RUN — no changes will be made]"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Counters
works_moved=0
meetings_moved=0
works_skipped=0
meetings_skipped=0

# ── 1. Register Medistream in orgs.json ──
echo "[1/4] Registering $ORG_NAME in orgs.json..."

if [[ ! -d "$NEW_BASE/orgs" ]]; then
  echo "  [ERROR] .personal/orgs/ does not exist. Run install.sh first."
  exit 1
fi

if [[ -f "$ORGS_JSON" ]]; then
  # Check if already registered
  if python3 -c "
import json, sys
with open('$ORGS_JSON') as f:
    data = json.load(f)
for org in data.get('orgs', []):
    if org['name'] == '$ORG_NAME':
        sys.exit(0)
sys.exit(1)
" 2>/dev/null; then
    echo "  [OK] $ORG_NAME already registered"
  else
    if [[ "$DRY_RUN" == "false" ]]; then
      python3 -c "
import json
with open('$ORGS_JSON') as f:
    data = json.load(f)
data['orgs'].append({'name': '$ORG_NAME', 'root': '$ORG_ROOT'})
with open('$ORGS_JSON', 'w') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
"
      echo "  [OK] Registered $ORG_NAME (root: $ORG_ROOT)"
    else
      echo "  [DRY] Would register $ORG_NAME (root: $ORG_ROOT)"
    fi
  fi
else
  echo "  [ERROR] orgs.json not found at $ORGS_JSON"
  exit 1
fi

# ── 2. Create target directories ──
echo "[2/4] Preparing target directories..."

if [[ "$DRY_RUN" == "false" ]]; then
  mkdir -p "$NEW_WORKS"
  mkdir -p "$NEW_MEETINGS"
  echo "  [OK] Created $ORG_DIR/{works,meetings}"
else
  echo "  [DRY] Would create $ORG_DIR/{works,meetings}"
fi

# ── 3. Move matching works and meetings ──
echo "[3/4] Moving workflow data..."

# Works: match IWS26H1
if [[ -d "$OLD_WORKS" ]]; then
  for dir in "$OLD_WORKS"/*/; do
    [[ ! -d "$dir" ]] && continue
    dirname=$(basename "$dir")
    if echo "$dirname" | grep -q "IWS26H1"; then
      if [[ "$DRY_RUN" == "false" ]]; then
        mv "$dir" "$NEW_WORKS/"
        echo "  [OK] works/$dirname → Medistream"
      else
        echo "  [DRY] works/$dirname → Medistream"
      fi
      works_moved=$((works_moved + 1))
    else
      echo "  [SKIP] works/$dirname (no IWS26H1 match)"
      works_skipped=$((works_skipped + 1))
    fi
  done
else
  echo "  [WARN] $OLD_WORKS not found"
fi

# Meetings: match medistream or 메디 (case-insensitive for English)
if [[ -d "$OLD_MEETINGS" ]]; then
  for dir in "$OLD_MEETINGS"/*/; do
    [[ ! -d "$dir" ]] && continue
    dirname=$(basename "$dir")
    if echo "$dirname" | grep -iq "medistream" || echo "$dirname" | grep -q "메디"; then
      if [[ "$DRY_RUN" == "false" ]]; then
        mv "$dir" "$NEW_MEETINGS/"
        echo "  [OK] meetings/$dirname → Medistream"
      else
        echo "  [DRY] meetings/$dirname → Medistream"
      fi
      meetings_moved=$((meetings_moved + 1))
    else
      echo "  [SKIP] meetings/$dirname (no medistream/메디 match)"
      meetings_skipped=$((meetings_skipped + 1))
    fi
  done
else
  echo "  [WARN] $OLD_MEETINGS not found"
fi

# ── 4. Copy learnings ──
echo "[4/4] Copying learnings..."

if [[ -f "$OLD_LEARNINGS" ]]; then
  if [[ -f "$NEW_LEARNINGS" ]]; then
    echo "  [SKIP] $NEW_LEARNINGS already exists"
  elif [[ "$DRY_RUN" == "false" ]]; then
    cp "$OLD_LEARNINGS" "$NEW_LEARNINGS"
    echo "  [OK] jarfis-learnings.md → Medistream/learnings.md"
  else
    echo "  [DRY] jarfis-learnings.md → Medistream/learnings.md"
  fi
else
  echo "  [WARN] $OLD_LEARNINGS not found"
fi

# ── Summary ──
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Migration Summary"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Works moved:    $works_moved"
echo "  Works skipped:  $works_skipped"
echo "  Meetings moved: $meetings_moved"
echo "  Meetings skipped: $meetings_skipped"
echo "  Learnings:      $(if [[ -f "$NEW_LEARNINGS" ]] || [[ "$DRY_RUN" == "true" && -f "$OLD_LEARNINGS" ]]; then echo "copied"; else echo "skipped"; fi)"
echo ""
if [[ "$DRY_RUN" == "true" ]]; then
  echo "  This was a DRY RUN. No changes were made."
  echo "  Run without --dry-run to execute."
else
  echo "  Done! Remaining data in .local/ can be manually cleaned:"
  echo "    ls $OLD_WORKS"
  echo "    ls $OLD_MEETINGS"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
