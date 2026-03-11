# JARFIS Implement — JARFIS 시스템 자체 수정

JARFIS 시스템의 명령어, 구조, 기능을 수정하거나 추가하는 전용 명령어입니다.

사용자 요청: $ARGUMENTS

---

> **🔒 스텝 강제 실행 규칙**
>
> 이 워크플로우의 **모든 Step은 순서대로 실행**해야 합니다. 어떤 Step도 스킵하거나 건너뛸 수 없습니다.
> 코딩(Step 2) 완료 후 반드시 Step 3 → 3.5 → 4 → 5를 실행하세요.
> 각 Step 완료 시 다음 Step으로 명시적으로 진행하세요.

---

## 실행 흐름

### Step 0: 시스템 현황 파악

1. `~/.claude/commands/jarfis/jarfis-index.md`를 읽어 현재 JARFIS 시스템 구조를 파악하세요.
2. 읽은 내용을 기반으로 사용자 요청이 어떤 파일에 영향을 주는지 판단하세요.
3. **탐색 최소화**: 인덱스에 이미 있는 정보로 충분하면 추가 탐색하지 마세요.
4. **Git repo 확인**: `~/.claude/.jarfis-source`를 읽어 JARFIS Git repo 경로를 확인하세요. 없으면 `~/repos/jarfis`를 기본으로 사용하세요.

> ⚠️ **동기화 방향**: JARFIS의 active 파일은 `~/.claude/`에 있습니다.
> 수정은 반드시 `~/.claude/`에서 하고, Step 4에서 `jarfis_cli.py sync`로 repo에 동기화합니다.
> repo를 직접 수정하면 active 시스템에 반영되지 않습니다.

→ Step 1로 진행

### Step 1: 영향 범위 분석

사용자 요청을 분석하여 다음을 판단하세요:

| 작업 유형 | 영향 대상 |
|-----------|-----------|
| 명령어 이름 변경 | 해당 파일 rename + 참조하는 모든 파일 + `jarfis.md` |
| 새 명령어 추가 | 새 md 파일 생성 + `jarfis.md` 목록 추가 |
| 기존 명령어 수정 | 해당 md 파일 |
| 명령어 삭제 | 파일 삭제 + 참조 제거 + `jarfis.md` 목록 제거 |
| 구조 변경 | 인덱스의 "내부 참조 관계" 참고하여 영향 파일 식별 |
| 에이전트 프롬프트 수정 | `prompts/*.md` (work.md에서 외부화된 Phase별 프롬프트) |
| 에이전트 역할 수정 | `~/.claude/agents/jarfis/*.md` (Agent 도구용 역할 프롬프트) |

**🔒 필수**: 아래 배너를 반드시 출력한 후 다음 Step으로 진행하세요. 배너 없이 Step 2로 넘어가지 마세요.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Implement — 영향 범위
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 요청: [요약]
📂 수정 대상: [파일 목록]
🔗 참조 갱신: [영향 받는 파일 목록]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

→ Step 1.5로 진행

### Step 1.5: Dialectic Review (토론 게이트)

JARFIS 시스템 변경의 품질을 보장하기 위한 다관점 검증 단계이다.

**게이트 진입 조건 판단**:
1. `$ARGUMENTS`에 리뷰 플래그가 있으면 따른다:
   - `--review=major` → 토론 필수
   - `--review=minor` → 토론 실행
   - `--review=patch` → 토론 스킵 → Step 2로 이동
2. 플래그가 없으면 JARFIS가 변경 규모를 판단한다:
   - 수정 대상 파일 1개 이하 & 내용 변경만(구조 변경 없음) → AskUserQuestion:
     ```
     question: "가벼운 업데이트로 보입니다. Dialectic Review를 진행하시겠어요?"
     header: "Review"
     options:
       - label: "스킵 (Recommended)"
         description: "토론 없이 바로 수정을 진행합니다"
       - label: "토론 진행"
         description: "Advocate/Critic 토론으로 변경을 검증합니다"
     ```
   - 수정 대상 파일 2개 이상 또는 구조 변경 → 토론 실행

**토론 흐름** (토론 실행 시):

1. 변경안 요약을 준비한다:
   - 현재 상태 (jarfis-index.md 기반)
   - 제안된 변경 내용
   - 영향 받는 파일 목록

2. **Advocate 호출** (Agent tool, subagent_type: `general-purpose`):
   - jarfis-advocate.md의 페르소나를 프롬프트에 포함
   - prompt: "다음 JARFIS 변경을 검토하세요: [변경안 요약]. 현재 시스템 상태: [index 요약]. 장점과 추가 제안을 분석하세요."

3. **Critic 호출** (Agent tool, subagent_type: `general-purpose`):
   - jarfis-critic.md의 페르소나를 프롬프트에 포함
   - prompt: "다음 JARFIS 변경을 검토하세요: [변경안 요약]. Advocate 의견: [advocate 결과]. 약점과 리스크를 분석하세요."

