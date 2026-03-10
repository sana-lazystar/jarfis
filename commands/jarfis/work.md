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

산출물은 `$JARFIS_WORKSPACE_DIR/works/{YYYYMMDD}/{작업물명}/` 디렉토리에 저장한다 (`$DOCS_DIR`).
> ※ `$JARFIS_WORKSPACE_DIR` 결정 규칙은 "Execution Rules > Workspace Dir Resolution" 참조.

- 워크플로우 시작 시 `$DOCS_DIR` 값을 결정하고, `.jarfis-state.json`의 `docs_dir` 필드에 **절대경로**로 저장한다.
- **프로젝트별 파일** (`project-profile.md`, `project-context.md`)은 각 프로젝트의 `.jarfis/`에 저장한다.

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
   - AskUserQuestion으로 작업물명(`$WORK_NAME`)을 입력받는다 (디렉토리명/Git 브랜치명으로 사용).
   - `$DOCS_DIR` = `$JARFIS_WORKSPACE_DIR/works/{YYYYMMDD}/$WORK_NAME` (절대경로). 디렉토리 생성 + `.jarfis-state.json` 초기화.
   > ※ `$JARFIS_WORKSPACE_DIR` 결정 규칙은 "Execution Rules > Workspace Dir Resolution" 참조.

   **0-a-2. Meeting 감지**
   - `$ARGUMENTS`에 `--meeting {기획명}` 있으면 → `$MEETING_REF` 설정, `$MEETING_DIR` = `./.jarfis/meetings/*/$MEETING_REF/` (glob)
   - 플래그 없으면 → `./.jarfis/meetings/*/summary.md` 스캔, `idea` 필드와 `$ARGUMENTS` 키워드 매칭. 관련 미팅 발견 시 AskUserQuestion으로 참조 여부 확인.
   - 미발견/미선택 시 `$MEETING_REF` = 빈 문자열

   **0-a-3. Meeting 컨텍스트 로드**
   - `$MEETING_REF` 있으면: `$MEETING_DIR/`의 `summary.md`, `meeting-notes.md`, `decisions.md`, `tech-research.md`(선택)를 읽어 변수 저장. `.jarfis-state.json`에 `meeting_ref`, `meeting_dir` 기록.
   - 없으면: 모든 `$MEETING_*` 변수 = 빈 문자열

   **0-a-4. Workspace Detection (프로젝트 구조 확인)**

   AskUserQuestion으로 프로젝트 구조를 확인하고 `.jarfis-state.json`의 `workspace` 필드를 즉시 기록한다.

   | 선택 | workspace.type | BE path | FE path | 비고 |
   |------|---------------|---------|---------|------|
   | Monorepo | monorepo | `.` | `.` | CWD가 git repo 아니면 경로 입력 |
   | Multi-project | multi-project | 입력 | 입력 | 각 경로 유효성 검증 |
   | FE만 | monorepo | `N/A` | `.` 또는 입력 | — |
   | BE만 | monorepo | `.` 또는 입력 | `N/A` | — |

   - 각 경로에서 `package.json`으로 프레임워크 자동 감지 (next→Next.js, nuxt→Nuxt 등)
   - `$BACKEND_PROJECT_DIR`, `$FRONTEND_PROJECT_DIR` 변수 설정 (`N/A`이면 빈 문자열)

   **0-b. Git 브랜치 동기화 및 생성**

   - **monorepo**: git repo 확인 → uncommitted 경고 → 기본 브랜치+develop pull → `git checkout -b $WORK_NAME develop` → `.jarfis-state.json` `branch` 기록. develop 없으면 기본 브랜치에서 분기 여부 확인.
   - **multi-project**: BE/FE 각 경로에서 독립적으로 동일 과정 반복. `.jarfis-state.json`에 `branches: { backend, frontend }` 기록.

