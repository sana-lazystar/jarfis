# JARFIS Workflow

> **Last aligned**: v4.0.5 · 2026-04-20
> **Audience**: 기여자 · 미래의 자신 · 외부 평가자
> **Source of truth**: `~/.claude/commands/jarfis/work.md` (255줄) — 본 문서는 그 orchestrator를 독자가 이해 가능한 narrative로 재서술
>
> **상위 설계**: [PHILOSOPHY.md](./PHILOSOPHY.md) #1 Deterministic Foundation + #4 Resilient Continuity + #6 Gated Autonomy
> **아키텍처 ADR**: [DESIGN.md](./DESIGN.md) ADR-9 Human Gate, ADR-15 verify.py, ADR-16 tmux-per-phase, ADR-18 Single-writer, ADR-19 Phase 4.5
> **구현 detail**: `~/Upscales/jarfis-v4-migration/system-spec.md` §9, §9.2, §16

---

## 1. 개요

`/jarfis:work`는 JARFIS의 메인 오케스트레이터다. 사용자의 입력(`$ARGUMENTS`)을 13단계 워크플로우에 태워 **요구 발굴 → 설계 → 구현 → 검증 → 회고** 까지 연결한다. 각 단계의 실행 경계와 검증은 deterministic하게 고정되어 있다 (DESIGN ADR-15, ADR-18).

### 1.1 13-step flow

```
T → 0 → 1a → 1b → Gate 1 → 2 ∥ 3 → Gate 2 → 4 → 4.5 → 5 → Gate 3 → 6
```

| # | 단계 | 실행 주체 | 성격 |
|---|------|----------|------|
| T | Triage | main (direct) | Type A/C/Resume 분류 |
| 0 | Pre-flight | main (direct) | State 초기화 + 10단계 설정 |
| 1a | PO Discovery Dialogue | main (direct) | AskUserQuestion multi-round |
| 1b | Discovery Processing | tmux (foreman) | PO + TA artifacts 처리 |
| **Gate 1** | Discovery Gate | main (direct) | `gate-check` + AskUserQuestion |
| 2 | Architecture & Planning | tmux (foreman) | 병렬 #1 |
| 3 | Design | tmux (foreman) | 병렬 #2 (conditional) |
| **Gate 2** | Planning + Design Gate | main (direct) | `gate-check` + AskUserQuestion |
| 4 | Implementation | tmux (foreman) | Sub-agent spawn |
| 4.5 | Operational Readiness | tmux (foreman) | DevOps first-class |
| 5 | Review & QA | tmux (foreman) | 내부 review_round loop (max 3) |
| **Gate 3** | Review Gate | main (direct) | `gate-check` + AskUserQuestion |
| 6 | Retrospective + Wiki Sync | tmux (foreman) | learnings 축적 |

> **주의**: "9 Phase" 는 v3 시대 표현이다. v4 실체는 **13 steps (T, 0, 1a, 1b, G1, 2, 3, G2, 4, 4.5, 5, G3, 6)**. 요약이 필요하면 "Phase T to 6 with Gate 1/2/3" 로 부른다.

### 1.2 실행 경계 (main vs tmux-foreman)

JARFIS v4는 Phase마다 실행 주체가 명시적으로 다르다 (ADR-16):

| 실행 주체 | 담당 단계 | 특성 |
|-----------|----------|------|
| **Main (direct)** | T, 0, 1a, Gate 1/2/3 | AskUserQuestion + 상태 쓰기 + gate-check |
| **tmux (`jarfis-foreman`)** | 1b, 2, 3, 4, 4.5, 5, 6 | 격리된 tmux 세션에서 sub-agent spawn + artifact 생성 |

**경계 규칙**:
- main은 사용자 대화 + state 쓰기 + gate 판정만 담당. tmux phase의 구현 detail에 관여하지 않는다.
- tmux foreman은 해당 Phase 프롬프트(`prompts/phase{N}.md`)를 로드 → `compose` CLI로 sub-agent 합성 → Task tool로 spawn → 결과 artifact 파일 생성.
- 두 주체는 **직접 통신 불가**. 파일 경로 단위로 단방향 통신 (ADR-18).

### 1.3 Single-writer state rule (ADR-18)

동시성 경합을 **파일 경로 단위**로 원천 차단:

