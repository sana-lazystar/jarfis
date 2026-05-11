"""
JARFIS v4 — tmux Claude 실행 유틸리티

tmux에서 Claude를 격리 실행하고 완료를 감지한다. JARFIS 로직은 모른다.

사용법:
  python tmux_claude.py \
    --name jf-a1b2c3d4-phase3 \
    --prompt /path/to/prompt.md \
    --result /path/to/phase-results/phase3/attempt1.json \
    --workspace /path/to/docsDir \
    [--mcp-config /path/to/.mcp.json] \
    [--timeout 3600]

exit 0: result.json에 status=completed
exit 1: error, 타임아웃, 크래시 (stderr에 내용)
"""

import subprocess
import time
import os
import sys
import json
import argparse
import atexit

# Allow direct invocation (`python3 tmux_claude.py ...`): ensure the parent
# directory (scripts/) is on sys.path so the `jarfis` package is importable
# regardless of CWD. When called via `python3 -m jarfis.tmux_claude` or from
# jarfis_cli.py, sys.path is already correct and this insertion is a no-op.
_SCRIPTS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from jarfis import trace

POLL_INTERVAL = 3                       # 초
DEFAULT_TIMEOUT = 3600                  # 1시간 (안전장치)
TMUX_SIZE = (200, 50)

AGENT_NAME = "jarfis-foreman"


def create_session(name: str, workspace: str, mcp_config: str | None = None) -> None:
    """tmux 세션 생성. `-c workspace`로 working directory 지정.
    새 세션 내에서 바로 Claude 실행 (경쟁 조건 회피)."""
    cmd = [
        "tmux", "new-session", "-d",
        "-s", name,
        "-x", str(TMUX_SIZE[0]),
        "-y", str(TMUX_SIZE[1]),
        "-c", workspace,
        "--",
        "claude",
        "--agent", AGENT_NAME,
        "--dangerously-skip-permissions",
    ]
    if mcp_config:
        cmd.extend(["--mcp-config", mcp_config])
    subprocess.run(cmd, check=True)


def wait_for_ready(name: str, max_wait: int = 30) -> bool:
    """Claude Code가 입력 대기 상태가 될 때까지 대기.

    M1 Part 4 fix:
      1) ">" 단순 일치는 tmux 초기 출력에 너무 빠르게 매치되어 실패 — 대신
         Claude Code TUI 전체가 그려진 후에만 나타나는 `"bypass permissions"`
         마커를 요구.
      2) 새 워크스페이스 진입 시 `"Do you trust this folder?"` 다이얼로그가 뜸.
         `--dangerously-skip-permissions`도 이 dialog는 bypass 안 함.
         감지되면 Enter(첫 옵션=trust) 전송하여 통과.
      3) 준비 완료 후 2초 안정화 대기.
    """
    trust_accepted = False
    for _ in range(max_wait * 2):  # 0.5초 간격
        output = capture_pane(name, lines=30)

        # (2) 워크스페이스 신뢰 다이얼로그 처리 (최초 1회)
        if not trust_accepted and "trust this folder" in output.lower():
            subprocess.run(["tmux", "send-keys", "-t", name, "Enter"])
            trust_accepted = True
            time.sleep(1)
            continue

        # (1) 진짜 ready 마커
        if "bypass permissions" in output and "❯" in output:
            time.sleep(2)  # (3) TUI 렌더링 안정화
            return True
        time.sleep(0.5)
    return False


def send_prompt(name: str, prompt_path: str) -> None:
    """프롬프트 파일 경로를 Claude에게 전달."""
    instruction = f"Read and execute the instructions in {prompt_path}"
    subprocess.run(["tmux", "send-keys", "-t", name, "-l", instruction])
    subprocess.run(["tmux", "send-keys", "-t", name, "Enter"])


