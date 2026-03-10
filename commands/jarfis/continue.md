# JARFIS Continue — 완료된 워크플로우 이어서 작업

사용자가 다음 후속 작업을 요청했습니다: $ARGUMENTS

이전 워크플로우의 산출물과 브랜치를 재활용하여 효율적으로 후속 작업을 수행합니다.

**플래그 옵션:**
- `--workflow {경로}` — 워크플로우 디렉토리를 직접 지정 (예: `.jarfis/works/20260310/결제-시스템`)
- `--mode fix|extend` — 모드를 명시적으로 지정 (자동 분류 없이 바로 해당 모드 실행)

---

## Step 0: 이전 워크플로우 탐색

**0-0. `$ARGUMENTS`에서 플래그를 파싱한다:**
- `--workflow {경로}` → `$WORKFLOW_PATH`에 저장, `$ARGUMENTS`에서 플래그 제거
- `--mode fix|extend` → `$FORCED_MODE`에 저장, `$ARGUMENTS`에서 플래그 제거
- 플래그가 없으면 각각 빈 값

**0-1. 워크플로우 선택:**

`$WORKFLOW_PATH`가 지정된 경우:
- 해당 경로에 `.jarfis-state.json`이 존재하는지 확인한다.
- 존재하면 해당 워크플로우를 선택한다 (완료 여부 무관 — 사용자가 명시적으로 지정했으므로).
- 존재하지 않으면: "지정된 경로에 워크플로우가 없습니다: `{$WORKFLOW_PATH}`" 출력 후 종료.

`$WORKFLOW_PATH`가 없는 경우 (기존 자동 탐색):

1. `.jarfis/works/` 디렉토리를 스캔하여 완료된 워크플로우를 찾는다:
   ```bash
   find .jarfis/works/ -name ".jarfis-state.json" -type f 2>/dev/null
   ```

2. 각 상태 파일을 읽어 `current_phase`가 `"done"` 또는 마지막 Phase가 `"completed"`인 워크플로우를 필터링한다.

3. **워크플로우가 1개**: 자동 선택
   **워크플로우가 2개 이상**: AskUserQuestion으로 선택:
   ```
   question: "어떤 워크플로우를 이어서 진행하시겠어요?"
   header: "Workflow"
   options:
     - label: "{작업물명1} ({날짜})"
       description: "{PRD 요약 or project_name}"
     - label: "{작업물명2} ({날짜})"
       description: "{PRD 요약 or project_name}"
   ```
   **워크플로우가 0개**: "완료된 워크플로우가 없습니다. `/jarfis:work`로 새 워크플로우를 시작하세요." 출력 후 종료.

4. 선택된 워크플로우의 상태 파일에서 다음을 복원한다:
   - `$DOCS_DIR` — 산출물 디렉토리
   - `$WORK_NAME` — 작업물명
   - `$BRANCH` — Git 브랜치명
   - `required_roles` — 필요 역할
   - `workspace` — 프로젝트 구조

5. 이전 워크플로우의 핵심 산출물을 빠르게 읽는다:
   - `$DOCS_DIR/prd.md` — PRD (기획 요약)
   - `$DOCS_DIR/tasks.md` — 태스크 분해 (완료된 항목 확인)
   - `$DOCS_DIR/architecture.md` — 아키텍처 (첫 50줄만, 개요 파악용)

6. 컨텍스트 로드:
   - `~/.claude/jarfis-learnings.md` — 학습 파일
   - `./.jarfis/context.md` — 프로젝트 컨텍스트

---

## Step 1: 후속 작업 분류

### 플래그로 모드가 지정된 경우

`$FORCED_MODE`가 있으면 자동 분류를 건너뛰고 해당 모드로 바로 진행한다.

### 자동 분류 (플래그 없는 경우)

사용자의 요청(`$ARGUMENTS`)과 이전 워크플로우 컨텍스트를 분석하여 모드를 판단한다.

| 신호 | 모드 |
|------|------|
| "수정", "버그", "fix", "고쳐", "안 돼", "에러", "테스트 실패" | **Fix** |
| "추가", "기능", "새로", "확장", "더", "리팩토링" | **Extend** |
| 판단 불가 | AskUserQuestion |

### 판단 불가 시 AskUserQuestion:
```
question: "어떤 유형의 후속 작업인가요?"
header: "Mode"
options:
  - label: "Fix — 수정/버그 수정"
    description: "기존 구현의 문제 수정. 설계 변경 없이 Phase 4→5→6 실행"
  - label: "Extend — 기능 추가/확장"
    description: "기존 설계 위에 새 기능 추가. Phase 1→2→4→5→6 경량 실행"
```

### 모드별 실행 흐름 요약

