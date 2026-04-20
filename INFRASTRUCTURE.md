# JARFIS Infrastructure

> **Last aligned**: v4.0.5 · 2026-04-20
> **Audience**: 기여자 · 외부 평가자 · 미래의 자신
>
> **상위 설계**: [PHILOSOPHY.md](./PHILOSOPHY.md) #1 Deterministic Foundation + #4 Resilient Continuity
> **ADR**: [DESIGN.md](./DESIGN.md) ADR-10 (Resilient), ADR-15 (verify.py), ADR-16 (tmux), ADR-18 (single-writer), ADR-20 (trace)

---

## 1. 디렉토리 구조

### 1.1 JARFIS 설치 위치 (`~/.claude/`)

```
~/.claude/
├── agents/jarfis/
│   ├── jarfis-foreman.md            # tmux phase executor (4,550 B, opus)
│   ├── jarfis-engineer.md           # v4 migration domain expert (6,711 B, opus)
│   ├── jarfis-advocate.md           # Dialectic advocate (2,900 B, opus)
│   ├── jarfis-critic.md             # Dialectic critic (3,130 B, opus)
│   └── personas/                    # 9 persona 파일 (1.5~3.0 KB each)
│       ├── product-owner.md · technical-architect.md
│       ├── frontend-developer.md · backend-developer.md · devops-engineer.md
│       ├── qa-engineer.md · security-engineer.md
│       ├── tech-lead.md · ux-designer.md
│
├── commands/jarfis/
│   ├── work.md                       # /jarfis:work orchestrator (255 lines)
│   ├── work-legacy.md                # v3 orchestrator (DEPRECATED, 2026-05-03 만료)
│   ├── sys-implement.md · sys-upgrade.md · sys-distill.md  # self-modification (Dialectic 적용)
│   ├── sys-health.md · sys-version.md                       # operational utilities
│   ├── level-check.md · locale.md · locale-set.md · search.md · search-index.md · search-setup.md
│   ├── org.md · org-init.md · project-init.md · project-update.md
│   ├── work-meeting.md · wiki-storyboard.md · jarfis-index.md
│   ├── agent-composition.yaml        # 합성 규칙 SSOT (ADR-17)
│   ├── prompts/                      # Phase 프롬프트 (8개)
│   │   └── phase{1b, 2, 3, 4, 4-5, 5, 6}.md · wiki-loading.md
│   ├── templates/                    # 산출물 템플릿 (10개)
│   │   └── jarfis-state-schema.md · learnings.md · project-profile.md · ...
│   ├── skills/                       # 16 skill 파일 (21~33 lines each)
│   │   └── react.md · vue.md · nodejs.md · rust.md · tauri-*.md · aws-lambda.md · ...
│   └── domains/                      # 도메인 팩
│       ├── web/ (_schema.yaml + web.yaml + skills 재사용)
│       └── desktop/ (_schema.yaml + desktop.yaml + external_skills: [web/react])
│
├── scripts/jarfis/                   # Python 구현 (총 ~2,840 lines)
│   ├── verify.py                     # 1,349 lines — gate-check/phase-check/phase-verify/pattern-detect (ADR-15)
│   ├── tmux_claude.py                # 250 lines — tmux lifecycle (ADR-16)
│   ├── state.py                      # 372 lines — .jarfis-state.json CRUD (single-writer, ADR-18)
│   ├── audit.py                      # 80 lines — audit.jsonl append-only
│   ├── trace.py                      # 158 lines — JARFIS_TRACE opt-in (ADR-20)
│   ├── domain.py                     # 883 lines — legacy compose + detection
│   ├── compose/                      # 독립 CLI 패키지 (9 모듈)
│   │   ├── __main__.py · assembler.py · config.py · models.py · reader.py
│   │   ├── resolver.py · skills.py · validate.py · errors.py
│   ├── detect.py · organization.py · preflight.py · quality_gate.py
│   ├── sync.py · measure.py · meetings.py · version.py · validate.py
│   ├── utils.py · verify_helpers.py
│   ├── wiki_search.py                # semantic search (31,115 B)
│   └── level_check.py                # 개발자 성숙도 평가
│
├── hooks/                            # 4 shell hooks (Resilient Continuity, ADR-10)
│   ├── jarfis-session-start.sh       # 세션 시작 — 미완료 워크플로우 감지 (4,683 B)
│   ├── jarfis-pre-compact.sh         # auto-compact 직전 — state 백업 (2,690 B)
│   ├── jarfis-safety.sh              # PreToolUse — 위험 명령 차단 (3,563 B)
│   └── jarfis-quality-gate.sh        # PostToolUse — lint/typecheck (2,340 B)
│
├── .jarfis-locale                    # 글로벌 locale 파일 (M12)
├── .jarfis-source                    # repo source path (symlink 해소용)
└── .jarfis-personal-dir              # 개인 workspace 경로 (optional override)
```

