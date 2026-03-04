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
"$DOCS_DIR/architecture.md를 기반으로 상세 API 명세를 작성하세요.

⚠️ 이 명세는 BE와 FE가 동시에 독립적으로 개발할 수 있도록 하는 **API Contract** 역할을 합니다.
BE는 이 명세대로 API를 구현하고, FE는 이 명세를 기준으로 타입 정의와 API 호출 코드를 작성합니다.

각 엔드포인트에 대해 다음을 정의하세요:

### 엔드포인트별 작성 형식:

## [Method] [Path]
예: ## POST /api/v1/boards

### Description
엔드포인트의 목적과 사용 시나리오를 간략히 설명

### Authentication
인증 필요 여부 및 필요한 권한/역할

### Request
| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| id | path | number | ✅ | 리소스 ID |
| page | query | number | ⬜ | 페이지 번호 (기본값: 1) |
| title | body | string | ✅ | 게시글 제목 |

### Request Body Example
```json
{
  \"title\": \"string\",
  \"content\": \"string\"
}
```

### Response (200 OK)
```json
{
  \"id\": 1,
  \"title\": \"string\",
  \"content\": \"string\",
  \"created_at\": \"2025-01-01T00:00:00Z\"
}
```

### Error Responses
| Code | Error Key | Message | 설명 |
|------|-----------|---------|------|
| 400 | INVALID_TITLE | 제목을 입력해주세요 | 제목이 빈 값 |
| 401 | UNAUTHORIZED | 인증이 필요합니다 | 미인증 접근 |
| 404 | NOT_FOUND | 리소스를 찾을 수 없습니다 | 존재하지 않는 리소스 |

---

모든 엔드포인트를 위 형식으로 작성하세요.
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
"$DOCS_DIR/prd.md와 $DOCS_DIR/architecture.md를 읽고 구현 태스크를 분해하세요.
$DOCS_DIR/api-spec.md가 존재하면 함께 참조하여, BE/FE 태스크에 관련 API 엔드포인트를 매핑하세요.
$DOCS_DIR/impact-analysis.md를 참조하여 영향 범위가 큰 변경은 태스크에 명시하세요.
$DOCS_DIR/test-strategy.md를 참조하여 각 태스크에 해당하는 테스트 항목을 인라인하세요.
Phase 4-0 보안 가이드라인이 아직 없으므로, $DOCS_DIR/architecture.md의 보안 아키텍처 섹션을 참고하여
각 태스크에 보안 주의사항을 인라인하세요.

⚠️ 중요: PRD의 'Required Roles' 표를 먼저 확인하세요.
'불필요'로 표시된 역할의 섹션은 'N/A — 이 프로젝트에서는 해당 없음'으로 표기하세요.

⚠️ **프로젝트 프로필 활용**: $BE_PROJECT_PROFILE 또는 $FE_PROJECT_PROFILE이 존재하면,
프로필의 디렉토리 구조와 파일 패턴을 참조하여 각 태스크의 '대상 파일'을 구체적으로 명시하세요.
프로필이 없으면 architecture.md 기준으로 추정하세요.

다음 형식으로 정리하세요:

## Backend Tasks
(또는: N/A — 이 프로젝트에서는 백엔드 작업이 필요하지 않습니다. 근거: ...)

### BE-1: [태스크명]
- 설명: [구현할 내용]
- 관련 API: [POST/GET/PUT/DELETE /api/v1/xxx] (api-spec.md 참조)
- 대상 파일:
  - [src/path/file.ts] (신규/수정)
  - [src/path/file2.ts] (수정 — 변경 이유)
- 의존: [없음 / BE-0 완료 후 / Shared-1 완료 후]
- 완료 기준: [구체적 수락 조건]
- 테스트: [test-strategy.md에서 이 태스크에 해당하는 항목 인라인]
- 보안: [이 태스크에 해당하는 보안 주의사항 인라인]
- 예상 규모: [S: ~50줄 / M: ~200줄 / L: ~500줄+]

### BE-2: [태스크명]
...

## Frontend Tasks
(또는: N/A — 이 프로젝트에서는 프론트엔드 작업이 필요하지 않습니다. 근거: ...)

### FE-1: [태스크명]
- 설명: [구현할 내용]
- 관련 API: [POST/GET /api/v1/xxx] (api-spec.md 참조)
- UX 참조: [ux-spec.md의 해당 화면/섹션 명시]
- 대상 파일:
  - [src/pages/xxx/index.tsx] (신규/수정)
  - [src/components/xxx.tsx] (신규/수정)
- 의존: [없음 / FE-0 완료 후]
- 완료 기준: [구체적 수락 조건]
- 테스트: [test-strategy.md에서 이 태스크에 해당하는 항목 인라인]
- 보안: [이 태스크에 해당하는 보안 주의사항 인라인]
- 예상 규모: [S / M / L]

### FE-2: [태스크명]
...

## DevOps Tasks
(또는: N/A — 이 프로젝트에서는 DevOps 작업이 필요하지 않습니다. 근거: ...)

### DevOps-1: [태스크명]
- 설명: [구현할 내용]
- 카테고리: [A: 로컬 생성 / B: 클라우드 작업 (문서화)]
- 대상 파일: [생성/수정할 파일 경로]
- 의존: [없음 / BE-1 완료 후]
- 완료 기준: [구체적 수락 조건]
- 예상 규모: [S / M / L]

## Shared / Cross-cutting
### Shared-1: [태스크명]
- 설명: [공통 작업 내용]
- 대상 파일: [파일 경로]
- 사용처: [BE-1, FE-2 등 이 결과를 사용하는 태스크]

## 의존관계 요약
(Mermaid 또는 텍스트로 전체 의존관계 시각화)

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

