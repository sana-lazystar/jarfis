# Phase 1: Discovery — Agent Prompts

> 이 파일은 work.md에서 외부화된 에이전트 프롬프트입니다.
> distill에 의해 자동 생성됨.

**Step 1-1: PO 역질문** (senior-product-owner)
```
Task prompt:
"사용자가 다음 기획을 요청했습니다: $ARGUMENTS

당신은 시니어 프로덕트 오너입니다. 이 기획에 대해 역질문을 통해 요구사항을 구체화하세요.
다음 관점에서 질문하세요:
- 타겟 사용자와 핵심 유즈케이스
- 비즈니스 목표와 성공 지표 (KPI)
- MVP 범위와 우선순위
- 기존 시스템과의 연계 필요성
- 비기능 요구사항 (성능, 보안, 확장성)
- UI/화면이 필요한 기획인지 (CLI 도구, 백엔드 API 등은 UI 불필요)
- **프로젝트 구조**: BE와 FE가 같은 프로젝트인지, 별도 프로젝트인지
  - 예: Next.js 풀스택 → 같은 디렉토리
  - 예: Vite(CSR) + Nest.js(BFF) → 별도 디렉토리
  - 별도 프로젝트인 경우 각 프로젝트의 디렉토리 경로를 확인

$PROJECT_CONTEXT

[미팅 참조 시 추가 — $MEETING_REF가 비어있으면 이 블록 생략]
---
이 기획은 사전 킥오프 미팅을 거쳤습니다.

미팅 요약: $MEETING_SUMMARY
미팅 결정사항: $MEETING_DECISIONS

중요: 위 미팅에서 이미 논의/결정된 사항은 재질문하지 마세요.
다음 항목만 질문하세요:
1. 미팅에서 '미결'로 남은 사항
2. PRD 작성에 필수적이지만 미팅에서 다루지 않은 항목
---

역질문 목록을 정리하여 사용자에게 보여주세요."
```

**Step 1-1.5: Working Backwards Document** (senior-product-owner)
```
Task prompt:
"사용자의 기획 내용과 역질문 답변을 바탕으로, PRD 작성 전에 Working Backwards 문서를 작성하세요.
이 문서는 '고객 관점에서 이 기능이 왜 가치 있는지'를 검증하는 역할입니다.

기획: $ARGUMENTS
사용자 답변: [역질문 답변]

[미팅 참조 시 추가 — $MEETING_REF가 비어있으면 이 블록 생략]
미팅 회의록: $MEETING_NOTES
미팅 결정사항: $MEETING_DECISIONS
(미팅에서 논의된 고객 문제, 솔루션, FAQ 내용을 적극 활용하세요)

다음 형식으로 작성하세요:

## 가상 프레스 릴리스
1. **제목**: 고객이 이해할 수 있는 기능명 (한 줄)
2. **부제**: 핵심 가치 한 줄 요약
3. **고객 문제**: 현재 고객이 겪는 Pain Point (2-3문장)
4. **솔루션**: 이 기능이 어떻게 해결하는지 — 고객 언어로 (3-5문장)
5. **고객 인용문**: '이 기능 덕분에 ___할 수 있게 되었습니다' (1-2개)
6. **시작하기**: 고객이 이 기능을 사용하는 첫 번째 단계

## FAQ
### External FAQ (고객 관점)
- Q1~Q5: 고객이 물어볼 법한 질문과 답변

### Internal FAQ (기술/비즈니스 관점)
- Q1~Q5: 내부 이해관계자가 물어볼 법한 질문과 답변

결과를 $DOCS_DIR/press-release.md에 저장하세요."
```

