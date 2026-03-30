# Phase 4: Implementation — Agent Prompts

> 이 파일은 work.md에서 외부화된 에이전트 프롬프트입니다.
> distill에 의해 자동 생성됨.

## Phase 2 Handoff (오케스트레이터 사전 작업)

> Phase 4 시작 전, 오케스트레이터는 `.jarfis-state.json`의 `phases.2.handoff`를 읽어
> 아래 정보를 각 구현 에이전트 프롬프트에 주입한다.

```
Handoff 주입 형식:
─── Phase 2 Architect Handoff ───
Key Decisions: $HANDOFF.key_decisions (각 항목)
Warnings: $HANDOFF.warnings (각 항목 — 반드시 이번 Phase에서 해결할 것)
Unresolved: $HANDOFF.unresolved (각 항목 — 구현 시 주의)
───────────────────────────────
```

> Handoff가 없으면 이 섹션을 생략한다.

## Handoff 작성 (Phase 2 완료 시)

> Phase 2 Architect가 설계 완료 시, 오케스트레이터는 다음을 `.jarfis-state.json`에 기록한다:
> `jarfis state set-nested <state_file> phases.2.handoff '{"key_decisions":[...],"warnings":[...],"unresolved":[...]}'`
> work.md Phase 2 완료 블록에도 handoff 요약을 추가한다.

---

## Artifact Loading Checklist (오케스트레이터 → 에이전트 공통 지침)

> 각 구현 에이전트는 작업 시작 전 아래 파일을 로딩한다.
> 오케스트레이터가 이 체크리스트를 Common Implementation Rules와 함께 전달한다.

```
필수 (반드시 존재):
- ✅ $DOCS_DIR/tasks.md — 태스크 목록 (없으면 오케스트레이터 오류)
- ✅ $DOCS_DIR/architecture.md — 시스템 설계 (없으면 오케스트레이터 오류)

조건부 (없으면 대안 사용):
- ❓ $DOCS_DIR/api-spec.md — BE+FE 모두 필요 시 생성됨
  → 없으면: architecture.md의 "API 설계" 섹션을 API 계약 기준으로 사용
- ❓ $DOCS_DIR/design/ — FE + UX Designer 필요 시 생성됨
  → 없으면: tasks.md의 UX 참조 + 프로젝트 기존 컴포넌트 스타일로 구현 (text-only mode)
- ❓ token-map.json — Figma 모드(phases.3.mode === 'figma')일 때만 존재
  → 없거나 파싱 불가 시: HTML 시안의 raw hex 값 사용, 불일치 사항을 커밋 메시지에 기록

※ 이 목록은 표준 워크플로우 기준이며, 프로젝트별 추가 산출물이 있을 수 있다.
  .jarfis-state.json과 $DOCS_DIR의 실제 파일을 우선 참조하라.
```

---

## Common Implementation Rules

> 아래 규칙은 BE/FE/DevOps 모든 구현 에이전트 프롬프트에 공통 적용한다.
> 각 에이전트 프롬프트에 이 섹션을 함께 전달하라.

```
공통 구현 규칙:
- 각 태스크의 '대상 파일'에 명시된 파일 기준으로 작업 (불필요한 코드베이스 탐색 금지)
- 프로젝트 프로필이 존재하면 프로필의 컨벤션을 따를 것
- 각 태스크의 '완료 기준', '테스트', '보안' 항목을 모두 충족할 것

Git Auto-Commit (태스크별):
- 각 태스크 완료 시 변경 파일 git add + 커밋
- 커밋 형식: jarfis({ROLE}-N): 태스크 완료 기준 요약 (한 줄)
- index.lock 에러 시 3초 대기 후 재시도 (최대 3회)
- 완료 시 [TASK_DONE: {ROLE}-N] 형식으로 보고
```

---

**Step 4-0: 보안 사전 리뷰** (senior-security-engineer)
```
Task prompt:
"$DOCS_DIR/architecture.md와 $DOCS_DIR/tasks.md를 읽고, 구현 전 보안 가이드라인을 작성하세요.

포함 항목:
- 인증/인가 구현 가이드
- 입력 검증 규칙
- 민감 데이터 처리 방침
- API 보안 체크리스트
- 주의해야 할 보안 취약점 목록 (OWASP Top 10 기준)

이 가이드라인을 BE/FE/DevOps 구현 시 참조할 수 있도록 정리하세요."
```