1. **시스템 헬스체크** — `~/.claude/scripts/claude-cleanup.sh` 존재 시 진단 모드 실행. 좀비 5개↑ → AskUserQuestion, 1~4개 → 경고, 0개 → 무시.
2. `~/.claude/jarfis-learnings.md` → `$LEARNINGS`, `./.jarfis/project-context.md` → `$PROJECT_CONTEXT` (없으면 빈 문자열)
3. 프로젝트 프로필 로드: `./.jarfis/project-profile.md` (Phase 0), `$BACKEND_PROJECT_DIR/.jarfis/project-profile.md` + `$FRONTEND_PROJECT_DIR/.jarfis/project-profile.md` (Phase 4~5) → `$BE_PROJECT_PROFILE`, `$FE_PROJECT_PROFILE`

**주입 규칙:**
- Phase 1 (PO, Architect): `$LEARNINGS`의 Workflow Patterns + `$PROJECT_CONTEXT` 전체
- Phase 2 (Architect — Impact Analysis, 설계): `$BE_PROJECT_PROFILE` + `$FE_PROJECT_PROFILE` (존재 시)
- Phase 4 (BE/FE/DevOps): `$LEARNINGS`의 해당 역할 Agent Hints + `$PROJECT_CONTEXT` 전체 + **해당 역할의 `$PROJECT_PROFILE`**
- Phase 5 (Tech Lead/QA/Security): `$LEARNINGS`의 해당 역할 Agent Hints

학습/프로필 파일이 없으면 빈 문자열로 치환한다.

---

## Phase 1: Discovery

### 목표
사용자의 기획 의도를 명확히 하고, 기술적 실현가능성을 동시에 검증한다.

### 실행 순서

**Step 1-1: PO 역질문** (senior-product-owner)

> **미팅 참조 시 조건부 동작**: `$MEETING_REF`가 존재하면, 미팅 컨텍스트를 주입하고 미결 사항만 질문한다.

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
산출물(`press-release.md`, `prd.md`) 요약 표시 → 승인/수정/중단 선택

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

**Step 3-1: UX 화면 설계** (senior-ux-designer) — UX Designer 필요 시만 실행
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 3-2: PO 검증** (senior-product-owner) — UX Designer 필요 시만 실행
> 📄 프롬프트: `prompts/phase2.md` 해당 섹션을 읽어서 에이전트에 전달한다.

### 🔒 게이트 2: 사용자 컨펌
산출물(`impact-analysis.md`, `architecture.md`, `api-spec.md`, `tasks.md`, `test-strategy.md`, `ux-spec.md`) 요약 + 실행 파트 표시 → 승인/수정/중단 선택

---

## Phase 4: Implementation

### 목표
설계 문서를 기반으로 병렬 구현한다. 구현 전 Security가 사전 리뷰한다.
> ※ 스킵 판단: "Execution Rules > Skip Rules" 참조

### 실행 순서

**Step 4-0: 보안 사전 리뷰** (senior-security-engineer)
> 📄 프롬프트: `prompts/phase4.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 4-1: 병렬 구현** (tasks.md에 태스크가 있는 파트만 동시 실행)

Backend (senior-backend-engineer), Frontend (senior-frontend-engineer), DevOps (senior-devops-sre-engineer):
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
> ※ 스킵 판단: "Execution Rules > Skip Rules" 참조

### 실행 순서

**Step 5-0: API Contract 자동 검증** — **api-spec.md 존재 시만 실행**

Tech Lead (tech-lead):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 5-1: 병렬 리뷰** (3개 에이전트 동시 실행)

Tech Lead (tech-lead), QA (senior-qa-engineer), Security (senior-security-engineer):
> 📄 프롬프트: `prompts/phase5.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**결과 통합**: 실행된 에이전트의 리뷰 결과만 `$DOCS_DIR/review.md`에 통합 저장한다.

### 🔒 게이트 3: 최종 컨펌

> **병리 패턴 감지 (2회차 이상 재리뷰 시)**: `prompts/phase5.md`의 "Step 5-2 병리 패턴 감지" 절차 실행.

리뷰 결과 요약 (코드리뷰/API Contract/QA/보안/배포) → 승인/수정 후 재리뷰/중단/설계 재검토(병리 시) 선택

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
이번 워크플로우에서 얻은 학습을 **전역 학습 파일**과 **프로젝트 컨텍스트 파일**에 축적한다.

