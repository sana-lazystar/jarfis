# JARFIS - IT Team Workflow Orchestration

사용자가 다음 기획을 요청했습니다: $ARGUMENTS

이 기획에 대해 아래 워크플로우를 자동 실행하세요.

---

## Phase T: Triage (요청 분류 — 워크플로우 진입 전 필수)

**이 단계는 Phase 0보다 먼저, 워크플로우 진입 여부를 판단하는 게이트이다.**

### 목표
사용자의 요청이 JARFIS 전체 워크플로우(Phase 0~6)에 적합한지 판단하고,
적합하지 않은 경우 사용자에게 대안을 제시하여 확인을 구한다.

### 분류 기준

사용자의 요청(`$ARGUMENTS` + 대화 컨텍스트)을 아래 3가지 유형으로 분류한다:

| 유형 | 판단 기준 | 예시 | 워크플로우 진입 |
|------|----------|------|---------------|
| **A. 신규 기획/기능 개발** | 새 기능 구현, 기존 기능 리팩토링, 시스템 설계가 필요한 작업 | "게시판 CRUD + 댓글", "결제 모듈 리팩토링" | ✅ Phase 0부터 정상 실행 |
| **B. 기존 작업의 부분 실행** | 이미 진행된 워크플로우의 특정 Phase만 필요한 작업 | "이미 구현한 작업 QA 검증해줘", "아키텍처 리뷰만 해줘" | ⚠️ 해당 Phase만 실행 (사용자 확인 후) |
| **C. 워크플로우 부적합** | 단순 질문, 디버깅, 설정 변경 등 워크플로우 구조에 맞지 않는 작업 | "이 에러 원인 찾아줘", "tsconfig 수정해줘" | ❌ 워크플로우 없이 직접 처리 (사용자 확인 후) |

### 실행 로직

1. $ARGUMENTS 분석 → 유형(A/B/C) 판단. `.jarfis-state.json` 존재 시 유형 B 가능성 높음.
2. 유형 A → Phase 0 자동 진행. 유형 B → AskUserQuestion (해당 Phase만/전체/직접 진행). 유형 C → AskUserQuestion (직접 진행 권장/전체 진행).

### 유형 B 매핑 가이드

| 요청 패턴 | 매핑 Phase |
|----------|-----------|
| QA, 테스트, 검증, 배포 전 확인 | Phase 5 (Review & QA) |
| 코드리뷰, 보안리뷰 | Phase 5 (Review & QA) |
| 설계 리뷰, 아키텍처 검토 | Phase 2 (Architecture & Planning) |
| UX 피드백, 화면 설계 수정 | Phase 3 (UX Design) |
| 추가 구현, 버그 수정 (기존 PRD 기반) | Phase 4 (Implementation) |
| 배포 전략, 롤백 계획 | Phase 4.5 (Operational Readiness) |

### 유형 B 브랜치 규칙
- 기존 작업의 연장인 경우, `develop`이 아닌 **원래 피처 브랜치**에서 분기 (`.jarfis-state.json`의 `branch` 필드 확인).
- `base_branch`를 `.jarfis-state.json`에 기록하여 분기 이력을 추적한다.

---

## Workflow Overview

```
Phase T: Triage → Phase 0: Pre-flight → Phase 1: Discovery 🔒
→ Phase 2&3: Architecture+UX (병렬) 🔒 → Phase 4: Implementation
→ Phase 4.5: Operational Readiness → Phase 5: Review & QA 🔒
→ Phase 6: Retrospective (자동)
```

## Artifacts (산출물 파일 경로)

### 산출물 디렉토리 규칙

산출물은 `$JARFIS_ORG_DIR/works/{YYYYMMDD}-{type}-{ticket-name}/` 디렉토리에 저장한다 (`$DOCS_DIR`).
> ※ `$JARFIS_ORG_DIR` 결정 규칙은 "Execution Rules > Org Dir Resolution" 참조.

- 워크플로우 시작 시 `$DOCS_DIR` 값을 결정하고, `.jarfis-state.json`의 `docs_dir` 필드에 **절대경로**로 저장한다.
- **프로젝트별 파일** (`project-profile.md`, `project-context.md`)은 각 프로젝트의 `.jarfis/`에 저장한다.

| Phase | File | Description | 조건부 |
|-------|------|-------------|--------|
| — | `$DOCS_DIR/.jarfis-state.json` | **워크플로우 상태 파일 (컨텍스트 유실 방어)** | 항상 |
| 1 | `$DOCS_DIR/press-release.md` | Working Backwards 가상 프레스 릴리스 + FAQ | 항상 |
| 1 | `$DOCS_DIR/prd.md` | PRD + 실현가능성 평가 + **필요 역할 판단** + **Performance Budget** | 항상 |
| 1 | `$DOCS_DIR/ux-direction.md` | UX 방향서 (IA, Tone & Voice, Pages + 인터랙션 패턴) | UX Designer 필요 시 |
| 2 | `$DOCS_DIR/impact-analysis.md` | 기존 코드베이스 영향 범위 분석 | 항상 |
| 2 | `$DOCS_DIR/architecture.md` | 시스템 아키텍처 설계서 + **ADR (Architecture Decision Records)** | 항상 |
| 2 | `$DOCS_DIR/api-spec.md` | API 명세서 (엔드포인트, 파라미터, 응답 스키마) | BE+FE 모두 필요 시 |
| 2 | `$DOCS_DIR/tasks.md` | 태스크 분해 (불필요 파트는 N/A) | 항상 |
| 2 | `$DOCS_DIR/test-strategy.md` | 테스트 전략 (테스트 피라미드, 시나리오, 성능 기준) | 항상 |
| 3 | `$DOCS_DIR/design/` | HTML 시안 디렉토리 (_index.html + URL별 시안) | FE + UX Designer 필요 시 |
| 4 | `$DOCS_DIR/infra-runbook.md` | 수동 인프라 설정 가이드 (AWS 등 클라우드 작업) | DevOps 실행 시 |
| 4.5 | `$DOCS_DIR/deployment-plan.md` | 배포 전략 + 롤백 계획 + 운영 준비도 체크리스트 | 항상 |
| 5 | `$DOCS_DIR/api-contract-check.md` | BE-FE API Contract 자동 검증 결과 | api-spec.md 존재 시 |
| 5 | `$DOCS_DIR/review.md` | 실행된 파트의 리뷰 결과만 포함 | 항상 |
| 5 | `$DOCS_DIR/diagnosis.md` | Root Cause 진단 + 수정 지시서 | 수정 후 재리뷰 시 |
| 6 | `$DOCS_DIR/retrospective.md` | 워크플로우 회고 (프로젝트별 기록) | 항상 |

### 학습 파일 경로

| 파일 | 위치 | 설명 |
|------|------|------|
| `learnings.md` | `$JARFIS_ORG_DIR/learnings.md` | **Org별** — Agent Hints + Workflow Patterns |
| `project-context.md` | `./.jarfis/project-context.md` | **프로젝트별** — 이 코드베이스 고유 지식 |