### 1.2 Work별 디렉토리 (`{docsDir}`)

```
{docsDir}/                            # Phase 0에서 결정, state.work.docsDir 절대 경로
├── .jarfis-state.json                # 중앙 state — Main 전용 쓰기 (ADR-18)
├── .wiki-cache.md                    # Phase 0 wiki 4-step 결과 (Org 등록 시)
│
├── phase-results/                    # tmux sub-agent 결과 — Sub 전용 쓰기 (ADR-18)
│   ├── phase1b/attempt{K}.json       # {status, reason, reasonDetail}
│   ├── phase2/attempt{K}.json · attempt{K}.pane.log
│   ├── phase3/...  phase4/... phase4-5/... phase5/... phase6/...
│
├── phase{id}-prompt-attempt{K}.md    # Main이 tmux 실행 직전 작성
│
├── discovery/                        # Phase 1b 산출물
│   ├── prd.md · working-backwards.md · ux-direction.md · po-qa.json
│
├── planning/                         # Phase 2 산출물
│   ├── architecture.md · tasks.md · test-strategy.md · api-spec.md
│
├── design/                           # Phase 3 산출물
│   ├── token-map.json
│   └── {page}/index.html · reference*.png
│
├── ops/                              # Phase 4 (devops 포함) + Phase 4.5
│   ├── infra-runbook.md · deployment-plan.md
│
├── review/                           # Phase 5 산출물
│   ├── review.md · api-contract-check.md · diagnosis-*.md
│
├── retrospective.md                  # Phase 6 회고
└── .compact-backups/                 # pre-compact hook이 state backup 저장 (최근 10개)
```

### 1.3 Org 레벨 (`{org_root}`)

```
{org_root}/                           # state.org.root
├── .jarfis-org/
│   ├── org-profile.md                # 조직 정보
│   └── wiki/
│       ├── INDEX.md                  # 전체 wiki 목차
│       ├── PO/_index.md · QA/_index.md · TA/_index.md · DESIGN/_index.md
│       └── {section}/{file}.md       # 축적된 지식
│
└── works/{work_name}/                # 이 경로가 각 work의 docsDir
    └── ... (§1.2 참조)
```

### 1.4 Project 레벨 (각 `scope[i].path`)

```
{project_path}/
└── .jarfis-project/                  # per-project 학습 자산
    ├── project-profile.md            # Tech Stack / Architecture / Conventions / ... (composition.yaml 핵심 소스)
    ├── project-rule.md               # 프로젝트 강제 규칙 (optional)
    └── project-context.md            # 작업 이력 / 경험 (optional)
```

---

## 2. Hooks (4개)

Claude Code의 hooks 메커니즘 활용. `settings.json` 에서 trigger → hook 매핑. ADR-10 "Resilient Continuity" 핵심 구현체.

### 2.1 `jarfis-session-start.sh` — SessionStart trigger

| 속성 | 값 |
|------|-----|
| 파일 크기 | 4,683 bytes |
| Trigger | Claude Code 세션 시작 |
| 역할 | 미완료 워크플로우 감지 → stdout으로 컨텍스트 주입 |
| Kill switch | `JARFIS_SESSION_RESTORE=0` |

**동작**:
1. ASCII art banner 출력 (stderr — 토큰 0)
2. `$ORGS_DIR` (기본 `~/repos/jarfis/.personal/orgs`) 스캔
3. `jarfis_cli.py state list-workflows` 호출 → JSON 파싱
4. `is_completed == false` 워크플로우 필터링
5. stdout 출력 형식:
   ```
   ## JARFIS: In-Progress Workflows Detected
   - **{work_name}** — Phase {N} ({project_name})
     Last checkpoint: {summary}
     Key decisions: {decision_1} | {decision_2} | ...
   To continue: /jarfis:work
   ```
