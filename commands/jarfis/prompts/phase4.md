# Phase 4: Implementation — Agent Prompts

> 이 파일은 work.md에서 외부화된 에이전트 프롬프트입니다.
> distill에 의해 자동 생성됨.

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
"$DOCS_DIR/tasks.md의 Backend Tasks 섹션을 읽고, 태스크를 의존 순서대로 구현하세요.

📂 **작업 디렉토리**: $BACKEND_PROJECT_DIR

참조 문서:
- $DOCS_DIR/tasks.md — Backend Tasks 섹션 (태스크별 대상 파일, 완료 기준, 테스트, 보안 주의사항 포함)
- $DOCS_DIR/api-spec.md — 존재 시 API Contract 원본 (엔드포인트, 스키마, 에러 코드를 반드시 명세대로 구현)
- $DOCS_DIR/architecture.md — 데이터 모델, 아키텍처 패턴 참조

$LEARNINGS (Backend Engineer 섹션)
$PROJECT_CONTEXT
$BE_PROJECT_PROFILE

구현 규칙:
- 각 태스크의 '대상 파일'에 명시된 파일을 기준으로 작업하세요 (불필요한 코드베이스 탐색 금지).
- $BE_PROJECT_PROFILE이 존재하면 프로필의 컨벤션을 따르세요.
- 각 태스크의 '완료 기준'을 충족하세요.
- 각 태스크의 '테스트' 항목에 따라 구현과 함께 테스트 코드를 작성하세요.
- 각 태스크의 '보안' 항목을 준수하세요.

⚠️ BE/FE 병렬 구현 시, 콘텐츠 데이터(정적 데이터, seed data)는 단일 소스에서 정의하세요.
FE mock과 BE seed가 별도로 존재하면 데이터 불일치가 발생합니다.

✅ Self-Checklist (Phase 5 진입 전 자가 검증):
- [ ] API 호출이 정상 동작하는가? (엔드포인트 경로, 파라미터, 응답 스키마)
- [ ] 콘텐츠 정합성: BE seed 데이터와 FE mock 데이터가 일치하는가?
- [ ] 민감 정보 추상화: 내부 서비스명, AWS 리소스명 등이 외부에 노출되지 않는가?

Git Auto-Commit (태스크별):
- 각 태스크 완료 시 변경된 파일을 git add하고 커밋하세요.
- 커밋 메시지 형식: jarfis(BE-N): 태스크 완료 기준 요약 (한 줄)
  예: jarfis(BE-1): 사용자 인증 API 엔드포인트 구현
- git commit이 index.lock 에러로 실패하면 3초 대기 후 재시도하세요 (최대 3회).
- 각 태스크 완료 시 [TASK_DONE: BE-N] 형식으로 보고하세요."
```

Frontend (senior-frontend-engineer) — **Frontend Tasks가 N/A이면 SKIP**:
```
Task prompt:
"$DOCS_DIR/tasks.md의 Frontend Tasks 섹션을 읽고, 태스크를 의존 순서대로 구현하세요.

📂 **작업 디렉토리**: $FRONTEND_PROJECT_DIR

참조 문서:
- $DOCS_DIR/tasks.md — Frontend Tasks 섹션 (태스크별 대상 파일, UX 참조, 완료 기준, 테스트, 보안 주의사항 포함)
- $DOCS_DIR/api-spec.md — 존재 시 API Contract 원본 (타입 정의, API 호출 함수, 에러 핸들링의 기준. BE 미완성이어도 명세 기준으로 구현)
- $DOCS_DIR/ux-spec.md — 존재 시 화면 구조와 인터랙션 패턴 참조

$LEARNINGS (Frontend Engineer 섹션)
$PROJECT_CONTEXT
$FE_PROJECT_PROFILE