---

## Phase 0: Pre-flight (학습 파일 로드)

### 목표
이전 워크플로우에서 축적된 학습과 프로젝트 컨텍스트를 로드하여 에이전트 품질을 높인다.

### 실행 순서

0. **Locale Detection + 작업물명 입력 + Git 브랜치 설정**

   **0-a-0. Locale Detection (최선두)**

   사용자 대면 출력 언어를 결정한다. JARFIS 내부 추론/지시는 항상 English.

   1. `.jarfis-state.json`이 이미 존재하고 `locale` 필드가 있으면 → 그 값을 `$LOCALE`로 사용
   2. 아직 없으면 (새 워크플로우) → `$ARGUMENTS`의 텍스트에서 언어를 규칙 기반으로 감지:
      - 한글 문자(U+AC00~U+D7AF)가 1자 이상 포함 → `$LOCALE = "ko"`
      - 일본어 문자(히라가나 U+3040~U+309F 또는 가타카나 U+30A0~U+30FF)가 1자 이상 포함 → `$LOCALE = "ja"`
      - 위 두 경우 모두 아닌 경우 → `$LOCALE = "en"`
   3. 감지된 `$LOCALE`을 `.jarfis-state.json` 초기화 후 기록 (Step 0-a에서 state init 이후):
      ```bash
      python3 ~/.claude/scripts/jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "locale" "$LOCALE"
      ```
   4. `$LOCALE`은 이후 모든 Phase에서 에이전트의 응답 언어를 제어하는 데 사용된다.
      에이전트에게 프롬프트를 전달할 때 다음 지시를 포함:
      `"Present ALL user-facing output in $LOCALE language."`

   > **기본값**: `$LOCALE`이 결정되지 않으면 `"ko"` (기존 동작과 동일)
   > **오버라이드**: `/jarfis:locale-set <code>`로 워크플로우 중 언제든 변경 가능

   **0-a. 작업물명 입력**
   - AskUserQuestion으로 작업물명(`$WORK_INPUT`)을 입력받는다 (예: `feat/TICKET-123`, `fix/BUG-456`).
   - `$WORK_DIR_NAME` = `{YYYYMMDD}-{$WORK_INPUT의 / → - 변환}` (예: `20260311-feat-TICKET-123`)
   - `$BRANCH` = `$WORK_INPUT` (Git 브랜치명은 원본 유지, 예: `feat/TICKET-123`)
   - `$DOCS_DIR` = `$JARFIS_ORG_DIR/works/$WORK_DIR_NAME` (절대경로). 디렉토리 생성 후 상태 초기화:
     ```bash
     python3 ~/.claude/scripts/jarfis_cli.py state init "$DOCS_DIR/.jarfis-state.json" "$PROJECT_NAME" "$WORK_DIR_NAME" "$DOCS_DIR"
     ```
   - 상태 파일에 원본 입력값 보존: `jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "work_input" "$WORK_INPUT"`
   - 브랜치명 기록: `jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "branch" "$BRANCH"`
   > ※ `$JARFIS_ORG_DIR` 결정 규칙은 "Execution Rules > Org Dir Resolution" 참조.

   **0-a-2. Meeting 선택 (시맨틱 검색 + fallback)**
   - **시맨틱 검색 우선**: `$ARGUMENTS`의 기획 내용으로 관련 미팅을 시맨틱 검색한다:
     ```bash
     python3 ~/.claude/scripts/jarfis_cli.py search meetings "$ARGUMENTS" --top-k 3
     ```
     - 결과가 있으면 (results 비어있지 않음) → AskUserQuestion으로 추천 표시:
       - 각 결과를 Option으로 변환: `[{source}] {file_path} (score: {score})`
       - 마지막 Option: `관련 미팅 없음`
     - 결과가 없거나 검색 실패 시 (메모리 부족 포함) → 사용자에게 표시: `⚠️ 시맨틱 검색을 사용할 수 없습니다 (메모리 부족 또는 미설치). LLM 기반 검색으로 대체합니다.` → **fallback**으로 최근 미팅 목록:
       ```bash
       python3 ~/.claude/scripts/jarfis_cli.py meetings 3
       ```
       - JSON 결과가 빈 배열이 아니면 → AskUserQuestion: `[{date}] {name} - {summary}` + `관련 미팅 없음`
       - 빈 배열이면 → 미팅 선택 스킵
   - `$ARGUMENTS`에 `--meeting {기획명}` 플래그가 있으면 → 스크립트 결과에서 해당 기획명과 매칭하여 자동 선택 (AskUserQuestion 스킵)

   **0-a-3. Meeting 컨텍스트 로드**
   - 미팅이 선택되면: `$MEETING_PATH` = `$JARFIS_ORG_DIR/{선택된 미팅 path}/`
     - `jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "source_meeting" "{선택된 미팅 디렉토리명}"`

     **알려진 파일 → 기존 변수 매핑** (존재하는 파일만):
     - `summary.md` → `$MEETING_SUMMARY`
     - `decisions.md` → `$MEETING_DECISIONS`
     - `meeting-notes.md` → `$MEETING_NOTES`
     - `tech-research.md` → `$MEETING_RESEARCH`

     **추가 파일 동적 스캔** → `$MEETING_EXTRA`:
     - `$MEETING_PATH` 내 모든 `.md` 파일을 Glob으로 스캔
     - 위 4개 알려진 파일과 숨김 파일(`.`으로 시작)을 제외한 나머지를 수집
     - 각 파일을 `## [파일명]` 헤더와 함께 `$MEETING_EXTRA`에 연결
     - **상한**: 추가 파일 합계 200줄 초과 시 truncate하고 `(... 이하 생략 — 원본: $MEETING_PATH/{파일명})` 안내
     - 추가 파일이 없으면 `$MEETING_EXTRA` = 빈 문자열

   - 미팅 없음 선택 시: `source_meeting` = `null`, 모든 `$MEETING_*` 변수 = 빈 문자열

   **0-a-4. Workspace Detection (프로젝트 구조 확인)**

   AskUserQuestion으로 프로젝트 구조를 확인하고 `.jarfis-state.json`의 `workspace` 필드를 즉시 기록한다.

   | 선택 | workspace.type | BE path | FE path | 비고 |
   |------|---------------|---------|---------|------|
   | Monorepo | monorepo | `.` | `.` | CWD가 git repo 아니면 경로 입력 |
   | Multi-project | multi-project | 입력 | 입력 | 각 경로 유효성 검증 |
   | FE만 | monorepo | `N/A` | `.` 또는 입력 | — |
   | BE만 | monorepo | `.` 또는 입력 | `N/A` | — |

   - 각 경로에서 프레임워크 자동 감지 스크립트 실행:
     ```bash
     python3 ~/.claude/scripts/jarfis_cli.py detect "$PROJECT_PATH"
     ```
     JSON 출력의 `frameworks`, `languages`, `project_type`을 활용하여 workspace 정보를 `.jarfis-state.json`에 기록한다.
   - `$BACKEND_PROJECT_DIR`, `$FRONTEND_PROJECT_DIR` 변수 설정 (`N/A`이면 빈 문자열)

   **0-a-5. Domain 감지** (v3.0)

   각 프로젝트 경로에서 Domain Pack을 감지한다:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py domain detect "$PROJECT_PATH"
   ```
   - 결과 JSON의 `matches[0].domain`을 `$DOMAIN`으로 설정
   - `tie`=true → AskUserQuestion으로 사용자에게 도메인 선택
   - 감지 실패(exit code != 0, 빈 matches) → `$DOMAIN` = `null`
   - `.jarfis-state.json`에 기록: `jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "domain" "$DOMAIN"`
   > ※ domain이 null이면 Phase 4에서 기존 하드코딩 방식으로 fallback

   **0-b. Git 브랜치 동기화 및 생성**

   - **monorepo**: git repo 확인 → uncommitted 경고 → 기본 브랜치+develop pull → `git checkout -b $BRANCH develop` → `.jarfis-state.json` `branch` 기록. develop 없으면 기본 브랜치에서 분기 여부 확인.
   - **multi-project**: BE/FE 각 경로에서 독립적으로 동일 과정 반복. `.jarfis-state.json`에 `branches: { backend, frontend }` 기록.

1. **시스템 헬스체크** — `~/.claude/scripts/claude-cleanup.sh` 존재 시 진단 모드 실행. 좀비 5개↑ → AskUserQuestion, 1~4개 → 경고, 0개 → 무시.
2. **Pre-flight 검증** — 스크립트로 프로필/학습/컨텍스트/Org 존재 여부를 한번에 확인:
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py preflight --check-meetings
   ```
   JSON 출력의 `has_learnings`, `has_context`, `has_profile`, `org_root`, `has_wiki`, `warnings`를 확인하여:
   - `has_learnings`=true → `learnings_path`에서 `$LEARNINGS` 로드
   - `has_context`=true → `context_path`에서 `$PROJECT_CONTEXT` 로드
   - `has_profile`=true → `profile_path`에서 프로필 로드
   - `org_root` non-null → `$ORG_ROOT` 변수 설정. `org_name`으로 Org 이름 확인. `org_auto_registered`=true이면 "Org '{org_name}' 자동 등록됨" 출력
   - `warnings` 배열이 비어있지 않으면 사용자에게 경고 표시
   - 없는 파일은 빈 문자열로 치환

   **2-1. 미완료 워크플로우 감지** (Org 등록된 경우 — `$ORG_ROOT` 존재 시)
   - `jarfis_cli.py state list-workflows` 실행 (전체 Org 워크스페이스 자동 스캔)
   - `status != "completed"` 워크플로우가 존재하면:
     - 미완료 워크플로우 목록과 `key_decisions` 표시
     - AskUserQuestion: "미완료 워크플로우가 있습니다. wiki에 미반영된 결정이 있을 수 있습니다." (계속 진행 / 확인 후 진행)

   **2-2. Wiki 4-Step 로딩** (Org 등록된 경우 — `$ORG_ROOT` 존재 + `has_wiki`=true)
   > 📄 프롬프트: `prompts/wiki-loading.md`의 "4-Step 전체 로딩" 절차를 실행한다.
   - INDEX.md → 4개 _index.md → 관련 파일 최대 5개 읽기
   - 읽은 wiki 내용을 `$WIKI_CONTEXT`로 저장

   **2-3. Cascading Specificity 규칙 주입**
   - Org 등록 시 모든 에이전트 프롬프트에 다음 규칙을 주입한다:
   > 정보 우선순위: $DOCS_DIR > project/.jarfis > wiki/ > INDEX.md
   > 이번 태스크가 다루는 주제: $DOCS_DIR 우선. 안 다루는 주제: wiki 유효.
