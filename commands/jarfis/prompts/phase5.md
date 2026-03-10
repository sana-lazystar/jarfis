# Phase 5: Review & QA — Agent Prompts

> 이 파일은 work.md에서 외부화된 에이전트 프롬프트입니다.
> distill에 의해 자동 생성됨.

Tech Lead (tech-lead):
```
Task prompt:
"$DOCS_DIR/api-spec.md와 실제 구현 코드를 대조하여 API Contract 준수 여부를 검증하세요.

📂 **프로젝트 디렉토리:**
- Backend: $BACKEND_PROJECT_DIR
- Frontend: $FRONTEND_PROJECT_DIR

검증 항목:
1. BE 코드에서 실제 구현된 엔드포인트 경로/메서드 추출 → api-spec.md와 대조
2. FE 코드에서 실제 호출하는 API 경로/타입 추출 → api-spec.md와 대조
3. 각 항목별 일치/불일치 판정:
   - [ ] 엔드포인트 경로 일치
   - [ ] HTTP Method 일치
   - [ ] Request 파라미터 일치
   - [ ] Response 스키마 호환
   - [ ] Error 코드 일치

결과를 $DOCS_DIR/api-contract-check.md에 저장하세요.
불일치 항목이 있으면 명확히 표시하세요."
```

Tech Lead (tech-lead):
```
Task prompt:
"Phase 4에서 구현된 코드를 리뷰하세요.
⚠️ $DOCS_DIR/tasks.md를 확인하여 N/A가 아닌 (실제 구현된) 파트의 코드만 리뷰하세요.

📂 **프로젝트 디렉토리:**
- Backend: $BACKEND_PROJECT_DIR
- Frontend: $FRONTEND_PROJECT_DIR
(N/A인 디렉토리는 무시하세요)

참조 문서:
- $DOCS_DIR/api-contract-check.md (존재 시 — 불일치 항목 우선 확인)
- $DOCS_DIR/deployment-plan.md (배포 전략 적절성 검토)

$LEARNINGS (Tech Lead 섹션)

리뷰 관점:
- 코드 품질 및 가독성
- 아키텍처 설계($DOCS_DIR/architecture.md) 준수 여부
- API Contract 준수 여부 — api-contract-check.md 결과 참조
- 디자인 패턴 적절성
- 에러 핸들링
- 성능 고려사항 — PRD의 Performance Budget 기준 충족 여부
- 기술 부채 여부
- 배포 전략($DOCS_DIR/deployment-plan.md) 적절성

리뷰 결과를 정리하세요."
```

QA (senior-qa-engineer):
```
Task prompt:
"Phase 4에서 구현된 코드를 기반으로 QA를 수행하세요.
⚠️ $DOCS_DIR/tasks.md를 확인하여 N/A가 아닌 (실제 구현된) 파트만 테스트하세요.
UX 설계($DOCS_DIR/ux-spec.md)가 존재하지 않으면 UI 관련 테스트는 제외하세요.

참조 문서:
- PRD: $DOCS_DIR/prd.md
- UX 설계: $DOCS_DIR/ux-spec.md (존재하는 경우만)
- 테스트 전략: $DOCS_DIR/test-strategy.md (이 전략 기준으로 검증)

$LEARNINGS (QA Engineer 섹션)

QA 항목:
- test-strategy.md의 테스트 시나리오별 Pass/Fail 판정
- 엣지 케이스 테스트
- 크로스 브라우저/디바이스 호환성 (Frontend가 있는 경우만)
- 성능 테스트 — PRD의 Performance Budget 기준으로 Pass/Fail 판정
- 접근성 테스트 (Frontend가 있는 경우만)

결과를 정리하세요."
```

Security (senior-security-engineer):
```
Task prompt:
"Phase 4에서 구현된 코드의 보안 리뷰를 수행하세요.
⚠️ $DOCS_DIR/tasks.md를 확인하여 N/A가 아닌 (실제 구현된) 파트만 리뷰하세요.

리뷰 항목:
- OWASP Top 10 취약점 점검
- 인증/인가 구현 검증
- 입력 검증 및 출력 인코딩
- 민감 데이터 노출 여부
- 의존성 취약점 확인
- 보안 헤더 및 CORS 설정 (해당 파트가 있는 경우만)

결과를 정리하세요."
```

**Step 5-2 병리 패턴 감지** (오케스트레이터 직접 실행 — 에이전트 아님)

> 이 검증은 Step 5-2 재리뷰(2회차 이상)에서만 실행한다.
> 이전 review.md와 현재 review.md를 비교하여 리뷰 루프의 병리 패턴을 감지한다.

검증 절차:
```
1. [Stagnation 감지]
   이전 review.md의 이슈 목록과 현재 이슈를 비교한다.
   - 동일한 이슈가 2회 연속 등장 → Stagnation
   - 경고 메시지: "⚠️ 다음 이슈가 2회 연속 미해결입니다. 현재 설계에서 해결 불가능할 수 있습니다:"
     (해당 이슈 목록 표시)

2. [Regression 감지]
   이전 review.md에 없던 새 이슈가 현재 등장했는지 확인한다.
   - 이전에 없던 이슈가 새로 발생 → Regression
   - 경고 메시지: "⚠️ 수정이 회귀를 유발했습니다. 새로 발생한 이슈:"
     (새 이슈 목록 표시)

3. [Oscillation 감지]
   3회차 이상인 경우, N회차와 N-2회차의 이슈가 동일한지 확인한다.
   - 동일하면 → Oscillation (두 상태 사이에서 진동)
   - 경고 메시지: "⚠️ 수정이 이전 상태로 되돌아갔습니다 (진동 패턴 감지)."
```

