# JARFIS - IT Team Workflow Orchestration

사용자가 다음 기획을 요청했습니다: $ARGUMENTS

이 기획에 대해 아래 워크플로우를 자동 실행하세요.

---

## Learned Workflow Patterns

아래 패턴은 실제 워크플로우 실행에서 검증된 학습이다. Phase 진행 시 참고하라.

- FE-only + HTML 속성 추가만 하는 작업은 BE/DevOps/UX SKIP이 적절함. API 변경 없으면 api-spec.md도 SKIP
- 성능 측정 프로토콜(환경, 네트워크 조건, 캐시 정책, 인증, 측정 순서)은 Phase 2 test-strategy에서 사전 정의해야 Phase 5에서 반복 측정을 줄일 수 있음
- Playwright + CDP로 네트워크 쓰로틀링(Slow 4G) + 캐시 비활성화 가능: Network.emulateNetworkConditions + Network.setCacheDisabled
- 변경 규모가 작아도(1파일) 브라우저 동작 원리가 개입하는 작업(Resource Hints, Cache-Control 등)은 성능 측정을 생략하지 마라. 측정 없이는 효과 검증 불가능하고 기술 부채 우선순위 판단 근거도 사라진다
- 참조 프로젝트(market-frontend 등)가 있는 작업에서는 Phase 2에서 참조 코드의 API 파라미터/폼 필드 구조를 스냅샷으로 기록해야 한다. Phase 4 구현 시작 전에 참조 코드 변경 여부를 재확인하는 체크포인트 필요
- i18n이 있는 프로젝트에서 Phase 4 FE 구현 시 i18n 하드코딩 방지 제약조건을 에이전트 프롬프트에 명시적으로 전달하라
- Phase 4.5에 자동화 pre-check(i18n 커버리지, base path 검증, 중복 ID 탐지)를 추가하면 Phase 5 리뷰 반복을 줄일 수 있음
- SSG(Astro/Next.js static) 프로젝트에서는 deployment-plan.md의 대부분 항목이 N/A. Big Bang + Git Revert가 최적 배포 전략
- admin 전용 / 내부 도구 피처에서는 Press Release 단계를 스킵하고 PRD의 "목표" 섹션으로 대체하라
- Devil's Advocate(architecture.md Section 8)가 실질적 효과를 냄. 설계에서 "무엇이 잘못될 수 있는가"를 구조화하는 패턴 유지
- JARFIS 시스템 파일(commands/jarfis/*, agents/jarfis/*, prompts/*, templates/*)을 수정할 때는 반드시 /jarfis:implement를 통해 실행하라

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

```
1. $ARGUMENTS와 대화 컨텍스트를 분석하여 유형(A/B/C)을 판단한다.
2. 기존 .jarfis/ 디렉토리에 관련 .jarfis-state.json이 있는지 확인한다.
   - 있으면: 해당 워크플로우의 현재 Phase를 파악 → 유형 B 가능성 높음

3. 유형별 처리:

   [유형 A] → Phase 0로 자동 진행. 별도 확인 없음.

   [유형 B] → AskUserQuestion으로 확인:
     "이 요청은 JARFIS 워크플로우의 [Phase N: 이름]에 해당합니다.
      기존 워크플로우 산출물이 있습니다: [경로]
      1. 해당 Phase만 실행 (기존 산출물 기반)
      2. 전체 워크플로우를 Phase 0부터 새로 시작
      3. 워크플로우 없이 직접 진행"

   [유형 C] → AskUserQuestion으로 확인:
     "이 요청은 JARFIS 워크플로우보다 직접 처리가 적합해 보입니다.
      이유: [판단 근거]
      1. 워크플로우 없이 직접 진행 (권장)
      2. 그래도 전체 워크플로우로 진행"
```

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
- 기존 작업의 연장(추가 구현, 후속 수정 등)인 경우, `develop`이 아닌 **원래 피처 브랜치**(예: `feat/admin-permission`)에서 분기해야 한다.
- `.jarfis-state.json`의 `branch` 필드를 확인하여 원래 브랜치를 파악하고, 해당 브랜치 기반으로 새 브랜치를 생성한다.
- `base_branch`를 `.jarfis-state.json`에 기록하여 분기 이력을 추적한다.

---

## Workflow Overview

```
/jarfis:work [기획 내용]
  ⬇
Phase T: Triage ───────────────── 요청 분류 (A/B/C) → B/C면 🔒 사용자 확인
  ⬇ (유형 A면 자동 진행)
Phase 0: Pre-flight ───────────── 작업물명 입력 → Git sync(main/develop) + 브랜치 생성 → 학습 파일 로드
  ⬇ 자동 진행
Phase 1: Discovery ─────────────── PO(역질문→Working Backwards→PRD+역할판단+성능예산) + Architect(실현가능성)
  ⬇ 🔒 사용자 컨펌               ↳ PRD에 "필요 역할" + "Performance Budget" 명시
Phase 2: Architecture & Planning ─ Impact Analysis → Architect(설계+ADR) → [BE+FE면] API 명세 → Tech Lead(태스크 분해) → QA(테스트 전략)
  ⬇ 자동 진행                      ↕ 병렬  ↳ 불필요 파트는 "N/A" 처리
Phase 3: UX Design ─────────────── [조건부] PO가 UI 필요로 판단한 경우만 실행
  ⬇ 🔒 사용자 컨펌 (UX + API 명세) ↳ UI 없으면 Phase 3 전체 SKIP
Phase 4: Implementation ────────── tasks.md + test-strategy.md 기준 실행 / api-spec.md가 BE-FE 공통 계약
  ⬇ 자동 진행                      ↳ BE/FE/DevOps 중 태스크 없는 파트는 SKIP
Phase 4.5: Operational Readiness ─ 배포 전략 + 롤백 계획 + 운영 준비도 체크리스트
  ⬇ 자동 진행
Phase 5: Review & QA ──────────── API Contract 검증 → Tech Lead + QA + Security 병렬리뷰
  ⬇ 🔒 사용자 컨펌 (최종 리뷰)
Phase 6: Retrospective ────────── 학습 축적 (전역 learnings + 프로젝트 context)
  ⬇ 자동 완료
```

## Artifacts (산출물 파일 경로)

### 산출물 디렉토리 규칙

산출물은 `.jarfis/works/{YYYYMMDD}/{작업물명}/` 디렉토리에 저장한다.
- `YYYYMMDD`: 워크플로우 시작 날짜 (예: `20260224`)
- `작업물명`: Phase 0에서 사용자가 직접 입력한 이름 (예: `게시판-에디터-고도화`)
- 이하 이 경로를 `$DOCS_DIR`로 표기한다.
- 워크플로우 시작 시 `$DOCS_DIR` 값을 결정하고, `.jarfis-state.json`의 `docs_dir` 필드에 저장한다.

예시: `.jarfis/works/20260224/게시판-에디터-고도화/prd.md`

| Phase | File | Description | 조건부 |
|-------|------|-------------|--------|
| — | `$DOCS_DIR/.jarfis-state.json` | **워크플로우 상태 파일 (컨텍스트 유실 방어)** | 항상 |
| 1 | `$DOCS_DIR/press-release.md` | Working Backwards 가상 프레스 릴리스 + FAQ | 항상 |
| 1 | `$DOCS_DIR/prd.md` | PRD + 실현가능성 평가 + **필요 역할 판단** + **Performance Budget** | 항상 |
| 2 | `$DOCS_DIR/impact-analysis.md` | 기존 코드베이스 영향 범위 분석 | 항상 |
| 2 | `$DOCS_DIR/architecture.md` | 시스템 아키텍처 설계서 + **ADR (Architecture Decision Records)** | 항상 |
| 2 | `$DOCS_DIR/api-spec.md` | API 명세서 (엔드포인트, 파라미터, 응답 스키마) | BE+FE 모두 필요 시 |
| 2 | `$DOCS_DIR/tasks.md` | 태스크 분해 (불필요 파트는 N/A) | 항상 |
| 2 | `$DOCS_DIR/test-strategy.md` | 테스트 전략 (테스트 피라미드, 시나리오, 성능 기준) | 항상 |
| 3 | `$DOCS_DIR/ux-spec.md` | UX 화면 설계서 | UI 필요 시만 |
| 4 | `$DOCS_DIR/infra-runbook.md` | 수동 인프라 설정 가이드 (AWS 등 클라우드 작업) | DevOps 실행 시 |
| 4.5 | `$DOCS_DIR/deployment-plan.md` | 배포 전략 + 롤백 계획 + 운영 준비도 체크리스트 | 항상 |
| 5 | `$DOCS_DIR/api-contract-check.md` | BE-FE API Contract 자동 검증 결과 | api-spec.md 존재 시 |
| 5 | `$DOCS_DIR/review.md` | 실행된 파트의 리뷰 결과만 포함 | 항상 |
| 5 | `$DOCS_DIR/diagnosis.md` | Root Cause 진단 + 수정 지시서 | 수정 후 재리뷰 시 |
| 6 | `$DOCS_DIR/retrospective.md` | 워크플로우 회고 (프로젝트별 기록) | 항상 |

### 학습 파일 경로

| 파일 | 위치 | 설명 |
|------|------|------|
| `jarfis-learnings.md` | `~/.claude/jarfis-learnings.md` | **전역** — Agent Hints + Workflow Patterns |
| `project-context.md` | `./.jarfis/project-context.md` | **프로젝트별** — 이 코드베이스 고유 지식 |

---

## Phase 0: Pre-flight (학습 파일 로드)

### 목표
이전 워크플로우에서 축적된 학습과 프로젝트 컨텍스트를 로드하여 에이전트 품질을 높인다.

### 실행 순서

0. **작업물명 입력 및 Git 브랜치 설정**

   **0-a. 작업물명 입력**
   - AskUserQuestion으로 작업물명을 입력받는다:
     ```
     "이 작업의 이름을 입력해주세요.
      (디렉토리명 및 Git 브랜치명으로 사용됩니다)
      예: 게시판-에디터-고도화, user-auth-refactoring"
     ```
   - 입력된 이름을 `$WORK_NAME` 변수로 저장한다.
   - `$DOCS_DIR`을 `.jarfis/works/{YYYYMMDD}/$WORK_NAME`으로 결정한다.
   - `$DOCS_DIR` 디렉토리를 생성하고 `.jarfis-state.json`을 초기화한다.

   **0-a-2. Meeting 감지**
   - `$ARGUMENTS`에 `--meeting {기획명}` 플래그가 있는지 확인한다.
     - **있으면**: `$ARGUMENTS`에서 `--meeting {기획명}` 부분을 제거하고 나머지를 `$ARGUMENTS`로 재설정한다.
       `$MEETING_REF` = `{기획명}`, `$MEETING_DIR` = `./.jarfis/meetings/*/$MEETING_REF/` (날짜 디렉토리를 glob으로 탐색)
       `$MEETING_DIR/summary.md` 존재 확인 → 없으면 경고 출력 후 미팅 없이 진행
     - **없으면**: `./.jarfis/meetings/` 디렉토리가 존재하는지 확인한다.
       - 존재하면: `./.jarfis/meetings/*/` 하위의 모든 `summary.md` 파일을 스캔한다.
         각 summary.md의 YAML frontmatter에서 `idea` 필드를 읽는다.
         `$ARGUMENTS`의 내용과 `idea` 필드를 비교하여 관련도를 판단한다.
         (키워드 매칭 — `$ARGUMENTS`의 핵심 명사/동사가 `idea`에 포함되는지 확인)
       - 관련 미팅이 발견되면 AskUserQuestion으로 선택지 제시:
         ```
         "관련 미팅 기록이 발견되었습니다:
          1. '{미팅명}' 미팅 참조하여 진행 (권장)
          2. 미팅 참조 없이 처음부터 진행"
         ```
         (관련 미팅이 2개 이상이면 각각 옵션으로 표시 + "미팅 참조 없이 진행" 옵션)
         - 미팅 참조 선택 시: `$MEETING_REF` = 해당 미팅명, `$MEETING_DIR` 설정
       - 관련 미팅 없으면: `$MEETING_REF` = 빈 문자열, 미팅 없이 진행

   **0-a-3. Meeting 컨텍스트 로드**
   - `$MEETING_REF`가 비어있지 않으면:
     - `$MEETING_DIR/summary.md` → `$MEETING_SUMMARY` 변수로 읽기
     - `$MEETING_DIR/meeting-notes.md` → `$MEETING_NOTES` 변수로 읽기
     - `$MEETING_DIR/decisions.md` → `$MEETING_DECISIONS` 변수로 읽기
     - `$MEETING_DIR/tech-research.md` → 존재하면 `$MEETING_RESEARCH` 변수로 읽기 (없으면 빈 문자열)
     - `.jarfis-state.json`에 `meeting_ref` 필드를 기록한다:
       ```json
       { "meeting_ref": "$MEETING_REF", "meeting_dir": "$MEETING_DIR" }
       ```
   - `$MEETING_REF`가 비어있으면: 모든 `$MEETING_*` 변수를 빈 문자열로 설정

   **0-b. Git 브랜치 동기화 및 생성**
   - 현재 Git 저장소인지 확인한다. Git 저장소가 아니면 이 단계를 건너뛴다.
   - **multi-project 환경**: 각 프로젝트 디렉토리의 `.git` 위치를 확인하라. 부모 repo와 자식 repo가 다를 수 있으므로, 실제 `.git`이 어디에 있는지 `git rev-parse --show-toplevel`로 검증한다.
   - uncommitted 변경사항이 있는지 확인한다. 있으면 사용자에게 경고하고 계속할지 확인한다.
   - 기본 브랜치를 감지한다 (`main` 또는 `master`):
     ```bash
     git remote show origin | grep 'HEAD branch' | cut -d' ' -f5
     ```
   - 기본 브랜치와 `develop` 브랜치를 최신 버전으로 동기화한다:
     ```bash
     git checkout $DEFAULT_BRANCH && git pull origin $DEFAULT_BRANCH
     git checkout develop && git pull origin develop
     ```
   - `develop` 브랜치가 없으면 사용자에게 알리고, 기본 브랜치에서 분기할지 확인한다.
   - `develop` 기준으로 작업 브랜치를 생성하고 전환한다:
     ```bash
     git checkout -b $WORK_NAME develop
     ```
   - 브랜치 이름을 `.jarfis-state.json`의 `branch` 필드에 기록한다.

1. **시스템 헬스체크** (좀비 프로세스 감지)
   - `~/.claude/scripts/claude-cleanup.sh` 존재 여부 확인 → 없으면 이 단계를 건너뛰고 1번으로 진행
   - 존재하면 Bash로 진단 모드 실행 (인자 없이): `~/.claude/scripts/claude-cleanup.sh`
   - 출력에서 좀비 프로세스 수를 파싱한다 ("좀비 Claude **N개**" 패턴)
   - 좀비 5개 이상 감지 시:
     - AskUserQuestion으로 사용자에게 3가지 선택지 제시:
       1. "지금 정리하고 계속 진행" → `~/.claude/scripts/claude-cleanup.sh --kill` 실행 후 1번으로 계속
       2. "무시하고 계속 진행" → 그냥 1번으로 진행
       3. "워크플로우 중단" → 워크플로우 즉시 종료
   - 좀비 1~4개이면 경고만 표시하고 자동으로 1번으로 진행:
     ```
     [Health] 좀비 프로세스 N개 감지됨 (5개 미만이므로 자동 진행)
     정리하려면: /jarfis:health --clean
     ```
   - 좀비 0개이면 아무것도 출력하지 않고 1번으로 진행

1. `~/.claude/jarfis-learnings.md` 존재 여부 확인 → 있으면 읽기
2. `./.jarfis/project-context.md` 존재 여부 확인 → 있으면 읽기
3. 프로젝트 프로필 로드 (`/jarfis:project-init`으로 생성된 파일):
   - workspace가 결정되기 전 (Phase 0): 현재 디렉토리의 `./.jarfis/project-profile.md` 확인
   - workspace가 결정된 후 (Phase 4~5): `$BACKEND_PROJECT_DIR/.jarfis/project-profile.md`와 `$FRONTEND_PROJECT_DIR/.jarfis/project-profile.md`를 각각 확인
   - 읽은 내용을 `$BE_PROJECT_PROFILE`, `$FE_PROJECT_PROFILE` 변수로 저장
   - monorepo인 경우 둘 다 같은 파일을 참조할 수 있음
4. 읽은 내용을 `$LEARNINGS` (전역)와 `$PROJECT_CONTEXT` (프로젝트) 변수로 저장
5. 이후 Phase 1~5의 에이전트 프롬프트에서 관련 항목을 선택적으로 주입

**주입 규칙:**
- Phase 1 (PO, Architect): `$LEARNINGS`의 Workflow Patterns + `$PROJECT_CONTEXT` 전체
- Phase 2 (Architect — Impact Analysis, 설계): `$BE_PROJECT_PROFILE` + `$FE_PROJECT_PROFILE` (존재 시)
- Phase 4 (BE/FE/DevOps): `$LEARNINGS`의 해당 역할 Agent Hints + `$PROJECT_CONTEXT` 전체 + **해당 역할의 `$PROJECT_PROFILE`**
- Phase 5 (Tech Lead/QA/Security): `$LEARNINGS`의 해당 역할 Agent Hints

학습 파일이 없으면 (최초 실행) 건너뛰고 Phase 1로 진행한다.
프로젝트 프로필이 없으면 해당 변수는 빈 문자열로 치환한다 (`/jarfis:project-init` 미실행 상태).

---

## Phase 1: Discovery

### 목표
사용자의 기획 의도를 명확히 하고, 기술적 실현가능성을 동시에 검증한다.

### 실행 순서

**Step 1-1: PO 역질문** (senior-product-owner)

> **미팅 참조 시 조건부 동작**: `$MEETING_REF`가 존재하면, 아래 프롬프트 마지막에 미팅 컨텍스트를 주입한다.
> 이미 미팅에서 논의/결정된 사항은 재질문하지 않고, **미결 사항 + PRD에 필수적이지만 미팅에서 다루지 않은 항목**만 질문한다.

> 📄 프롬프트: `prompts/phase1.md` 해당 섹션을 읽어서 에이전트에 전달한다.

> 사용자가 역질문에 답변하면 다음 단계로 진행

**Step 1-1.5: Working Backwards Document** (senior-product-owner)
> 📄 프롬프트: `prompts/phase1.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 1-2: PRD 작성 + 실현가능성 평가** (병렬 실행)

PO (senior-product-owner):
> 📄 프롬프트: `prompts/phase1.md` 해당 섹션을 읽어서 에이전트에 전달한다.

Architect (technical-architect):
> 📄 프롬프트: `prompts/phase1.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 1-2.5: PRD Completeness Check** (오케스트레이터 직접 실행 — 에이전트 아님)

> 📄 프롬프트: `prompts/phase1.md` Step 1-2.5 섹션을 읽어서 오케스트레이터가 직접 실행한다.
> PRD 자동 검증 후 미통과 항목이 있으면 PO에게 재작성 지시 (최대 2회).

### 🔒 게이트 1: 사용자 컨펌
```
Phase 1이 완료되었습니다.

📄 산출물:
- $DOCS_DIR/press-release.md (Working Backwards)
- $DOCS_DIR/prd.md (PRD + 실현가능성 + 역할 판단 + 성능 예산)

PRD 내용을 검토해주세요:
1. ✅ 승인 — Phase 2로 진행합니다
2. ✏️ 수정 요청 — 수정할 내용을 알려주세요
3. ❌ 중단 — 워크플로우를 종료합니다
```

---

## Phase 2: Architecture & Planning + Phase 3: UX Design (병렬)

Phase 2와 Phase 3은 동시에 진행한다.

### Phase 2: Architecture & Planning

**Step 2-0: Impact Analysis** (technical-architect)
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 2-1: 시스템 아키텍처 설계** (technical-architect)
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 2-1.5: API 명세 작성** (technical-architect → tech-lead 순차) — **BE+FE 모두 필요 시만 실행**

> **실행 조건**: PRD의 'Required Roles'에서 Backend Engineer와 Frontend Engineer가 **모두 ✅ 필요**인 경우에만 실행한다.
> 둘 중 하나만 필요하거나 모두 불필요하면 이 스텝을 SKIP하고 Step 2-2로 진행한다.

Architect (technical-architect):
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

Tech Lead (tech-lead) — api-spec.md 리뷰:
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 2-2: 태스크 분해** (tech-lead)
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 2-3: 테스트 전략 수립** (senior-qa-engineer)
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

### Phase 3: UX Design (조건부 실행)

> **스킵 조건**: $DOCS_DIR/prd.md의 'Required Roles' 표에서 UX Designer가 '⬜ 불필요'이면 Phase 3 전체를 건너뛴다.
> 스킵 시 `$DOCS_DIR/ux-spec.md`는 생성하지 않으며, 게이트 2에서 "(Phase 3: UX 불필요로 SKIP됨)"을 표시한다.

**Step 3-1: UX 화면 설계** (senior-ux-designer) — UX Designer 필요 시만 실행
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 3-2: PO 검증** (senior-product-owner) — UX Designer 필요 시만 실행
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

> UX Designer가 PO 피드백을 반영하여 ux-spec.md를 업데이트 (필요 시 반복)

### 🔒 게이트 2: 사용자 컨펌
```
Phase 2 & 3이 완료되었습니다.

📄 산출물:
- $DOCS_DIR/impact-analysis.md (영향 범위 분석)
- $DOCS_DIR/architecture.md (아키텍처 설계 + ADR)
- $DOCS_DIR/api-spec.md (API 명세) — BE+FE 모두 불필요 시 "(SKIP됨)" 표시
- $DOCS_DIR/tasks.md (태스크 분해) — N/A 표시된 파트 확인
- $DOCS_DIR/test-strategy.md (테스트 전략)
- $DOCS_DIR/ux-spec.md (UX 설계) — UX 불필요 시 "(SKIP됨)" 표시

⚡ 실행 파트 요약:
- Backend: [✅ 실행 예정 / ⬜ SKIP]
- Frontend: [✅ 실행 예정 / ⬜ SKIP]
- DevOps: [✅ 실행 예정 / ⬜ SKIP]
- UX: [✅ 완료 / ⬜ SKIP]
- API Contract: [✅ 작성됨 / ⬜ SKIP (BE+FE 동시 필요하지 않음)]

결과를 검토해주세요:
1. ✅ 승인 — Phase 4 (구현)로 진행합니다
2. ✏️ 수정 요청 — 수정할 내용을 알려주세요
3. ❌ 중단 — 워크플로우를 종료합니다
```

---

## Phase 4: Implementation

### 목표
설계 문서를 기반으로 **tasks.md에 실제 태스크가 있는 파트만** 병렬로 구현한다. 구현 전 Security가 사전 리뷰한다.

### 스킵 판단 규칙
Phase 4 실행 전, `$DOCS_DIR/tasks.md`의 각 섹션을 확인한다:
- **Backend Tasks** 섹션이 "N/A"이면 → senior-backend-engineer 실행하지 않음
- **Frontend Tasks** 섹션이 "N/A"이면 → senior-frontend-engineer 실행하지 않음
- **DevOps Tasks** 섹션이 "N/A"이면 → senior-devops-sre-engineer 실행하지 않음
- 모든 파트가 N/A일 수는 없음 (최소 1개 파트는 실행)

### 실행 순서

**Step 4-0: 보안 사전 리뷰** (senior-security-engineer)
> 📄 프롬프트: `prompts/phase4.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 4-1: 병렬 구현** (tasks.md에 태스크가 있는 파트만 동시 실행)

Backend (senior-backend-engineer) — **Backend Tasks가 N/A이면 SKIP**:
> 📄 프롬프트: `prompts/phase4.md` 해당 섹션을 읽어서 에이전트에 전달한다.

Frontend (senior-frontend-engineer) — **Frontend Tasks가 N/A이면 SKIP**:
> 📄 프롬프트: `prompts/phase4.md` 해당 섹션을 읽어서 에이전트에 전달한다.

DevOps (senior-devops-sre-engineer) — **DevOps Tasks가 N/A이면 SKIP**:
> 📄 프롬프트: `prompts/phase4.md` 해당 섹션을 읽어서 에이전트에 전달한다.

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

### 스킵 판단 규칙
- Phase 4에서 SKIP된 파트는 리뷰 대상에서도 제외한다.
- Tech Lead는 실행된 파트의 코드만 리뷰한다.
- QA는 구현된 기능만 테스트한다 (UX가 SKIP되었으면 UI 테스트 제외).
- Security는 구현된 코드만 보안 리뷰한다.

### 실행 순서

**Step 5-0: API Contract 자동 검증** — **api-spec.md 존재 시만 실행**

> **실행 조건**: `$DOCS_DIR/api-spec.md`가 존재하는 경우에만 실행한다.
> 존재하지 않으면 이 스텝을 SKIP하고 Step 5-1로 진행한다.

Tech Lead (tech-lead):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 5-1: 병렬 리뷰** (3개 에이전트 동시 실행)

Tech Lead (tech-lead):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

QA (senior-qa-engineer):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

Security (senior-security-engineer):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**결과 통합**: 실행된 에이전트의 리뷰 결과만 `$DOCS_DIR/review.md`에 통합 저장한다.

### 🔒 게이트 3: 최종 컨펌

> **병리 패턴 감지 (2회차 이상 재리뷰 시)**: 게이트 3 표시 전에 `prompts/phase5.md`의 "Step 5-2 병리 패턴 감지" 절차를 실행한다.
> 병리 패턴이 감지되면 아래 선택지에 옵션 4를 추가하고, `.jarfis-state.json`의 `review_iterations` 필드를 증가시킨다.

```
Phase 5가 완료되었습니다.

📄 산출물: $DOCS_DIR/review.md

리뷰 결과를 확인해주세요:
- 🔍 코드리뷰: [이슈 n건 / 통과]
- 📋 API Contract: [불일치 n건 / 전체 일치 / SKIP]
- 🧪 QA: [실패 n건 / 전체 통과]
- 🔒 보안리뷰: [취약점 n건 / 통과]
- 🚀 배포 전략: [준비 완료 / 미비 항목 n건]

1. ✅ 승인 — Phase 6 (회고) 후 워크플로우를 완료합니다
2. 🔄 수정 후 재리뷰 — Step 5-2 (진단) → Step 5-3 (수정) → Phase 5 재실행
3. ❌ 중단 — 워크플로우를 종료합니다
4. 🔙 설계 재검토 — Phase 2로 돌아가 아키텍처/태스크를 재설계합니다 (병리 패턴 감지 시 표시)
```

### Step 5-2: Root Cause Diagnosis (게이트 3에서 "수정 후 재리뷰" 선택 시)

> **실행 조건**: 게이트 3에서 사용자가 "🔄 수정 후 재리뷰"를 선택한 경우에만 실행한다.

Tech Lead (tech-lead):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

### Step 5-3: Fix Implementation (진단 기반 수정)

$DOCS_DIR/diagnosis.md의 수정 지시서에 따라, 담당 에이전트(BE/FE/DevOps)를 실행하여 수정한다.

**실행 규칙:**
- diagnosis.md의 "수정 우선순위 요약"에서 담당 에이전트별로 수정 지시를 그룹핑한다.
- 해당 에이전트에게 diagnosis.md를 참조하도록 프롬프트를 전달한다.
- P0 이슈를 우선 수정하고, 회귀 방지 테스트도 함께 작성한다.
- 수정 완료 후 Phase 5 (Step 5-0 ~ Step 5-1)를 **재실행**한다.

Backend (senior-backend-engineer) — **diagnosis.md에 BE 수정 지시가 있을 때만**:
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

Frontend (senior-frontend-engineer) — **diagnosis.md에 FE 수정 지시가 있을 때만**:
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

> 수정 완료 후 Step 5-0 ~ Step 5-1 → 게이트 3를 **재실행**한다. (재진단이 필요하면 다시 Step 5-2로 반복)

---

## Phase 6: Retrospective (자동 실행)

### 목표
이번 워크플로우에서 얻은 학습을 **전역 학습 파일**(에이전트/워크플로우 개선)과 **프로젝트 컨텍스트 파일**(코드베이스 지식)에 축적한다.

### 실행 순서

**Step 6-1: 회고 작성** (tech-lead)
> 📄 프롬프트: `prompts/phase6.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 6-2: 학습 파일 업데이트** (오케스트레이터가 직접 실행)

retrospective.md를 읽고 다음 두 파일에 분배 저장한다:

**1. 전역 학습 — `~/.claude/jarfis-learnings.md`**

retrospective.md에서 **프로젝트에 무관하게 재사용 가능한 학습**만 추출하여 저장:

> 📄 템플릿: `templates/learnings.md`를 읽어서 산출물 양식으로 사용한다.

관리 규칙:
- 기존 파일이 있으면 해당 섹션에 **추가** (중복이면 기존 항목 업데이트)
- 오래되거나 틀린 것으로 판명된 항목은 **제거**
- 각 항목에 날짜를 기록하여 추적 가능하게 유지

**2. 프로젝트 컨텍스트 — `./.jarfis/project-context.md`**

retrospective.md에서 **이 코드베이스에만 해당하는 지식**만 추출하여 저장:

> 📄 템플릿: `templates/project-context.md`를 읽어서 산출물 양식으로 사용한다.

관리 규칙:
- 기존 파일이 있으면 **업데이트** (새 정보 추가, 오래된 정보 갱신)
- 이 파일은 같은 프로젝트에서 다음 JARFIS 실행 시 Phase 0에서 로드됨

---

## Execution Rules

### Workflow State Management (컨텍스트 유실 방어)

메인 오케스트레이터의 컨텍스트가 압축되어도 워크플로우 진행 상태를 잃지 않기 위해,
**`$DOCS_DIR/.jarfis-state.json`** 파일을 워크플로우의 단일 진실 공급원(Single Source of Truth)으로 사용한다.

> 📄 상태 파일 스키마: `templates/jarfis-state-schema.md`를 참조한다.

**`api_spec_required` 판단 규칙:**
- `required_roles.backend == true AND required_roles.frontend == true` → `api_spec_required: true`
- 그 외 → `api_spec_required: false`
- Phase 1 완료 후, required_roles가 확정되면 이 값을 설정한다.

**`workspace` 설정 규칙:**
- Phase 1 완료 후, PRD의 'Workspace' 표를 파싱하여 `.jarfis-state.json`의 `workspace` 필드를 설정한다.
- `type: "monorepo"` — BE/FE 경로가 모두 `.`이거나 동일한 경우. 에이전트들이 동일 디렉토리에서 작업.
- `type: "multi-project"` — BE/FE 경로가 다른 경우. 각 에이전트에게 해당 경로를 `$PROJECT_DIR`로 전달.
- 불필요 역할의 경로는 `"N/A"`로 설정하고, 해당 에이전트 프롬프트에서는 무시한다.

**상태 파일 관리 규칙:**

1. **워크플로우 시작 시**: Phase 0의 Step 0-a에서 사용자로부터 `$WORK_NAME`을 입력받은 후 `$DOCS_DIR`을 결정한다 — `.jarfis/works/{YYYYMMDD}/$WORK_NAME` 형식. 해당 디렉토리를 생성하고 상태 파일을 생성한다 (`current_phase: 0`, 모든 Phase `pending`, `docs_dir: "$DOCS_DIR"`, `work_name: "$WORK_NAME"`, `branch: "$WORK_NAME"`).
2. **Phase 시작 시**: 해당 Phase의 status를 `"in_progress"`로 업데이트한다.
3. **에이전트 실행 시**: 개별 에이전트의 상태를 `"in_progress"` → `"completed"` / `"skipped"`로 업데이트한다.
4. **게이트 통과 시**: gate 결과와 사용자 피드백을 기록하고, `current_phase`를 다음 Phase로 업데이트한다.
5. **Phase 완료 시**: 해당 Phase의 status를 `"completed"` 또는 `"skipped"`로 업데이트한다.
6. **매 Phase 시작 전**: 반드시 상태 파일을 **읽어서** 현재 진행 상황을 확인한다. 이미 완료된 Phase는 다시 실행하지 않는다.
7. **워크플로우 종료 시**: `current_phase`를 `"done"`으로 설정한다.
8. **체크포인트 기록**: Phase 시작, 에이전트 완료, 게이트 통과 등 상태 변경 시마다 `last_checkpoint`를 갱신한다:
   ```json
   "last_checkpoint": {
     "timestamp": "ISO8601",
     "phase": <현재 Phase 번호>,
     "summary": "<현재까지 진행 상황 한줄 요약>"
   }
   ```
   이 필드는 auto-compact 후 컨텍스트 복구 시 "마지막으로 확인된 상태"를 빠르게 파악하는 데 사용된다.

**컨텍스트 복구 시나리오:**
메인 세션의 컨텍스트가 압축된 후에도, 상태 파일을 읽으면 다음을 즉시 파악할 수 있다:
- `docs_dir` — 산출물 디렉토리 경로 (`$DOCS_DIR`)
- `work_name` — 작업물명 (`$WORK_NAME`)
- `branch` — 작업 브랜치명
- 현재 몇 Phase인지
- 어떤 역할이 필요/불필요한지
- `api_spec_required` — API 명세가 필요한 프로젝트인지 (BE+FE 동시 필요 여부)
- `workspace` — 프로젝트 구조 유형과 각 역할별 작업 디렉토리 경로
  - `workspace.projects.backend.path` → `$BACKEND_PROJECT_DIR`
  - `workspace.projects.frontend.path` → `$FRONTEND_PROJECT_DIR`
- Phase 2에서 어떤 단계가 완료/진행중인지 (impact_analysis, architect, api_spec, tech_lead_tasks, qa_test_strategy)
- Phase 4/4.5/5/6에서 어떤 에이전트가 완료/진행중/대기중인지
- 게이트에서 사용자가 어떤 결정을 했는지

### Agent Mapping
| Role | Agent (subagent_type) | Model |
|------|----------------------|-------|
| Product Owner | senior-product-owner | opus |
| Architect | technical-architect | opus |
| Tech Lead | tech-lead | opus |
| UX Designer | senior-ux-designer | sonnet |
| Backend Engineer | senior-backend-engineer | sonnet |
| Frontend Engineer | senior-frontend-engineer | sonnet |
| DevOps/SRE | senior-devops-sre-engineer | sonnet |
| QA Engineer | senior-qa-engineer | sonnet |
| Security Engineer | senior-security-engineer | sonnet |

### Skip & Parallel Execution Rules

**핵심 원칙**: 에이전트는 할 일이 있을 때만 실행한다. 불필요한 에이전트를 돌리지 않는다.
> ※ 각 Phase의 스킵 조건은 해당 Phase 섹션에 명시되어 있다. (Phase 2-1.5, Phase 3, Phase 4, Phase 5 참조)

#### Adaptive Skip 경험 가이드

아래는 실제 워크플로우에서 검증된 스킵 판단 기준이다:

- **UX Designer 스킵**: 기존 디자인 시스템/UI 패턴을 재활용하는 작업이고, 새로운 화면 설계가 불필요한 경우 → UX SKIP 적절
- **DevOps 스킵**: serverless.yml 설정 변경만 필요하고, Lambda/인프라 구조 변경이 없는 경우 → DevOps SKIP 적절
- **Mongoose default null 패턴**: DB 마이그레이션이 아닌 Mongoose `default: null`로 처리 가능하면 DB 마이그레이션 태스크 불필요
- **Phase 4.5 경량 모드**: `required_roles.devops == false`이면 deployment-plan.md를 5항목 체크리스트(배포 순서, 사전 확인, 스모크 테스트, 롤백 트리거, 롤백 명령)로 축소
- **diagnosis.md 이슈 그룹 효과**: 개별 이슈 나열보다 상관관계 기반 그룹핑이 교차 분석에 효과적. 같은 근본 원인의 이슈를 묶으면 수정 범위가 줄어든다

#### Parallel Execution Rules
- Phase 2와 Phase 3은 **동시 시작**한다. 단, Phase 3 자체가 SKIP이면 Phase 2만 실행한다.
- Phase 2 내부 순서: Step 2-0(impact-analysis.md) → Step 2-1(architecture.md+ADR) → Step 2-1.5(api-spec.md, 조건부) → Step 2-2(tasks.md) → Step 2-3(test-strategy.md). Step 2-0은 Step 2-1과 **병렬 실행 가능** (Architect는 impact-analysis를 참조하므로 Step 2-0 완료 후 Step 2-1 시작이 이상적이나, 시간 절약을 위해 병렬 시작 후 Architect가 impact-analysis.md를 참조하도록 할 수 있다). Step 2-3은 Step 2-2 완료 후에만 실행 가능하다.
- Phase 3의 PO 검증(Step 3-2)은 UX 설계(Step 3-1) 완료 후 실행한다.
- Phase 4의 BE/FE/DevOps 중 **tasks.md에 태스크가 있는 파트만 동시 실행**한다. 보안 사전 리뷰(Step 4-0)는 구현 전에 완료한다. api-spec.md가 존재하면 BE와 FE는 이를 공통 계약으로 참조하여 **완전 병렬 실행**한다.
- Phase 4.5는 Phase 4 완료 후 **자동 진행**한다.
- Phase 5의 Step 5-0(API Contract 검증)은 Step 5-1(병렬 리뷰) 시작 전에 완료한다. Step 5-1의 Tech Lead/QA/Security는 **동시 실행**한다 (리뷰 범위만 실행된 파트로 한정).
- Phase 6은 게이트 3 승인 후 **자동 실행**한다.

### Variable Resolution
> ※ `$BACKEND_PROJECT_DIR`, `$FRONTEND_PROJECT_DIR` 변수는 `.jarfis-state.json`의 `workspace` 필드에서 치환한다. (workspace 설정 규칙 참조)
> ※ 학습/프로필 변수(`$LEARNINGS`, `$PROJECT_CONTEXT`, `$BE_PROJECT_PROFILE`, `$FE_PROJECT_PROFILE`)의 소스 경로와 주입 규칙은 Phase 0의 "주입 규칙" 섹션 참조. 파일이 없으면 빈 문자열로 치환한다.

### File Handoff Protocol
1. 각 에이전트는 이전 Phase의 산출물 파일을 **읽어서** 컨텍스트로 사용한다.
2. 산출물은 반드시 지정된 파일 경로에 저장한다.
3. `$DOCS_DIR/` 디렉토리(`.jarfis/works/{YYYYMMDD}/{작업명-slug}/`)가 없으면 자동 생성한다.
4. 파일 충돌 시: 나중에 쓰는 에이전트가 기존 내용을 유지하고 자신의 섹션을 **추가**한다.

### Gate Point Rules
1. 게이트에서는 반드시 산출물 파일 내용을 **요약하여 사용자에게 보여준다**.
2. 사용자가 "수정"을 요청하면, 해당 Phase의 에이전트를 수정 사항과 함께 **재실행**한다.
3. 사용자가 "승인"하면 다음 Phase로 **자동 진행**한다.
4. 사용자가 "중단"하면 워크플로우를 **즉시 종료**한다 (Phase 6은 실행하지 않음).

### SuperClaude Integration
필요 시 다음 /sc 명령을 Phase 내에서 활용할 수 있다:
- `/sc:brainstorm` — Phase 1에서 아이디어 확장
- `/sc:design` — Phase 2에서 설계 보완
- `/sc:implement` — Phase 4에서 구현 보조
- `/sc:analyze` — Phase 5에서 코드 분석 보조
- `/sc:test` — Phase 5에서 테스트 실행

### Progress Display
각 Phase 시작 시 **`.jarfis-state.json`을 읽고** 진행 상태를 표시한다:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 JARFIS Workflow — Phase N: [Phase Name]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 기획: [기획 내용 요약]
✅ Phase 1 → ✅ Phase 2&3 → 🔄 Phase 4 → ⬜ Phase 4.5 → ⬜ Phase 5 → ⬜ Phase 6
👥 활성 역할: BE ✅ / FE ⬜ / UX ⬜ / DevOps ✅
📚 학습: 전역 ✅ / 프로젝트 ✅
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Resume After Context Compression
컨텍스트 압축이 감지되거나, 현재 워크플로우 상태가 불확실할 때:
1. `$DOCS_DIR/.jarfis-state.json`을 읽는다. (`$DOCS_DIR`을 모르는 경우, `.jarfis/works/` 디렉토리에서 가장 최근 상태 파일을 찾는다.)
2. `docs_dir` 필드에서 `$DOCS_DIR` 경로를 복원한다.
3. `current_phase`와 각 Phase의 status를 확인한다.
4. `last_checkpoint`를 확인하여 마지막 체크포인트 시점의 진행 상황을 파악한다.
5. `"in_progress"` 상태인 Phase부터 이어서 진행한다.

**Compact 백업 확인 (PreCompact 훅 연동):**
- auto-compact가 실행되면 `$DOCS_DIR/.compact-backups/` 디렉토리에 상태 파일 백업이 자동 생성된다.
- 상태 파일이 손상되었거나 비어있을 경우, `.compact-backups/last_compact.json`을 확인하고 가장 최근 `state_*.json` 백업에서 복구한다.
- 백업 디렉토리가 없으면 PreCompact 훅이 미설정된 것이므로, 현재 상태 파일만으로 복구를 시도한다.
5. 이미 `"completed"` 된 Phase는 절대 재실행하지 않는다.
6. 산출물 파일이 존재하는지 확인하여 실제 완료 여부를 교차 검증한다.
