# Phase 6: Retrospective — Agent Prompts

> 이 파일은 work.md에서 외부화된 에이전트 프롬프트입니다.
> distill에 의해 자동 생성됨.

**Step 6-1: 회고 작성** (tech-lead)
```
Task prompt:
"이번 JARFIS 워크플로우 전체를 회고하세요.
$DOCS_DIR/ 내의 모든 산출물과 .jarfis-state.json을 참조하세요.

다음 형식으로 작성하세요:

## 워크플로우 회고

### 잘 된 점 (Keep)
- 효율적이었던 에이전트/Phase
- 좋은 판단이었던 역할 스킵/실행 결정

### 개선할 점 (Improve)
- 병목이었던 구간
- 불필요했던 단계
- 빠졌던 고려사항

### 다음에 적용할 것 (Action Items)
- JARFIS 워크플로우 자체의 개선 제안 (있는 경우만)

### 프로젝트 고유 학습
- 이 코드베이스에서 발견된 패턴, 컨벤션, 주의사항
- 재사용 가능한 컴포넌트/모듈 정보
- 자주 참조한 파일 경로

### 학습 분류 기준
각 학습 항목에 scope를 태깅하세요:
- [universal]: 다른 프로젝트에서도 유효한 원칙/기법/도구 사용법
- [project]: 이 코드베이스/팀/설정에만 해당하는 패턴

판단 기준:
- 특정 파일 경로, 디렉토리 구조 언급 → [project]
- 특정 프레임워크 버전/설정 종속 → [project]
- '이 프로젝트에서' 등 한정 표현 → [project]
- 범용 도구 사용법, 엔지니어링 원칙 → [universal]

### Suggested Learnings (자동 생성 섹션)
.jarfis-state.json의 learning_candidates 필드가 존재하면, 아래 형식으로 추가하세요:

**반복 패턴에서 도출된 학습 후보:**
| 카테고리 | 반복 횟수 | 예시 | 제안 학습 |
|----------|----------|------|----------|
(learning_candidates 각 항목을 표로 정리하고, 각각에 대해 구체적인 학습 규칙을 제안)

사용자가 /jarfis:sys-upgrade로 명시적 승격할 수 있도록 후보 형태로 제시합니다.
learning_candidates가 없으면 이 섹션을 생략하세요.

결과를 $DOCS_DIR/retrospective.md에 저장하세요."
```

**Step 6-3: Wiki 2-트랙 갱신** (Org 등록 시만 실행, 오케스트레이터)

> 핵심 원칙: learning = JARFIS 에이전트/워크플로우 개선, wiki = Org 누적 지식 — 목적이 다르므로 독립

실행 순서: **학습 추출 (Step 6-1~6-2 먼저) → wiki 갱신 (이 Step 나중)**

### 트랙 A: 텍스트 Wiki (PO, TA, QA)

1. **산출물 스캔**: $DOCS_DIR/ 내 산출물에서 누적 지식 추출
2. **추출 기준 체크리스트 적용**:
   - ✅ 누적 대상: 비즈니스 규칙, 기술 선택(ADR), API 계약, 데이터 모델, 디자인 토큰, 정책 변경, 아키텍처 결정
   - ❌ 누적 제외: 일정 관련, 구현 세부사항, 리뷰 코멘트, 진행 상태, 에이전트 간 토론
3. **"6개월 테스트" 적용**: "6개월 후에도 유용한 정보인가?" → No면 제외
4. **기존 파일 매칭**: INDEX.md Summary 기반으로 기존 wiki 파일과 매칭 → 병합 or 신규 생성
5. **갱신**: 해당 wiki 파일 갱신 + _index.md + INDEX.md 갱신

### 트랙 B: DESIGN HTML 동기화 (FE 포함 시만)

1. `$DOCS_DIR/design/` → `wiki/DESIGN/pages/{project}/` 동기화
2. 규칙: 기존 파일 덮어쓰기, 신규 추가, wiki에만 있는 파일은 보존
3. `wiki/DESIGN/pages/{project}/_index.html` 자동 재생성
4. `wiki/DESIGN/_index.md` + `wiki/INDEX.md` 갱신

### Wiki 파일 프론트매터 가이드

신규/수정 wiki 파일에 아래 프론트매터를 포함:
```
---
owner: {PO|TA|QA|DESIGN}
projects: [{project_name}]
created: {date}
created_by: {work_name}
last_updated: {date}
last_updated_by: {work_name}
status: active
---
```

### 시맨틱 검색 인덱스 갱신

Wiki 파일 추가/수정 후 wiki + works 시맨틱 검색 인덱스를 갱신한다:
```bash
# Wiki 인덱스 갱신
python3 ~/.claude/scripts/jarfis_cli.py search index wiki
# Works 인덱스 갱신 (이번 워크플로우 산출물 포함)
python3 ~/.claude/scripts/jarfis_cli.py search index works
```
실패해도 워크플로우를 중단하지 않는다 (best-effort). 에러 시 사용자에게 `/jarfis:search-index --current` 수동 실행 안내만 표시.

### 갱신 요약 사용자 표시
```
━━ Wiki 갱신 요약 ━━
트랙 A (텍스트):
  - PO/: +1 신규 (domain-map.md), 1 갱신 (policies/refund.md)
  - TA/: +1 신규 (decisions/adr-003.md)
  - QA/: 변경 없음
트랙 B (DESIGN):
  - pages/{project}/: 4 파일 동기화
━━━━━━━━━━━━━━━━━━
```