6. Wiki 업데이트 alert 추가 (v2): Org 등록된 CWD에서 `status != "completed"` 워크플로우가 있으면 안내

stdout 출력은 Claude 컨텍스트에 **자동 주입** 됨. 사용자가 세션 재시작 후 즉시 상황 파악 가능.

### 2.2 `jarfis-pre-compact.sh` — PreCompact trigger

| 속성 | 값 |
|------|-----|
| 파일 크기 | 2,690 bytes |
| Trigger | auto-compact (automatic / manual) 직전 |
| 역할 | state + meeting 백업 |

**동작**:
1. stdin JSON 파싱 → `trigger` / `cwd` / `session_id` / timestamp
2. `$ORGS_DIR` 스캔하여 `works/*/.jarfis-state.json` 찾기 (최대 4 depth)
3. 백업 저장: `{docsDir}/.compact-backups/state_{timestamp}.json`
4. 최신 **10개** 유지, 초과분 삭제
5. 메타 기록: `.compact-backups/last_compact.json`
6. Meeting 노트 백업 (summary/decisions/tech-research/meeting-notes): 최신 **20개** 유지

**중요**: 백업은 **append-only로 누적되지 않음** — cap된 rotation. 디스크 누수 없음.

### 2.3 `jarfis-safety.sh` — PreToolUse trigger

| 속성 | 값 |
|------|-----|
| 파일 크기 | 3,563 bytes |
| Trigger | Bash 툴 호출 직전 |
| 역할 | 위험 명령 차단 (exit 2) + 경고 (exit 0) |
| Kill switch | `JARFIS_SAFETY_HOOK=0` |

**BLOCK 패턴 (exit 2 — 명령 실행 차단)**:

| 패턴 | 이유 |
|------|------|
| `git push --force` / `-f` | 히스토리 파괴 |
| `git ... --no-verify` | hook 우회 |
| `git commit` on main/master (directly) | 보호 브랜치 직접 커밋 |

**WARN 패턴 (stderr, exit 0 — 경고만)**:

| 패턴 | 이유 |
|------|------|
| `.env` 파일 접근 | 비밀 노출 위험 |
| `rm -rf` | 복구 불가 삭제 |
| credential/secret 파일 (`id_rsa`, `*.pem`, `*.key`, `*.p12`) | 비밀 노출 |
| `curl ... \| sh` / `wget ... \| sh` | 출처 미확인 실행 |

**`git commit` 분기 구현**: 명령어 파싱으로 타겟 디렉토리 추출 (`git -C <path>` 또는 `cd <path> &&` 또는 현재 CWD) → `git branch --show-current` → main/master 일치 시 차단.

### 2.4 `jarfis-quality-gate.sh` — PostToolUse trigger

| 속성 | 값 |
|------|-----|
| 파일 크기 | 2,340 bytes |
| Trigger | Edit / Write / MultiEdit 직후 |
| 역할 | lint / typecheck 경고 (**차단 안 함**, PostToolUse는 항상 exit 0) |
| Kill switch | `JARFIS_QUALITY_GATE=0` |

**동작**:
1. stdin JSON에서 `tool_name` 확인 (Edit/Write/MultiEdit만 처리)
2. `tool_input.file_path` 추출
3. `jarfis_cli.py quality-gate {FILE_PATH}` 호출 → JSON 결과
4. 상태별 처리:
   - `"skipped"` — stdout에 "[quality-gate] skipped"
   - `"warn"` — stderr에 FAIL 라인 + 경고 메시지
   - `"ok"` — stdout에 "[quality-gate] OK"

**차단 없음** — PostToolUse는 반드시 exit 0. 이는 Claude Code 정책 + JARFIS가 개발 흐름을 끊지 않기 위한 설계 결정.

### 2.5 Hooks Trade-off

| 장점 | 비용 |
|------|------|
| 자동 복구 + 안전망 | 세션 시작 latency (수십 ms) |
| 비밀 노출 사고 방지 | Kill switch 로 비활성 시 안전망 전체 상실 |
| Lint 경고 조기 발견 | jarfis_cli.py 없는 환경(비설치 / 경로 문제)에선 silently skip |

모든 hook은 **best-effort** — 실패해도 워크플로우 자체를 망가뜨리지 않는다 (ADR-10 정책 F-02 계승).

---