| 파일 | Writer | Reader |
|------|--------|--------|
| `.jarfis-state.json` | Main only | Main + tmux (read-only) |
| `phase-results/phase{N}/attempt{K}.json` | tmux sub-agent only | Main |
| Phase 출력 디렉토리 (`discovery/`, `planning/`, `design/`, `review/`, `ops/`, `retrospective.md`) | 해당 Phase 실행 주체만 | 모두 |

Main이 sub-agent 결과(phase-results)에서 분기 결정에 필요한 필드만 **선별 반영**하여 state에 기록. tmux sub-agent는 state를 읽기만 하고 쓰지 않는다. Lock 없이 안전 보장.

---

## 2. Resume Dispatch (Phase T 이전 실행)

워크플로우 진입 시 **기존 진행 중 작업 감지**가 먼저 실행된다.

### 2.1 감지 흐름

1. `docsDir` 후보 해소:
   - `$ARGUMENTS`가 경로 형태면 사용
   - 아니면 `cwd`
   - 아니면 `$JARFIS_ORG_DIR/works/` 최신 엔트리
2. `{docsDir}/.jarfis-state.json` 검사
3. 상태 분기:

| state 최상위 키 | 해석 | 동작 |
|----------------|------|------|
| `sessionKey` 있음 | **v4 state** | AskUserQuestion (`$LOCALE`): Resume / Start over / Abort |
| `project_name` 있음 (no `sessionKey`) | **v3 state** | 사용자에게 안내 후 halt (silent migration 금지 — findings F-08) |
| state 파일 없음 | 신규 | Phase T로 진행 |

### 2.2 v4 Resume 동작

- `state.currentPhase` 부터 재진입
- `phases.{N}.status == "verified"` 인 Phase는 skip
- 재진입 직후 **idempotence check** — 해당 Phase artifact가 이미 `phase-verify` PASS면 재실행 없이 `verified`로 승격

### 2.3 v3 state silent migration 금지 (F-08)

v3 → v4 state는 **incompatible** (CHANGELOG v4.0.0). 감지 시 사용자 메시지 (`$LOCALE`):

> "v3 workflow state detected at this path. Continue with the legacy `/jarfis:work` (v3) for this work; start v4 work in a new directory."