3. 프로젝트 프로필 로드: `$BACKEND_PROJECT_DIR/.jarfis/project-profile.md` + `$FRONTEND_PROJECT_DIR/.jarfis/project-profile.md` (Phase 4~5) → `$BE_PROJECT_PROFILE`, `$FE_PROJECT_PROFILE`

**주입 규칙:**
- Phase 1 (PO, Architect): `$LEARNINGS`의 Workflow Patterns + `$PROJECT_CONTEXT` 전체 + `$WIKI_CONTEXT` (Org 등록 시)
- Phase 2 (Architect — Impact Analysis, 설계): `$BE_PROJECT_PROFILE` + `$FE_PROJECT_PROFILE` (존재 시) + `$WIKI_CONTEXT` (Org 등록 시)
- Phase 4 (BE/FE/DevOps): `$DOMAIN` 설정 시 `domain compose`가 Skills+Rules를 합성하여 주입. 미설정 시 `$LEARNINGS`의 해당 역할 Agent Hints + `$PROJECT_CONTEXT` 전체 + **해당 역할의 `$PROJECT_PROFILE`**
- Phase 5 (Tech Lead/QA/Security): `$LEARNINGS`의 해당 역할 Agent Hints
- **Cascading Specificity**: Org 등록 시 모든 Phase에 우선순위 규칙 주입

학습/프로필 파일이 없으면 빈 문자열로 치환한다.

---

## Phase 1: Discovery

### 목표
사용자의 기획 의도를 명확히 하고, 기술적 실현가능성을 동시에 검증한다.

### 실행 순서

**Step 1-0: PO Wiki 참조** (Org 등록 시)
- PO에게 PO/ wiki 컨텍스트를 주입한다: domain-map.md, policies/, business-rules/ 등
- 기존 정책/규칙과 일관성을 유지하도록 가이드

> 📄 프롬프트: `prompts/phase1.md` Step 1-0 섹션을 읽어서 에이전트에 전달한다.
> Org 미등록 시 이 Step은 스킵한다.

**Step 1-1: PO 역질문** (senior-product-owner)

> **미팅 참조 시 조건부 동작**: `$MEETING_REF`가 존재하면, 미팅 컨텍스트(`$MEETING_SUMMARY`, `$MEETING_DECISIONS`, `$MEETING_NOTES`, `$MEETING_RESEARCH` + 동적 스캔 `$MEETING_EXTRA`)를 주입하고 미결 사항만 질문한다.

> 📄 프롬프트: `prompts/phase1.md` 해당 섹션을 읽어서 에이전트에 전달한다.

> 사용자가 역질문에 답변하면 다음 단계로 진행

**Step 1-1.5: Working Backwards Document** (senior-product-owner)
> 📄 프롬프트: `prompts/phase1.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 1-2: PRD 작성 + 실현가능성 평가** (병렬 실행)

PO (senior-product-owner):
> 📄 프롬프트: `prompts/phase1.md` 해당 섹션을 읽어서 에이전트에 전달한다.

Architect (technical-architect):
> 📄 프롬프트: `prompts/phase1.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 1-2.5: PRD Completeness Check — Ratchet** (오케스트레이터 직접 실행 — 에이전트 아님)

