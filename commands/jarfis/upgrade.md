# JARFIS Upgrade — 학습 항목 관리 및 시스템 적용

`~/.claude/jarfis-learnings.md`의 학습 항목을 관리하고, 실제 에이전트/워크플로우 프롬프트에 적용합니다.

---

## 실행 흐름

### Step 1: 학습 파일 로드

`~/.claude/jarfis-learnings.md` 파일을 읽어라.
파일이 없으면 "학습 파일이 아직 없습니다. `/jarfis` 워크플로우를 먼저 실행하세요."라고 안내하고 종료하라.

파일이 존재하면, 섹션별로 파싱하여 현재 학습 목록을 사용자에게 보여줘라:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JARFIS Learnings — 현재 학습 목록
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

## Agent Hints

### Backend Engineer
1. (항목 내용)
2. (항목 내용)

### Frontend Engineer
1. (항목 내용)
...

## Workflow Patterns
1. (항목 내용)
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 2: 액션 선택

AskUserQuestion을 사용하여 다음 중 하나를 선택하게 하라:

```
question: "어떤 작업을 수행할까요?"
header: "Action"
options:
  - label: "학습 적용 (Recommended)"
    description: "학습 항목을 에이전트/워크플로우 프롬프트에 반영합니다"
  - label: "항목 관리"
    description: "학습 항목 추가/수정/삭제"
  - label: "전체 비우기"
    description: "학습 파일의 모든 항목을 제거합니다 (구조는 유지)"
  - label: "종료"
    description: "종료합니다"
```

### Step 3: 액션별 처리

---

#### [학습 적용] 선택 시

학습 항목을 실제 에이전트 프롬프트와 워크플로우에 반영하는 핵심 기능이다.

##### 3-A-1. 적용 대상 매핑

학습 항목을 적용 대상 파일에 매핑하라:

| learnings 섹션 | 적용 대상 파일 |
|---------------|---------------|
| `Agent Hints > Frontend Engineer` | `~/.claude/agents/jarfis/senior-frontend-engineer.md` |
| `Agent Hints > Backend Engineer` | `~/.claude/agents/jarfis/senior-backend-engineer.md` |
| `Agent Hints > QA Engineer` | `~/.claude/agents/jarfis/senior-qa-engineer.md` |
| `Agent Hints > Tech Lead` | `~/.claude/agents/jarfis/tech-lead.md` |
| `Agent Hints > Security Engineer` | `~/.claude/agents/jarfis/senior-security-engineer.md` |
| `Agent Hints > DevOps Engineer` | `~/.claude/agents/jarfis/senior-devops-sre-engineer.md` |
| `Agent Hints > UX Designer` | `~/.claude/agents/jarfis/senior-ux-designer.md` |
| `Agent Hints > Product Owner` | `~/.claude/agents/jarfis/senior-product-owner.md` |
| `Agent Hints > Architect` | `~/.claude/agents/jarfis/technical-architect.md` |
| `Workflow Patterns` | `~/.claude/commands/jarfis/work.md` |

##### 3-A-2. Scope 자동 분류 + Dialectic Review

각 학습 항목에 scope를 자동 분류한다:

**자동 분류 규칙**:
1. 특정 파일 경로/디렉토리 언급 → `[project]`
2. 특정 프레임워크 버전/설정 언급 → `[project]` 후보 (판단 불가 시 `[ambiguous]`)
3. "이 프로젝트에서", "이 코드베이스" 등 한정 표현 → `[project]`
4. 범용 도구/기법/원칙 → `[universal]`
5. 판단 불가 → `[ambiguous]`