구현 규칙:
- 각 태스크의 '대상 파일'에 명시된 파일을 기준으로 작업하세요 (불필요한 코드베이스 탐색 금지).
- 각 태스크의 'UX 참조'에 명시된 ux-spec.md 섹션을 참고하세요.
- $FE_PROJECT_PROFILE이 존재하면 프로필의 컨벤션을 따르세요.
- 각 태스크의 '완료 기준'을 충족하세요.
- 각 태스크의 '테스트' 항목에 따라 구현과 함께 테스트 코드를 작성하세요.
- 각 태스크의 '보안' 항목을 준수하세요.

⚠️ BE/FE 병렬 구현 시, 콘텐츠 데이터(정적 데이터, seed data)는 단일 소스에서 정의하세요.
FE mock과 BE seed가 별도로 존재하면 데이터 불일치가 발생합니다.

- 태스크가 15개를 초과하면 10~15개 배치 단위로 분할하여 실행하세요.
- 각 태스크 완료 시 tasks.md의 해당 항목 체크박스를 [ ] → [x]로 마킹하여 진행 상태를 추적하세요.

✅ Self-Checklist (Phase 5 진입 전 자가 검증):
- [ ] API 호출: useQuery/useSuspenseQuery로 실제 API를 호출하는가? (JSX 하드코딩 금지)
- [ ] 콘텐츠 정합성: FE mock 데이터와 BE seed 데이터가 일치하는가?
- [ ] 민감 정보 추상화: 내부 서비스명, AWS 리소스명 등이 외부에 노출되지 않는가?
- [ ] 기본 접근성: 키보드 내비게이션, ARIA 속성이 적용되어 있는가?

Git Auto-Commit (태스크별):
- 각 태스크 완료 시 변경된 파일을 git add하고 커밋하세요.
- 커밋 메시지 형식: jarfis(FE-N): 태스크 완료 기준 요약 (한 줄)
  예: jarfis(FE-1): 로그인 폼 컴포넌트 및 유효성 검증 구현
- git commit이 index.lock 에러로 실패하면 3초 대기 후 재시도하세요 (최대 3회).
- 각 태스크 완료 시 [TASK_DONE: FE-N] 형식으로 보고하세요."
```

DevOps (senior-devops-sre-engineer) — **DevOps Tasks가 N/A이면 SKIP**:
```
Task prompt:
"$DOCS_DIR/tasks.md의 DevOps Tasks 섹션을 읽고, 태스크를 의존 순서대로 구현하세요.

참조 문서:
- $DOCS_DIR/tasks.md — DevOps Tasks 섹션 (태스크별 카테고리, 대상 파일, 완료 기준 포함)
- $DOCS_DIR/architecture.md — 인프라 구성 섹션 참조

⚠️ **로컬 작업과 인프라 작업을 분리하세요.**
이 환경에서는 클라우드 인프라에 대한 직접 접근 권한이 없습니다.

각 태스크의 '카테고리' 필드를 확인하세요:
- **카테고리 A** (로컬 생성): Dockerfile, CI/CD, IaC, 설정 파일 등 → 프로젝트 디렉토리에 직접 생성
- **카테고리 B** (클라우드 작업): AWS 콘솔, SSH, DNS 등 → $DOCS_DIR/infra-runbook.md에 단계별 실행 가이드로 문서화

infra-runbook.md 작성 시 각 작업에 포함: 작업명, 사전 조건, 실행 단계 (CLI/콘솔), 예상 결과, 실행 순서.

Git Auto-Commit (태스크별):
- 각 태스크 완료 시 변경된 파일을 git add하고 커밋하세요.
- 커밋 메시지 형식: jarfis(DevOps-N): 태스크 완료 기준 요약 (한 줄)
  예: jarfis(DevOps-1): GitHub Actions CI 파이프라인 설정
- git commit이 index.lock 에러로 실패하면 3초 대기 후 재시도하세요 (최대 3회).
- 각 태스크 완료 시 [TASK_DONE: DevOps-N] 형식으로 보고하세요."
```

