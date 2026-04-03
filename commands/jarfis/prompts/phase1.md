# Phase 1: Discovery — Agent Prompts

> 이 파일은 work.md에서 외부화된 에이전트 프롬프트입니다.
> distill에 의해 자동 생성됨.

**Step 1-0: PO Wiki 참조** (senior-product-owner, Org 등록 시만)
```
Task prompt:
"PO/ wiki에서 다음 파일을 확인하세요:
- domain-map.md (도메인 용어집, 비즈니스 개념 관계)
- policies/ (정책 문서 — 환불 정책, 개인정보 처리 등)
- business-rules/ (비즈니스 규칙 — 할인 계산, 자격 조건 등)

기존 정책/규칙과 일관성을 유지하면서 이번 기획을 진행하세요.
충돌이 있으면 에스컬레이션하세요."
```

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
(참고: 프로젝트 구조(monorepo/multi-project)는 Phase 0에서 이미 확정됨 — 재질문 불필요)

$PROJECT_CONTEXT

[미팅 참조 시 추가 — $MEETING_REF가 비어있으면 이 블록 생략]
---
이 기획은 사전 킥오프 미팅을 거쳤습니다.

미팅 요약: $MEETING_SUMMARY
미팅 결정사항: $MEETING_DECISIONS

[추가 미팅 자료 — $MEETING_EXTRA가 비어있으면 이 블록 생략]
추가 미팅 자료: $MEETING_EXTRA

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
[추가 미팅 자료 — $MEETING_EXTRA가 비어있으면 이 블록 생략]
추가 미팅 자료: $MEETING_EXTRA
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
[추가 미팅 자료 — $MEETING_EXTRA가 비어있으면 이 블록 생략]
추가 미팅 자료: $MEETING_EXTRA
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
8. **Required Roles** — 표 형식(Role, 필요 여부 ✅/⬜, 근거)으로 BE/FE/UX/DevOps 각각 판단. UI 없으면 UX/FE 불필요, 기존 인프라면 DevOps 불필요 등.

9. **Workspace** — `.jarfis-state.json`의 `workspace` 값을 그대로 반영 (type, BE/FE path, framework). PO가 별도 판단하지 않음.

10. **Performance Budget** — 정량적 성능 목표 표(지표, 목표값, 측정 방법). 기획 특성에 맞는 지표만 선택 (FE-only면 API 응답 불필요 등).

결과를 $DOCS_DIR/prd.md에 저장하세요."
```

**Step 1-2.5: PRD Completeness Check** (오케스트레이터 직접 실행 — 에이전트 아님)

> 이 단계는 에이전트를 호출하지 않고, 오케스트레이터가 직접 $DOCS_DIR/prd.md를 검증한다.
> Gate 1 사용자 컨펌 전에 PRD의 품질을 자동으로 확인하여, 모호한 PRD가 후속 Phase에 전파되는 것을 방지한다.

검증 체크리스트 (5개 항목):
1. **모호 표현** — "적절한/빠른/충분한/필요에 따라/추후 결정" 등 감지 → 구체적 수치로 대체 지시
2. **KPI 측정 가능성** — 각 KPI에 숫자(목표값) + 측정 방법 존재 여부
3. **Performance Budget 구체성** — 각 지표에 구체적 숫자 + 측정 방법 존재 여부
4. **Required Roles 근거** — 각 역할의 근거 칸이 1문장 이상인지
5. **스코프 경계** — "Out of Scope" 섹션 또는 포함/미포함 구분 존재 여부

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

**Step 1-3: PO 추가 태스크** (senior-product-owner, 선택제)

Gate 1 통과 후, 사용자가 선택한 태스크에 따라 실행:

**법무/컴플라이언스 체크**:
```
Task prompt:
"PRD를 기반으로 법무/컴플라이언스 관련 고려사항을 확인하세요.

확인 항목:
- 개인정보 수집/처리: 어떤 개인정보를 수집하는가? 동의 절차는?
- 약관/결제/환불: 결제 기능이 있다면 관련 법적 의무는?
- 산업별 규제: 해당 산업(의료, 금융 등)의 특수 규제는?
- GDPR/개인정보보호법: 국내외 개인정보보호 규정 해당 여부?

확실하지 않은 사항은 '법무 검토 필요'로 표기하세요.
결과를 $DOCS_DIR/prd.md의 '법무/컴플라이언스' 섹션에 추가하세요."
```

**UX 방향서 작성** (UX Designer 필요 시):
```
Task prompt:
"PRD를 기반으로 UX 방향서를 작성하세요.

templates/ux-direction.md 템플릿을 참조하여 $DOCS_DIR/ux-direction.md를 생성하세요.

필수 포함 항목:
1. IA & URL Structure — 전체 페이지 구조와 URL 패턴
2. Tone & Voice — 전체 톤, 에러 메시지 톤, CTA 스타일
3. Pages — 각 페이지별:
   - 헤딩, 콘텐츠 구조
   - 요구사항 (사용자가 할 수 있어야 하는 것)
   - 인터랙션 패턴 (동기/비동기, 로딩 전략, 에러 처리 방식) — 필수

반응형 범위: $RESPONSIVE (사용자 선택값)

단일 파일로 작성하세요. 분할하지 마세요."
```

