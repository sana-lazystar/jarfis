# JARFIS Distill — 프롬프트 증류 (정리/최적화)

JARFIS 프롬프트 파일들의 토큰 효율을 분석하고, 중복 제거 + 템플릿 외부화 + 규칙 통합을 수행합니다.

사용자 요청: $ARGUMENTS

---

## 실행 흐름

### D-0: 측정 (Before)

0. **시스템 현황 파악**
   - `~/.claude/commands/jarfis/jarfis-index.md`를 먼저 읽어 현재 JARFIS 파일 구조를 파악한다.
   - 인덱스의 "파일 구조"와 "명령어 매핑"을 기반으로 아래 스캔 범위를 동적으로 결정한다.
   - 인덱스에 없는 파일이 디스크에 존재하거나, 인덱스에 있는 파일이 디스크에 없으면 경고를 출력한다.

1. **파일별 토큰 비용 측정**
   - 스캔 범위:
     - `~/.claude/commands/jarfis.md` (메인 도우미)
     - `~/.claude/commands/jarfis/` 내 **워크플로우 프롬프트** `.md` 파일
     - `~/.claude/agents/jarfis/` 내 모든 `.md` 파일 (에이전트 프롬프트)
     - `~/.claude/commands/jarfis/templates/` (외부화된 템플릿, 존재 시)
     - `~/.claude/commands/jarfis/prompts/` (외부화된 프롬프트, 존재 시)
   - 제외 대상 판단 기준:
     - JARFIS 메타 도구 (시스템 관리용, 워크플로우가 아닌 것): `distill.md`, `implement.md`, `jarfis-index.md`, `health.md`, `upgrade.md`, `version.md`
     - 위 목록은 인덱스의 명령어 매핑에서 역할이 "시스템 관리"에 해당하는 것들이다.
     - **인덱스에 새 명령어가 추가된 경우**: 역할을 확인하여 워크플로우 프롬프트인지 메타 도구인지 판단하고, 워크플로우 프롬프트만 증류 대상에 포함한다.
   - 각 파일: 줄 수, 문자 수, 토큰 추정 (문자 수 / 4)
   - 결과를 테이블로 출력:
     ```
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
       JARFIS Distill — Before 측정
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     파일명              줄수    토큰추정
     work.md             1507   16,527
     meeting.md           363    2,972
     ...
     ─────────────────────────────────────────
     TOTAL               2838   29,234
     ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     ```

2. **대상 파일 결정** (위 제외 대상을 뺀 워크플로우 파일만 후보)
   - `$ARGUMENTS`가 있으면: 해당 파일만 분석 (예: `work.md`)
   - `$ARGUMENTS`가 없으면: 토큰 비용 상위 3개 파일을 대상으로 제안
   - AskUserQuestion으로 대상 확인:
     ```
     "다음 파일을 증류 대상으로 분석합니다:
      1. work.md (16,527tok)
      2. meeting.md (2,972tok)
      진행할까요?"
     ```

### D-1: 진단

대상 파일 각각에 대해 다음 4가지 진단을 수행한다:

#### 1. 인라인 템플릿 탐지
- 코드블록(``` ... ```) 내부의 줄 수를 합산한다.
- 전체 대비 코드블록 비율이 50%를 넘으면 "템플릿 과다 인라인" 경고.
- 각 코드블록의 위치, 크기, 소속 Phase를 기록한다.

#### 2. 에이전트 프롬프트 탐지
- `Task prompt:` 또는 `prompt:` 패턴으로 시작하는 코드블록을 찾는다.
- 각 프롬프트의 줄 수, 토큰 추정, 소속 Phase를 기록한다.
- 15줄 이상인 프롬프트를 "외부화 후보"로 표시한다.

#### 3. 중복 규칙 탐지
- 동일/유사 문장이 2회 이상 등장하는 패턴을 찾는다.
  - 키워드 기반: 같은 개념어(예: `.jarfis-state.json`, `AskUserQuestion`)가 규칙 맥락에서 N회 이상 등장
  - 규칙 반복: "반드시 ~ 한다", "~ 해야 한다" 패턴의 유사 문장
