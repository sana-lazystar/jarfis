# Phase 4.5: Operational Readiness — Agent Prompts

> 이 파일은 work.md에서 외부화된 에이전트 프롬프트입니다.
> distill에 의해 자동 생성됨.

**Step 4.5-1: 배포 전략 + 운영 준비도** (tech-lead)
```
Task prompt:
"Phase 4에서 구현된 코드의 배포/롤아웃 전략을 수립하세요.
$DOCS_DIR/tasks.md를 확인하여 실제 구현된 파트 기준으로 작성하세요.
$DOCS_DIR/architecture.md와 $DOCS_DIR/impact-analysis.md를 참조하세요.

다음 형식으로 작성하세요:

## 배포 전략
- **배포 방식**: (Blue-Green / Canary / Rolling / Big Bang 중 선택 + 근거)
- **Feature Flag 계획**: 어떤 기능에 플래그가 필요한지 (불필요하면 '해당 없음')
- **배포 순서**: (예: DB 마이그레이션 → BE 배포 → FE 배포)

## 롤백 계획
- **롤백 트리거 조건**: (예: 에러율 1% 초과, P95 응답시간 500ms 초과)
- **롤백 절차**: 단계별 복구 방법
- **DB 롤백**: 마이그레이션 롤백 가능 여부 및 방법 (해당 시)

## 운영 준비도 체크리스트
- [ ] 로깅: 핵심 동작에 로그가 남는가?
- [ ] 모니터링: 에러율, 응답시간 모니터링이 되는가?
- [ ] 알림: 임계치 초과 시 알림이 발생하는가?
- [ ] DB 마이그레이션: 안전하게 실행/롤백 가능한가?
- [ ] 환경 변수: 새로 필요한 환경 변수가 모두 설정되었는가?
- [ ] 의존성: 외부 서비스 의존성이 안정적인가?

결과를 $DOCS_DIR/deployment-plan.md에 저장하세요."
```