**분류 결과 표시**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
학습 Scope 분류 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[universal] FE-1: img 태그 대량 수정 시 인덴테이션 일관성 검증
[project]  FE-2: src/components/shared/ 하위 컴포넌트 수정 시 ...
[ambiguous] QA-1: Playwright PerformanceObserver 설정 패턴
...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Dialectic Review 게이트**:
- 모든 항목이 `[universal]` 또는 `[project]`로 명확 분류 → 토론 SKIP, 분류 결과만 사용자에게 보여주고 확인
- `[ambiguous]` 항목이 1개 이상 → 해당 항목에 대해서만 토론 실행:
  1. **Advocate 호출** (Agent tool, subagent_type: `general-purpose`):
     - jarfis-advocate.md 페르소나를 프롬프트에 포함
     - prompt: "다음 학습 항목의 scope를 판단하세요: [항목 내용]. 이것이 범용 원칙인 이유를 논증하세요."
  2. **Critic 호출** (Agent tool, subagent_type: `general-purpose`):
     - jarfis-critic.md 페르소나를 프롬프트에 포함
     - prompt: "다음 학습 항목의 scope를 판단하세요: [항목 내용]. Advocate 의견: [결과]. 이것이 프로젝트 종속인 이유를 논증하세요."
  3. 합의 or 사용자 판단 → `[universal]` 또는 `[project]`로 확정

##### 3-A-2b. 적용 계획 표시

분류 확정 후, 적용 대상을 scope별로 매핑하여 보여줘라:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
학습 적용 계획
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🌐 Universal 적용:
[FE] senior-frontend-engineer.md → Learned Rules ← 3개 항목
  1. img 태그 대량 수정 시 인덴테이션 일관성 검증...
  2. ...

[WF] work.md → Learned Workflow Patterns ← 2개 항목
  1. ...

📁 Project-Specific 적용:
[FE] .jarfis/project-context.md → Frontend 섹션 ← 1개 항목
  1. src/components/shared/ 하위 컴포넌트 수정 시 ...

[WF] .jarfis/project-context.md → Workflow 섹션 ← 2개 항목
  1. ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

##### 3-A-3. 적용 범위 선택

AskUserQuestion으로 적용 범위를 선택하게 하라:

```
question: "어떤 항목을 적용할까요?"
header: "Scope"
options:
  - label: "전체 적용"
    description: "모든 학습 항목을 해당 파일에 적용합니다"
  - label: "선택 적용"
    description: "적용할 항목을 직접 선택합니다"
```

"선택 적용" 시: AskUserQuestion의 **multiSelect: true**로 적용할 항목을 선택하게 하라.

##### 3-A-4. 에이전트 파일 적용 방법

**scope에 따라 적용 경로가 다르다:**

| 학습 scope | 적용 대상 |
|-----------|----------|
| `[universal]` Agent Hints | `~/.claude/agents/jarfis/{role}.md`의 `## Learned Rules` |
| `[project]` Agent Hints | `./.jarfis/project-context.md`의 해당 역할 섹션 |

**`[universal]` 항목 적용**:

대상 에이전트 파일을 읽고, 파일 끝에 `## Learned Rules` 섹션이 있는지 확인하라:

- **섹션이 없으면**: 파일 맨 끝에 새로 추가:
  ```markdown

  ## Learned Rules

  아래 규칙은 실제 프로젝트에서 검증된 학습 항목이다. 반드시 준수하라.

  - (학습 항목 내용, 날짜 제거)
  ```
- **섹션이 이미 있으면**: 기존 항목 뒤에 새 항목을 추가하되, **중복 체크**하라 (내용이 유사하면 스킵).

**`[project]` 항목 적용**:

`./.jarfis/project-context.md`를 읽고, 해당 역할 섹션이 있는지 확인하라:

- **파일이 없으면**: `./.jarfis/project-context.md`를 생성하고 기본 구조를 만든다.
- **역할 섹션이 없으면**: `## Project-Specific Learned Rules` 하위에 `### {역할명}` 섹션을 추가한다.
- **역할 섹션이 있으면**: 기존 항목 뒤에 새 항목을 추가하되, **중복 체크**.

날짜 정보 `(YYYY-MM-DD)` 는 적용 시 제거하라 — 프롬프트에 날짜는 불필요하다.

##### 3-A-5. 워크플로우 파일 적용 방법

**scope에 따라 적용 경로가 다르다:**

| 학습 scope | 적용 대상 |
|-----------|----------|
| `[universal]` Workflow Patterns | `work.md`의 `## Learned Workflow Patterns` |
| `[project]` Workflow Patterns | `./.jarfis/project-context.md`의 Workflow 섹션 |

**`[universal]` 항목 적용**:

