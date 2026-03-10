# Phase 2: Architecture & Planning — Agent Prompts

> 이 파일은 work.md에서 외부화된 에이전트 프롬프트입니다.
> distill에 의해 자동 생성됨.

**Step 2-0: Impact Analysis** (technical-architect)
```
Task prompt:
"$DOCS_DIR/prd.md를 읽고, 기존 코드베이스에 대한 영향 범위를 분석하세요.

$PROJECT_CONTEXT
$BE_PROJECT_PROFILE
$FE_PROJECT_PROFILE

분석 항목:
1. **변경 영향을 받는 파일/모듈** 목록 — 코드베이스를 탐색하여 실제 파일 경로와 함께 나열
2. **의존하는 외부 서비스/API** 목록
3. **DB 스키마 변경 필요 여부** — 마이그레이션이 필요한 경우 명시
4. **공유 컴포넌트 변경 시 다른 기능에 미치는 영향** — 변경할 공유 모듈이 다른 곳에서도 사용되는지
5. **Breaking Change 여부** — 기존 API 소비자, 기존 데이터 포맷에 영향이 있는지

결과를 $DOCS_DIR/impact-analysis.md에 저장하세요."
```

**Step 2-1: 시스템 아키텍처 설계** (technical-architect)
```
Task prompt:
"$DOCS_DIR/prd.md와 $DOCS_DIR/impact-analysis.md를 읽고 시스템 아키텍처를 설계하세요.

포함 항목:
1. 시스템 아키텍처 다이어그램 (Mermaid)
2. 기술 스택 선정 및 근거
3. 데이터 모델 설계
4. API 설계 (주요 엔드포인트)
5. 인프라 구성
6. 보안 아키텍처
7. 확장성 전략

8. **Architecture Decision Records (ADR)** — 주요 설계 결정마다 아래 형식으로 기록:

## Architecture Decision Records

### ADR-001: [결정 제목]
- **상태**: 승인됨
- **맥락**: 어떤 문제를 해결해야 했는지
- **검토한 대안들**:
  | 대안 | 장점 | 단점 |
  |------|------|------|
  | A안 | ... | ... |
  | B안 | ... | ... |
- **결정**: 선택한 안
- **근거**: 트레이드오프 분석 결과
- **영향**: 이 결정으로 인해 변경되거나 제약되는 것들

최소 기술 스택 선정, 데이터 모델 구조, 주요 아키텍처 패턴에 대해 ADR을 작성하세요.

결과를 $DOCS_DIR/architecture.md에 저장하세요."
```

Architect (technical-architect):
```
Task prompt:
"$DOCS_DIR/architecture.md를 기반으로 상세 API 명세(BE-FE API Contract)를 작성하세요.

각 엔드포인트별 포함 항목:
- ## [Method] [Path] (예: ## POST /api/v1/boards)
- Description, Authentication(권한/역할)
- Request 파라미터 표 (Parameter, Location, Type, Required, Description)
- Request Body Example (JSON)
- Response Example (JSON)
- Error Responses 표 (Code, Error Key, Message, 설명)

FE가 타입 정의로 바로 변환할 수 있을 정도로 명확하게 작성하세요.
결과를 $DOCS_DIR/api-spec.md에 저장하세요."
```

Tech Lead (tech-lead) — api-spec.md 리뷰:
```
Task prompt:
"$DOCS_DIR/api-spec.md를 리뷰하세요.

검증 관점:
- 기존 코드베이스의 API 패턴/네이밍 컨벤션과 일관성이 있는지
- 파라미터 타입과 응답 스키마가 FE에서 바로 타입 정의로 변환할 수 있을 정도로 명확한지
- 누락된 에러 케이스가 없는지
- 인증/인가 요구사항이 명확한지

수정이 필요하면 $DOCS_DIR/api-spec.md에 직접 반영하세요."
```

**Step 2-2: 태스크 분해** (tech-lead)
```
Task prompt:
"$DOCS_DIR/prd.md, architecture.md, impact-analysis.md, test-strategy.md, api-spec.md(존재 시)를 읽고 태스크를 분해하세요.

⚠️ PRD 'Required Roles' 표에서 '불필요' 역할 섹션은 'N/A'로 표기.
프로젝트 프로필($BE/$FE_PROJECT_PROFILE) 존재 시 대상 파일을 구체적으로 명시.

각 역할별(BE/FE/DevOps) 태스크를 다음 필드로 정리:
- 설명, 관련 API(api-spec.md 참조), 대상 파일(신규/수정), 의존관계
- 완료 기준, 테스트(test-strategy.md에서 인라인), 보안(architecture.md 보안 섹션 참고)
- 예상 규모(S/M/L), UX 참조(FE만), 카테고리 A/B(DevOps만)

추가 섹션: Shared/Cross-cutting + 의존관계 요약(Mermaid)
결과를 $DOCS_DIR/tasks.md에 저장하세요."
```

**Step 2-3: 테스트 전략 수립** (senior-qa-engineer)
```
Task prompt:
"$DOCS_DIR/prd.md, $DOCS_DIR/tasks.md, $DOCS_DIR/api-spec.md(존재 시)를 읽고 테스트 전략을 수립하세요.
⚠️ tasks.md에서 N/A인 파트의 테스트는 제외하세요.

포함 항목:

## 테스트 피라미드

### Unit Tests
| 대상 모듈/함수 | 테스트 항목 | 우선순위 |
|---------------|-----------|---------|
| (예: createPost) | 정상 생성, 빈 제목, 권한 없음 | P0 |

### Integration Tests
| 통합 대상 | 테스트 항목 | 우선순위 |
|----------|-----------|---------|
| (예: API → DB) | CRUD 정상 동작, 트랜잭션 롤백 | P0 |

### E2E Tests (Critical Path)
| 시나리오 | 단계 | 우선순위 |
|---------|------|---------|
| (예: 게시글 작성 플로우) | 로그인 → 작성 → 저장 → 확인 | P0 |

## 엣지 케이스 목록
- (각 기능별 엣지 케이스 나열)

## 성능 테스트 기준
- PRD의 Performance Budget 참조하여 Pass/Fail 기준 명시

결과를 $DOCS_DIR/test-strategy.md에 저장하세요."
```

**Step 3-1: UX 화면 설계** (senior-ux-designer) — UX Designer 필요 시만 실행
```
Task prompt:
"$DOCS_DIR/prd.md를 읽고 UX 화면 설계를 수행하세요.

포함 항목:
1. 정보 구조 (Information Architecture)
2. 사용자 흐름도 (User Flow — Mermaid)
3. 주요 화면별 와이어프레임 (ASCII 또는 상세 설명)
4. 인터랙션 패턴 정의
5. 접근성 고려사항
6. 반응형 전략

결과를 $DOCS_DIR/ux-spec.md에 저장하세요."
```

**Step 3-2: PO 검증** (senior-product-owner) — UX Designer 필요 시만 실행
```
Task prompt:
"$DOCS_DIR/ux-spec.md를 읽고 프로덕트 관점에서 검증하세요.

검증 항목:
- PRD의 유저 스토리가 모두 반영되었는지
- 사용자 흐름에 빠진 엣지 케이스가 없는지
- 비즈니스 목표 달성에 적합한 UX인지

피드백이 있으면 $DOCS_DIR/ux-spec.md에 '## PO 피드백' 섹션을 추가하세요."
```

