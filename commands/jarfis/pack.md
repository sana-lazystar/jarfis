# JARFIS Pack — 포터블 아카이브 생성

현재 설치된 JARFIS 관련 파일을 수집하여 다른 환경에 이식 가능한 아카이브를 생성합니다.

---

## 실행 흐름

아래 단계를 순서대로 실행하세요.

### Step 1: 파일 수집 및 패키징

다음 Bash 스크립트를 실행하세요:

```bash
#!/bin/bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d)
STAGE_DIR=$(mktemp -d)/jarfis-portable
OUTPUT_DIR="$HOME/Desktop"

# Read version from .jarfis-version or VERSION file
JARFIS_VERSION="unknown"
if [[ -f "$HOME/.claude/.jarfis-version" ]]; then
  JARFIS_VERSION=$(cat "$HOME/.claude/.jarfis-version" | tr -d '[:space:]')
elif [[ -f "$HOME/.claude/.jarfis-source" ]]; then
  SOURCE_DIR=$(cat "$HOME/.claude/.jarfis-source" | tr -d '[:space:]')
  [[ -f "$SOURCE_DIR/VERSION" ]] && JARFIS_VERSION=$(cat "$SOURCE_DIR/VERSION" | tr -d '[:space:]')
fi

ARCHIVE_NAME="jarfis-v${JARFIS_VERSION}-portable.tar.gz"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  JARFIS Pack"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# --- 1. 스테이징 디렉토리 구성 ---
mkdir -p "$STAGE_DIR/commands/jarfis"
mkdir -p "$STAGE_DIR/agents"
mkdir -p "$STAGE_DIR/scripts"
mkdir -p "$STAGE_DIR/docs"

# --- 1.5. VERSION 파일 복사 ---
if [[ -f "$HOME/.claude/.jarfis-source" ]]; then
  SOURCE_DIR=$(cat "$HOME/.claude/.jarfis-source" | tr -d '[:space:]')
  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
    cp "$SOURCE_DIR/VERSION" "$STAGE_DIR/VERSION"
    echo "  [OK] VERSION ($JARFIS_VERSION)"
  fi
fi

# --- 2. Commands 수집 (현재 설치된 파일) ---
echo "[1/5] Collecting commands..."
CLAUDE_DIR="$HOME/.claude"

cp "$CLAUDE_DIR/commands/jarfis.md" "$STAGE_DIR/commands/jarfis.md"
echo "  [OK] jarfis.md (helper)"

for f in "$CLAUDE_DIR/commands/jarfis/"*.md; do
  filename=$(basename "$f")
  cp "$f" "$STAGE_DIR/commands/jarfis/$filename"
  echo "  [OK] jarfis/$filename"
done

# Subdirectories (prompts/, templates/, etc.)
for subdir in "$CLAUDE_DIR/commands/jarfis/"*/; do
  [ ! -d "$subdir" ] && continue
  dirname=$(basename "$subdir")
  # Skip hidden/backup directories
  [[ "$dirname" == .* ]] && continue
  mkdir -p "$STAGE_DIR/commands/jarfis/$dirname"
  for f in "$subdir"*.md; do
    [ ! -f "$f" ] && continue
    filename=$(basename "$f")
    cp "$f" "$STAGE_DIR/commands/jarfis/$dirname/$filename"
    echo "  [OK] jarfis/$dirname/$filename"
  done
done

# --- 2.5. Scripts 수집 ---
echo "[1.5/5] Collecting scripts..."
script_count=0
for f in "$CLAUDE_DIR/scripts/"*.sh; do
  [ ! -f "$f" ] && continue
  filename=$(basename "$f")
  cp "$f" "$STAGE_DIR/scripts/$filename"
  echo "  [OK] $filename"
  script_count=$((script_count + 1))
done

# --- 3. Agents 수집 (jarfis 서브디렉토리 전체) ---
echo "[2/5] Collecting agents..."
agent_count=0
for f in "$CLAUDE_DIR/agents/jarfis/"*.md; do
  [ ! -f "$f" ] && continue
  filename=$(basename "$f")
  cp "$f" "$STAGE_DIR/agents/$filename"
  echo "  [OK] $filename"
  agent_count=$((agent_count + 1))
done

# --- 4. 스크립트 생성 ---
echo "[3/5] Generating install script..."

cat > "$STAGE_DIR/install.sh" << 'INSTALL_EOF'
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
BACKUP_SUFFIX=".backup.$(date +%s)"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  JARFIS Portable Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. Create directories
echo "[1/5] Creating directories..."
mkdir -p "$CLAUDE_DIR/commands/jarfis"
mkdir -p "$CLAUDE_DIR/agents/jarfis"
mkdir -p "$CLAUDE_DIR/scripts"

# 2. Install scripts
echo "[2/5] Installing scripts..."
for f in "$SCRIPT_DIR/scripts/"*.sh; do
  [ ! -f "$f" ] && continue
  filename=$(basename "$f")
  target="$CLAUDE_DIR/scripts/$filename"
  if [ -f "$target" ]; then
    cp "$target" "${target}${BACKUP_SUFFIX}"
    echo "  [BACKUP] $filename"
  fi
  cp "$f" "$target"
  chmod +x "$target"
  echo "  [OK] $filename"
done

# 3. Install agents (with backup)
echo "[3/5] Installing agents..."
for agent_file in "$SCRIPT_DIR/agents/"*.md; do
  filename=$(basename "$agent_file")
  target="$CLAUDE_DIR/agents/jarfis/$filename"
  if [ -f "$target" ]; then
    cp "$target" "${target}${BACKUP_SUFFIX}"
    echo "  [BACKUP] $filename"
  fi
  cp "$agent_file" "$target"
  echo "  [OK] $filename"
done

# 4. Install commands
echo "[4/5] Installing commands..."

# Helper command
target="$CLAUDE_DIR/commands/jarfis.md"
if [ -f "$target" ]; then
  cp "$target" "${target}${BACKUP_SUFFIX}"
fi
cp "$SCRIPT_DIR/commands/jarfis.md" "$target"
echo "  [OK] jarfis.md"

# Subcommands
for f in "$SCRIPT_DIR/commands/jarfis/"*.md; do
  filename=$(basename "$f")
  target="$CLAUDE_DIR/commands/jarfis/$filename"
  if [ -f "$target" ]; then
    cp "$target" "${target}${BACKUP_SUFFIX}"
  fi
  cp "$f" "$target"
  echo "  [OK] jarfis/$filename"
done

# Subdirectories (prompts/, templates/, etc.)
for subdir in "$SCRIPT_DIR/commands/jarfis/"*/; do
  [ ! -d "$subdir" ] && continue
  dirname=$(basename "$subdir")
  [[ "$dirname" == .* ]] && continue
  mkdir -p "$CLAUDE_DIR/commands/jarfis/$dirname"
  for f in "$subdir"*.md; do
    [ ! -f "$f" ] && continue
    filename=$(basename "$f")
    target="$CLAUDE_DIR/commands/jarfis/$dirname/$filename"
    if [ -f "$target" ]; then
      cp "$target" "${target}${BACKUP_SUFFIX}"
    fi
    cp "$f" "$target"
    echo "  [OK] jarfis/$dirname/$filename"
  done
done

# Migrate old files if they exist
if [ -f "$CLAUDE_DIR/commands/jarfis-learnings.md" ]; then
  echo "  [MIGRATE] Moving jarfis-learnings.md to ~/.claude/"
  mv "$CLAUDE_DIR/commands/jarfis-learnings.md" "$CLAUDE_DIR/jarfis-learnings.md"
fi

# 5. Verify
echo "[5/5] Verifying..."
errors=0
[ ! -f "$CLAUDE_DIR/commands/jarfis.md" ] && echo "  [FAIL] jarfis.md" && errors=$((errors + 1))
for f in "$SCRIPT_DIR/scripts/"*.sh; do
  [ ! -f "$f" ] && continue
  filename=$(basename "$f")
  [ ! -f "$CLAUDE_DIR/scripts/$filename" ] && echo "  [FAIL] scripts/$filename" && errors=$((errors + 1))
done
for f in "$SCRIPT_DIR/commands/jarfis/"*.md; do
  filename=$(basename "$f")
  [ ! -f "$CLAUDE_DIR/commands/jarfis/$filename" ] && echo "  [FAIL] jarfis/$filename" && errors=$((errors + 1))
done
for agent_file in "$SCRIPT_DIR/agents/"*.md; do
  filename=$(basename "$agent_file")
  [ ! -f "$CLAUDE_DIR/agents/jarfis/$filename" ] && echo "  [FAIL] $filename" && errors=$((errors + 1))
done

echo ""
if [ $errors -eq 0 ]; then
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  Installation complete!"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo ""
  echo "  /jarfis          — 명령어 도움말"
  echo "  /jarfis:work     — 워크플로우 실행"
  echo "  /jarfis:health   — 시스템 헬스체크"
  echo "  /jarfis:upgrade  — 학습 관리"
else
  echo "  Installation finished with $errors error(s)"
  exit 1
fi
INSTALL_EOF
chmod +x "$STAGE_DIR/install.sh"
echo "  [OK] install.sh"

# --- 5. 아카이브 생성 ---
echo "[4/5] Creating archive..."
PARENT_DIR=$(dirname "$STAGE_DIR")
cd "$PARENT_DIR"
tar -czf "$OUTPUT_DIR/$ARCHIVE_NAME" \
  --exclude='.DS_Store' \
  jarfis-portable/

echo "[5/5] Cleaning up..."
rm -rf "$PARENT_DIR"

# --- 결과 ---
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Pack complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Archive : $OUTPUT_DIR/$ARCHIVE_NAME"
echo "  Size    : $(du -h "$OUTPUT_DIR/$ARCHIVE_NAME" | awk '{print $1}')"
echo "  Commands: $(find "$STAGE_DIR" -name '*.md' -path '*/commands/*' 2>/dev/null | wc -l | tr -d ' ') files"
echo "  Scripts : $script_count files"
echo "  Agents  : $agent_count files"
echo ""
echo "  Transfer & install:"
echo "    tar -xzf $ARCHIVE_NAME"
echo "    cd jarfis-portable"
echo "    bash install.sh"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

### Step 2: 결과 보고

스크립트 실행 결과를 사용자에게 보여주세요.
아카이브 생성에 성공했으면 파일 경로와 크기를 안내합니다.
실패했으면 원인을 분석하여 알려줍니다.