> 📄 프롬프트: `prompts/phase1.md` Step 1-2.5 섹션을 읽어서 오케스트레이터가 직접 실행한다.
> PRD를 5개 항목별 Pass/Fail + 점수(0-2)로 채점하고, 래칫 규칙을 적용한다.

**채점 기준** (각 항목 0-2점, 총 10점):

| 항목 | 0점 (Fail) | 1점 (Fail) | 2점 (Pass) |
|------|-----------|-----------|-----------|
| 모호 표현 | "적절한/빠른/충분한" 등 3개+ | 1-2개 남음 | 모두 구체적 수치로 전환됨 |
| KPI 측정 가능성 | KPI 없거나 정성적 | 숫자 있으나 측정 방법 미명시 | 숫자 + 측정 방법 모두 명시 |
| Performance Budget | 미정의 | 일부 지표만 수치화 | 모든 지표에 숫자 + 측정 방법 |
| Required Roles 근거 | 근거 없음 | 일부 역할만 근거 제시 | 모든 역할에 1문장+ 근거 |
| 스코프 경계 | Out of Scope 미정의 | 포함 범위만 정의 | 포함 + 제외 범위 모두 명시 |

> ⚠️ **불변 평가자 원칙**: 위 채점 기준은 오케스트레이터 전용이다. PO 에이전트 프롬프트에는 이 기준을 포함하지 않는다.

**래칫 로직**:
1. PRD 최초 생성 시 → 5개 항목 채점 → 항목별 Pass(2점)/Fail(0-1점) 상태 + 총점 기록
2. 5개 항목 모두 Pass → Gate 1로 진행
3. Fail 항목 존재 → PO에게 Fail 항목 + 현재 점수 전달, 해당 항목만 재작성 지시
4. PO 재작성 후 재채점:
   - **래칫 검증**: 이전에 Pass였던 항목이 Fail로 변했는지 확인
   - 래칫 위반 없음 → 결과 반영, 남은 횟수 내 재시도
   - **래칫 위반 발생** → PO에게 경고: "이전에 통과했던 [항목명]이 미통과로 변경됨. 해당 항목의 품질을 유지하면서 Fail 항목만 개선하라" 재지시
5. 최대 2회 시도 후에도 Fail 항목 존재 → Gate 1에 "PRD Score: X/10, Fail 항목: [목록]" 표시하고 사용자 판단

**상태 기록** (`.jarfis-state.json`):
```
jarfis_cli.py state set-nested phases.1.ratchet '{
  "prd_score": <총점>,
  "items": {"ambiguity": <0-2>, "kpi": <0-2>, "perf_budget": <0-2>, "roles_rationale": <0-2>, "scope_boundary": <0-2>},
  "passed_items": ["<Pass된 항목 목록>"],
  "attempts": <시도 횟수>,
  "history": [{"score": <N>, "passed": ["<항목>"], "action": "accept|ratchet_violation"}]
}'
```

### 🔒 게이트 1: 사용자 컨펌
산출물(`press-release.md`, `prd.md`) 요약 + **PRD Completeness Score** 를 표시한 후 AskUserQuestion:
```
question: "Phase 1 산출물을 확인하세요. PRD Score: {X}/10 (Pass: {N}/5). 어떻게 진행할까요?"
header: "Gate 1"
options:
  - label: "승인 — 다음 Phase로 진행"
    description: "PRD + Working Backwards 문서가 충분합니다"
  - label: "수정 요청"
    description: "피드백을 반영하여 PO가 재작성합니다"
  - label: "중단"
    description: "워크플로우를 즉시 종료합니다"
```

**Step 1-3: PO 추가 태스크** (Gate 1 승인 후, senior-product-owner)

> Gate 1 통과 후, PO가 추가 태스크를 선택적으로 실행한다.

**Step 1-3-pre: 디자이너 유무 확인** (Required Roles에서 UX Designer ✅일 때만)

> PRD에서 UX Designer가 필요로 판단된 경우, 팀 내 디자이너 존재 여부를 확인한다.

AskUserQuestion:
```
question: "팀에 UX 디자이너가 있나요?"
header: "Design Path"
options:
  - label: "예 — Figma 디자인이 있습니다"
    description: "디자이너가 Figma로 전달한 디자인 시안이 있습니다"
  - label: "아니오 — AI 에이전트가 디자인합니다"
    description: "UX Designer 에이전트가 ux-direction.md 기반으로 직접 디자인합니다"
```

- "예" 선택 시:
  - `.jarfis-state.json`에 `phases.3.has_designer: true` 기록
  - AskUserQuestion으로 Figma 페이지 목록 입력:
    ```
    question: "Figma 페이지 URL을 JSON 배열로 입력해주세요.\n예: [{\"title\": \"혜택 소개\", \"url\": \"https://figma.com/design/...?node-id=123-456\"}, ...]"
    header: "Figma Pages"
    ```
  - 입력된 JSON 배열을 `.jarfis-state.json`에 `phases.3.figma_pages` 저장
  - `phases.3.mode: "figma"` 기록
  - 페이지 5개 초과 시 경고: "5개 이상의 페이지는 토큰 소비가 많습니다. 우선순위 기준으로 축소를 권장합니다."

- "아니오" 선택 시:
  - `.jarfis-state.json`에 `phases.3.has_designer: false`, `phases.3.mode: "text"` 기록
  - `phases.3.figma_pages: []` 기록

> PRD에서 UX Designer가 ⬜ 불필요이면 이 Step을 스킵하고 `has_designer: null` 유지.

AskUserQuestion:
```
question: "PO 추가 태스크를 선택하세요 (복수 선택 가능)"
header: "PO Tasks"
multiSelect: true
options:
  - label: "법무/컴플라이언스 체크"
    description: "개인정보 수집/처리, 약관/결제/환불, 산업별 규제, GDPR 관련 확인"
  - label: "UX 방향서 작성"
    description: "ux-direction.md 작성 (UX Designer 필요 시 — IA, Tone, Pages 일괄)"
```

- **법무/컴플라이언스**: PO가 PRD 기반으로 법적 고려사항을 prd.md에 추가
- **UX 방향서**: PO가 `templates/ux-direction.md` 참조하여 `$DOCS_DIR/ux-direction.md` 작성. 인터랙션 패턴 필수 포함.

**반응형 범위 설정** (FE 필요 시 — Required Roles에서 Frontend ✅인 경우):
AskUserQuestion:
```
question: "반응형 범위를 선택하세요"
header: "Responsive"
options:
  - label: "PC만"
    description: "데스크톱 뷰포트만 지원"
  - label: "PC + Mobile"
    description: "데스크톱 + 모바일 (FE 공수 ~1.3x)"
  - label: "PC + Mobile + Tablet"
    description: "데스크톱 + 모바일 + 태블릿 (FE 공수 ~1.5x)"
```
선택 결과를 `.jarfis-state.json`에 `responsive` 필드로 기록한다.

