#!/usr/bin/env bash
# claude-cleanup.sh - Claude 좀비 프로세스 진단 및 정리
#
# Usage:
#   ./claude-cleanup.sh          진단만 (dry-run)
#   ./claude-cleanup.sh --kill   좀비 프로세스 종료
#
# 좀비 판정 기준 (우선순위순):
#   1. 부모 프로세스(Plugin Helper)가 죽은 고아 프로세스 → 확실한 좀비
#   2. 같은 프로젝트에 여러 프로세스 → 가장 최신(PID 최대)만 유지, 나머지 좀비
#   3. 프로젝트당 단독 프로세스 → 구버전이어도 활성으로 판단 (유지)
#
# 안전장치:
#   - 터미널에서 직접 실행된 세션(tty 있음) → 무조건 보호
#   - Task tool 서브에이전트는 별도 프로세스가 아님 (동일 프로세스 내 API 호출) → 안전
#   - MCP 서버(serena, context7 등)는 claude의 자식 프로세스 → kill 시 함께 정리

set -euo pipefail

MODE="${1:-}"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
DIM='\033[2m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}========================================"
echo " Claude 프로세스 진단기"
echo -e "========================================${NC}"
echo ""

# ── 1. 참고 정보: 설치된 확장 버전 ──
LATEST_INSTALLED=$(ls -dt ~/.vscode/extensions/anthropic.claude-code-*-darwin-arm64 2>/dev/null | head -1 | grep -o 'claude-code-[0-9.]*' | sed 's/claude-code-//' || echo "")
RUNNING_LATEST=$(ps -eo args 2>/dev/null | grep "native-binary/claude" | grep -v grep | grep -o 'claude-code-[0-9.]*' | sed 's/claude-code-//' | sort -V | tail -1 || echo "")

echo -e "${CYAN}설치된 최신 확장:${NC} ${LATEST_INSTALLED:-없음}"
echo -e "${CYAN}실행 중 최신 버전:${NC} ${RUNNING_LATEST:-없음}"
if [ -n "$LATEST_INSTALLED" ] && [ -n "$RUNNING_LATEST" ] && [ "$LATEST_INSTALLED" != "$RUNNING_LATEST" ]; then
    echo -e "${YELLOW}[!] 확장이 업데이트되었지만 VSCode를 Reload하지 않아 이전 버전이 실행 중${NC}"
    echo -e "${DIM}    Cmd+Shift+P → 'Developer: Reload Window' 권장${NC}"
fi
echo ""

# ── 2. 터미널에서 직접 실행된 Claude 수집 (보호 대상) ──
TERMINAL_PIDS=""
while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $1}')
    tty=$(echo "$line" | awk '{print $2}')
    if [ "$tty" != "??" ]; then
        TERMINAL_PIDS="$TERMINAL_PIDS $pid"
    fi
done < <(ps -eo pid,tty,args 2>/dev/null | grep "[n]ative-binary/claude\| claude$" | grep -v "grep\|claude-cleanup" || true)

# ── 3. 임시 작업 디렉토리 ──
TMPDIR_WORK=$(mktemp -d)
trap "rm -rf $TMPDIR_WORK" EXIT

ZOMBIE_FILE="$TMPDIR_WORK/zombies"
KEEP_FILE="$TMPDIR_WORK/keeps"
WARN_FILE="$TMPDIR_WORK/warns"
INFO_DIR="$TMPDIR_WORK/info"
PROJECT_DIR="$TMPDIR_WORK/projects"
mkdir -p "$INFO_DIR" "$PROJECT_DIR"
touch "$ZOMBIE_FILE" "$KEEP_FILE" "$WARN_FILE"

