#!/bin/bash
set -euo pipefail

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#   JARFIS Installer
#   Git-based distribution with version management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
VERSION_FILE="$SCRIPT_DIR/VERSION"
INSTALLED_VERSION_FILE="$CLAUDE_DIR/.jarfis-version"
SOURCE_FILE="$CLAUDE_DIR/.jarfis-source"

# Parse arguments
TARGET_VERSION=""
FORCE=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --version)
      TARGET_VERSION="$2"
      shift 2
      ;;
    --force)
      FORCE=true
      shift
      ;;
    -h|--help)
      echo "Usage: bash install.sh [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --version X.Y.Z   Install a specific version (git tag vX.Y.Z)"
      echo "  --force            Reinstall even if same version"
      echo "  -h, --help         Show this help"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

# ── Version check ──────────────────────────
if [[ -n "$TARGET_VERSION" ]]; then
  echo "[*] Checking out version v${TARGET_VERSION}..."
  cd "$SCRIPT_DIR"
  git fetch --tags 2>/dev/null || true
  if ! git tag -l "v${TARGET_VERSION}" | grep -q "v${TARGET_VERSION}"; then
    echo "[ERROR] Tag v${TARGET_VERSION} not found."
    echo "  Available tags:"
    git tag -l 'v*' | sort -V | tail -10
    exit 1
  fi
  git checkout "v${TARGET_VERSION}" --quiet
  echo "  Checked out v${TARGET_VERSION}"
fi

REPO_VERSION=$(cat "$VERSION_FILE" | tr -d '[:space:]')

if [[ -f "$INSTALLED_VERSION_FILE" ]] && [[ "$FORCE" == "false" ]]; then
  INSTALLED_VERSION=$(cat "$INSTALLED_VERSION_FILE" | tr -d '[:space:]')
  if [[ "$INSTALLED_VERSION" == "$REPO_VERSION" ]]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "  Already installed: v${REPO_VERSION}"
    echo "  Use --force to reinstall."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 0
  fi
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  JARFIS Installer — v${REPO_VERSION}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Step 1: Backup ─────────────────────────
BACKUP_DIR="$CLAUDE_DIR/backups/jarfis-$(date +%Y%m%d_%H%M%S)"
BACKUP_NEEDED=false

# Check if any JARFIS files exist
if [[ -d "$CLAUDE_DIR/commands/jarfis" ]] || [[ -f "$CLAUDE_DIR/commands/jarfis.md" ]] || [[ -d "$CLAUDE_DIR/agents/jarfis" ]]; then
  BACKUP_NEEDED=true
fi

if [[ "$BACKUP_NEEDED" == "true" ]]; then
  echo "[1/6] Creating backup..."
  mkdir -p "$BACKUP_DIR"

  # Backup commands
  if [[ -f "$CLAUDE_DIR/commands/jarfis.md" ]]; then
    mkdir -p "$BACKUP_DIR/commands"
    cp "$CLAUDE_DIR/commands/jarfis.md" "$BACKUP_DIR/commands/"
  fi
  if [[ -d "$CLAUDE_DIR/commands/jarfis" ]]; then
    cp -r "$CLAUDE_DIR/commands/jarfis" "$BACKUP_DIR/commands/"
  fi

  # Backup agents
  if [[ -d "$CLAUDE_DIR/agents/jarfis" ]]; then
    mkdir -p "$BACKUP_DIR/agents"
    cp -r "$CLAUDE_DIR/agents/jarfis" "$BACKUP_DIR/agents/"
  fi

  # Backup hooks
  if [[ -f "$CLAUDE_DIR/hooks/jarfis-pre-compact.sh" ]]; then
    mkdir -p "$BACKUP_DIR/hooks"
    cp "$CLAUDE_DIR/hooks/jarfis-pre-compact.sh" "$BACKUP_DIR/hooks/"
  fi

  # Backup scripts
  if [[ -d "$CLAUDE_DIR/scripts" ]]; then
    mkdir -p "$BACKUP_DIR/scripts"
    for f in "$CLAUDE_DIR/scripts/"*.sh; do
      [[ -f "$f" ]] && cp "$f" "$BACKUP_DIR/scripts/"
    done
  fi

  # Backup statusline
  if [[ -f "$CLAUDE_DIR/statusline-command.sh" ]]; then
    cp "$CLAUDE_DIR/statusline-command.sh" "$BACKUP_DIR/"
  fi

  # Backup version info
  [[ -f "$INSTALLED_VERSION_FILE" ]] && cp "$INSTALLED_VERSION_FILE" "$BACKUP_DIR/"

  echo "  [OK] Backup → $BACKUP_DIR"
