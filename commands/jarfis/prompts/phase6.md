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

결과를 $DOCS_DIR/retrospective.md에 저장하세요."
```