Backend (senior-backend-engineer) — **Backend Tasks가 N/A이면 SKIP**:
```
Task prompt:
"$DOCS_DIR/tasks.md의 Backend Tasks를 의존 순서대로 구현하세요.

📂 작업 디렉토리: $BACKEND_PROJECT_DIR

참조: tasks.md(태스크), api-spec.md(API Contract, 존재 시), architecture.md(데이터 모델/패턴)

$LEARNINGS (Backend Engineer 섹션)
$PROJECT_CONTEXT
$BE_PROJECT_PROFILE

위 Common Implementation Rules를 준수하세요. 커밋 형식: jarfis(BE-N):"
```

Frontend (senior-frontend-engineer) — **Frontend Tasks가 N/A이면 SKIP**:
```
Task prompt:
"$DOCS_DIR/tasks.md의 Frontend Tasks를 의존 순서대로 구현하세요.

📂 작업 디렉토리: $FRONTEND_PROJECT_DIR

참조: tasks.md(태스크+UX 참조), api-spec.md(타입 정의/API 호출 기준, 존재 시)

─── Design Contract (디자인 시안 참조 규칙) ───
$DOCS_DIR/design/ 디렉토리의 산출물을 시각적 계약서(Visual Contract)로 참조.

필수 참조 파일 (존재 시):
- $DOCS_DIR/design/{path}/index.html — HTML 시안 (pixel-perfect 레이아웃/인터랙션 참조)
- $DOCS_DIR/design/{path}/reference.png — 비교 기준 스크린샷 (Figma 원본 또는 Text Path 촬영)
  ⚠️ reference.png가 최종 시각 기준이다. HTML과 reference.png가 다르면 reference.png를 따른다.

조건부 참조 파일 (Figma-driven: state phases.3.mode === 'figma'):
- $DOCS_DIR/design/token-map.json — Figma hex → 프로젝트 CSS/SCSS 변수 매핑
  HTML 시안의 CSS variable을 프로젝트 실제 변수로 변환. unmapped는 raw 값 사용.
- $DOCS_DIR/design/assets/ — 이미지 에셋 (photos/, icons/, illustrations/, backgrounds/)
  프로젝트의 적절한 위치(public/, assets/ 등)에 복사하여 사용.
- $DOCS_DIR/design/{path}/figma-spec.yaml — Figma YAML 원본 (상세 스펙 확인 필요 시)
- $DOCS_DIR/design/{path}/section-map.json — 섹션 구조 (레이아웃 의도 파악 시)

공통 규칙:
- URL → 시안 매핑: /{path} → $DOCS_DIR/design/{path}/index.html
- HTML/CSS를 그대로 복붙하지 않음 — 프로젝트의 기술 스택(Vue, React, SCSS 등)으로 구현
- 반응형: HTML 시안이 반응형이면 동일한 breakpoint 적용
- <!-- COMMON: {name} --> 주석: 프로젝트의 기존 공통 컴포넌트를 사용
───────────────────────────────

$LEARNINGS (Frontend Engineer 섹션)
$PROJECT_CONTEXT
$FE_PROJECT_PROFILE

위 Common Implementation Rules를 준수하세요. 커밋 형식: jarfis(FE-N):"
```

DevOps (senior-devops-sre-engineer) — **DevOps Tasks가 N/A이면 SKIP**:
```
Task prompt:
"$DOCS_DIR/tasks.md의 DevOps Tasks를 의존 순서대로 구현하세요.

참조: tasks.md(태스크별 카테고리/대상 파일), architecture.md(인프라 구성)

⚠️ 각 태스크의 '카테고리'를 확인:
- 카테고리 A (로컬 생성): Dockerfile, CI/CD, IaC 등 → 직접 생성
- 카테고리 B (클라우드 작업): → $DOCS_DIR/infra-runbook.md에 단계별 실행 가이드 문서화

위 Common Implementation Rules를 준수하세요. 커밋 형식: jarfis(DevOps-N):"
```