else
  echo "[1/6] No existing installation found, skipping backup."
fi

# ── Step 2: Extract Learned Rules ──────────
echo "[2/6] Extracting Learned Rules..."
LEARNED_RULES_DIR=$(mktemp -d)
learned_count=0

for agent_file in "$CLAUDE_DIR/agents/jarfis/"*.md; do
  [[ ! -f "$agent_file" ]] && continue
  filename=$(basename "$agent_file")

  # Extract "## Learned Rules" section to end of file
  if grep -q "^## Learned Rules" "$agent_file" 2>/dev/null; then
    # Get line number of "## Learned Rules"
    lr_line=$(grep -n "^## Learned Rules" "$agent_file" | head -1 | cut -d: -f1)
    # Extract from that line to end of file
    tail -n +"$lr_line" "$agent_file" > "$LEARNED_RULES_DIR/$filename"
    learned_count=$((learned_count + 1))
    echo "  [OK] Preserved: $filename"
  fi
done

if [[ $learned_count -eq 0 ]]; then
  echo "  (no Learned Rules found)"
fi

# ── Step 3: Install files ─────────────────
echo "[3/6] Installing files..."

# Create directories
mkdir -p "$CLAUDE_DIR/commands/jarfis/prompts"
mkdir -p "$CLAUDE_DIR/commands/jarfis/templates"
mkdir -p "$CLAUDE_DIR/agents/jarfis"
mkdir -p "$CLAUDE_DIR/hooks"
mkdir -p "$CLAUDE_DIR/scripts"

# Install commands/jarfis.md
cp "$SCRIPT_DIR/commands/jarfis.md" "$CLAUDE_DIR/commands/jarfis.md"
echo "  [OK] commands/jarfis.md"

# Install commands/jarfis/*.md
for f in "$SCRIPT_DIR/commands/jarfis/"*.md; do
  [[ ! -f "$f" ]] && continue
  filename=$(basename "$f")
  cp "$f" "$CLAUDE_DIR/commands/jarfis/$filename"
  echo "  [OK] commands/jarfis/$filename"
done

# Install commands/jarfis/prompts/
for f in "$SCRIPT_DIR/commands/jarfis/prompts/"*.md; do
  [[ ! -f "$f" ]] && continue
  filename=$(basename "$f")
  cp "$f" "$CLAUDE_DIR/commands/jarfis/prompts/$filename"
  echo "  [OK] commands/jarfis/prompts/$filename"
done

# Install commands/jarfis/templates/
for f in "$SCRIPT_DIR/commands/jarfis/templates/"*.md; do
  [[ ! -f "$f" ]] && continue
  filename=$(basename "$f")
  cp "$f" "$CLAUDE_DIR/commands/jarfis/templates/$filename"
  echo "  [OK] commands/jarfis/templates/$filename"
done

# Install agents
for f in "$SCRIPT_DIR/agents/jarfis/"*.md; do
  [[ ! -f "$f" ]] && continue
  filename=$(basename "$f")
  cp "$f" "$CLAUDE_DIR/agents/jarfis/$filename"
  echo "  [OK] agents/jarfis/$filename"
done

# Install hooks
if [[ -f "$SCRIPT_DIR/hooks/jarfis-pre-compact.sh" ]]; then
  cp "$SCRIPT_DIR/hooks/jarfis-pre-compact.sh" "$CLAUDE_DIR/hooks/"
  chmod +x "$CLAUDE_DIR/hooks/jarfis-pre-compact.sh"
  echo "  [OK] hooks/jarfis-pre-compact.sh"
fi

# Install scripts
for f in "$SCRIPT_DIR/scripts/"*.sh; do
  [[ ! -f "$f" ]] && continue
  filename=$(basename "$f")
  cp "$f" "$CLAUDE_DIR/scripts/$filename"
  chmod +x "$CLAUDE_DIR/scripts/$filename"
  echo "  [OK] scripts/$filename"
done