```
Fix 모드:
  Step 2: 수정 사항 정리 → Step 4: 구현 → Step 5: 리뷰 → Step 6: 회고

Extend 모드:
  Step 2: PRD 보강 → Step 3: 설계 보강 → Step 4: 구현 → Step 5: 리뷰 → Step 6: 회고
```

---

## Step 2: 작업 준비

### Git 브랜치 확인

1. 현재 브랜치가 `$BRANCH`인지 확인한다.
   - 아니면: `git checkout $BRANCH` 실행
   - 브랜치가 삭제되었거나 없으면: 기본 브랜치(main/develop)에서 새 브랜치 `$WORK_NAME-follow-up` 생성

2. uncommitted 변경사항 확인 → 있으면 사용자에게 경고

### 상태 파일 갱신

`.jarfis-state.json`에 follow-up 정보를 추가한다:
```json
{
  "current_phase": "follow-up",
  "follow_up": {
    "mode": "fix|extend",
    "description": "$ARGUMENTS 요약",
    "started_at": "ISO8601",
    "iteration": 1
  }
}
```
(`iteration`은 같은 워크플로우에서 continue를 반복 실행할 때 증가)

기존 `follow_up` 필드가 있으면 `iteration`을 +1 한다.

---

## Step 3: Fix 모드 실행

### 3-1. 수정 사항 정리

사용자의 수정 요청을 분석하여 수정 대상을 정리한다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔧 JARFIS Continue — Fix 모드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 원본 기획: {PRD 제목}
🔧 수정 사항: {$ARGUMENTS 요약}
📂 이전 산출물: {$DOCS_DIR}
🌿 브랜치: {$BRANCH}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

1. `$DOCS_DIR/tasks.md`를 읽어 기존 태스크 구조를 파악한다.
2. 수정 사항을 기존 역할(BE/FE/DevOps)에 매핑하여 fix 태스크를 생성한다.
3. 기존 `tasks.md`에 `## Follow-up Fix (#{iteration})` 섹션을 **추가**한다:
   ```markdown
   ## Follow-up Fix (#1)
   > 요청: {수정 사항 요약}

   ### BE Tasks
   - [ ] FIX-BE-1: {수정 내용}

   ### FE Tasks
   - [ ] FIX-FE-1: {수정 내용}
   ```

### 3-2. 구현 (Phase 4 재활용)

work.md의 Phase 4 에이전트 프롬프트(`prompts/phase4.md`)를 사용하되, 다음을 조정한다:

- **태스크 소스**: `tasks.md`의 `## Follow-up Fix` 섹션만 실행
- **기존 코드 참조**: 이전 Phase 4에서 구현한 코드가 이미 있으므로, 해당 코드 기반으로 수정
- **커밋 형식**: `jarfis(fix/BE-N):`, `jarfis(fix/FE-N):`

에이전트 실행:
- `required_roles`에서 fix 태스크가 있는 역할만 실행
- 각 에이전트에게 전달할 컨텍스트:
  - `$DOCS_DIR/prd.md` — 원본 PRD
  - `$DOCS_DIR/architecture.md` — 아키텍처
  - `$DOCS_DIR/tasks.md` — 태스크 (Follow-up Fix 섹션 중심)
  - `$LEARNINGS` — 해당 역할 Agent Hints
  - `$PROJECT_CONTEXT` — 프로젝트 컨텍스트

### 3-3. 리뷰 (Phase 5 경량 실행)

work.md의 Phase 5를 경량으로 실행한다:

- **Tech Lead 리뷰만** 실행 (QA/Security는 원본에서 이미 통과했으므로 스킵)
  - 단, 보안 관련 수정이면 Security도 실행
- 리뷰 결과를 `$DOCS_DIR/review.md`에 `## Follow-up Review (#N)` 섹션으로 추가
- 수정 필요 시 → 3-2로 돌아가 재수정 (최대 2회)

### 3-4. 🔒 게이트: 사용자 컨펌

```
Fix 작업이 완료되었습니다.

📋 수정 내역:
- [수정 사항 요약]

📄 리뷰 결과: $DOCS_DIR/review.md

1. ✅ 승인 — 회고 후 완료
2. ✏️ 추가 수정 — 수정할 내용을 알려주세요
3. ❌ 완료 — 회고 없이 종료
```

### 3-5. 회고 (Phase 6 경량)

`prompts/phase6.md`를 참조하되, 회고 범위를 fix 작업으로 한정한다:
- "이번 Fix에서 어떤 문제가 있었고, 원본 워크플로우에서 어떻게 예방할 수 있었을까?"
- 회고 결과를 `$DOCS_DIR/retrospective.md`에 `## Follow-up Retrospective (#N)` 섹션으로 추가
- 학습 항목이 있으면 `jarfis-learnings.md`에 추가