**자동 이관 금지** — 결정권은 사용자에게. 상세 경로는 [MIGRATION.md §3](./MIGRATION.md#3-전환-경로) 참조.

---

## 3. Phase T — Triage (main, direct)

`$ARGUMENTS` + 최근 대화를 3분기 중 하나로 분류 (Type B는 M7에서 제거 — findings F-07).

| Type | 특성 | 동작 |
|------|------|------|
| **A** | 신규 기능 / 리팩터링 / 설계 요청 | 자동으로 Phase 0 진행 |
| **C** | 단순 질문 / 디버그 / config 튜닝 (워크플로우 아님) | AskUserQuestion: "직접 응답 (권장)" / "그래도 풀 워크플로우" / "Abort" |
| **Resume** | 기존 워크플로우 이어서 | Resume Dispatch에서 이미 처리 (§2) |

**Phase T는 state를 쓰지 않는다** — state 생성은 Phase 0부터.

**"암묵 게이트" 성격**: 3개 공식 Gate(1/2/3)와 별개로, Triage는 분류 게이트 역할을 한다. Type C에서 AskUserQuestion이 발동하는 것이 그 증거.

---

## 4. Phase 0 — Pre-flight (main, direct)

State 초기화 + 워크스페이스 + 인벤토리 확정. 10단계를 순차로 실행하며 각 단계는 `jarfis_cli.py state set` / `set-nested` 로 state에 반영.

| Step | 내용 | 출력 |
|------|------|------|
| 1 | **Locale**: `~/.claude/.jarfis-locale` → `state.locale`. 없으면 사용자 입력에서 자동 감지 후 persist (M12) | `state.locale` |
| 2 | **Work identity**: AskUserQuestion (or `$ARGUMENTS` 파생) → `state.work = {name, input, docsDir (absolute), startedAt}` | `state.work` |
| 3 | **sessionKey**: `jf-` + uuid4 앞 8자 | `state.sessionKey` |
| 4 | **Org detect**: `jarfis_cli.py org detect` → `state.org = {name, root}` 또는 `null` (M10 snapshot once) | `state.org` |
| 5 | **Workspace scope**: 프로젝트 경로 루프. 각 경로에 `jarfis_cli.py detect` 실행 → framework/languages auto-fill + 사용자가 name/type 입력 | `state.workspace.scope[]` + `structure` |
| 6 | **Git branch cut**: 각 scope에 `git checkout -b {branch}` + baseCommit 기록 (B2) | `scope[i].baseCommit` |
| 7 | **Domain detect**: `jarfis_cli.py domain detect` → `state.domain`. tie면 AskUserQuestion | `state.domain` |
| 8 | **Meetings**: `jarfis_cli.py search meetings` (fallback: `jarfis_cli.py meetings 3`). User picks 0..N | meeting 참조 |
| 9 | **Wiki loading** (Org 있을 때만): `prompts/wiki-loading.md` 4-step → `{docsDir}/.wiki-cache.md` | wiki cache |
| 10 | **Preflight verify**: `jarfis_cli.py preflight` — exit 0 필수 | verified |

Phase 0 완료 후 `.jarfis-state.json` 에 workspace 전체 맥락이 고정된다. 이후 Phase는 이 state를 read-only 참조.

---

## 5. Phase 1a — PO Discovery Dialogue (main, direct)

Product Owner 관점의 요구 발굴을 **AskUserQuestion multi-round** 로 진행. 한 턴에 하나의 결정, 라벨은 `$LOCALE`.

### 5.1 수집 필드

| 필드 | 값 | 조건 |
|------|-----|------|
| `design.mode` | figma / text / null | null이면 Phase 3 skip |
| `design.figmaPages[]` | `[{title, url}]` JSON 배열 | mode=figma 일 때만 |
| `responsive` | pc-only / pc-mobile / pc-mobile-tablet | frontend scope 있을 때만 |
| `api.mode` | design / swagger / null | frontend만 있고 backend 없을 때. swagger면 `api.swaggerUrl` 추가 |
| `devops` | boolean | DevOps agent 필요 여부 |
| PO extras | multi-select: `legal-review`, `ux-direction` | Phase 1b 출력 영향 |

### 5.2 산출물

- `{docsDir}/discovery/po-qa.json` — 전체 Q&A 아카이브
- state 즉시 반영 (각 답변마다)

**PO sub-agent spawn은 v4.1로 연기** — v4.0은 main에서 직접 처리 (context 비용 낮음).

---

## 6. Phase 1b — Discovery Processing (tmux, foreman)

PO artifacts + TA(Technical Architect) 관점을 통합하여 PRD와 Working Backwards 문서를 생성.

**Prompt**: `prompts/phase1b.md` (8,185 bytes)

**Sub-agents (foreman이 spawn)**:
- `product-owner` persona — PRD 작성
- `technical-architect` persona — 기술 제약 반영
- UX direction 요청 시 `ux-designer` persona 추가

### 6.1 주요 산출물

- `discovery/prd.md` — Product Requirements Document
- `discovery/working-backwards.md` — press release 역산
- `discovery/ux-direction.md` — UX 방향 (ux-direction extras 선택 시)
- `phase-results/phase1b/attempt{K}.json` — 실행 메타

### 6.2 foreman 실행 패턴

tmux 내부에서 foreman이:
1. `jarfis_cli.py compose --agent product-owner --state {state}` → PRD sub-agent prompt 생성
2. Task tool로 sub-agent spawn
3. 결과 artifact 수집
4. Completion Protocol에 따라 `phase-results/phase1b/attempt{K}.json` 에 `{status, reason, reasonDetail}` 기록

Main session은 완료 알림 후 `phase-verify` 호출.

---

## 7. Gate 1 — Discovery Gate (main, direct)

Phase 1b 완료 후 사용자 검토 + 승인 단계.

### 7.1 사전 검증

```bash
python3 ~/.claude/scripts/jarfis_cli.py gate-check {state_file} 1
```

- exit 0 PASS → 사용자에게 요약 제시
- exit 1 FAIL → `missing[]` 표시, Phase 1b 복귀. **Gate 제시 금지**.

### 7.2 AskUserQuestion

PASS 시 artifact 요약 (`discovery/prd.md`, `working-backwards.md`, `ux-direction.md`) 후:

| 옵션 | 동작 |
|------|------|
| Approve | Phase 2 (+3 parallel) 로 진행 |
| Revision | Phase 1b 재실행 (`state.phases.1b.attempt += 1`) |
| Abort | 워크플로우 종료 |

`state.gates.1 = "approved" | "rejected"` 반영.

---

## 8. Phase 2 ∥ Phase 3 — 병렬 tmux 실행 (ADR-16, findings F-04)

JARFIS v4의 **절대 병렬성** 예시. 두 독립 tmux 세션에서 동시 실행.

### 8.1 병렬 구조

```
Gate 1 PASS
    ↓
    ├── tmux A: {sessionKey}-phase2   (Architecture & Planning)
    └── tmux B: {sessionKey}-phase3   (Design)
              (state.design.mode != null 일 때만)
    ↓
Gate 2 (둘 다 verified 된 후)
```

**B1 Isolation 규칙**: `tmux_claude.py::kill_existing_session` 은 exact name match만 허용. prefix 기반 대량 kill 금지 → 두 세션이 서로 죽이는 사고 원천 차단.

### 8.2 Phase 2 — Architecture & Planning (tmux)

**Prompt**: `prompts/phase2.md` (7,324 bytes)

**Sub-agents**:
- `technical-architect` — 아키텍처 설계
- `backend-developer` / `frontend-developer` — 구현 계획 초안
- `qa-engineer` — 테스트 전략
- `security-engineer` (조건부) — 보안 요구

**산출물**:
- `planning/architecture.md` — 아키텍처 결정
- `planning/tasks.md` — 태스크 분해
- `planning/test-strategy.md` — 테스트 전략
- `planning/api-spec.md` — API 스펙 (backend + frontend 혼재 + `api.mode` 해당 시)

### 8.3 Phase 3 — Design (tmux, conditional)

**Prompt**: `prompts/phase3.md` (25,916 bytes — figma + text 통합)

**Conditional**: `state.design.mode == null` 이면 Phase 3 entire skip (progress tracking task #6도 생성하지 않음).

**Sub-agents**: `ux-designer` persona + figma MCP (figma 모드) 또는 text-only design generation.

**산출물**:
- `design/token-map.json` — 디자인 토큰 매핑
- `design/{page}/index.html` — HTML 시안 (페이지별)
- `design/{page}/reference*.png` — 참조 이미지 (figma 모드)

---

## 9. Gate 2 — Planning + Design Gate (main, direct)

두 병렬 Phase (2 + 3) 모두 `verified` 상태 된 후 진입.

### 9.1 gate-check

```bash
python3 ~/.claude/scripts/jarfis_cli.py gate-check {state_file} 2
```

### 9.2 사용자 옵션

| 옵션 | 동작 |
|------|------|
| Approve | Phase 4 진행 |
| Revision | Phase 2 or Phase 3 재실행 (어느 것인지 AskUserQuestion) |
| Abort | 종료 |

---

## 10. Phase 4 — Implementation (tmux, foreman)

**Prompt**: `prompts/phase4.md` (14,881 bytes)

### 10.1 Sub-agent 구성

Scope 기반 동적 합성:
- `state.workspace.scope[]` 의 각 프로젝트마다 type/framework에 맞는 role
  - frontend scope → `frontend-developer` + skill set (react/vue/nextjs 등)
  - backend scope → `backend-developer` + skill set (nodejs/express 등)
  - DevOps 필요 시 → `devops-engineer` (`state.devops == true` 일 때)

### 10.2 TDD Ratchet (조건부 — ADR-21)

`$TDD_ENABLED == 'true'` 일 때만 활성. Phase 4 Step 4에서 foreman이 직접 실행:
- `current_pass_rate >= baseline_pass_rate` 필수
- REJECT 시: `git stash` → 에이전트 재지시 → 태스크당 최대 2회
- 2회 실패 시: `git stash pop` → 원복 → 다음 태스크 → Phase 5에서 진단

PRD Ratchet / Fix Ratchet은 v4에서 legacy (DESIGN ADR-21 참조).

### 10.3 산출물

- 코드 변경 (각 scope 저장소에 커밋)
- `phase-results/phase4/attempt{K}.json` meta — `tddEnabled` 값 포함

Phase 4 완료 시 main이 `meta.tddEnabled` 를 `state.tddEnabled` 에 반영.

---

## 11. Phase 4.5 — Operational Readiness (tmux, foreman — ADR-19, F-05)

DevOps를 **first-class Phase 주체**로 승격. Phase 4와 Phase 5 사이에 삽입.

**Prompt**: `prompts/phase4-5.md` (4,787 bytes — 상대적으로 간결)

### 11.1 Phase ID 표기 규칙

- 파일/경로/state key: **`4-5` (하이픈)** — 예: `prompts/phase4-5.md`, `phase-results/phase4-5/attempt1.json`
- 이유: `.` 은 파일 확장자/URL 도메인 구분자와 충돌

### 11.2 Sub-agents

- `devops-engineer` persona (primary)
- 필요 시 `security-engineer` (운영 보안 관점)

### 11.3 산출물

- `ops/infra-runbook.md` — 운영 절차 (배포 방법, 롤백, 모니터링)
- `ops/deployment-plan.md` — 배포 계획 (환경별 체크리스트, 의존성)

### 11.4 Skip 불가

Phase 4.5는 conditional skip이 없다. 모든 워크플로우가 운영 준비 산출물을 요구한다 (작은 작업에서 overhead 가능성은 단점으로 인정 — DESIGN ADR-19).

---

## 12. Phase 5 — Review & QA (tmux, foreman)

**Prompt**: `prompts/phase5.md` (24,348 bytes — 가장 큰 phase prompt)

### 12.1 내부 review_round loop (MAX_REVIEW_ROUNDS = 3)

Phase 5는 **tmux foreman 내부**에서 최대 3 review round를 돌린다. Main session은 **단 한 번의 tmux 호출**로 인식.

각 라운드 foreman이 실행:
1. sub-agent (tech-lead, qa-engineer, security-engineer) 가 `review/review.md` 생성/갱신
2. `python3 ~/.claude/scripts/jarfis_cli.py pattern-detect {docsDir}/review/review.md` — stdout JSON `{patterns[], details}` (exit 0 항상, main 직접 호출 안 함)
3. patterns 값: `"stagnation"` / `"oscillation"` / `"regression"` 중 일부 또는 `[]`
4. non-empty 시 → 다음 라운드에서 review 개선
5. 3 라운드 이후 종료

### 12.2 반영할 meta (verify PASS 직후 main이 읽음)

- `meta.review_rounds` (int, 1..3)
- `meta.pathological_patterns` (string[])

`meta.pathological_patterns` 가 non-empty 면 foreman이 이미 `review/review.md` 에 경고 섹션 + diagnosis 파일을 기록. Main은 Gate 3에서 조건부 "Re-design Phase 2" 옵션을 제시.

### 12.3 산출물

- `review/review.md` — 코드/QA/보안/UX 리뷰 (각 sub-agent 섹션)
- `review/api-contract-check.md` — API 스펙 부합 (api-spec 존재 시)
- `review/diagnosis-*.md` — pattern-detect 이상 탐지 시 진단 문서

---

## 13. Gate 3 — Review Gate (main, direct)

### 13.1 옵션 (pattern-detect 결과에 따라 조건부)

| 옵션 | 조건 | 동작 |
|------|------|------|
| Approve | 항상 | Phase 6 진행 |
| Re-review | 항상 | Phase 5 additional round (`state.phases.5.attempt += 1`, max 2) |
| **Re-design Phase 2** | `meta.pathological_patterns` non-empty (M3 결정) | Phase 2로 복귀 — 아키텍처/태스크 재작성 |
| Abort | 항상 | 종료 |

### 13.2 "Re-design Phase 2" 의미

병적 패턴(stagnation / oscillation / regression)이 Phase 5에서 지속 감지되면 **Phase 4 구현의 문제가 아니라 Phase 2 설계의 문제** 가능성이 높다. 구현 땜질 대신 상위 단계 복귀가 ROI 우세.

---

## 14. Phase 6 — Retrospective + Wiki Sync (tmux, foreman)

**Prompt**: `prompts/phase6.md` (18,478 bytes)

### 14.1 주요 작업

1. **Retrospective**: `retrospective.md` — 작업 회고 (어려웠던 점, 잘된 점, 개선점)
2. **learnings 축적**: `learnings.md` (global) + `project-context.md` (project) 업데이트
3. **workflow metrics**: `workflow-metrics.tsv` 한 행 추가 (Phase별 시간/토큰/에러 기록 — v2.5.5 AutoResearch 패턴)
4. **Wiki sync** (Org 등록 시): 변경 사항을 `.jarfis-org/wiki/` 해당 섹션 `_index.md` 에 반영

### 14.2 #3 Dogfooding Evolution 구현점

Phase 6는 PHILOSOPHY #3의 활성 인스턴스. 매 워크플로우가 학습 데이터가 되는 지점이다.

---

## 15. tmux Phase 실행 공통 패턴

1b, 2, 3, 4, 4.5, 5, 6 모두 아래 패턴으로 실행.

### 15.1 단계

```
0. phase-check (prerequisites)
1. 프롬프트 조합 (phase{N}.md + attempt {K} + Completion Protocol)
2. result path 결정 (phase-results/phase{N}/attempt{K}.json)
3. tmux_claude.py 백그라운드 실행
4. tmux 종료 후 result 읽기
5. phase-verify 실행
6. PASS: state 갱신 + AskUserQuestion
7. FAIL: retry or failed status
```

### 15.2 Step 0 — phase-check (prerequisites)

```bash
python3 ~/.claude/scripts/jarfis_cli.py phase-check {state_file} {phase_id}
```

- exit 0 READY → tmux 실행 가능
- exit 1 BLOCKED → `blockers[]` 표시, 이전 Phase / Gate 복귀. **tmux 실행 금지**.

system-spec §16 "Phase Required Inputs Matrix" 에 각 Phase의 전제 조건 정의.

### 15.3 Step 1 — 프롬프트 조합

```
{docsDir}/phase{phase_id}-prompt-attempt{K}.md  ← main이 작성
```

내용:
- `prompts/phase{N}.md` 본문 (4.5는 `phase4-5.md`)
- `{N}`, `{K}` 치환
- retry 시: "Previous attempt did not produce: <missing[]>. You must create them." 블록 추가
- Completion Protocol (implement-plan A.10) 부록

### 15.4 Step 3 — tmux_claude.py 실행

```bash
python3 ~/.claude/scripts/jarfis/tmux_claude.py \
  --name {sessionKey}-phase{phase_id} \
  --prompt {prompt_path} \
  --result {result_path} \
  --workspace {docsDir} \
  --save-pane {docsDir}/phase-results/phase{phase_id}/attempt{K}.pane.log
```

**Options**:
- `--mcp-config ~/.claude/.mcp.json` — M6 MCP 상속 실패 시에만 추가
- `--save-pane` (v4.0.4 N-1) — tmux scrollback 저장 (post-mortem 용)

**Bash tool description 규약** (UX-2):
- 첫 attempt: `"JARFIS Phase {phase_id} execution"`
- retry: `"JARFIS Phase {phase_id} retry attempt {K}"`
- 백그라운드 완료 알림이 `Background command "{description}" completed` 로 표시되어 context 가독성 보장

### 15.5 Step 4 — result 읽기

tmux 종료 후 `{result_path}` 파일 읽기. JSON `{status, reason, reasonDetail}`.

| status | 처리 |
|--------|------|
| `"error"` | `reason` + `reasonDetail` 사용자에게 그대로 (`$LOCALE`). `state.phases[id].status = "failed"`. **재시도 없음** (Claude-level crash는 재실행해도 같은 결과) |
| `"completed"` | Step 5 verify 진행 |

### 15.6 Step 5 — phase-verify

```bash
python3 ~/.claude/scripts/jarfis_cli.py phase-verify {state_file} {phase_id}
```

stdout JSON: `{verdict, missing, checkedAt}`
- exit 0 PASS
- exit 1 FAIL → `missing[]` 표시

### 15.7 Step 6 — PASS 처리

1. `state.phases[id].status = "verified"`
2. phase-results meta 검사:
   - `importance: required` missing (entries where `injected == false`) → **soft warning** (`$LOCALE`): "Phase {N} complete. Required context missing: `{path}`, ..." — **차단 안 함**, 계속 진행
   - `importance: recommended` missing → silent (debug log)
   - Phase 4 전용: `meta.tddEnabled` → `state.tddEnabled`
   - Phase 5 전용: `meta.review_rounds` + `meta.pathological_patterns` 보존 (Gate 3에서 읽음)
3. AskUserQuestion (`$LOCALE`): "Phase {N} complete (X/Y artifacts). Proceed?" — Approve / Abort

### 15.8 Step 7 — FAIL 처리

```
if attempt < MAX_RETRIES (2):
    state.phases[id].attempt += 1
    state.phases[id].status = "retry"
    → Step 1 복귀 (missing 명시)
    (silent retry — 다음 Phase 시작에 한 줄 note: "Phase {N} retry ({K}/{MAX_RETRIES})")
else:  # attempt >= 2
    state.phases[id].status = "failed"
    AskUserQuestion: "2 attempts failed. Missing: {missing}. Proceed how?"
        - Manual completion
        - Force next Phase
        - Abort workflow
```

---

## 16. Gate Handling 공통 패턴

Gate 1, 2, 3 모두 동일 구조.

### 16.1 필수 단계

```
1. gate-check (deterministic, exit 0/1)
   └─ FAIL: missing 표시, Phase 복귀. Gate 제시 금지.
2. PASS: artifact 요약
3. AskUserQuestion (options는 Gate마다 상이)
4. state.gates.{N} = "approved" | "rejected"
5. Approve → 다음 Phase. Rejected/Abort → 워크플로우 종료.
```

### 16.2 Gate별 옵션 요약

| Gate | 시점 | Options |
|------|------|---------|
| 1 | Phase 1b 후 | Approve / Revision (Phase 1b 재실행) / Abort |
| 2 | Phase 2+3 후 | Approve / Revision (Phase 2 or 3 선택) / Abort |
| 3 | Phase 5 후 | Approve / Re-review (Phase 5 round+1, max 2) / **Re-design Phase 2** (조건부) / Abort |

---

## 17. Error Handling 전역 매트릭스

| 조건 | 동작 |
|------|------|
| `phase-check` BLOCKED | `blockers[]` 표시. Phase/Gate 복귀. tmux 실행 금지. |
| `tmux_claude.py` exit 1 (timeout / runtime error) | result.json `reason` + `reasonDetail` 그대로 (`$LOCALE`). `phases.{N}.status = "failed"`. 자동 재시도 없음. |
| `gate-check` FAIL | `missing[]` 표시. 현 Phase 복귀. Gate 제시 금지. |
| `phase-verify` FAIL + `attempt < 2` | Silent auto-retry (다음 Phase 시작에 한 줄 note). |
| `phase-verify` FAIL + `attempt >= 2` | AskUserQuestion: Manual completion / Force next Phase / Abort |
| `importance: required` missing (verify PASS에도 불구) | Soft warning (`$LOCALE`). 계속 진행. |
| `importance: recommended` missing | Silent (debug log only). |
| Phase 5 pattern-detect non-empty | foreman이 review.md에 경고 추가. Main이 Gate 3에서 "Re-design Phase 2" 옵션 조건부 제시. |

---

## 18. User Confirmation 통일 규칙

- **모든** 사용자 의사결정은 AskUserQuestion — 자유 텍스트 응답 금지
- 질문 + 모든 옵션 라벨은 `$LOCALE` 언어
- 옵션 라벨은 verb + noun 패턴: "Approve and proceed", "Revise and re-run Phase 2", "Abort workflow"

---

## 19. Progress Tracking — per-Phase TaskCreate (UX-1)

Main session은 **논리 단계마다 TaskCreate 항목 1개** 를 생성. 여러 Phase/Gate를 한 태스크로 묶지 않는다.

### 19.1 필수 태스크 리스트 (순서대로)

| # | Subject (예시) | Owner (trigger) |
|---|---------------|-----------------|
| 1 | `Phase 0 — project profile` | main direct |
| 2 | `Phase 1a — PO + TA discovery (parallel)` | main direct (Task tool, parallel sub-agents) |
| 3 | `Gate 1 — discovery confirmation` | main direct (AskUserQuestion) |
| 4 | `Phase 1b — discovery processing` | tmux foreman |
| 5 | `Phase 2 — architecture & planning` | tmux foreman |
| 6 | `Phase 3 — design` (omit if `design.mode == null`) | tmux foreman |
| 7 | `Gate 2 — planning + design confirmation` | main direct (AskUserQuestion) |
| 8 | `Phase 4 — implementation` | tmux foreman |
| 9 | `Phase 4.5 — operational readiness` | tmux foreman |
| 10 | `Phase 5 — review & QA` | tmux foreman (internal review_round loop) |
| 11 | `Gate 3 — review confirmation` | main direct (AskUserQuestion) |
| 12 | `Phase 6 — retrospective + wiki sync` | tmux foreman |

### 19.2 상태 전이

- Phase/Gate 진입 → `TaskUpdate(taskId, status="in_progress")`
- `phase-verify` PASS (or Gate Approve) → `TaskUpdate(taskId, status="completed")`
- retry (`attempt += 1`) → 동일 task 유지, `activeForm` 을 `"Phase {N} retry attempt {K}"` 로 변경. **새 task 생성 금지.**
- Abort → 현재 in_progress task를 subject "(aborted)" 접미로 completed 처리, 이후 task 생성 중단

### 19.3 Skip 규칙

- `state.design.mode == null` → task #6 entire 생성 안 함 ("skipped" completed task 만들지 말 것)
- 백엔드 scope 없고 `api.mode == null` → task #5 subject 유지. api-spec skip은 phase prompt 내부 처리

### 19.4 배경

M8 Attempt 3 관찰: main이 TODOs를 3개 coarse bucket("Phase 0 / 1a / 1b~6")으로 압축하여 tmux 15+ 분 실행 중 Phase 4 진행이 안 보였음. Per-Phase + per-Gate task로 가시성 복원.

---

## 20. Troubleshooting — trace subsystem (v4.0.5)

`trace` 서브시스템은 **opt-in**. 기본값 off, 런타임 비용 없음. Post-mortem 데이터가 필요할 때만 활성.

### 20.1 활성화

```bash
export JARFIS_TRACE=1
# 선택: 경로 지정 (default: /tmp/jarfis-trace.jsonl)
export JARFIS_TRACE_PATH=~/work-debug/trace.jsonl
```

### 20.2 이벤트 (JSONL, 한 줄당 `{ts, event, attrs}`)

| Event | Source | Attributes |
|-------|--------|-----------|
| `tmux_session_start` | `tmux_claude.py` | `session, workspace, mcp_config (bool)` |
| `tmux_session_ready` | `tmux_claude.py` | `session` |
| `tmux_prompt_sent` | `tmux_claude.py` | `session, prompt_path` |
| `tmux_session_end` | `tmux_claude.py` | `session, status, reason, duration_ms` |
| `phase_verify_start` | `verify.cmd_phase_verify` | `phase_id` |
| `phase_verify_end` | `verify.cmd_phase_verify` | `phase_id, verdict, missing_count, duration_ms` |
| `compose_start` | `compose/__main__::_compose` | `agent, scope_index` |
| `compose_end` | `compose/__main__::_compose` | `agent, context_files, injected_files, skills_count, prompt_chars, duration_ms` |

### 20.3 비활성화

```bash
export JARFIS_TRACE=0
# 또는
unset JARFIS_TRACE
```

코드 변경/재배포 불필요 (ADR-20 kill switch).

### 20.4 안전성

모든 instrumentation 사이트는 `try/except` 으로 감싸져 있어 trace 실패가 Phase 결과를 뒤집지 않는다. `JARFIS_TRACE=0` (기본) 일 때 overhead ~0.008%. `=1` 일 때 overhead < 20% (v4.0.5 preflight Phase 6 baseline 기준).

### 20.5 Trace 파일 성장

append-only JSONL. **수동 rotation/prune** — 자동 cleanup은 v4.0.6+ follow-up.

---

## 21. Anti-Optimization (orchestrator 수준)

오케스트레이터는 아래 규칙을 강제한다. agent output 수준의 anti-optimization은 `jarfis-foreman` persona + 각 `prompts/phase*.md` 에서 관리.

- **Phase 병합 금지** — 여러 Phase를 하나의 tmux 세션으로 합치는 것 금지. Phase 2 ∥ 3 병렬은 두 개의 distinct session (서로 다른 `sessionKey-phase{N}`) 로만 허용.
- **Step skip 금지** — 명시적 Skip Rules 외에는 skip 금지 (`design.mode == null` 이 Phase 3 skip, backend 없고 `api.mode == null` 이 api-spec skip).
- **`gate-check` bypass 금지** — gate-check exit 1일 때 Gate 제시 금지.

---

## 22. 참조

- **Flow chart + executor matrix**: `~/Upscales/jarfis-v4-migration/system-spec.md §9`
- **Required Inputs per Phase**: system-spec §16
- **verify.py 4 subcommands**: system-spec §6
- **tmux_claude.py core flow**: system-spec §7
- **state schema**: `~/Upscales/jarfis-v4-migration/implement-plan.md A.1`
- **phase-results schema**: implement-plan A.3
- **Completion Protocol**: implement-plan A.10
- **Agent mapping per Phase**: implement-plan A.11
- **agent-composition.yaml**: `~/.claude/commands/jarfis/agent-composition.yaml`
- **Per-phase prompts**: `~/.claude/commands/jarfis/prompts/phase{1b,2,3,4,4-5,5,6}.md` (M6)
- **Personas**: `~/.claude/agents/jarfis/personas/*.md`
- **jarfis-foreman (tmux executor)**: `~/.claude/agents/jarfis/jarfis-foreman.md`

---

*이 문서는 `work.md` v4.0.5 (255줄) 의 실 orchestrator 흐름을 narrative로 재기술한다. 구현 detail은 work.md + phase prompts + system-spec을 1차 source로 참조.*