# ── 4. VSCode Claude 프로세스 수집 ──
while IFS= read -r line; do
    pid=$(echo "$line" | awk '{print $1}')

    # 터미널 세션은 제외
    if echo " $TERMINAL_PIDS " | grep -q " $pid "; then
        continue
    fi

    # 버전
    ver=$(echo "$line" | grep -o 'claude-code-[0-9.]*' | sed 's/claude-code-//' || echo "unknown")

    # 시작 시간
    start=$(ps -o lstart= -p "$pid" 2>/dev/null | xargs)

    # 부모 프로세스 확인
    ppid=$(ps -o ppid= -p "$pid" 2>/dev/null | tr -d ' ')
    parent_alive=$(ps -p "$ppid" -o comm= 2>/dev/null || echo "")

    # 프로젝트 경로 추출 (lsof에서 열린 파일 기반)
    project=$(lsof -p "$pid" 2>/dev/null | awk '{print $NF}' \
        | grep "^/Users" \
        | grep -v "Library\|\.vscode/extensions\|\.claude" \
        | head -1 || echo "unknown")

    # ── 판정 ──
    status="candidate"

    # 기준 1: 부모 프로세스 죽음 → 확실한 좀비
    if [ -z "$parent_alive" ]; then
        status="orphan_zombie"
        echo "$pid" >> "$ZOMBIE_FILE"
    fi

    # 정보 저장
    echo "$ver|$start|$project|$status" > "$INFO_DIR/$pid"

    # candidate는 프로젝트별 그룹에 추가 (기준 2에서 처리)
    if [ "$status" = "candidate" ]; then
        safe_project=$(echo "$project" | tr '/' '_')
        echo "$pid" >> "$PROJECT_DIR/$safe_project"
    fi

done < <(ps -eo pid,args 2>/dev/null | grep "native-binary/claude" | grep -v grep || true)

