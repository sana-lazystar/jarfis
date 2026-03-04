# JARFIS Implement — JARFIS 시스템 자체 수정

JARFIS 시스템의 명령어, 구조, 기능을 수정하거나 추가하는 전용 명령어입니다.

사용자 요청: $ARGUMENTS

---

## 실행 흐름

### Step 0: 시스템 현황 파악

1. `~/.claude/commands/jarfis/jarfis-index.md`를 읽어 현재 JARFIS 시스템 구조를 파악하세요.
2. 읽은 내용을 기반으로 사용자 요청이 어떤 파일에 영향을 주는지 판단하세요.
3. **탐색 최소화**: 인덱스에 이미 있는 정보로 충분하면 추가 탐색하지 마세요.
4. **Git repo 확인**: `~/.claude/.jarfis-source`를 읽어 JARFIS Git repo 경로를 확인하세요. 없으면 `~/repos/jarfis`를 기본으로 사용하세요.

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

분석 결과를 표시하세요:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Implement — 영향 범위
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 요청: [요약]
📂 수정 대상: [파일 목록]
🔗 참조 갱신: [영향 받는 파일 목록]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 2: 수정 실행

1. 필요한 파일만 읽어서 수정하세요.
2. 인덱스의 "수정 시 체크리스트"를 따르세요.
3. 명령어 추가/삭제/이름 변경 시 `jarfis.md`(메인 도우미)도 반드시 갱신하세요.
4. **프롬프트 외부화 구조 주의**: work.md의 에이전트 프롬프트는 `prompts/*.md`에 외부화되어 있습니다.
   - work.md의 Phase별 워크플로우 **흐름/규칙**을 수정할 때 → work.md 직접 수정
   - Phase별 에이전트에게 전달하는 **Task prompt 내용**을 수정할 때 → `prompts/phase{N}.md` 수정
   - work.md에서 `> 📄 프롬프트:` 참조와 prompts/ 파일의 실제 내용이 일치하는지 확인

### Step 3: 인덱스 갱신

**반드시** `~/.claude/commands/jarfis/jarfis-index.md`를 수정 결과에 맞게 갱신하세요:

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

"Skip"이 아닌 경우, 다음 파일들을 갱신하세요:

1. **Git repo의 VERSION 파일**: `{repo_path}/VERSION` → 새 버전
2. **jarfis-index.md**: `Last updated` 줄의 `Version: X.Y.Z` 갱신
3. **~/.claude/.jarfis-version**: 새 버전으로 갱신
4. **CHANGELOG.md**: `[Unreleased]` 섹션에 변경 내용 추가

Git repo 경로는 Step 0에서 확인한 `.jarfis-source` 값을 사용하세요.

- 파일 구조 트리 갱신 (파일 추가/삭제/이름 변경 시 줄 수 포함)
- 명령어 매핑 테이블 갱신
- 산출물/데이터 파일 갱신 (새 데이터 파일이 생긴 경우)
- 내부 참조 관계 갱신
- `Last updated` 날짜를 오늘로 변경

### Step 4: 결과 보고

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
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