PO (senior-product-owner):
```
Task prompt:
"사용자의 기획 내용, 역질문 답변, Working Backwards 문서를 바탕으로 PRD를 작성하세요.

기획: $ARGUMENTS
사용자 답변: [역질문 답변]
Working Backwards: $DOCS_DIR/press-release.md를 참조

$LEARNINGS (Workflow Patterns 섹션)

[미팅 참조 시 추가 — $MEETING_REF가 비어있으면 이 블록 생략]
미팅 결정사항: $MEETING_DECISIONS
미팅 기술 조사: $MEETING_RESEARCH
(미팅에서 확정된 결정사항을 PRD에 사전 반영하세요.
 잠정 결정은 '잠정' 표기와 함께 포함하세요.
 미결 사항은 '미결 — work 진행 중 확정 필요'로 표기하세요.)

PRD에 포함할 항목:
1. 프로젝트 개요 (배경, 목표, 범위)
2. 타겟 사용자 및 페르소나
3. 기능 요구사항 (유저 스토리 형태)
4. 비기능 요구사항
5. 성공 지표 (KPI)
6. 타임라인 및 마일스톤
7. 위험 요소 및 의존성
8. **필요 역할 판단** — 아래 표 형식으로 반드시 포함:

## Required Roles

| Role | 필요 여부 | 근거 |
|------|----------|------|
| Backend Engineer | ✅ 필요 / ⬜ 불필요 | (이유) |
| Frontend Engineer | ✅ 필요 / ⬜ 불필요 | (이유) |
| UX Designer | ✅ 필요 / ⬜ 불필요 | (이유) |
| DevOps/SRE | ✅ 필요 / ⬜ 불필요 | (이유) |

판단 기준:
- UI/화면이 없는 기획 (CLI 도구, API 서버, 배치 작업 등) → UX Designer 불필요, Frontend 불필요 가능
- 기존 인프라를 그대로 사용하는 경우 → DevOps 불필요 가능
- 프론트엔드만의 기획 (UI 라이브러리, 위젯 등) → Backend 불필요 가능

9. **Workspace 구성** — 사용자의 프로젝트 구조 답변을 기반으로 아래 표 작성:

## Workspace

| 항목 | 값 |
|------|-----|
| 구조 유형 | monorepo / multi-project |
| Backend 경로 | (예: `.` 또는 `./backend-bff`) |
| Backend 프레임워크 | (예: Next.js API Routes, Nest.js, Spring Boot) |
| Frontend 경로 | (예: `.` 또는 `./frontend-app`) |
| Frontend 프레임워크 | (예: Next.js, Vite+React, Vue) |

판단 기준:
- BE/FE가 같은 package.json을 공유 (Next.js, Nuxt 등) → monorepo, 경로 모두 `.`
- BE/FE가 별도 디렉토리에 각자 package.json 보유 → multi-project, 각각의 경로 명시
- Backend 불필요인 경우 → Backend 경로는 `N/A`
- Frontend 불필요인 경우 → Frontend 경로는 `N/A`

10. **Performance Budget** — 정량적 성능 목표:

## Performance Budget

| 지표 | 목표값 | 측정 방법 |
|------|--------|----------|
| API 응답 시간 (P95) | (예: < 200ms) | APM / 서버 로그 |
| 페이지 로드 — LCP | (예: < 2.5s) | Lighthouse |
| 에러율 | (예: < 0.1%) | 로그 분석 |
| 동시 접속자 처리 | (예: 1,000명) | 부하 테스트 |

판단 기준:
- 해당 기획의 특성에 맞는 지표만 선택 (FE-only면 API 응답 시간 불필요 등)
- 기존 시스템 기준이 있으면 그에 맞춤
- 새 시스템이면 업계 표준 기준 제시

결과를 $DOCS_DIR/prd.md에 저장하세요."
```

**Step 1-2.5: PRD Completeness Check** (오케스트레이터 직접 실행 — 에이전트 아님)

> 이 단계는 에이전트를 호출하지 않고, 오케스트레이터가 직접 $DOCS_DIR/prd.md를 검증한다.
> Gate 1 사용자 컨펌 전에 PRD의 품질을 자동으로 확인하여, 모호한 PRD가 후속 Phase에 전파되는 것을 방지한다.

검증 체크리스트:
```
1. [모호한 표현 감지]
   PRD 전문에서 다음 패턴을 검색한다:
   - "적절한", "적절히", "빠른", "빠르게", "충분한", "충분히"
   - "필요에 따라", "상황에 맞게", "등", "기타", "추후 결정"
   - "가능하면", "될 수 있으면", "적당한", "합리적인"
   → 발견 시: 해당 표현을 구체적 수치/기준으로 대체하도록 PO에게 재작성 지시

2. [성공 기준 측정 가능성]
   PRD의 '성공 지표(KPI)' 섹션에서:
   - 각 KPI에 숫자(목표값)가 포함되어 있는가?
   - 측정 방법이 명시되어 있는가?
   → 미충족 시: PO에게 정량적 목표값 추가 지시

3. [Performance Budget 구체성]
   PRD의 'Performance Budget' 표에서:
   - 각 지표에 구체적 숫자가 있는가? ("빠르게" → "< 2.5s")
   - 측정 방법이 명시되어 있는가?
   → 미충족 시: PO에게 구체적 수치 추가 지시

4. [Required Roles 근거]
   PRD의 'Required Roles' 표에서:
   - 각 역할의 '근거' 칸이 비어있지 않은가?
   - "필요"/"불필요" 판단에 대한 이유가 1문장 이상인가?
   → 미충족 시: PO에게 근거 보강 지시

5. [스코프 경계 명확성]
   PRD에 다음 중 하나가 존재하는가:
   - "Out of Scope" / "범위 밖" / "하지 않는 것" 섹션
   - 또는 범위 섹션에 포함/미포함이 명확히 구분
   → 미존재 시: PO에게 스코프 경계 섹션 추가 지시
```

검증 결과 처리:
- **전체 통과**: Gate 1로 직접 진행
- **미통과 항목 존재**: PO(senior-product-owner)에게 미통과 항목을 명시하여 PRD 수정 지시 → 수정 후 재검증 (최대 2회 반복, 그 이후에는 미통과 항목을 Gate 1에서 사용자에게 경고와 함께 표시)

Architect (technical-architect):
```
Task prompt:
"다음 기획의 기술적 실현가능성을 평가하세요.

기획: $ARGUMENTS
사용자 답변: [역질문 답변]

$PROJECT_CONTEXT

다음을 분석하세요:
- 기술적 복잡도 (상/중/하)
- 핵심 기술 스택 후보
- 예상 병목 포인트
- 기존 시스템 연계 시 고려사항
- 기술적 위험 요소

결과는 $DOCS_DIR/prd.md의 '기술적 실현가능성 평가' 섹션에 추가하세요."
```