# ── 5. 프로젝트별 중복 판별 ──
for pfile in "$PROJECT_DIR"/*; do
    [ -f "$pfile" ] || continue
    pids=($(sort -n "$pfile"))

    if [ ${#pids[@]} -le 1 ]; then
        # 단독 프로세스 → 유지 (구버전이어도)
        p="${pids[0]}"
        echo "$p" >> "$KEEP_FILE"

        # 구버전 경고만 표시
        info=$(cat "$INFO_DIR/$p")
        ver=$(echo "$info" | cut -d'|' -f1)
        if [ -n "$RUNNING_LATEST" ] && [ "$ver" != "$RUNNING_LATEST" ]; then
            echo "$p" >> "$WARN_FILE"
        fi
        continue
    fi

    # 여러 개 → 가장 최신(PID 최대)만 유지
    newest="${pids[${#pids[@]}-1]}"
    echo "$newest" >> "$KEEP_FILE"

    for p in "${pids[@]}"; do
        if [ "$p" != "$newest" ]; then
            echo "$p" >> "$ZOMBIE_FILE"
            info=$(cat "$INFO_DIR/$p")
            echo "${info%|*}|duplicate_zombie" > "$INFO_DIR/$p"
        fi
    done
done

# ── 6. 결과 출력 ──
echo -e "${GREEN}${BOLD}=== 활성 프로세스 (유지) ===${NC}"
echo ""

# 터미널 세션
for pid in $TERMINAL_PIDS; do
    [ -z "$pid" ] && continue
    echo -e "  ${GREEN}PID $pid${NC} - 터미널 세션 (직접 실행) ${DIM}← 현재 세션${NC}"
done

# 유지할 VSCode 세션
while IFS= read -r pid; do
    [ -z "$pid" ] && continue
    [ -f "$INFO_DIR/$pid" ] || continue
    info=$(cat "$INFO_DIR/$pid")
    ver=$(echo "$info" | cut -d'|' -f1)
    start=$(echo "$info" | cut -d'|' -f2)
    project=$(echo "$info" | cut -d'|' -f3)
    project_name=$(basename "$project" 2>/dev/null || echo "$project")

    warn=""
    if grep -qw "$pid" "$WARN_FILE" 2>/dev/null; then
        warn=" ${YELLOW}(구버전 v$ver - Reload 후 갱신됨)${NC}"
    fi

    echo -e "  ${GREEN}PID $pid${NC} - v$ver - ${BOLD}$project_name${NC}${warn} ${DIM}($start)${NC}"
done < "$KEEP_FILE"

echo ""
echo -e "${RED}${BOLD}=== 좀비 프로세스 (정리 대상) ===${NC}"
echo ""

zombie_count=0
total_rss=0

# 중복 제거 후 출력
sort -u "$ZOMBIE_FILE" > "$ZOMBIE_FILE.uniq"
mv "$ZOMBIE_FILE.uniq" "$ZOMBIE_FILE"

while IFS= read -r pid; do
    [ -z "$pid" ] && continue
    [ -f "$INFO_DIR/$pid" ] || continue
    info=$(cat "$INFO_DIR/$pid")
    ver=$(echo "$info" | cut -d'|' -f1)
    start=$(echo "$info" | cut -d'|' -f2)
    project=$(echo "$info" | cut -d'|' -f3)
    status=$(echo "$info" | cut -d'|' -f4)
    project_name=$(basename "$project" 2>/dev/null || echo "$project")
    rss=$(ps -o rss= -p "$pid" 2>/dev/null | tr -d ' ' || echo "0")
    rss_mb=$((rss / 1024))
    total_rss=$((total_rss + rss))
    zombie_count=$((zombie_count + 1))

    reason=""
    case "$status" in
        orphan_zombie)    reason="부모 프로세스 죽음" ;;
        duplicate_zombie) reason="같은 프로젝트 중복 (최신 아님)" ;;
        *)                reason="$status" ;;
    esac

    # MCP 서버 자식 프로세스 수 확인
    mcp_children=$(ps -eo pid,ppid 2>/dev/null | awk -v pp="$pid" '$2==pp' | wc -l | tr -d ' ')
    mcp_rss=$(ps -eo ppid,rss 2>/dev/null | awk -v pp="$pid" '$1==pp {sum+=$2} END {print sum+0}')
    mcp_rss_mb=$((mcp_rss / 1024))
    total_rss=$((total_rss + mcp_rss))

    mcp_info=""
    if [ "$mcp_children" -gt 0 ]; then
        mcp_info=" + MCP ${mcp_children}개(${mcp_rss_mb}MB)"
    fi

    echo -e "  ${RED}PID $pid${NC} - v$ver - $project_name - ${YELLOW}${reason}${NC} - ${rss_mb}MB${mcp_info}"
done < "$ZOMBIE_FILE"

if [ "$zombie_count" -eq 0 ]; then
    echo -e "  ${GREEN}좀비 프로세스가 없습니다!${NC}"
else
    total_mb=$((total_rss / 1024))
    echo ""
    echo -e "  좀비 Claude ${RED}${BOLD}${zombie_count}개${NC} + MCP 서버 자식 포함, 회수 가능 메모리 ${RED}${BOLD}~${total_mb}MB${NC}"
fi

# ── 7. 정리 실행 ──
echo ""
if [ "$MODE" = "--kill" ] && [ "$zombie_count" -gt 0 ]; then
    echo -e "${YELLOW}좀비 프로세스를 종료합니다...${NC}"
    echo -e "${DIM}  (각 Claude의 MCP 서버 자식 프로세스도 함께 정리)${NC}"
    echo ""
    killed=0
    while IFS= read -r pid; do
        [ -z "$pid" ] && continue

        # 1) 자식 프로세스(MCP 서버) 먼저 종료
        child_pids=$(ps -eo pid,ppid 2>/dev/null | awk -v pp="$pid" '$2==pp {print $1}')
        child_count=0
        for cpid in $child_pids; do
            kill "$cpid" 2>/dev/null && child_count=$((child_count + 1))
        done

        # 2) Claude 프로세스 종료
        if kill "$pid" 2>/dev/null; then
            echo -e "  ${GREEN}PID $pid 종료됨${NC} (MCP 자식 ${child_count}개 함께 정리)"
            killed=$((killed + 1))
        else
            echo -e "  ${RED}PID $pid 종료 실패${NC}"
        fi

        # 3) 잠시 대기 후 남은 자식 강제 종료 (SIGKILL)
        sleep 0.2
        for cpid in $child_pids; do
            if ps -p "$cpid" > /dev/null 2>&1; then
                kill -9 "$cpid" 2>/dev/null
            fi
        done
    done < "$ZOMBIE_FILE"
    echo ""
    echo -e "${GREEN}${BOLD}${killed}개 프로세스 그룹 정리 완료. ~${total_mb}MB 메모리 회수.${NC}"
elif [ "$zombie_count" -gt 0 ]; then
    echo -e "${DIM}실제로 정리하려면:${NC}"
    echo -e "  ${CYAN}${BOLD}./claude-cleanup.sh --kill${NC}"
fi

echo ""