> 📄 프롬프트: `prompts/phase1.md` Step 1-3 섹션을 읽어서 에이전트에 전달한다.
> 선택 없으면 이 Step은 스킵한다.

---

## Phase 2: Architecture & Planning + Phase 3: UX Design (병렬)

Phase 2와 Phase 3은 동시에 진행한다.

### Phase 2: Architecture & Planning

**Step 2-(-1): TA/QA Wiki 참조** (Org 등록 시)
- TA: TA/ wiki에서 decisions/, api-contracts/, data-models/ 확인
- QA: QA/ wiki에서 test-standards.md, regression-checklist.md 확인
> 📄 프롬프트: `prompts/phase2.md` Step 2-(-1) 섹션을 읽어서 에이전트에 전달한다.
> Org 미등록 시 이 Step은 스킵한다.

**Step 2-0: Impact Analysis** (technical-architect)
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 2-1: 시스템 아키텍처 설계** (technical-architect)
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 2-1.5: API 명세 작성** (technical-architect → tech-lead 순차) — **BE+FE 모두 필요 시만 실행**

> **실행 조건**: PRD의 'Required Roles'에서 Backend Engineer와 Frontend Engineer가 **모두 ✅ 필요**인 경우에만 실행한다.

Architect (technical-architect):
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

Tech Lead (tech-lead) — api-spec.md 리뷰:
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 2-2: 태스크 분해** (tech-lead)
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 2-3: 테스트 전략 수립** (senior-qa-engineer)
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

### Phase 3: UX Design (조건부 실행 — FE 포함 + UX Designer 필요 시만)

> **스킵 조건**: PRD 'Required Roles'에서 Frontend Engineer가 '⬜ 불필요'이거나 UX Designer가 '⬜ 불필요'이면 Phase 3 전체를 건너뛴다.
> Phase 2와 **병렬** 실행한다 (의도적 병렬).

**Step 3-(-2): MCP 도구 가용성 체크** (오케스트레이터)

> Phase 3 실행에 필요한 MCP 서버가 설치되어 있는지 확인한다.
> `.jarfis-state.json`의 `phases.3.mode`에 따라 필요 도구가 다르다.

```
mode === "figma" 필요 도구:
  [필수] Framelink (get_figma_data, download_figma_images) — Figma 데이터 추출/에셋 다운로드
  [필수] Playwright (browser_navigate, browser_take_screenshot 등) — 스크린샷 촬영/검증
  [권장] mcp-design-comparison (compare_design) — pixel-diff 수치 비교

mode === "text" 필요 도구:
  [필수] Playwright — reference.png 생성 + Phase 5 UX Review 스크린샷
  [권장] mcp-design-comparison — Phase 5 pixel-diff 비교
```

체크 방법: 각 MCP 도구를 가볍게 호출 시도하여 응답 여부로 판단.
- Framelink: `get_figma_data` 도구 존재 확인
- Playwright: `browser_take_screenshot` 도구 존재 확인
- compare_design: `compare_design` 도구 존재 확인

누락 시 처리:
- **필수 도구 누락** → 설치 안내 메시지 표시 + AskUserQuestion:
  ```
  question: "Phase 3에 필요한 MCP 서버가 누락되었습니다:\n- {누락 목록}\n\n설치 후 계속하시겠어요?"
  header: "MCP Check"
  options:
    - label: "설치 완료 — 계속 진행"
      description: "MCP 서버를 설치한 후 이 옵션을 선택하세요"
    - label: "없이 진행 (비권장)"
      description: "해당 기능이 제한됩니다 (Figma 추출 불가 등)"
  ```
- **권장 도구(compare_design) 누락** → 경고만 표시, 자동 진행:
  "⚠️ mcp-design-comparison이 없습니다. pixel-diff 수치 비교 대신 시각적 비교로 폴백합니다."

**Step 3-(-1): 기존 시안 가져오기** (오케스트레이터)
- Org 등록 시: `wiki/DESIGN/pages/{project}/` → `$DOCS_DIR/design/` 복사
- 기존 시안이 없으면 빈 `$DOCS_DIR/design/` 디렉토리 생성

#### 🔀 분기: 디자이너 유무에 따른 경로 선택

> `.jarfis-state.json`의 `phases.3.has_designer`와 `phases.3.mode`로 경로를 결정한다.
> 이 값은 Phase 1 Step 1-3-pre에서 이미 설정되어 있다.

`phases.3.mode === "figma"` (디자이너 있음, Figma 제공) → **Figma-Driven Path** (Step 3-F0~3-F4)
- `phases.3.figma_pages` 배열의 **각 페이지를 병렬로** 3-F0~3-F3 실행
- 각 페이지별 독립 디렉토리: `design/{title의 kebab-case}/` (예: `design/benefits-signup/`)
- 3-F4 리뷰는 전체 페이지를 한번에 수행

`phases.3.mode === "text"` (디자이너 없음) → **텍스트 경로** (Step 3-0~3-1, 기존)

> 📄 Figma-Driven Path 프롬프트: `prompts/phase3-figma.md` 전체를 읽어서 순서대로 실행한다.

**[텍스트 경로] Step 3-0: HTML 시안 제작/수정** (senior-ux-designer)
- `$DOCS_DIR/ux-direction.md` 기반으로 HTML 시안 제작
- URL → 파일 매핑: `/{path}` → `$DOCS_DIR/design/{path}/index.html` 또는 `{path}.html`
- 각 HTML 파일 상단에 `templates/design-html-meta.md` 메타 주석 삽입
- `$DOCS_DIR/design/_index.html` 자동 생성 (전체 시안 목차)
> 📄 프롬프트: `prompts/phase2.md` Step 3-0 섹션을 읽어서 에이전트에 전달한다.

**[텍스트 경로] Step 3-1: PO ↔ Designer 피드백 루프** (최대 3회)
1. PO (senior-product-owner): 시안 검토, PRD 대비 누락/불일치 피드백
2. Designer (senior-ux-designer): 피드백 반영하여 시안 수정
3. 3회 반복 후에도 미해결 시 → 사용자 Gate로 넘김
> 📄 프롬프트: `prompts/phase2.md` Step 3-1 섹션을 읽어서 에이전트에 전달한다.

**사용자 Gate**: `open $DOCS_DIR/design/_index.html`로 브라우저에서 시안을 열고, AskUserQuestion:
```
question: "HTML 시안을 확인하셨나요? 어떻게 진행할까요?"
header: "UX Gate"
options:
  - label: "승인 — 시안 확정"
    description: "시안이 PRD/ux-direction.md와 일치합니다"
  - label: "수정 요청"
    description: "피드백을 입력하면 Designer가 수정합니다"
  - label: "Phase 2 완료 후 재검토"
    description: "아키텍처 설계와 함께 다시 확인합니다"
```