## 3. tmux Phase Orchestration (ADR-16)

### 3.1 세션 네이밍

```
{sessionKey}-phase{N}
```

- `sessionKey` = `jf-` + uuid4 앞 8자 (Phase 0에서 발급)
- `N` = phase id (예: `1b`, `2`, `3`, `4`, `4-5`, `5`, `6`) — Phase 4.5는 `4-5` (하이픈)

예시: `jf-a1b2c3d4-phase3`, `jf-a1b2c3d4-phase4-5`

### 3.2 B1 Isolation (tmux_claude.py)

```python
def kill_existing_session(name: str) -> None:
    """동일 이름 세션이 있으면 kill. (재실행 시 이전 인스턴스 정리)
    
    주의: prefix 기반 대량 kill 하지 않는다. Phase 2+3 병렬 실행 시
    서로 죽이는 버그 방지. 좀비 세션 청소는 별도 책임.
    """
    if session_alive(name):   # exact name match only
        kill_session(name)
```

**중요**: Phase 2 ∥ 3 병렬 실행 시 두 tmux 세션이 공존해야 한다. prefix match로 kill하면 서로 죽이는 버그. exact match가 B1 isolation의 핵심.

### 3.3 실행 명령

메인 세션이 백그라운드로 호출:

```bash
python3 ~/.claude/scripts/jarfis/tmux_claude.py \
  --name {sessionKey}-phase{phase_id} \
  --prompt {docsDir}/phase{phase_id}-prompt-attempt{K}.md \
  --result {docsDir}/phase-results/phase{phase_id}/attempt{K}.json \
  --workspace {docsDir} \
  --save-pane {docsDir}/phase-results/phase{phase_id}/attempt{K}.pane.log
```

**추가 옵션**:
- `--mcp-config ~/.claude/.mcp.json` — M6 MCP 상속 폴백 (필요 시)
- `--save-pane` (v4.0.4 N-1) — tmux scrollback 저장 (post-mortem 용)
- `--timeout` (기본 3600s) — 안전장치

### 3.4 Claude 준비 감지

tmux_claude.py가 `wait_for_ready()` 로 Claude CLI 기동 확인:
- pane 출력에서 `>` 또는 `"claude"` 문자열 감지
- 최대 30s 대기 (기본)
- 감지 실패 시 세션 kill + result에 error 작성

### 3.5 완료 감지 (Polling)

```python
POLL_INTERVAL = 3   # 초

def poll(name, result_path, timeout):
    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(result_path):
            return read_result(result_path)
        if not session_alive(name):
            # 크래시 — tmux_claude가 대신 result 작성
            output = capture_pane(name) if session_alive(name) else ""
            write_result(result_path, "error", "크래시: 세션 비정상 종료", output)
            return ...
        time.sleep(POLL_INTERVAL)
    # 타임아웃
```

Sub-agent가 직접 `{result_path}` 에 `{"status","reason","reasonDetail"}` JSON 작성. 크래시/타임아웃 시 tmux_claude.py가 pane 캡처하여 대신 작성.

### 3.6 Post-mortem 지원 — `--save-pane` (v4.0.4)

tmux 세션이 종료되기 직전에 전체 scrollback을 지정 경로에 캡처:

```
{docsDir}/phase-results/phase{N}/attempt{K}.pane.log
```

- 매 attempt마다 독립 로그 (디버깅용)
- Best-effort: 캡처 실패는 경고만, Phase 결과에 영향 없음
- attempt{K}.json 과 1:1 페어링

---

## 4. Single-writer State Rule (ADR-18, findings F-06)

### 4.1 규칙 전체

| 파일 | Writer | Reader |
|------|--------|--------|
| `.jarfis-state.json` | **Main session only** | Main + tmux (read-only) |
| `phase-results/phase{N}/attempt{K}.json` | **tmux sub-agent only** (또는 tmux_claude.py의 lifecycle 폴백) | Main |
| Phase 출력 디렉토리 (`discovery/`, `planning/`, `design/`, `review/`, `ops/`, `retrospective.md`) | **해당 Phase 실행 주체만** (direct=Main, tmux=Sub) | 모두 |

### 4.2 물리적 경합 불가능

- Main은 자기 파일만 씀 — state.json
- Sub는 자기 파일만 씀 — phase-results / Phase 출력 디렉토리
- **동일 파일에 두 writer가 존재하지 않음** → race condition 원천 차단