- 각 중복 그룹의 위치와 내용을 기록한다.

#### 4. 구조 분석
- `##` 레벨 헤더 목록을 추출한다.
- "워크플로우 규칙" 헤더와 "산출물 템플릿" 헤더를 분류한다:
  - Phase N, Execution Rules, Workflow Overview 등 → 규칙
  - 나머지 (산출물 양식명) → 템플릿
- 두 유형이 같은 레벨에 섞여있으면 "구조 혼재" 경고.

#### 진단 결과 출력
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Distill — 진단 결과: [파일명]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 인라인 템플릿: N개 코드블록, ~X,XXX토큰 (전체의 XX%)
   외부화 후보: [목록]

📊 에이전트 프롬프트: N개, ~X,XXX토큰
   외부화 후보: [목록]

📊 중복 규칙: N개 그룹
   - [규칙 요약]: L123, L456, L789에서 반복

📊 구조 혼재: ## 헤더 N개 중 M개가 산출물 템플릿

🎯 증류 예상 효과: ~XX,XXX tok → ~X,XXX tok (XX% 절감)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### D-2: 증류 계획 수립

진단 결과를 기반으로 증류 액션 목록을 생성한다:

| 액션 유형 | 설명 | 예시 |
|-----------|------|------|
| `externalize-template` | 인라인 템플릿을 별도 파일로 분리 | PRD 템플릿 → `templates/prd.md` |
| `externalize-prompt` | 에이전트 프롬프트를 별도 파일로 분리 | Phase 5 QA 프롬프트 → `prompts/phase5-qa.md` |
| `consolidate-rule` | 중복 규칙을 한 곳에 통합 | 상태 관리 → Execution Rules에만 |
| `restructure-headers` | 산출물 헤더 레벨 조정 | `##` → 코드블록 내부 또는 별도 파일 |

각 액션에 대해:
- 원본 위치 (파일명, 라인 범위)
- 대상 위치 (새 파일 경로 또는 통합 위치)
- 원본에 남길 참조 문구 (예: "`templates/prd.md` 템플릿을 로드하여 사용")
- 예상 절감 토큰

계획을 AskUserQuestion으로 확인:
```
"다음 증류 액션을 수행합니다:

 1. [externalize-template] PRD 템플릿 → templates/prd.md (~480tok 절감)
 2. [externalize-prompt] Phase 5 QA → prompts/phase5-qa.md (~230tok 절감)
 3. [consolidate-rule] 상태 관리 규칙 3곳 → Execution Rules 1곳 (~400tok 절감)
 ...
 총 예상 절감: ~X,XXXtok (XX%)

 진행할까요?"
```
- 옵션: "전체 진행" / "선택적 진행" / "취소"
- "선택적 진행" 시 개별 액션 선택 가능

### D-3: 증류 실행

승인된 액션을 순서대로 실행한다:

#### externalize-template 실행
1. 대상 코드블록/섹션을 별도 `.md` 파일로 추출한다.
   - 저장 위치: `~/.claude/commands/jarfis/templates/[이름].md`
2. 원본에서 해당 내용을 삭제하고, 참조 문구로 대체한다:
   ```
   > 📄 템플릿: `templates/[이름].md`를 읽어서 산출물 양식으로 사용한다.
   ```
3. 원본 파일이 해당 템플릿을 사용하는 Phase의 에이전트 프롬프트에 파일 경로를 추가한다.

#### externalize-prompt 실행
1. 에이전트 프롬프트 코드블록을 별도 `.md` 파일로 추출한다.
   - 저장 위치: `~/.claude/commands/jarfis/prompts/[phase]-[역할].md`
2. 원본에서 해당 프롬프트를 삭제하고, 로드 지시로 대체한다:
   ```
   > 📄 프롬프트: `prompts/[phase]-[역할].md`를 읽어서 에이전트에 전달한다.
   ```