**[텍스트 경로] Step 3-2: reference.png 생성** (승인 시 자동 실행)

> 시안 승인 후, Phase 5 UX Review에서 비교 기준으로 사용할 reference.png를 생성한다.
> Figma Path의 reference.png와 이름을 통일하여, Phase 4/5에서 경로 분기 없이 동일하게 참조 가능.

```
각 design/{path}/index.html에 대해:
1. Playwright MCP로 HTML 스크린샷 촬영 (fullPage: true, DPR: 2)
2. design/{path}/reference.png로 저장
```

### 🔒 게이트 2: 사용자 컨펌
산출물(`impact-analysis.md`, `architecture.md`, `api-spec.md`, `tasks.md`, `test-strategy.md`, `design/`) 요약 + 실행 파트를 표시한 후 AskUserQuestion:
```
question: "Phase 2&3 산출물을 확인하세요. 어떻게 진행할까요?"
header: "Gate 2"
options:
  - label: "승인 — 구현 Phase로 진행"
    description: "설계 + 태스크 분해가 충분합니다"
  - label: "수정 요청"
    description: "피드백을 반영하여 해당 에이전트가 재작성합니다"
  - label: "중단"
    description: "워크플로우를 즉시 종료합니다"
```

---

## Phase 4: Implementation

### 목표
설계 문서를 기반으로 병렬 구현한다. 구현 전 Security가 사전 리뷰한다.
> ※ 스킵 판단: "Execution Rules > Skip Rules" 참조

### 실행 순서

**Step 4-0: 보안 사전 리뷰** (senior-security-engineer)
> 📄 프롬프트: `prompts/phase4.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 4-0.5: 테스트 선행 작성 (TDD Red Phase)** (senior-qa-engineer) — **조건부**
> 실행 조건: `$DOCS_DIR/test-strategy.md` 존재 + P0 테스트 시나리오 3개 이상 + 프로젝트에 단위 테스트 프레임워크 존재.
> 활성화 시 `.jarfis-state.json`에 `phases.4.tdd_enabled: true` 기록.
> 스킵 시 `phases.4.tdd_enabled: false` 기록.
> 📄 프롬프트: `prompts/phase4.md` Step 4-0.5 섹션을 읽어서 에이전트에 전달한다.

**Step 4-0.5a: TDD Baseline 기록** (오케스트레이터 직접 실행, `tdd_enabled: true`일 때만)

> Step 4-0.5 완료 직후, 오케스트레이터가 전체 테스트를 실행하여 baseline을 기록한다.
> 구현 에이전트에게 "테스트 실행 후 passed/failed/total을 보고하라" 지시하여 결과를 받는다.
> 프레임워크 독립: 테스트 러너 명령어는 project-profile의 scripts 섹션에서 추출한다.

```
jarfis_cli.py state set-nested "$DOCS_DIR/.jarfis-state.json" "ratchet.phase4_tests" '{
  "baseline_pass_rate": <passed/total>,
  "test_command": "<project-profile에서 추출한 테스트 명령어>",
  "task_index": 0,
  "test_modifications": [],
  "history": []
}'
```

**Step 4-1: 병렬 구현 — Ratchet Loop** (tasks.md에 태스크가 있는 파트만 동시 실행)
> Step 4-0.5에서 TDD가 활성화된 경우, 각 구현 에이전트에게 TDD Green Phase 블록이 추가된다.
> 📄 프롬프트: `prompts/phase4.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**에이전트 매핑 분기** (v3.0):

`$DOMAIN`이 null이 아닌 경우 (domain.yaml 기반):
1. `jarfis_cli.py domain agents "$DOMAIN" implement` → 역할 목록 JSON 로드
2. domain.yaml의 `hooks.phase4.before`가 있으면 해당 파일을 읽어 사전 컨텍스트로 제공
3. 각 역할에 대해:
   a. `jarfis_cli.py domain compose "$DOMAIN" "$ROLE_NAME"` 호출
   b. 반환된 `{agent_type, prompt_content}`로 Agent 도구 호출 (model은 역할의 model 필드)
   c. 자동 커밋 (commit_prefix 사용: `jarfis({PREFIX}-{N}):`)
4. domain.yaml의 `hooks.phase4.after`가 있으면 실행
5. 래칫 체크: domain.yaml의 `pipeline.test.runner`로 테스트 실행

`$DOMAIN`이 null인 경우 (기존 방식 — fallback):
- 아래 하드코딩 에이전트 매핑으로 실행

Backend (senior-backend-engineer), Frontend (senior-frontend-engineer), DevOps (senior-devops-sre-engineer):
> 📄 프롬프트: `prompts/phase4.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**TDD 래칫 규칙** (`tdd_enabled: true`일 때, 오케스트레이터가 각 태스크 완료 후 실행):

1. 구현 에이전트가 태스크 완료 + git commit 후
2. 오케스트레이터: 에이전트에게 "전체 테스트 실행 → passed/failed/total 숫자 보고" 지시
3. current_pass_rate = passed / total
4. **래칫 판정**:
   - current_pass_rate >= baseline_pass_rate → **ACCEPT**
     - baseline_pass_rate = current_pass_rate (갱신)
     - ratchet.phase4_tests.task_index 증가
     - history에 `{"task": "BE-N", "pass_rate": X, "action": "accept"}` 추가
   - current_pass_rate < baseline_pass_rate → **REJECT**
     - `git stash`로 변경사항 저장
     - 에이전트에게: "태스크 구현이 기존 테스트 N개를 깨뜨림. 깨진 테스트: [목록]. `git stash pop`으로 코드를 복원한 뒤, 기존 테스트를 통과하면서 태스크를 구현하라." 재지시
     - 재시도 (태스크당 **최대 2회**)
     - history에 `{"task": "BE-N", "pass_rate": X, "action": "reject", "attempt": N}` 추가
5. 2회 재시도 후에도 실패 → `git stash pop`으로 원복 → 경고 기록 → 다음 태스크로 진행
   - history에 `{"task": "BE-N", "pass_rate": X, "action": "skipped_after_max_retries"}` 추가
   - Phase 5에서 해당 태스크를 진단 대상으로 플래그

**테스트 파일 수정 감지** (오케스트레이터):
- 각 태스크 커밋에서 `tests/`, `__tests__/`, `*.test.*`, `*.spec.*` 경로의 파일 수정 여부 확인
- 수정 감지 시: `ratchet.phase4_tests.test_modifications`에 `{"file": "<경로>", "task": "BE-N", "reason": "<커밋 메시지>"}` 추가
- Phase 5 QA 리뷰에서 해당 수정의 타당성 사후 검증 대상으로 플래그

> ⚠️ **Anti-pattern**: Phase 4 전체를 반복하거나, 태스크당 2회를 초과하여 재시도하지 않는다. 해결 불가 시 Phase 5에서 진단한다.

---

## Phase 4.5: Operational Readiness

### 목표
구현 완료 후 프로덕션 투입 전, 배포 전략과 운영 준비 상태를 점검한다.

### 실행 순서

**Step 4.5-1: 배포 전략 + 운영 준비도** (tech-lead)
> 📄 프롬프트: `prompts/phase4-5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