Lock 필요 없음. 디버깅은 파일 경로만 보면 writer 즉시 식별.

### 4.3 통신 방향

```
tmux sub (writes phase-results attempt{K}.json)
    → main (reads phase-results)
    → main (writes state.json, reflecting selected fields — ex: tddEnabled, review_rounds)
```

Main이 sub-agent 결과에서 **분기 결정에 필요한 필드만 선별** 하여 state에 반영. phase-results는 원본 그대로 보존 (디버깅 + audit).

### 4.4 구현 위치

- 원 설계: `~/Upscales/jarfis-v4-migration/architecture.md §1 설계 원칙` "쓰기 주체 분리" bullet
- 정식 선언: `~/.claude/commands/jarfis/work.md:22` — "State write rule (architecture §1 principle #6)"

---

## 5. JARFIS_TRACE Opt-in Observability (ADR-20)

### 5.1 기본 정책 — off

```python
def is_enabled() -> bool:
    return os.getenv("JARFIS_TRACE", "0") != "0"
```

**디폴트**: 꺼져있음. 런타임 비용 ~0.008% (실측, `os.getenv` 호출 1회).

### 5.2 활성화

```bash
export JARFIS_TRACE=1
# 선택: 경로 지정 (기본 /tmp/jarfis-trace.jsonl)
export JARFIS_TRACE_PATH=~/work-debug/trace.jsonl
```

### 5.3 Instrumentation 지점 (3 hot paths)

| 지점 | 함수 | 이벤트 쌍 |
|------|------|-----------|
| `tmux_claude.py` | 세션 lifecycle | `tmux_session_start` → `tmux_session_ready` → `tmux_prompt_sent` → `tmux_session_end` |
| `verify.py::cmd_phase_verify` | Phase 검증 | `phase_verify_start` → `phase_verify_end` |
| `compose/__main__::_compose` | Agent 합성 | `compose_start` → `compose_end` |

### 5.4 이벤트 스키마 (JSONL, 한 줄당)

```json
{"ts":"2026-04-20T12:34:56Z","event":"compose_end","attrs":{"agent":"frontend-developer","scope_index":0,"context_files":5,"injected_files":3,"skills_count":2,"prompt_chars":8432,"duration_ms":124}}
```

### 5.5 API

```python
# Simple event
trace.log_event("compose_start", {"agent": "frontend-developer", "scope_index": 0})

# Span context manager
with trace.trace_agent(path, trace_id, phase=4, persona="frontend-developer", skills=["react"]) as span_id:
    ...  # agent 실행
# exit 시 span JSON 자동 기록

# Phase completion
trace.trace_phase(path, trace_id, phase=4, duration_ms=12345)
```

### 5.6 Safety 및 Overhead

- **모든 I/O 및 JSON serialize** 은 `try/except Exception: pass` 로 감싸짐 — trace 실패가 Phase 결과를 뒤집지 않음
- **Overhead (실측, v4.0.5 preflight Phase 6 baseline 기준)**:
  - `JARFIS_TRACE` unset: ~0.008% (거의 측정 불가)
  - `JARFIS_TRACE=1`: < 20% wall time (postflight에서 enforce)

### 5.7 비활성화

```bash
export JARFIS_TRACE=0
# 또는
unset JARFIS_TRACE
```

코드 변경/재배포 불필요. Kill switch가 os.getenv 호출 1회로 즉시 반영.

### 5.8 Trace 파일 수명

append-only JSONL. **자동 cleanup 없음** — 수동 rotation/prune 필요. v4.0.6+ audit command에서 stale trace file surface 기능 후보.

---

## 6. verify.py — Deterministic Gate (ADR-15)

### 6.1 4개 서브커맨드 (실 파일 위치)

| 커맨드 | 함수 | 호출 주체 |
|--------|------|----------|
| `gate-check` | `cmd_gate_check` (`verify.py:789`) | Main session |
| `phase-check` | `cmd_phase_check` (`verify.py:819`) | Main session |
| `phase-verify` | `cmd_phase_verify` (`verify.py:1131`) | Main session (+ tmux foreman은 phase 5 내부에서) |
| `pattern-detect` | `cmd_pattern_detect` (`verify.py:1285`) | Phase 5 foreman 내부 only (main 직접 호출 금지) |

