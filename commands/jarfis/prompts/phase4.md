# Phase 4: Implementation — Agent Prompts

> 이 파일은 work.md에서 외부화된 에이전트 프롬프트입니다.
> distill에 의해 자동 생성됨.

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

참조: tasks.md(태스크+UX 참조), api-spec.md(타입 정의/API 호출 기준, 존재 시), ux-spec.md(화면 구조, 존재 시)

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