---

## Phase 5: Review & QA

### 목표
**Phase 4에서 실제로 실행된 파트의 코드만** 코드리뷰, QA, 보안리뷰를 수행한다.
> ※ 스킵 판단: "Execution Rules > Skip Rules" 참조

### 실행 순서

**Step 5-0: API Contract 자동 검증** — **api-spec.md 존재 시만 실행**

Tech Lead (tech-lead):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 5-1: 병렬 리뷰** (3~4개 에이전트 동시 실행)

Tech Lead (tech-lead), QA (senior-qa-engineer), Security (senior-security-engineer):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

UX Designer (senior-ux-designer) — **FE 포함 + UX Designer required 시만 참여**:
> **사전 조건**: dev 서버 URL이 필요하다. AskUserQuestion으로 사용자에게 요청:
> ```
> question: "UX Design Review를 위해 dev 서버 URL을 알려주세요 (예: http://localhost:3000)"
> header: "Dev Server"
> ```
> 사용자가 URL을 제공하면 `$DEV_SERVER_URL`로 저장하고, `.jarfis-state.json`에 `dev_server_url` 필드로 기록한다.
> 📄 프롬프트: `prompts/phase5.md` UX Design Review 섹션을 읽어서 에이전트에 전달한다.
> playwright로 HTML 시안 vs FE 구현물 시각적 비교 수행

**결과 통합**: 실행된 에이전트의 리뷰 결과만 `$DOCS_DIR/review.md`에 통합 저장한다.

### 🔒 게이트 3: 최종 컨펌

> **병리 패턴 감지 (2회차 이상 재리뷰 시)**: `prompts/phase5.md`의 "Step 5-2 병리 패턴 감지" 절차 실행.

리뷰 결과 요약 (코드리뷰/API Contract/QA/보안/배포/UX Design Review)을 표시한 후 AskUserQuestion:
```
question: "Phase 5 리뷰 결과를 확인하세요. 어떻게 진행할까요?"
header: "Gate 3"
options:
  - label: "승인 — 회고 Phase로 진행"
    description: "리뷰 이슈가 없거나 수용 가능합니다"
  - label: "수정 후 재리뷰"
    description: "이슈를 수정하고 Step 5-0부터 재실행합니다"
  - label: "중단"
    description: "워크플로우를 즉시 종료합니다"
```
> 병리 패턴이 감지되면 4번째 옵션 추가: `"Phase 2 설계 재검토" — "반복 수정으로 해결 불가, 설계부터 재검토"`

### Step 5-2: Root Cause Diagnosis (게이트 3에서 "수정 후 재리뷰" 선택 시)

Tech Lead (tech-lead):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

### Step 5-3: Fix Implementation (진단 기반 수정)

diagnosis.md의 수정 지시서 기반, 담당 에이전트(BE/FE/DevOps) 실행. P0 우선 수정 + 회귀 방지 테스트.

Backend/Frontend (해당 수정 지시가 있을 때만):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

> 수정 완료 후 Step 5-0 ~ Step 5-1 → 게이트 3를 **재실행**한다.

---

## Phase 6: Retrospective (자동 실행)

### 목표
이번 워크플로우에서 얻은 학습을 **전역 학습 파일**과 **프로젝트 컨텍스트 파일**에 축적하고, Org 등록 시 **wiki를 갱신**한다.

### 실행 순서 (순차: 학습 추출 먼저 → wiki 갱신 나중)