### 6.2 호출 패턴

```bash
# Gate 1/2/3 검증 (main)
python3 ~/.claude/scripts/jarfis_cli.py gate-check {state_file} {1|2|3}

# Phase 진입 전 전제조건 검사 (main)
python3 ~/.claude/scripts/jarfis_cli.py phase-check {state_file} {phase_id}

# Phase 완료 후 산출물 검증 (main)
python3 ~/.claude/scripts/jarfis_cli.py phase-verify {state_file} {phase_id}

# 리뷰 병적 패턴 감지 (foreman 내부)
python3 ~/.claude/scripts/jarfis_cli.py pattern-detect {docsDir}/review/review.md
```

### 6.3 반환 규약

- exit 0 = PASS / READY
- exit 1 = FAIL / BLOCKED
- stdout = JSON (`{verdict, missing, checkedAt}` 등)
- stderr = 진단 메시지 (있는 경우)

### 6.4 성능

- 일반 실행 시간: ~10ms (Python cold start 포함)
- 대비 v3 `jarfis-black` LLM gate: 2-5초 (~300x 빠름)
- 비용: 0 토큰 (vs ~1,400 토큰)

---

## 7. State + Audit + Trace 3층 (ADR-3 Updated)

### 7.1 파일 역할 분화

| 파일 | 수명 | 용도 | 실패 시 |
|------|------|------|---------|
| `.jarfis-state.json` | 워크플로우 단위 | 현재 상태 CRUD (Phase, Gate, Ratchet 결과) | 워크플로우 중단 |
| `audit.jsonl` | append-only (영구) | 이벤트 로그 (14 EVENT_TYPES) | 무시 (recovery source 아님) |
| `trace/*.jsonl` | opt-in (영구) | 성능/타이밍 메트릭 | 무시 |

### 7.2 EVENT_TYPES (`audit.py:13-21`)

14개 이벤트:
- `WorkflowStarted` · `WorkflowCompleted` · `WorkflowAborted`
- `PhaseStarted` · `PhaseCompleted`
- `AgentInvoked` · `AgentCompleted` · `AgentFailed`
- `QualityGateEvaluated` · `GateApproved`
- `RatchetChecked`
- `AutoCommit`
- `FallbackTriggered` · `CircuitBreakerChanged`

### 7.3 Best-effort 기록 (`state.py:_try_audit`)

```python
def _try_audit(audit_path, event_type, **data):
    """Best-effort audit logging. Failures are silently ignored."""
    if not audit_path:
        return
    try:
        global _audit_module
        if _audit_module is None:
            from . import audit as _mod
            _audit_module = _mod
        _audit_module.append_event(audit_path, event_type, **data)
    except Exception:
        pass
```

**원칙**: audit 기록 실패는 **state 변경을 차단하지 않는다**. audit은 복구 소스가 아님.

---

## 8. workflow-metrics.tsv — 측정 로그 (현재 상태)

### 8.1 기록 위치

```
{docsDir}/workflow-metrics.tsv
```

### 8.2 기록 시점

Phase 6 (Retrospective) 에서 한 행 추가:
- Phase별 시간
- Phase별 토큰 소비
- Phase별 에러/retry 수
- Review rounds (Phase 5)
- 기타 메트릭

### 8.3 역사 (AutoResearch pattern)

- v2.5.5: Workflow Metrics Recording 최초 도입 (`AutoResearch results.tsv` 패턴 차용)
- v4 유지: 기록 계속 누적

### 8.4 **현재 제한** (정직)

- **기록만 됨**. 대시보드 없음
- **자동 A/B 반영 루프 없음** — 사람이 수동으로 tsv 보고 패턴 식별
- v4.1 후보: 대시보드 + 자동 learnings 반영 루프