### 실행 순서

**Step 6-1: 회고 작성** (tech-lead)
> 📄 프롬프트: `prompts/phase6.md` 해당 섹션을 읽어서 에이전트에 전달한다.

**Step 6-2: 학습 파일 업데이트** (오케스트레이터가 직접 실행)

retrospective.md를 읽고 다음 두 파일에 분배 저장한다:

**1. 전역 학습 — `~/.claude/jarfis-learnings.md`**
> 📄 템플릿: `templates/learnings.md`를 읽어서 산출물 양식으로 사용한다.

관리 규칙: 기존 파일에 추가 (중복이면 업데이트), 오래된 항목 제거, 날짜 기록

**2. 프로젝트 컨텍스트 — `./.jarfis/project-context.md`**
> 📄 템플릿: `templates/project-context.md`를 읽어서 산출물 양식으로 사용한다.

관리 규칙: 기존 파일에 업데이트 (새 정보 추가, 오래된 정보 갱신)

---

## Execution Rules

### Workflow State Management (컨텍스트 유실 방어)

**`$DOCS_DIR/.jarfis-state.json`**을 워크플로우의 단일 진실 공급원(SSOT)으로 사용한다.

> 📄 상태 파일 스키마 및 필드 설명: `templates/jarfis-state-schema.md`를 참조한다.

**상태 파일 관리 규칙:**
1. 워크플로우 시작 시 `$DOCS_DIR` 결정 + 상태 파일 초기화 (`current_phase: 0`, 모든 Phase `pending`)
2. Phase 시작/완료 시 status 업데이트 (`in_progress` → `completed`/`skipped`)
3. 에이전트 실행 시 개별 상태 업데이트
4. 게이트 통과 시 결과 기록 + `current_phase` 갱신
5. 매 Phase 시작 전 상태 파일 읽기 — 이미 완료된 Phase는 재실행하지 않음
6. 상태 변경 시마다 `last_checkpoint` 갱신 (timestamp, phase, summary)
7. 워크플로우 종료 시 `current_phase`를 `"done"`으로 설정

**`api_spec_required` 판단**: `required_roles.backend == true AND frontend == true` → `true`, 그 외 → `false`

### Workspace Dir Resolution

`$JARFIS_WORKSPACE_DIR` = `~/.claude/.jarfis-works-dir` 파일 내용 (없으면 `~/.jarfis-workspace` 기본값, 자동 생성)

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

### Skip Rules

**핵심 원칙**: 에이전트는 할 일이 있을 때만 실행한다.

**Phase 4 스킵**: `tasks.md`의 각 섹션이 "N/A"이면 해당 에이전트 SKIP. 단, 최소 1개 파트는 반드시 실행한다 (전체 N/A 불가).
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
2. "수정" → 해당 Phase 에이전트 재실행. "승인" → 다음 Phase 자동 진행. "중단" → 즉시 종료.

### SuperClaude Integration
필요 시: `/sc:brainstorm`(Phase 1), `/sc:design`(Phase 2), `/sc:implement`(Phase 4), `/sc:analyze`·`/sc:test`(Phase 5)

### Progress Display
각 Phase 시작 시 `.jarfis-state.json`을 읽고 진행 상태 바 + 활성 역할 + 학습 로드 상태를 표시한다.

### Resume After Context Compression
1. `$DOCS_DIR/.jarfis-state.json` 읽기 (`$DOCS_DIR` 모르면 `$JARFIS_WORKSPACE_DIR/works/`에서 최근 파일 탐색)
2. `docs_dir`, `current_phase`, `last_checkpoint` 확인
3. `in_progress` Phase부터 이어서 진행. `completed` Phase는 절대 재실행하지 않음.
4. **Compact 백업**: `$DOCS_DIR/.compact-backups/` 디렉토리에서 상태 파일 복구 가능 (PreCompact 훅 연동)
5. 산출물 파일 존재 여부로 실제 완료 교차 검증