#### consolidate-rule 실행
1. 중복 규칙 중 가장 완전한 버전을 "정본"으로 선택한다.
2. 나머지 위치에서 중복 내용을 삭제하고, 정본 참조로 대체한다:
   ```
   > ※ 상태 관리 규칙은 "Execution Rules > Workflow State Management" 참조.
   ```

#### restructure-headers 실행
1. 산출물 템플릿 헤더의 `##` 레벨을 `###` 이하로 낮추거나, 외부화된 경우 헤더 자체를 제거한다.

### D-4: 측정 (After) + 리포트

1. **After 측정**: D-0과 동일한 방식으로 토큰 비용을 재측정한다.

2. **Before/After 비교 리포트 출력**:
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
     JARFIS Distill 완료
   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

   📊 Before / After 비교:
   파일명              Before    After     절감
   work.md             16,527    5,800    -65%
   ...
   ─────────────────────────────────────────
   TOTAL               29,234   XX,XXX    -XX%

   ✅ 수행된 액션:
      - [externalize-template] N건
      - [externalize-prompt] N건
      - [consolidate-rule] N건

   📂 생성된 파일:
      - templates/prd.md
      - templates/tasks.md
      - prompts/phase5-qa.md
      ...

   🔄 인덱스 갱신 완료

   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```

3. **인덱스 갱신**: `jarfis-index.md`를 수정 결과에 맞게 갱신한다.

4. **버전 범프 (PATCH)**: 증류는 동작 변경 없이 토큰 최적화만 수행하므로 PATCH 범프한다.
   - `~/.claude/.jarfis-source`에서 Git repo 경로를 읽는다 (없으면 `~/repos/jarfis`).
   - `{repo_path}/VERSION`의 PATCH를 +1 한다 (예: 1.0.0 → 1.0.1).
   - `~/.claude/.jarfis-version`을 새 버전으로 갱신한다.
   - `jarfis-index.md`의 `Version:` 표기를 새 버전으로 갱신한다.
   - `{repo_path}/CHANGELOG.md`의 `[Unreleased]` 섹션에 증류 내역을 추가한다.

5. **Repo 동기화**: 이번 증류에서 수정/생성된 파일들을 Git repo에 반영한다.
   - `~/.claude/.jarfis-source`에서 Git repo 경로를 읽는다 (없으면 `~/repos/jarfis`).
   - 수정된 워크플로우 파일: `~/.claude/commands/jarfis/*.md` → `{repo_path}/commands/jarfis/*.md`
   - 생성된 prompts/templates 파일: `~/.claude/commands/jarfis/prompts/*`, `templates/*` → `{repo_path}/commands/jarfis/prompts/*`, `templates/*`
   - 수정된 에이전트 파일 (있을 경우): `~/.claude/agents/jarfis/*` → `{repo_path}/agents/jarfis/*`
   - `jarfis-index.md`: `~/.claude/commands/jarfis/jarfis-index.md` → `{repo_path}/commands/jarfis/jarfis-index.md`
   - `.jarfis-version`, `.jarfis-source`, `jarfis-learnings.md`, `.jarfis-state.json`, `.distill-backup/`은 복사하지 않는다 (로컬 전용).
   - 동기화 후 표시: `🔄 Repo 동기화: {N}개 파일 → {repo_path}`

---

## 증류 원칙

1. **의미 보존**: 증류 전후로 워크플로우의 동작은 동일해야 한다. 규칙을 삭제하지 않고 통합/이동만 한다.
2. **참조 연결**: 외부화된 내용은 반드시 원본에 로드 지시를 남긴다.
3. **단계적 실행**: 사용자가 각 액션을 검토하고 선택할 수 있어야 한다.
4. **측정 기반**: 감으로 정리하지 않고, 토큰 비용을 실측하여 효과를 검증한다.
5. **롤백 가능**: 증류 전 원본을 `.distill-backup/`에 백업한다.