씨앗은 있으나 **"Dogfooding Evolution(#3) 의 Aspiration path"** 로 분류 (PHILOSOPHY §#3).

---

<a id="tradeoffs"></a>
## 9. Trade-offs — 운영 비용 (findings F-10, 정직 섹션)

v4 tmux-per-phase는 설계 개선이지만 **운영 비용**을 수반한다. 외부 평가(ChatGPT/Claude 3라운드)가 일부만 인식한 영역. 본 섹션에서 정면 기술.

<a id="tradeoffs-zombie-tmux"></a>
### 9.1 비용 1 — 좀비 tmux 세션

| 문제 | 설명 |
|------|------|
| 현상 | 워크플로우 중단(크래시 / 사용자 강제 종료)시 tmux 세션이 고아 상태로 남을 수 있음 |
| 영향 | 리소스 점유 (메모리 + Claude CLI 프로세스) |
| 대응 | `/jarfis:sys-health` 명령 — 좀비 Claude 프로세스 진단 + kill 제안 |
| 한계 | 사용자가 sys-health를 주기적으로 돌려야 함. 자동 백그라운드 청소 없음 |

### 9.2 비용 2 — 디버깅 복잡도

| 문제 | 설명 |
|------|------|
| 현상 | v3는 "한 세션에서 로그 다 보임", v4는 "main + 여러 tmux 세션에 분산" |
| 영향 | "어디서 무슨 일이 일어났는가" 추적 비용 증가 |
| 대응 | `--save-pane` (v4.0.4) — scrollback 자동 보존. `JARFIS_TRACE` (v4.0.5) — 구조화 span |
| 한계 | Monitor App 미구현 (v4.2+). 현재 pane.log + trace.jsonl 직접 읽어야 |

### 9.3 비용 3 — tmux 의존성

| 문제 | 설명 |
|------|------|
| 현상 | tmux가 설치되지 않은 환경에서 작동 불가 |
| 영향 | Docker / CI 환경 등에서 추가 설정 필요 |
| 대응 | macOS/Linux 표준 도구라 일반적으론 문제 없음. WSL/Cygwin 등에서 미검증 |
| 한계 | Windows native 지원 없음 (v4.1 후보) |

### 9.4 비용 4 — 세션 초기화 오버헤드

| 문제 | 설명 |
|------|------|
| 현상 | 매 Phase마다 Claude CLI를 새로 띄움 (5-10초) |
| 영향 | 13 steps 워크플로우당 ~7개 tmux phase × 5-10초 = 35-70초 초기화 비용 |
| 대응 | v4.0에서는 이 비용을 수용 (컨텍스트 89% 감소의 trade-off) |
| 한계 | 세션 pool / 재사용은 v4.1+ 논의 (단 격리 원칙과 충돌 가능) |

### 9.5 비용 5 — 1인 dogfooding pool

| 문제 | 설명 |
|------|------|
| 현상 | 단일 사용자의 실행 패턴만으로 운영 안정성 검증 |
| 영향 | 다양한 환경/사용 패턴에서의 회귀를 조기 포착 어려움 |
| 대응 | `workflow-metrics.tsv` + `learnings.md` 축적 → sys-upgrade로 반영 |
| 한계 | 사용자 pool이 커져야 진짜 검증됨. 현 단계는 "아키텍처 성숙도 상승, 운영 안정성 정착 중" |

### 9.6 요약 — 운영 이원화 프레임

ChatGPT 3라운드 정제 표현:

> **"v4는 아키텍처 성숙도가 상승했고, 운영 안정성은 정착 중."**

tmux-per-phase / verify.py / single-writer / JARFIS_TRACE 같은 **설계**는 명확한 개선. 반면 **운영**은 solo dev pool + sys-health 수동 의존 단계. 정직하게 구분하여 README / PHILOSOPHY / 이력서에 반영.

---

## 10. 참조

- **설치/업데이트**: `~/.claude/.jarfis-source` (repo 경로), `/jarfis:sys-version` 명령
- **실 구현 소스**: `~/.claude/scripts/jarfis/` 디렉토리 (Python 모듈들)
- **hooks 설정**: `~/.claude/settings.json` (Claude Code hooks 표준 형식)
- **v4 설계 상세**:
  - `~/Upscales/jarfis-v4-migration/architecture.md` — tmux orchestration 원 설계
  - `~/Upscales/jarfis-v4-migration/system-spec.md` §6 (verify.py) / §7 (tmux_claude) / §8 (디렉토리)
- **trace-design ADR**: `~/Upscales/jarfis-v4-migration/adr/v4.0.5-trace-design.md`
- **sys-health 구현**: `~/.claude/commands/jarfis/sys-health.md`

---

*이 문서는 v4.0.5 시점의 실행 환경 구성을 기록한다. 실제 디렉토리 / 파일 / 스크립트가 1차 source이며 본 문서는 독자를 위한 narrative view. drift 발생 시 코드가 우선한다.*