병리 패턴 발견 시:
- 게이트 3 선택지에 "🔙 Phase 2로 돌아가 설계 재검토" 옵션을 추가한다.
- `.jarfis-state.json`의 `review_iterations` 필드를 증가시킨다.
- 3회 이상 반복 시: "⚠️ 리뷰 루프가 3회 이상 반복되었습니다. 설계 재검토를 강력히 권장합니다."

---

Tech Lead (tech-lead):
```
Task prompt:
"Phase 5의 모든 리뷰 결과를 종합하여 근본 원인을 진단하고, 구현 에이전트를 위한 수정 지시서를 작성하세요.

다음 리뷰 결과를 모두 읽으세요:
- $DOCS_DIR/review.md (Tech Lead 코드리뷰 + QA 결과 + Security 리뷰)
- $DOCS_DIR/api-contract-check.md (존재 시 — API Contract 불일치 항목)

분석 절차:
1. 모든 이슈를 나열한다.
2. 이슈 간 상관관계를 분석하여 공통 원인이 있는 이슈를 그룹핑한다.
   예: 'API 500 에러'(QA) + '인증 토큰 검증 누락'(Security) → 미들웨어 등록 순서 오류
3. 각 그룹의 근본 원인을 코드 레벨에서 특정한다 (파일 경로, 라인, 로직).
4. 수정 지시서를 작성한다 — 담당 에이전트(BE/FE/DevOps), 수정 대상 파일, 수정 방향, 주의사항.
5. 같은 유형의 문제가 재발하지 않도록 추가 테스트 또는 구조 개선을 제안한다.

결과를 다음 형식으로 $DOCS_DIR/diagnosis.md에 저장하세요:

## 이슈 종합 (N건)

### 이슈 그룹 1: [공통 원인 요약]
관련 이슈:
- [QA] 이슈 설명
- [Security] 이슈 설명
- [CodeReview] 이슈 설명

근본 원인: (코드 레벨 원인 분석)
영향 범위: (이 원인이 영향을 미치는 기능/파일 목록)

수정 지시:
| 담당 | 파일 | 수정 내용 | 우선순위 |
|------|------|----------|---------|
| BE | src/path/file.ts:42 | 수정 방향 | P0 |

회귀 방지: (추가할 테스트 또는 구조 개선)

(이슈 그룹 반복)

## 수정 우선순위 요약
| 순위 | 이슈 그룹 | 담당 | 예상 난이도 |
|------|----------|------|-----------|
"
```

Backend (senior-backend-engineer) — **diagnosis.md에 BE 수정 지시가 있을 때만**:
```
Task prompt:
"$DOCS_DIR/diagnosis.md를 읽고, 당신에게 할당된 수정 지시를 수행하세요.

📂 **작업 디렉토리**: $BACKEND_PROJECT_DIR

각 수정 지시에 대해:
1. 지시된 파일과 라인을 확인한다.
2. 근본 원인 분석을 참고하여 수정한다.
3. 회귀 방지 섹션에 명시된 테스트를 추가한다.
4. 수정 전후의 동작을 검증한다.

Git Auto-Commit (이슈별):
- 각 이슈 그룹 수정 완료 시 변경된 파일을 git add하고 커밋하세요.
- 커밋 메시지 형식: jarfis(fix/BE): 이슈 요약 (한 줄)
  예: jarfis(fix/BE): SQL injection 취약점 수정 및 파라미터 바인딩 적용
- git commit이 index.lock 에러로 실패하면 3초 대기 후 재시도하세요 (최대 3회).

⚠️ diagnosis.md에 명시된 수정 범위만 수정하세요. 범위 밖의 리팩토링은 하지 마세요."
```

Frontend (senior-frontend-engineer) — **diagnosis.md에 FE 수정 지시가 있을 때만**:
```
Task prompt:
"$DOCS_DIR/diagnosis.md를 읽고, 당신에게 할당된 수정 지시를 수행하세요.

📂 **작업 디렉토리**: $FRONTEND_PROJECT_DIR

각 수정 지시에 대해:
1. 지시된 파일과 라인을 확인한다.
2. 근본 원인 분석을 참고하여 수정한다.
3. 회귀 방지 섹션에 명시된 테스트를 추가한다.
4. 수정 전후의 동작을 검증한다.

Git Auto-Commit (이슈별):
- 각 이슈 그룹 수정 완료 시 변경된 파일을 git add하고 커밋하세요.
- 커밋 메시지 형식: jarfis(fix/FE): 이슈 요약 (한 줄)
  예: jarfis(fix/FE): XSS 방지를 위한 입력 새니타이징 추가
- git commit이 index.lock 에러로 실패하면 3초 대기 후 재시도하세요 (최대 3회).

⚠️ diagnosis.md에 명시된 수정 범위만 수정하세요. 범위 밖의 리팩토링은 하지 마세요."
```

