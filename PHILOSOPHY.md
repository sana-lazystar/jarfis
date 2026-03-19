# JARFIS Philosophy — 9 Principles

> JARFIS의 설계와 진화를 이끄는 핵심 원칙.

## 0. Principle Zero

철학이 시스템을 이끄는 것이 기본 원칙이다. 현재 구현이 철학을 100% 충족하지 못하더라도, 철학을 구현 수준으로 낮추지 않는다. 철학은 지향점(aspiration)이며, 시스템은 이를 향해 진화한다.

## 1. Orchestration for All

비전문가도 영구적으로 개발을 이어갈 수 있는 AI IT 팀. 사용자는 "무엇"만 말하면 된다.

## 2. Token Austerity

AI는 사고/추론/학습/비판에만 쓴다. 기계적 작업(파일 검증, 상태 관리, 측정)은 Script가 담당. 최소 토큰, 최대 효과.

## 3. Self-Evolution

매 워크플로우가 학습 데이터. 회고 → 학습 축적 → 에이전트 강화. 쓸수록 진화한다.

## 4. Dialectic Quality

모든 중요 결정에는 생산적 비판자가 존재한다. Advocate/Critic 토론이 완벽성을 높인다.

## 5. AI-Native Artifacts

산출물은 AI가 읽고 재사용하기 좋은 형태로. 구조화된 마크다운 + JSON = 컨텍스트 효율 극대화.

## 6. Abstraction over Memorization

프로젝트별 암기는 Coder. 패턴을 추상화하여 범용 원칙으로 승격하면 Developer. 에이전트는 Developer가 되어야 한다.

## 7. Deterministic Foundation

결정적(deterministic)인 부분은 반드시 Script로. AI의 비결정성은 "판단이 필요한 곳"에만 허용. 예측 가능한 토대 위에 지능을 얹는다.

## 8. Human Gate, AI Execute

의사결정 지점에서는 사람이 판단. 실행은 AI가 자율적으로. 게이트는 인간의 것, 파이프라인은 AI의 것.

## 9. Resilient Continuity

세션이 죽어도, 컨텍스트가 압축되어도, 작업은 이어진다. 상태 파일 + 자동 커밋 + 백업이 영속성을 보장한다.

---

## 원칙 간 긴장 관계

9개 원칙은 서로 보완하지만, 일부는 긴장 관계에 있다. 이 긴장을 인식하고 의식적으로 관리한다.

| 긴장 관계 | 내용 |
|-----------|------|
| **P3 vs P8** | Self-Evolution(자동 진화)이 완전하면 Human Gate(수동 승인)가 약해진다 |
| **P2 vs P3** | Token Austerity(최소 토큰)와 Self-Evolution(학습 축적)은 학습이 쌓일수록 충돌한다 |
| **P4 vs P1** | Dialectic Quality(모든 결정에 토론)와 Orchestration for All(단순 사용)은 UX 복잡도에서 충돌한다 |

**해소 원칙**: 긴장이 발생하면, 사용자의 의도를 확인하는 게이트를 우선한다 (P8 우위).