# Install statusline
if [[ -f "$SCRIPT_DIR/statusline-command.sh" ]]; then
  cp "$SCRIPT_DIR/statusline-command.sh" "$CLAUDE_DIR/statusline-command.sh"
  chmod +x "$CLAUDE_DIR/statusline-command.sh"
  echo "  [OK] statusline-command.sh"
fi

# ── Step 4: Re-apply Learned Rules ────────
echo "[4/6] Re-applying Learned Rules..."
reapplied=0

for lr_file in "$LEARNED_RULES_DIR/"*.md; do
  [[ ! -f "$lr_file" ]] && continue
  filename=$(basename "$lr_file")
  target="$CLAUDE_DIR/agents/jarfis/$filename"

  if [[ ! -f "$target" ]]; then
    echo "  [SKIP] $filename (target not found)"
    continue
  fi

  # Check if the newly installed file already has Learned Rules
  if grep -q "^## Learned Rules" "$target" 2>/dev/null; then
    # Replace the existing Learned Rules section
    lr_line=$(grep -n "^## Learned Rules" "$target" | head -1 | cut -d: -f1)
    # Keep everything before Learned Rules, append preserved rules
    head -n $((lr_line - 1)) "$target" > "${target}.tmp"
    cat "$lr_file" >> "${target}.tmp"
    mv "${target}.tmp" "$target"
  else
    # Append Learned Rules at the end
    echo "" >> "$target"
    cat "$lr_file" >> "$target"
  fi
  reapplied=$((reapplied + 1))
  echo "  [OK] Re-applied: $filename"
done

if [[ $reapplied -eq 0 ]]; then
  echo "  (nothing to re-apply)"
fi

# Cleanup temp
rm -rf "$LEARNED_RULES_DIR"

# ── Step 5: Register hooks in settings.json ─
echo "[5/6] Checking settings.json..."

SETTINGS_FILE="$CLAUDE_DIR/settings.json"

if command -v jq &>/dev/null && [[ -f "$SETTINGS_FILE" ]]; then
  changed=false

  # Check PreCompact hook
  has_precompact=$(jq -r '.hooks.PreCompact // empty' "$SETTINGS_FILE")
  if [[ -z "$has_precompact" ]]; then
    jq '.hooks.PreCompact = [{"matcher":"auto","hooks":[{"type":"command","command":"bash '"$CLAUDE_DIR"'/hooks/jarfis-pre-compact.sh","timeout":10000}]}]' \
      "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    echo "  [OK] Added PreCompact hook"
    changed=true
  else
    echo "  [OK] PreCompact hook already exists"
  fi

  # Check statusLine
  has_statusline=$(jq -r '.statusLine // empty' "$SETTINGS_FILE")
  if [[ -z "$has_statusline" ]]; then
    jq '.statusLine = {"type":"command","command":"bash '"$CLAUDE_DIR"'/statusline-command.sh"}' \
      "$SETTINGS_FILE" > "${SETTINGS_FILE}.tmp" && mv "${SETTINGS_FILE}.tmp" "$SETTINGS_FILE"
    echo "  [OK] Added statusLine"
    changed=true
  else
    echo "  [OK] statusLine already configured"
  fi

  if [[ "$changed" == "false" ]]; then
    echo "  (no changes needed)"
  fi
else
  if ! command -v jq &>/dev/null; then
    echo "  [WARN] jq not found — skipping settings.json hook registration"
    echo "         Install jq or manually add PreCompact hook and statusLine"
  fi
fi

# ── Step 6: Version stamps ────────────────
echo "[6/6] Writing version stamps..."

echo "$REPO_VERSION" > "$INSTALLED_VERSION_FILE"
echo "  [OK] $INSTALLED_VERSION_FILE → $REPO_VERSION"

echo "$SCRIPT_DIR" > "$SOURCE_FILE"
echo "  [OK] $SOURCE_FILE → $SCRIPT_DIR"

# ── Done ──────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  JARFIS v${REPO_VERSION} installed!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  /jarfis          — 명령어 도움말"
echo "  /jarfis:work     — 워크플로우 실행"
echo "  /jarfis:version  — 버전 확인/업데이트"
echo ""
if [[ "$BACKUP_NEEDED" == "true" ]]; then
  echo "  Backup: $BACKUP_DIR"
fi
if [[ $reapplied -gt 0 ]]; then
  echo "  Learned Rules: $reapplied agent(s) preserved"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