---

## Step 4: Extend 모드 실행

### 4-1. PRD 보강 (Phase 1 경량)

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚀 JARFIS Continue — Extend 모드
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 원본 기획: {PRD 제목}
➕ 확장 내용: {$ARGUMENTS 요약}
📂 이전 산출물: {$DOCS_DIR}
🌿 브랜치: {$BRANCH}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

PO (senior-product-owner)에게 다음 프롬프트로 호출:
```
기존 PRD를 참조하여 확장 요구사항을 추가해주세요.

## 기존 PRD
{$DOCS_DIR/prd.md 내용}

## 확장 요청
{$ARGUMENTS}

## 지시사항
1. 기존 PRD의 구조와 스타일을 유지하세요.
2. 새 요구사항을 기존 PRD 뒤에 "## Extension #{iteration}" 섹션으로 추가하세요.
3. 기존 기능과의 의존성/충돌을 분석하세요.
4. 추가 역할이 필요한지 판단하세요 (기존: {required_roles 요약}).
5. Working Backwards는 생략합니다 (기존 press-release.md 참조).
6. 불명확한 점이 있으면 사용자에게 역질문하세요.
```

PO의 역질문이 있으면 사용자에게 전달 → 답변 후 PRD 보강 완료.

### 4-2. 설계 보강 (Phase 2 경량)

Architect (technical-architect)에게 호출:
```
기존 아키텍처를 기반으로 확장 설계를 추가해주세요.

## 기존 아키텍처
{$DOCS_DIR/architecture.md 내용}

## 확장 PRD
{prd.md의 Extension 섹션}

## 지시사항
1. 기존 아키텍처에 미치는 영향을 분석하세요.
2. 변경/추가할 컴포넌트를 식별하세요.
3. architecture.md에 "## Extension #{iteration}" 섹션으로 추가하세요.
4. 기존 ADR과 충돌하는 결정이 있으면 새 ADR을 추가하세요.
```

Tech Lead (tech-lead)에게 호출:
```
확장 요구사항에 대한 태스크를 분해해주세요.

## 기존 태스크
{$DOCS_DIR/tasks.md 내용}

## 확장 설계
{architecture.md Extension 섹션}

## 확장 PRD
{prd.md Extension 섹션}

## 지시사항
1. tasks.md에 "## Extension Tasks (#N)" 섹션을 추가하세요.
2. 기존 태스크와의 의존성을 명시하세요.
3. 기존과 동일한 형식(BE/FE/DevOps 분류, 체크박스)을 따르세요.
```

### 4-3. 🔒 게이트: 사용자 컨펌 (설계 리뷰)

```
확장 설계가 완료되었습니다.

📄 산출물:
- $DOCS_DIR/prd.md (Extension 섹션 추가)
- $DOCS_DIR/architecture.md (Extension 섹션 추가)
- $DOCS_DIR/tasks.md (Extension Tasks 추가)

확장 설계를 검토해주세요:
1. ✅ 승인 — 구현으로 진행합니다
2. ✏️ 수정 요청 — 수정할 내용을 알려주세요
3. ❌ 중단 — 워크플로우를 종료합니다
```

### 4-4. 구현 (Phase 4 재활용)

Fix 모드의 3-2와 동일하되:
- **태스크 소스**: `tasks.md`의 `## Extension Tasks` 섹션
- **커밋 형식**: `jarfis(ext/BE-N):`, `jarfis(ext/FE-N):`

### 4-5. 리뷰 (Phase 5 실행)

work.md의 Phase 5를 실행하되:
- 리뷰 범위를 Extension 태스크로 한정
- Tech Lead + QA 리뷰 실행 (새 기능이므로 QA 필요)
- Security는 보안 관련 변경이 있을 때만 실행
- 리뷰 결과를 `$DOCS_DIR/review.md`에 `## Extension Review (#N)` 섹션으로 추가

### 4-6. 🔒 게이트: 최종 컨펌

Fix 모드의 3-4와 동일한 형식.

### 4-7. 회고 (Phase 6 경량)

Fix 모드의 3-5와 동일하되, 회고 관점을 확장 작업에 맞춤:
- "확장 기능이 기존 아키텍처와 잘 통합되었는가?"
- "확장 시 발견된 기존 설계의 개선점은?"

---

## Step 5: 완료

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ JARFIS Continue 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 원본: {작업물명}
🔧 모드: {Fix|Extend} (#{iteration})
✅ 완료 내역:
   - {변경 사항 요약}
📂 갱신된 산출물: {$DOCS_DIR}
🌿 브랜치: {$BRANCH}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

상태 파일의 `follow_up.status`를 `"completed"`로 갱신한다.