def read_result(path: str) -> dict | None:
    """result JSON 읽기."""
    try:
        with open(path) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def write_result(path: str, status: str, reason: str = "", detail: str = "") -> None:
    """result JSON 쓰기 (tmux_claude.py 폴백 전용)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(
            {"status": status, "reason": reason, "reasonDetail": detail},
            f, indent=2, ensure_ascii=False
        )


def poll(name: str, result_path: str, timeout: int) -> dict:
    """result JSON이 생성될 때까지 폴링. 크래시/타임아웃 시 폴백 작성."""
    start = time.time()
    while time.time() - start < timeout:
        result = read_result(result_path)
        if result:
            return result
        if not session_alive(name):
            # 크래시 — pane 캡처 후 폴백 작성
            output = capture_pane(name) if session_alive(name) else ""
            write_result(result_path, "error", "크래시: 세션 비정상 종료", output)
            return read_result(result_path)
        time.sleep(POLL_INTERVAL)

    # 타임아웃
    output = capture_pane(name) if session_alive(name) else ""
    write_result(result_path, "error", f"타임아웃: {timeout}초 초과", output)
    return read_result(result_path)


def session_alive(name: str) -> bool:
    """tmux 세션 존재 확인."""
    result = subprocess.run(
        ["tmux", "has-session", "-t", name],
        capture_output=True
    )
    return result.returncode == 0


def capture_pane(name: str, lines: int = 100) -> str:
    """tmux pane 내용 캡처."""
    result = subprocess.run(
        ["tmux", "capture-pane", "-t", name, "-p", "-J", "-S", f"-{lines}"],
        capture_output=True, text=True
    )
    return result.stdout


def kill_session(name: str) -> None:
    """tmux 세션 종료."""
    subprocess.run(["tmux", "kill-session", "-t", name], capture_output=True)


def save_pane(name: str, path: str) -> bool:
    """tmux pane 전체 스크롤백을 `path`에 저장 (post-mortem 디버깅용).

    실패는 phase 결과를 뒤집지 않는다 — M8 Attempt 3 디버깅에서 pane이
    세션 종료와 함께 소실되어 verify FAIL 원인 추적이 어려웠던 점(N-1) 대응.
    호출 시점은 kill_session 직전이어야 한다 (세션 소멸 후 capture 불가).

    Returns True on successful write, False on any failure (warning to stderr).
    """
    try:
        dirname = os.path.dirname(path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        result = subprocess.run(
            ["tmux", "capture-pane", "-t", name, "-p", "-J", "-S", "-"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            print(
                f"[tmux_claude] save-pane capture failed "
                f"(rc={result.returncode}): {result.stderr.strip()}",
                file=sys.stderr,
            )
            return False
        with open(path, "w", encoding="utf-8") as f:
            f.write(result.stdout)
        return True
    except OSError as e:
        print(f"[tmux_claude] save-pane write failed: {e}", file=sys.stderr)
        return False


def kill_existing_session(name: str) -> None:
    """동일 이름 세션이 있으면 kill (재실행 시 이전 인스턴스 정리).

    주의: prefix 기반 대량 kill 안 함. Phase 2+3 병렬 실행 안전성 보장.
    좀비 세션 청소는 별도 책임 (/jarfis:sys-health 또는 메인 재개 시).

    Prefix-match 관련 참고 (I-M8-P4-2):
        tmux의 has-session / kill-session은 `-t` 인자에 대해 접두사 매칭을
        허용한다 (예: `-t jf-abc`가 `jf-abc-phase4`와 매치 가능).
        단 JARFIS 세션 명명 규칙은 `jf-{shortId}-phase{N}` 고정이고
        shortId는 nanoid/uuid 기반이라 서로 prefix 관계가 될 수 없다.
        따라서 본 함수가 정확 이름 매칭만 수행해도 실질적 위험은 0이다.
        (shortId 생성 로직을 짧은 순차 ID 등으로 바꾸면 이 가정이 깨지므로
        변경 시 해당 시점에 본 함수도 함께 재검토할 것.)
    """
    if session_alive(name):
        kill_session(name)


def main():
    p = argparse.ArgumentParser(description="JARFIS v4 Phase Runner")
    p.add_argument("--name", required=True, help="tmux 세션 이름 (예: jf-a1b2c3d4-phase3)")
    p.add_argument("--prompt", required=True, help="프롬프트 파일 경로")
    p.add_argument("--result", required=True,
                   help="결과 JSON 경로 (예: phase-results/phase3/attempt1.json)")
    p.add_argument("--workspace", required=True, help="작업 디렉토리 (일반적으로 docsDir)")
    p.add_argument("--mcp-config", default=None, help="MCP 설정 파일 (선택, 글로벌 미상속 시)")
    p.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT,
                   help="안전장치 타임아웃 (기본 1시간)")
    p.add_argument("--save-pane", default=None,
                   help="(선택) tmux 세션 종료 직전 pane 전체 스크롤백을 "
                        "해당 경로에 저장. 캡처 실패해도 phase 결과엔 영향 없음. "
                        "권장 경로: {docsDir}/phase-results/phase{N}/attempt{K}.pane.log")
    args = p.parse_args()

    # 비정상 종료 시 세션 자동 정리
    atexit.register(lambda: kill_session(args.name))

    run_start = time.monotonic()
    try:
        if trace.is_enabled():
            trace.log_event(
                "tmux_session_start",
                {"session": args.name, "workspace": args.workspace,
                 "mcp_config": bool(args.mcp_config)},
            )
    except Exception:
        pass

    # 1. 동일 이름 세션 정리 (재실행/크래시 복구)
    kill_existing_session(args.name)

    # 2. 같은 attempt 재호출 시 partial 결과 정리
    if os.path.exists(args.result):
        os.remove(args.result)

    # 3. 세션 생성
    create_session(args.name, args.workspace, args.mcp_config)

    # 4. Claude 준비 대기
    if not wait_for_ready(args.name):
        if args.save_pane:
            save_pane(args.name, args.save_pane)
        kill_session(args.name)
        write_result(args.result, "error", "Claude 시작 실패", "")
        try:
            if trace.is_enabled():
                trace.log_event(
                    "tmux_session_end",
                    {"session": args.name, "status": "error",
                     "reason": "ready_timeout",
                     "duration_ms": int((time.monotonic() - run_start) * 1000)},
                )
        except Exception:
            pass
        print("Claude failed to start", file=sys.stderr)
        sys.exit(1)

    try:
        if trace.is_enabled():
            trace.log_event("tmux_session_ready", {"session": args.name})
    except Exception:
        pass

    # 5. 프롬프트 전송
    send_prompt(args.name, args.prompt)

    try:
        if trace.is_enabled():
            trace.log_event(
                "tmux_prompt_sent",
                {"session": args.name, "prompt_path": args.prompt},
            )
    except Exception:
        pass

    # 6. 결과 대기
    result = poll(args.name, args.result, args.timeout)
    if args.save_pane:
        save_pane(args.name, args.save_pane)
    kill_session(args.name)

    try:
        if trace.is_enabled():
            trace.log_event(
                "tmux_session_end",
                {"session": args.name, "status": result.get("status"),
                 "reason": result.get("reason", ""),
                 "duration_ms": int((time.monotonic() - run_start) * 1000)},
            )
    except Exception:
        pass

    # 7. 결과 반환
    if result["status"] == "completed":
        print(f"PHASE_COMPLETED: {args.name}")
        sys.exit(0)
    else:
        print(result["reason"], file=sys.stderr)
        if result.get("reasonDetail"):
            print(f"\n{result['reasonDetail']}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
