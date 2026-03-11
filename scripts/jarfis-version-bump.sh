#!/bin/bash
# JARFIS Version Bump — semver 버전 범프 자동화
# implement/distill/upgrade 완료 시 호출.
#
# Usage:
#   jarfis-version-bump.sh <patch|minor|major> "changelog entry"
#
# Reads repo path from ~/.claude/.jarfis-source (default: ~/repos/jarfis)
# Updates: VERSION, .jarfis-version, jarfis-index.md, CHANGELOG.md
#
# Output: JSON summary (stdout)

set -euo pipefail

BUMP_TYPE="${1:-}"
CHANGELOG_ENTRY="${2:-}"

if [ -z "$BUMP_TYPE" ]; then
  echo '{"error":"Usage: jarfis-version-bump.sh <patch|minor|major> \"changelog entry\""}' >&2
  exit 1
fi

if [[ ! "$BUMP_TYPE" =~ ^(patch|minor|major)$ ]]; then
  echo "{\"error\":\"Invalid bump type: $BUMP_TYPE. Must be patch, minor, or major.\"}" >&2
  exit 1
fi

# ── Resolve paths ──
SOURCE_FILE="$HOME/.claude/.jarfis-source"
if [ -f "$SOURCE_FILE" ]; then
  REPO_PATH="$(cat "$SOURCE_FILE" | tr -d '[:space:]')"
else
  REPO_PATH="$HOME/repos/jarfis"
fi

VERSION_FILE="$REPO_PATH/VERSION"
JARFIS_VERSION_FILE="$HOME/.claude/.jarfis-version"
INDEX_FILE="$HOME/.claude/commands/jarfis/jarfis-index.md"
CHANGELOG_FILE="$REPO_PATH/CHANGELOG.md"

# ── Read current version ──
if [ ! -f "$VERSION_FILE" ]; then
  echo "{\"error\":\"VERSION file not found: $VERSION_FILE\"}" >&2
  exit 1
fi

CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

# Validate
if [ -z "$MAJOR" ] || [ -z "$MINOR" ] || [ -z "$PATCH" ]; then
  echo "{\"error\":\"Invalid version format: $CURRENT\"}" >&2
  exit 1
fi

# ── Bump ──
case "$BUMP_TYPE" in
  patch) PATCH=$((PATCH + 1)) ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
TODAY=$(date +%Y-%m-%d)

# ── Update VERSION file ──
echo "$NEW_VERSION" > "$VERSION_FILE"

# ── Update .jarfis-version ──
echo "$NEW_VERSION" > "$JARFIS_VERSION_FILE"

# ── Update jarfis-index.md Version line ──
if [ -f "$INDEX_FILE" ]; then
  # Update "Last updated: YYYY-MM-DD | Version: X.Y.Z"
  sed -i.bak "s/Last updated: [0-9-]* | Version: [0-9.]*/Last updated: $TODAY | Version: $NEW_VERSION/" "$INDEX_FILE" && rm -f "$INDEX_FILE.bak"
fi

# ── Update CHANGELOG.md ──
if [ -f "$CHANGELOG_FILE" ] && [ -n "$CHANGELOG_ENTRY" ]; then
  # Find [Unreleased] section and add entry after it
  # Check if [Unreleased] exists
  if grep -q '^\[Unreleased\]' "$CHANGELOG_FILE" 2>/dev/null || grep -q '^## \[Unreleased\]' "$CHANGELOG_FILE" 2>/dev/null; then
    # Add entry after [Unreleased] line
    # Use awk to insert after the [Unreleased] header
    awk -v entry="- $CHANGELOG_ENTRY ($TODAY)" '
      /\[Unreleased\]/ {
        print
        # Skip blank lines after header
        getline
        if ($0 == "") {
          print ""
          print entry
        } else {
          print entry
          print
        }
        next
      }
      {print}
    ' "$CHANGELOG_FILE" > "$CHANGELOG_FILE.tmp"
    mv "$CHANGELOG_FILE.tmp" "$CHANGELOG_FILE"
  fi
fi

# ── Output ──
echo "{\"previous\":\"$CURRENT\",\"new\":\"$NEW_VERSION\",\"bump_type\":\"$BUMP_TYPE\",\"date\":\"$TODAY\",\"files_updated\":[\"$VERSION_FILE\",\"$JARFIS_VERSION_FILE\",\"$INDEX_FILE\",\"$CHANGELOG_FILE\"]}"