`work.md`에서 `## Learned Workflow Patterns` 섹션이 있는지 확인하라:

- **섹션이 없으면**: `## Phase T` 바로 위에 새로 추가:
  ```markdown
  ## Learned Workflow Patterns

  아래 패턴은 실제 워크플로우 실행에서 검증된 학습이다. Phase 진행 시 참고하라.

  - (학습 항목 내용, 날짜/확인 횟수 제거)

  ---
  ```
- **섹션이 이미 있으면**: 기존 항목 뒤에 새 항목을 추가하되, **중복 체크**.

**`[project]` 항목 적용**:

`./.jarfis/project-context.md`를 읽고, `## Project-Specific Workflow Patterns` 섹션이 있는지 확인하라:

- **섹션이 없으면**: 해당 섹션을 추가한다.
- **섹션이 있으면**: 기존 항목 뒤에 새 항목을 추가하되, **중복 체크**.

날짜 및 확인 횟수 정보 `(YYYY-MM-DD, N회 확인)` 는 적용 시 제거하라.

##### 3-A-6. 적용 후 처리

적용 결과를 보여주고, AskUserQuestion으로 learnings 파일 처리를 선택하게 하라:

```
question: "적용 완료된 항목을 learnings 파일에서 어떻게 처리할까요?"
header: "Cleanup"
options:
  - label: "적용된 항목만 비우기 (Recommended)"
    description: "적용된 항목만 learnings에서 제거합니다"
  - label: "그대로 유지"
    description: "learnings 파일을 변경하지 않습니다 (다음에 다시 적용 가능)"
  - label: "전체 비우기"
    description: "learnings 파일의 모든 항목을 제거합니다"
```

비우기 시: 섹션 헤더 구조는 유지하고 항목(`-`로 시작하는 줄)만 제거하라.

##### 3-A-7. 버전 범프 (PATCH)

학습 적용은 에이전트 프롬프트 내용 변경이므로 PATCH 범프한다:
- `~/.claude/.jarfis-source`에서 Git repo 경로를 읽는다 (없으면 `~/repos/jarfis`).
- `{repo_path}/VERSION`의 PATCH를 +1 한다.
- `~/.claude/.jarfis-version`을 새 버전으로 갱신한다.
- `jarfis-index.md`의 `Version:` 표기를 새 버전으로 갱신한다.
- `{repo_path}/CHANGELOG.md`의 `[Unreleased]` 섹션에 적용 내역을 추가한다.

##### 3-A-8. Repo 동기화

이번 학습 적용에서 수정된 파일들을 Git repo에 반영한다:
- `~/.claude/.jarfis-source`에서 Git repo 경로를 읽는다 (없으면 `~/repos/jarfis`).
- 수정된 에이전트 파일: `~/.claude/agents/jarfis/*` → `{repo_path}/agents/jarfis/*`
- 수정된 워크플로우 파일 (Workflow Patterns 적용 시): `~/.claude/commands/jarfis/work.md` → `{repo_path}/commands/jarfis/work.md`
- `jarfis-index.md`: `~/.claude/commands/jarfis/jarfis-index.md` → `{repo_path}/commands/jarfis/jarfis-index.md`
- `.jarfis-version`, `.jarfis-source`, `jarfis-learnings.md`, `.jarfis-state.json`은 복사하지 않는다 (로컬 전용).
- 동기화 후 표시: `🔄 Repo 동기화: {N}개 파일 → {repo_path}`

적용 결과를 보여주고 Step 2로 돌아가라.

---

#### [항목 관리] 선택 시

AskUserQuestion으로 세부 액션을 선택하게 하라:

```
question: "어떤 관리 작업을 수행할까요?"
header: "Manage"
options:
  - label: "항목 삭제"
    description: "불필요한 학습 항목을 제거합니다"
  - label: "항목 수정"
    description: "기존 학습 내용을 업데이트합니다"
  - label: "항목 추가"
    description: "새로운 학습을 직접 입력합니다"
```

##### [삭제]