4. **합의 판단**:
   - Critic이 "동의하는 부분"에 핵심 변경을 포함 → 합의 도출
   - 미합의 시 → Round 2 (Advocate 반론 → Critic 재반론)
   - Round 2에서도 미합의 → 사용자에게 양측 요약 + AskUserQuestion

5. **결과 표시**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Dialectic Review
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 변경안: [요약]

┌─ Advocate ────────────────────────────┐
│ ✅ 장점: [요약]                        │
│ 💡 추가 제안: [있을 경우]               │
│ ⚠️ 인정한 리스크: [요약]               │
└───────────────────────────────────────┘

┌─ Critic ──────────────────────────────┐
│ ❌ 문제점: [요약]                      │
│ 🔄 대안: [있을 경우]                   │
│ ✅ 동의: [요약]                        │
└───────────────────────────────────────┘

🤝 합의: [합의안 요약 / 또는 "사용자 판단 필요"]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

합의 또는 사용자 승인 후 → Step 2로 진행

### Step 2: 수정 실행

> ⚠️ **수정 위치**: 반드시 `~/.claude/` 경로의 파일을 수정하세요.
> `~/repos/jarfis/` (Git repo)를 직접 수정하지 마세요. repo는 Step 4에서 자동 동기화됩니다.

1. 필요한 파일만 읽어서 수정하세요.
2. 인덱스의 "수정 시 체크리스트"를 따르세요.
3. 명령어 추가/삭제/이름 변경 시 `jarfis.md`(메인 도우미)도 반드시 갱신하세요.
4. **프롬프트 외부화 구조 주의**: work.md의 에이전트 프롬프트는 `prompts/*.md`에 외부화되어 있습니다.
   - work.md의 Phase별 워크플로우 **흐름/규칙**을 수정할 때 → work.md 직접 수정
   - Phase별 에이전트에게 전달하는 **Task prompt 내용**을 수정할 때 → `prompts/phase{N}.md` 수정
   - work.md에서 `> 📄 프롬프트:` 참조와 prompts/ 파일의 실제 내용이 일치하는지 확인

→ 수정 완료 후 반드시 Step 3으로 진행 (여기서 멈추지 마세요)

### Step 3: 인덱스 갱신

**반드시** `~/.claude/commands/jarfis/jarfis-index.md`를 수정 결과에 맞게 갱신하세요:

- 파일 구조 트리 갱신 (파일 추가/삭제/이름 변경 시 줄 수 포함)
- 명령어 매핑 테이블 갱신
- 산출물/데이터 파일 갱신 (새 데이터 파일이 생긴 경우)
- 내부 참조 관계 갱신
- `Last updated` 날짜를 오늘로 변경

→ Step 3.5로 진행

### Step 3.5: 버전 범프

수정이 완료되면 버전을 범프하세요. AskUserQuestion으로 범프 유형을 선택하게 하세요:

```
question: "버전을 어떻게 올릴까요? (현재: v{현재버전})"
header: "Version"
options:
  - label: "PATCH (Recommended)"
    description: "프롬프트/템플릿 내용 변경 (X.Y.Z+1)"
  - label: "MINOR"
    description: "새 명령어/에이전트 추가 (X.Y+1.0)"
  - label: "MAJOR"
    description: "Phase 구조 변경/호환 깨짐 (X+1.0.0)"
  - label: "Skip"
    description: "버전 범프를 건너뜁니다"
```

"Skip"이 아닌 경우, `jarfis_cli.py version`을 사용하세요:
```bash
python3 ~/.claude/scripts/jarfis_cli.py version <patch|minor|major> "implement: 변경 내역 요약"
```
- 스크립트가 VERSION, .jarfis-version, jarfis-index.md Version, CHANGELOG.md를 자동 갱신한다.
- 출력 JSON의 `previous`/`new` 버전을 결과 보고에 포함한다.

→ Step 4로 진행

### Step 4: Repo 동기화 (자동)

**반드시** 다음 스크립트를 실행하여 `~/.claude/` → `{repo_path}/` 동기화를 수행한다:

```bash
python3 ~/.claude/scripts/jarfis_cli.py sync
```

이 스크립트는:
- `~/.claude/.jarfis-source`에서 repo 경로를 자동 읽기 (없으면 `~/repos/jarfis`)
- commands, agents, hooks, scripts, statusline 전체를 diff 비교 후 변경분만 복사
- `.distill-backup/`, 로컬 전용 파일은 자동 제외
- 결과를 자동 보고

**주의**: 이 Step은 스크립트 한 줄 실행이다. 수동 복사하지 말 것.
파일 삭제가 있었다면, 스크립트 실행 후 repo에서도 수동 삭제한다.

→ Step 5로 진행

### Step 5: 결과 보고

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Implement 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 수정 내역:
   - [변경 사항 1]
   - [변경 사항 2]
📂 수정된 파일:
   - [파일 경로]: [변경 요약]
🔄 인덱스 갱신 완료
🔄 Repo 동기화 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
