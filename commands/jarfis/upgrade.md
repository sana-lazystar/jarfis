# JARFIS Upgrade — 학습 항목 관리 및 시스템 적용

`{JARFIS_SOURCE}/.local/jarfis-learnings.md`의 학습 항목을 관리하고, 실제 에이전트/워크플로우 프롬프트에 적용합니다.

> **`{JARFIS_SOURCE}` 결정**: `~/.claude/.jarfis-source` 파일을 읽어 JARFIS Git repo 경로를 확인한다. 없으면 `~/repos/jarfis`를 기본값으로 사용한다.

---

## 실행 흐름

### Step 1: 학습 파일 로드

`{JARFIS_SOURCE}/.local/jarfis-learnings.md` 파일을 읽어라.
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
3개 독립 블록으로 구성되며, 각 블록은 실패 시 해당 블록부터 재실행 가능하다.

---

##### 블록 1: 분석 (Scope 분류 + Dialectic Review)

> 입력: jarfis-learnings.md 학습 항목
> 출력: 각 항목에 `[universal]`/`[project]` scope 태깅 완료

**1-1. 적용 대상 매핑**

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
| `Workflow Patterns` | `jarfis-learnings.md`에 유지 (work.md에 복사하지 않음 — Phase 0에서 동적 로드) |

**1-2. Scope 자동 분류**

각 학습 항목에 scope를 자동 분류한다:

- 특정 파일 경로/디렉토리/한정 표현("이 프로젝트에서") → `[project]`
- 범용 도구/기법/원칙 → `[universal]`
- 판단 불가 → `[ambiguous]`

분류 결과를 사용자에게 표시한다.

**1-3. Dialectic Review (ambiguous 항목만)**

> ※ Dialectic Review 절차는 implement.md §Step 1.5를 따른다 (정본).
> **Delta**: upgrade에서는 ambiguous 항목의 scope 판단에만 적용한다.
> - Advocate prompt: "이 학습 항목이 범용 원칙인 이유를 논증하세요"
> - Critic prompt: "이 학습 항목이 프로젝트 종속인 이유를 논증하세요"
> - 모든 항목이 명확 분류 시 → 토론 SKIP

---

##### 블록 2: 계획 (적용 계획 표시 + 범위 선택)

> 입력: 블록 1의 scope 분류 결과
> 출력: 사용자가 승인한 적용 대상 항목 목록

**2-1. 적용 계획 표시**

scope별로 매핑하여 보여준다: Universal 적용 (에이전트 Learned Rules) + Project-Specific 적용 (.jarfis/project-context.md). Workflow Patterns는 jarfis-learnings.md에 유지되며 Phase 0에서 동적 로드된다.

**2-2. 적용 범위 선택**

AskUserQuestion으로 "전체 적용" 또는 "선택 적용" (multiSelect: true)을 선택하게 한다.

---

##### 블록 3: 실행 (적용 + 정리 + 버전 범프 + 동기화)

> 입력: 블록 2에서 승인된 항목 목록
> 출력: 에이전트/워크플로우 파일 갱신 + 버전 범프 + repo 동기화

**3-1. 에이전트 파일 적용**

| 학습 scope | 적용 대상 |
|-----------|----------|
| `[universal]` Agent Hints | `~/.claude/agents/jarfis/{role}.md`의 `## Learned Rules` |
| `[project]` Agent Hints | `./.jarfis/project-context.md`의 해당 역할 섹션 |

- `[universal]`: 에이전트 파일의 `## Learned Rules` 섹션에 추가 (없으면 생성). 중복 체크.
- `[project]`: `.jarfis/project-context.md`에 추가 (없으면 파일/섹션 생성). 중복 체크.
- 날짜 정보 `(YYYY-MM-DD)` 는 적용 시 제거.

**3-2. 워크플로우 파일 적용**

| 학습 scope | 적용 대상 |
|-----------|----------|
| `[universal]` Workflow Patterns | `jarfis-learnings.md`에 유지 (work.md에 복사하지 않음 — Phase 0에서 동적 로드) |
| `[project]` Workflow Patterns | `./.jarfis/project-context.md`의 Workflow 섹션 |

- 중복 체크. 날짜/확인 횟수 제거.

**3-3. 적용 후 정리**

AskUserQuestion으로 learnings 파일 처리를 선택:
- "적용된 항목만 비우기 (Recommended)" / "그대로 유지" / "전체 비우기"
- 비우기 시: 섹션 헤더 유지, 항목(`-`줄)만 제거.

**3-4. 버전 범프 (PATCH)**

```bash
python3 ~/.claude/scripts/jarfis_cli.py version patch "upgrade: 학습 적용 (적용 내역 요약)"
```

**3-5. Repo 동기화**

```bash
python3 ~/.claude/scripts/jarfis_cli.py sync
```

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
3. 선택된 항목들을 `{JARFIS_SOURCE}/.local/jarfis-learnings.md`에서 제거하라.
4. 삭제 결과를 보여주고 Step 2로 돌아가라.

##### [수정]

1. 전체 학습 항목을 번호와 함께 나열하라.
2. AskUserQuestion을 사용하여 수정할 항목 **하나**를 선택하게 하라.
3. 선택된 항목의 현재 내용을 보여주고, AskUserQuestion으로 새 내용을 입력받아라.
   - question: "새로운 내용을 입력해주세요 (현재: [현재 내용 요약])"
   - "Other"를 통해 자유 입력
4. 입력받은 내용으로 `{JARFIS_SOURCE}/.local/jarfis-learnings.md`의 해당 항목을 교체하라.
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
3. 오늘 날짜를 자동 추가하여 `{JARFIS_SOURCE}/.local/jarfis-learnings.md`의 해당 섹션에 항목을 추가하라.
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
2. "비우기 실행" 선택 시: `{JARFIS_SOURCE}/.local/jarfis-learnings.md`에서 모든 항목(`-`로 시작하는 줄)을 제거하라. 섹션 헤더(`#`, `##`, `###`)는 유지하라.
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

버전 범프가 실행되었으면, **Commit + Push 명령어를 생성하여 사용자에게 제공한다** (직접 실행하지 않음):
- `git status`와 `git diff --stat`으로 repo의 변경 파일을 확인한다.
- 변경된 파일만 명시적으로 `git add`에 나열한다.
- 커밋 메시지: `upgrade: [적용 내역 요약] (v{새버전})`
- 버전 범프가 있었으면 태그 + `--tags` 포함
- `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>` 포함
- heredoc 대신 큰따옴표로 감싼 한 줄 메시지 사용 (쉘 호환성)

```
📋 아래 명령어를 복사해서 실행하세요:

git add [파일1] [파일2] ... && git commit -m "upgrade: [요약] (v{버전})

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>" && git tag v{버전} && git push origin main --tags
```

---

## 주의사항

- 파일 수정은 매 액션 완료 시마다 즉시 저장하라 (중간에 종료해도 손실 없도록).
- 섹션이 존재하지 않으면 새로 생성하라 (예: Security Engineer 섹션이 없는데 추가 요청 시).
- 항목 삭제 후 빈 섹션이 되면 섹션 헤더는 유지하되 항목만 제거하라.
- 파일 형식(마크다운 리스트, 날짜 형식 등)을 기존 형식과 일관되게 유지하라.
- **적용 시 중복 체크**: 이미 대상 파일의 `Learned Rules` 섹션에 유사한 내용이 있으면 스킵하고 사용자에게 알려라.
- **적용 시 날짜 제거**: learnings의 날짜/확인 횟수 메타데이터는 프롬프트에 포함하지 마라.