1. 전체 학습 항목을 번호와 함께 나열하라 (섹션 구분 포함).
2. AskUserQuestion의 **multiSelect: true**를 사용하여 삭제할 항목들을 선택하게 하라.
   - 각 option의 label은 항목 번호와 내용 요약 (예: "[FE-1] img 태그 인덴테이션 검증")
   - description은 전체 항목 내용
3. 선택된 항목들을 `~/.claude/jarfis-learnings.md`에서 제거하라.
4. 삭제 결과를 보여주고 Step 2로 돌아가라.

##### [수정]

1. 전체 학습 항목을 번호와 함께 나열하라.
2. AskUserQuestion을 사용하여 수정할 항목 **하나**를 선택하게 하라.
3. 선택된 항목의 현재 내용을 보여주고, AskUserQuestion으로 새 내용을 입력받아라.
   - question: "새로운 내용을 입력해주세요 (현재: [현재 내용 요약])"
   - "Other"를 통해 자유 입력
4. 입력받은 내용으로 `~/.claude/jarfis-learnings.md`의 해당 항목을 교체하라.
5. 수정 결과를 보여주고 Step 2로 돌아가라.

##### [추가]

1. AskUserQuestion을 사용하여 추가할 섹션을 선택하게 하라:
   ```
   question: "어느 섹션에 추가할까요?"
   header: "Section"
   options:
     - label: "Backend Engineer"
       description: "백엔드 개발 관련 학습"
     - label: "Frontend Engineer"
       description: "프론트엔드 개발 관련 학습"
     - label: "QA Engineer"
       description: "QA/테스트 관련 학습"
     - label: "Workflow Patterns"
       description: "워크플로우 판단 패턴"
   ```
   - "Other"를 통해 Tech Lead, Security Engineer 등 다른 섹션도 입력 가능
2. AskUserQuestion으로 학습 내용을 입력받아라.
   - question: "추가할 학습 내용을 입력해주세요"
   - "Other"를 통해 자유 입력
3. 오늘 날짜를 자동 추가하여 `~/.claude/jarfis-learnings.md`의 해당 섹션에 항목을 추가하라.
   - 형식: `- (입력 내용) (YYYY-MM-DD)`
   - Workflow Patterns의 경우: `- (입력 내용) (YYYY-MM-DD, 확인 1회)`
4. 추가 결과를 보여주고 Step 2로 돌아가라.

---

#### [전체 비우기] 선택 시

1. AskUserQuestion으로 확인하라:
   ```
   question: "정말로 모든 학습 항목을 비울까요? 이 작업은 되돌릴 수 없습니다."
   header: "Confirm"
   options:
     - label: "비우기 실행"
       description: "모든 항목을 제거합니다 (섹션 구조는 유지)"
     - label: "취소"
       description: "아무것도 하지 않고 돌아갑니다"
   ```
2. "비우기 실행" 선택 시: `~/.claude/jarfis-learnings.md`에서 모든 항목(`-`로 시작하는 줄)을 제거하라. 섹션 헤더(`#`, `##`, `###`)는 유지하라.
3. 결과를 보여주고 Step 2로 돌아가라.

---

#### [종료] 선택 시

최종 변경 요약을 보여주고 종료하라:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
JARFIS Upgrade 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
변경 사항:
- 적용: N건 (에이전트 M개 파일, 워크플로우 K건)
- 삭제: N건
- 수정: N건
- 추가: N건
- learnings 비우기: Y/N
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## 주의사항

- 파일 수정은 매 액션 완료 시마다 즉시 저장하라 (중간에 종료해도 손실 없도록).
- 섹션이 존재하지 않으면 새로 생성하라 (예: Security Engineer 섹션이 없는데 추가 요청 시).
- 항목 삭제 후 빈 섹션이 되면 섹션 헤더는 유지하되 항목만 제거하라.
- 파일 형식(마크다운 리스트, 날짜 형식 등)을 기존 형식과 일관되게 유지하라.
- **적용 시 중복 체크**: 이미 대상 파일의 `Learned Rules`/`Learned Workflow Patterns` 섹션에 유사한 내용이 있으면 스킵하고 사용자에게 알려라.
- **적용 시 날짜 제거**: learnings의 날짜/확인 횟수 메타데이터는 프롬프트에 포함하지 마라.