**Step 6-1: 회고 작성** (tech-lead)
> 📄 프롬프트: `prompts/phase6.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 6-2: 학습 파일 업데이트** (오케스트레이터가 직접 실행)

retrospective.md를 읽고 다음 두 파일에 분배 저장한다:

**1. 전역 학습 — `$JARFIS_ORG_DIR/learnings.md`**
> 📄 템플릿: `templates/learnings.md`를 읽어서 산출물 양식으로 사용한다.

관리 규칙: 기존 파일에 추가 (중복이면 업데이트), 오래된 항목 제거, 날짜 기록

**2. 프로젝트 컨텍스트 — `./.jarfis/project-context.md`**
> 📄 템플릿: `templates/project-context.md`를 읽어서 산출물 양식으로 사용한다.

관리 규칙: 기존 파일에 업데이트 (새 정보 추가, 오래된 정보 갱신)

**Step 6-2.5: Workflow Metrics 기록** (오케스트레이터 직접 실행)

> 📄 프롬프트: `prompts/phase6.md` Step 6-2.5 섹션을 읽어서 오케스트레이터가 직접 실행한다.
> .jarfis-state.json에서 핵심 메트릭을 추출하여 $JARFIS_ORG_DIR/workflow-metrics.tsv에 기록한다. best-effort — 실패 시 경고만.

**Step 6-3: Wiki 갱신** (Org 등록 시만 실행, 오케스트레이터)
> 📄 프롬프트: `prompts/phase6.md` Step 6-3 섹션을 읽어서 실행한다.
- 트랙 A: 텍스트 Wiki (PO, TA, QA) — 산출물에서 누적 지식 추출 → wiki 갱신
- 트랙 B: DESIGN HTML 동기화 (FE 포함 시만) — $DOCS_DIR/design/ → wiki/DESIGN/pages/{project}/
- 갱신 요약을 사용자에게 표시

**Step 6-4: 워크플로우 완료 상태 기록**
```bash
jarfis_cli.py state set "$DOCS_DIR/.jarfis-state.json" "status" "completed"
```
- `key_decisions` 필드에 Gate 1/2/3에서 합의된 핵심 결정사항 최종 기록

---

## Execution Rules

### Prompt & Template Path Resolution

이 문서에서 참조하는 상대 경로의 기준 디렉토리(base path):

| 참조 패턴 | 절대 경로 |
|-----------|----------|
| `prompts/*.md` | `~/.claude/commands/jarfis/prompts/*.md` |
| `templates/*.md` | `~/.claude/commands/jarfis/templates/*.md` |
| `agents/jarfis/*.md` | `~/.claude/agents/jarfis/*.md` |

> ⚠️ `$JARFIS_SOURCE`(Git repo)가 아닌 `~/.claude/`가 기준이다.
> 프롬프트/템플릿을 읽을 때 반드시 위 절대 경로를 사용하라.

### Workflow State Management (컨텍스트 유실 방어)

**`$DOCS_DIR/.jarfis-state.json`**을 워크플로우의 단일 진실 공급원(SSOT)으로 사용한다.

> 📄 상태 파일 스키마 및 필드 설명: `templates/jarfis-state-schema.md`를 참조한다.

**상태 파일 관리 규칙 (jarfis_cli.py state 사용):**
1. 워크플로우 시작: `jarfis_cli.py state init "$STATE_FILE" "$PROJECT_NAME" "$WORK_NAME" "$DOCS_DIR"`
2. Phase 시작/완료 시: `jarfis_cli.py state set-nested "$STATE_FILE" "phases.{N}.status" "in_progress|completed|skipped"`
3. 에이전트 상태: `jarfis_cli.py state set-nested "$STATE_FILE" "phase4_agents.backend" "completed"`
4. 게이트 결과: `jarfis_cli.py state set-nested "$STATE_FILE" "gate_results.gate1.decision" "approved"`
5. 매 Phase 시작 전: `jarfis_cli.py state read "$STATE_FILE"` — 이미 완료된 Phase는 재실행하지 않음
6. 상태 변경 시마다: `jarfis_cli.py state set "$STATE_FILE" "current_phase" "{N}"` + `last_checkpoint` 갱신
7. 워크플로우 종료: `jarfis_cli.py state set "$STATE_FILE" "current_phase" '"done"'`

**`api_spec_required` 판단**: `required_roles.backend == true AND frontend == true` → `true`, 그 외 → `false`

### Org Dir Resolution

`$JARFIS_PERSONAL_DIR` = `~/.claude/.jarfis-personal-dir` 파일 내용 (없으면 `{JARFIS_SOURCE}/.personal` 기본값). `{JARFIS_SOURCE}`는 `~/.claude/.jarfis-source` 파일에서 읽는다.
`$JARFIS_ORG_DIR` = `$JARFIS_PERSONAL_DIR/orgs/{org_name}/` (Org 감지 시) 또는 `$JARFIS_PERSONAL_DIR/orgs/_standalone/` (Org 없을 때). `jarfis_cli.py preflight`의 `org_root` 결과로 결정한다.

### Agent Mapping
> v3.0: `$DOMAIN` 설정 시 domain.yaml의 `roles` 섹션이 이 테이블을 대체한다. 아래는 `$DOMAIN`=null fallback 전용.

| Role | Agent (subagent_type) | Model |
|------|----------------------|-------|
| Product Owner | senior-product-owner | opus |
| Architect | technical-architect | opus |
| Tech Lead | tech-lead | opus |
| UX Designer | senior-ux-designer | opus |
| Backend Engineer | senior-backend-engineer | sonnet |
| Frontend Engineer | senior-frontend-engineer | sonnet |
| DevOps/SRE | senior-devops-sre-engineer | sonnet |
| QA Engineer | senior-qa-engineer | opus |
| Security Engineer | senior-security-engineer | opus |

### Skip Rules

**핵심 원칙**: 에이전트는 할 일이 있을 때만 실행한다.

**Phase 4 스킵**: `tasks.md`의 각 섹션이 "N/A"이면 해당 에이전트 SKIP. 단, 최소 1개 파트는 반드시 실행한다 (전체 N/A 불가).
**Step 4-0.5 스킵**: test-strategy.md가 없거나, P0 테스트 시나리오가 3개 미만이거나, 프로젝트에 단위 테스트 프레임워크가 없으면 SKIP. DevOps 전용 태스크에는 적용하지 않는다.
**Phase 5 스킵**: Phase 4에서 SKIP된 파트는 리뷰에서도 제외. UX SKIP이면 UI 테스트 제외.
**Phase 3 스킵**: PRD의 Required Roles에서 UX Designer '⬜ 불필요'이면 전체 SKIP
**Phase 2-1.5 스킵**: BE+FE 모두 필요하지 않으면 api-spec.md SKIP

#### Adaptive Skip 경험 가이드
- UX SKIP: 기존 디자인 시스템 재활용 + 새 화면 불필요 시. DevOps SKIP: 설정 변경만 + 인프라 구조 변경 없음 시.
- Phase 4.5 경량: `required_roles.devops == false`이면 5항목 체크리스트로 축소. Mongoose `default: null`로 마이그레이션 대체 가능.

### Parallel Execution Rules
- Phase 2+3 동시 시작 (Phase 3 SKIP이면 Phase 2만)
- Phase 2 내부: 2-0 → 2-1(병렬 가능) → 2-1.5(조건부) → 2-2 → 2-3(2-2 완료 후)
- Phase 4: BE/FE/DevOps 중 태스크 있는 파트만 동시 실행. Step 4-0 보안 리뷰 선행.
- Phase 5: Step 5-0(API Contract) 선행 → Step 5-1(TL/QA/Security 동시)
- Phase 4.5, 6은 이전 Phase 완료 후 자동 진행

### Variable Resolution
> ※ `$BACKEND_PROJECT_DIR`, `$FRONTEND_PROJECT_DIR`는 `.jarfis-state.json`의 `workspace` 필드에서 치환.
> ※ 학습/프로필 변수의 소스 경로와 주입 규칙은 Phase 0의 "주입 규칙" 참조. 파일 없으면 빈 문자열.

### File Handoff Protocol
1. 각 에이전트는 이전 Phase의 산출물 파일을 **읽어서** 컨텍스트로 사용한다.
2. 산출물은 반드시 지정된 파일 경로에 저장한다.
3. `$DOCS_DIR/` 디렉토리가 없으면 자동 생성한다.
4. 파일 충돌 시: 나중에 쓰는 에이전트가 기존 내용을 유지하고 자신의 섹션을 **추가**한다.

### Gate Point Rules
1. 게이트에서는 산출물 내용을 **요약하여 사용자에게 보여준다**.
2. **반드시 AskUserQuestion을 사용**하여 사용자의 명시적 선택을 받는다 (텍스트 출력만으로 자동 진행하지 않는다).
3. "수정" → 해당 Phase 에이전트 재실행. "승인" → 다음 Phase 자동 진행. "중단" → 즉시 종료.

### SuperClaude Integration
필요 시: `/sc:brainstorm`(Phase 1), `/sc:design`(Phase 2), `/sc:implement`(Phase 4), `/sc:analyze`·`/sc:test`(Phase 5)

### Progress Display
각 Phase 시작 시 `.jarfis-state.json`을 읽고 진행 상태 바 + 활성 역할 + 학습 로드 상태를 표시한다.

### Resume After Context Compression
1. `$DOCS_DIR/.jarfis-state.json` 읽기 (`$DOCS_DIR` 모르면 `$JARFIS_ORG_DIR/works/`에서 최근 파일 탐색)
2. `docs_dir`, `current_phase`, `last_checkpoint` 확인
3. `in_progress` Phase부터 이어서 진행. `completed` Phase는 절대 재실행하지 않음.
4. **Compact 백업**: `$DOCS_DIR/.compact-backups/` 디렉토리에서 상태 파일 복구 가능 (PreCompact 훅 연동)
5. 산출물 파일 존재 여부로 실제 완료 교차 검증
