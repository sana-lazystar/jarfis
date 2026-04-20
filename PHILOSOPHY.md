# JARFIS Philosophy

> **Last aligned**: v4.0.5 · 2026-04-20
> **Audience**: 기여자 · 외부 평가자 · 미래의 자신

JARFIS는 **AI를 판단·실행 단위로 운영하는 개발 시스템**이다.
철학은 그 운영의 **지향과 기준**을 선언한다.

---

## Preface — v3에서 v4로

> "JARFIS v4는 기능적으로 v3보다 분명히 전진했다. 특히 deterministic verification 전환이 크다.
> 지금의 가장 큰 약점은 시스템 자체보다, 그 전진을 철학·설계 문서가 아직 제대로 선언하지 못하고 있다는 점이다."

이 문서는 그 선언이다. v3 PHILOSOPHY(2026-03-19)에서 고정되어 있던 원칙들을 v4 현실에 맞춰 재정의했다.
변경 근거는 [MIGRATION.md](./MIGRATION.md#principle-changes) 참조.

**용어**: 본 문서에서 "ROI"는 **Return on Investment** — 비용 대비 가치(value per cost)를 의미한다.
절대 비용의 최소화가 아닌, **비용 1단위당 얻는 가치의 비율**을 판단 기준으로 삼는다.

<sup>*헤드라인 출처: 외부 평가 (ChatGPT + Claude, 3라운드 교차 검증, 2026-04-19).*</sup>

---

## Principle Zero — Function over Form
> *Philosophy as Tool · ROI Decides*
> 도구로서의 철학 · ROI가 결정한다

철학·패턴·아키텍처·규율은 모두 도구다.
이름뿐인 허울은 중요하지 않다.

### 원칙의 자격

- 같은 비용에 더 많은 가치를 만들어야 한다.
- 지금은 못 만들더라도, 만들 수 있는 명백한 경로가 있어야 한다.
- 실제로 의사결정을 이끈 기록이 있어야 한다.

### 원칙의 폐기

- 오랫동안 의사결정을 이끌지 못했다면, 담당자 없는 형식이다.
- ROI가 명백히 낮은데 유지되는 원칙은 설계 추적성(Design Traceability)을 훼손한다.
- 정직한 삭제가 맹목적 수호보다 우선한다.

철학도 방향을 바꾼다. 방향 전환의 기준은 ROI다.

---

## #1. Deterministic Foundation
> *Deterministic by Default · AI by Necessity*
> 기본은 결정론 · 필요할 때만 AI

결정 가능한 것은 결정적으로 구현한다.
AI의 비결정성은 **증명 가능한 경계** 안에만 허용된다.

- Script가 판정, AI가 판단.
- 판정 경계는 자동 테스트로 방어한다.
- 구현 없는 결정 장치는 허위 형식이므로 정직하게 삭제한다.

### 역할 분담

| 영역 | 담당 | 근거 |
|------|------|------|
| Gate 판정 (`phase-verify`, `pattern-detect`) | Script (`verify.py`) | Deterministic Python ~10ms vs LLM gate ~1400 tokens + non-deterministic |
| State 쓰기 (`.jarfis-state.json`) | Script (single-writer: main session only) | 동시성 경합 회피, 파일 경로 단위 보장 |
| 구조 검증 (Leaky Abstraction 경계) | Script (`test_architecture.py`) | 회귀 자동 차단, LLM 재판정 불필요 |
| 도메인 판단 (domain detect tie-break) | Hybrid (Script 우선, AskUserQuestion 보완) | 휴리스틱 + 명시 config |
| Nuanced 판단 (PRD, 아키텍처, 리뷰) | AI Persona | 창의성·맥락 필요 영역 |

### 함의

"더 똑똑한 AI가 있으니 판단도 맡기자"는 설계를 배제한다.
AI는 nuanced 판단에만 쓰인다. Gate/State/Test 같은 영역은
Script가 2-3 orders of magnitude 빠르게 결정한다.

**v4의 강화**: v4.0.0에서 `jarfis-black`(LLM gate) → `verify.py`(Python gate) 교체로
원칙이 한 단계 극단화. 외부 평가자 3명 모두 "v4의 가장 큰 변화"로 인정.

---

## #2. Dialectic for Self-Modification
> *Dialectic for Self-Modification Only*
> Dialectic은 시스템 자기수정에만

시스템이 **자기 자신을 고칠 때**는 생산적 비판자가 존재한다.
일반 워크플로우의 품질 보장은 다른 원칙들(#1 Deterministic Foundation + 파생 장치)이 담당한다.

### 적용 범위

**시스템 자기수정(self-modification) 계열 명령** — JARFIS가 JARFIS 자체의
프롬프트·에이전트·워크플로우·도메인 팩 구조를 변경하는 행위.

- **현재 (v4.0.5) 인스턴스**: `sys-implement`, `sys-upgrade`, `sys-distill`
- **제외**: `sys-health`(진단), `sys-version`(버전 번프) 등 운영/유틸성 명령.
  사용자 프로젝트 코드 수정, Phase 2~5 워크플로우 구간도 제외.
- **확장 규칙**: 향후 추가되는 자기수정 계열 명령(예: 가상의 sys-evolve)은
  정의에 부합하면 자동 포함.

### 방식

Advocate / Critic 2인 토론, 라운드당 300 단어, 최대 2라운드 (v3.0.0부터 **래칫 수렴**과 결합).
파급력 큰 결정(자기수정)에 한정된 비용 높은 도구.

---

## #3. Dogfooding Evolution
> *Every Execution is Training Data · JARFIS Included*
> 모든 실행이 학습 데이터 · JARFIS도 포함

모든 실행은 학습 데이터다 — 사용자 프로젝트 워크플로우와 JARFIS 자체의 자기 수정 세션 모두.

- 회고(Phase 6) → `learnings.md` / `project-context.md` / `workflow-metrics.tsv`
- 축적된 학습은 `sys-upgrade`로 다음 실행에 반영
- 시스템이 자기 자신을 학습 대상에 포함시킨다 (dogfooding)
- 1회 초기 비용, N회 실행에 분할 상환 — 대상이 적어도 가치가 돌아온다

### 현재 상태 (v4.0.5)

- **활성 구현**: `learnings.md` / `project-context.md` 축적 (v1.1.0부터),
  `sys-upgrade` 반영 루프, `sys-distill` 프롬프트 압축,
  dogfooding (v3.0.0 "120회 래칫 수렴 + 11 병렬 에이전트 분석" 사례)
- **Aspiration path (v4.1 후보)**: `workflow-metrics.tsv`는 v2.5.5부터 기록 중이나,
  대시보드와 자동 A/B 반영 루프 미완. 데이터 축적 중이므로 경로 명확.
- **ROI 완성도**: 활성 구현만으로 46일간 메이저 릴리스 4회 + 113 tags 진행 실증.
  대시보드 완성 시 외부 rubric 축 11(Self-Evidence) + 축 12(Design Traceability) 상승 예상.

---

## #4. Resilient Continuity
> *State Outlives Session*
> 상태는 세션보다 오래 유지될 수 있다

세션은 종료하면 끝난다. 세션 종료로 작업이 사라진다면, 복구 비용이 커진다.
이 비용 격차를 활용해서, 평소에 적은 비용을 들여 큰 사고를 막는다.
상태는 세션과 별개로 저장되며, 세션이 끝나도 남아있다.

### 방어 원칙

세션의 **모든 경계 지점** — 진입·종료·압축·도구 호출·출력 분리 —
에 상태를 보존하는 장치를 둔다.

### 현재 (v4.0.5) 인스턴스

- **상태 파일**: `.jarfis-state.json` — main 세션만 쓰기 (single-writer 규칙)
- **Hook 4종**:
  - `pre-compact` — 컨텍스트 압축 직전에 상태 백업
  - `session-start` — 재진입 시 v3 / v4 감지 후 상태 복원
  - `safety` (PreToolUse) — 위험한 tool 호출 차단
  - `quality-gate` (PostToolUse) — 품질 실패 조기 감지
- **세션 격리**: sub-agent 출력을 상태와 분리해 저장
  *(v4.0.5 구현: tmux `phase-results/phase{N}/attempt{K}.json`)*
- **Post-mortem 캡처**: 세션이 끝나기 전에 scrollback 저장
  *(v4.0.5 구현: `tmux_claude --save-pane`)*

### 현재 상태 (v4.0.5)

- **활성 구현**: 위 현재 인스턴스 (4 hooks + single-writer state + phase-results 격리 + --save-pane)
- **Aspiration path (v4.1+ 후보)**:
  - tmux 외 실행 환경(Docker, standalone) 전환 시 방어 장치 재구현
  - 현 구조는 **거의 완숙** — v4.0.4 이후 session survival 회귀 없음
- **ROI 완성도**: v4.0.4 이후 M8 Step 8.5 같은 post-mortem 근본 원인 불명 사례 0건.
  원칙 구현이 가장 "완성형"에 가까운 상태.

**확장 규칙**: 새 경계 지점이 생기거나 실행 방식이 바뀌어도,
방어 원칙에 맞는 장치만 추가하면 된다. 원칙 자체는 바뀌지 않는다.

---

## #5. Context as Investment
> *Default Minimal · Scale with Value*
> 기본은 최소 · 가치에 따라 확장

컨텍스트는 자원이다. 토큰·시간·주의력 모두 비용이다.
같은 가치를 얻는다면 비용이 낮은 쪽을 택한다.
가치가 비례해서 커지면 비용도 기꺼이 지불한다.
핵심은 "싼 것"이 아니라 **비용 대비 가치**다.

이 원칙은 AI가 컨텍스트를 다루는 **세 가지 차원**에 모두 적용된다.

### 1. 경제성 — 토큰과 주의력

**투자 원칙**: 기본값은 최소 컨텍스트. 가치가 증명된 만큼만 확장한다.
추가·관측·학습 로드는 기본값을 off로 두고, 가치가 확인될 때만 켠다 (opt-in).

**현재 (v4.0.5) 인스턴스**:
- Skill 예산: 스킬 토큰 2500 이내, 첫 스킬은 예산 초과해도 보장
- Context injection matrix + lazy loading: 필요할 때만 로드
- Opt-in 관측: `JARFIS_TRACE=0` 기본, 필요 시 `JARFIS_TRACE=1` (~0.008% overhead)
- 주기 압축: `sys-distill`로 프롬프트 누적 비용 정리
- 역방향 투자: Phase 4 tmux-per-phase는 세션별 컨텍스트 중복 비용이 크지만,
  병렬성·격리 가치가 비용을 정당화 *(v4.0.0 의식적 trade-off)*

### 2. 산출물 포맷 — AI가 다시 읽을 형태

**원칙**: 산출물은 다음 실행이 재활용할 수 있는 **구조화된 형태**로 남긴다.
자유 서술보다 고정 스키마가 재사용 비용을 낮춘다.

**현재 (v4.0.5) 인스턴스**:
- 구조화 마크다운 + JSON + YAML 포맷
- 고정 스키마 산출물:
  - `.jarfis-state.json` (세션 상태)
  - `phase-results/phase{N}/attempt{K}.json` (Phase 실행 기록)
  - `learnings.md` / `project-context.md` (학습 축적)
  - `workflow-metrics.tsv` (측정 로그)
  - `agent-composition.yaml` (에이전트 합성 규격)
  - `_schema.yaml` (Domain Pack Published Language)

### 3. Composition — 역할 조립 재사용

**원칙**: 프로젝트별 암기 대신 재사용 가능한 합성 단위를 만든다.
Persona + Skill + Rule 3계층은 **도메인 간 재사용 가능한 자산**이다.

**현재 (v4.0.5) 인스턴스**:
- **Persona**: 역할별 인지 프레임 — product-owner, technical-architect,
  backend-developer, frontend-developer, devops-engineer, qa-engineer,
  security-engineer, tech-lead, ux-designer
- **Skill**: 기술 전문성 — react, vue, nodejs, tauri, rust, aws-lambda,
  dynamodb, redis, postgres, s3, cognito 등 16개
  (전체 목록은 [INFRASTRUCTURE.md](./INFRASTRUCTURE.md) 참조)
- **Rule**: 프로젝트별 학습 — `learnings.md`, `project-context.md`
- **동적 합성**: `agent-composition.yaml` + `compose` CLI —
  LLM inference 아닌 **결정적 조립** (#1 Deterministic Foundation과 교차)
- **Domain Pack 확장성**: `_schema.yaml` Published Language —
  도메인별 7개 Extension Points (EP1~EP7)

### 안티패턴 (3 차원 공통)

- 프롬프트 stuffing — 모든 것을 다 주입 → 토큰 낭비 + LLM attention 분산
- 자유 포맷 산출 — 다음 실행이 재활용 못 하는 형태
- 프로젝트별 암기 — 추상화 없이 프롬프트 복제로 확장 시도

### 현재 상태 (v4.0.5)

- **활성 구현**: 세 차원 모두 구현 — 경제성(Skill 예산 / lazy loading / opt-in 관측 / sys-distill),
  산출물 포맷(고정 스키마 6종), Composition(Persona + Skill + Rule + agent-composition.yaml).
- **Aspiration path (v4.1+ 후보)**:
  - 실시간 토큰 소비 대시보드 (현재 사후 CHANGELOG 분석만 가능)
  - A/B 프롬프트 실험 프레임 (`workflow-metrics.tsv` 활용)
  - Anthropic prompt caching 확대 시 토큰 비용 계산 재보정
- **ROI 완성도**: 46일간 token-efficient refine 5건 + Persona/Skill/Rule 3계층 v3.0.0 완성 +
  고정 스키마 산출물 체계 완성 — 세 차원 모두 살아있는 원칙.

**확장 규칙**: 새 기능 추가 시 세 차원 모두 검토:
- 경제성 — 기본값 off (opt-in)
- 산출물 포맷 — 다음 실행이 재활용 가능한 구조화 형태
- Composition — 재사용 가능한 단위로 추상화

가치가 실사용으로 증명된 후에야 opt-in 권고 또는 default-on 승격.

---

## #6. Gated Autonomy
> *Gate the Irreversible · Automate the Rest*
> 되돌릴 수 없는 곳만 게이트 · 나머지는 자동

판단은 사람이 한다. 실행은 AI가 한다.
하지만 모든 지점에 게이트를 두면 실행 흐름이 무거워진다.
게이트는 **"틀렸을 때 복구 비용이 큰 지점"**에만 둔다.

### 게이트 기준 (세 개 중 하나라도 충족 시 정당화)

1. **작업 방향 전체에 영향 주는 결정** — 잘못 가면 전체 재시작
2. **AI가 합리적 default를 추론할 수 없는 개인적 선택** — locale, 타겟 사용자, 브랜드 등
3. **잘못된 자율 실행의 복구 비용 > 사용자 개입 비용** — irreversible 영역

### 현재 (v4.0.5) 인스턴스

- **주요 게이트 3개**:
  - Gate 1 (Discovery → Architecture)
  - Gate 2 (Architecture + UX → Implementation)
  - Gate 3 (Review → Retrospective)
- **Phase T Triage**: Type A(전체 워크플로우) · Type C(direct 답변) 분기
- **Phase 0/1a 대화형 설정**: 스코프 · 도메인 · design mode 등 AI 추론 불가 영역

### 안티패턴

- 사소한 결정까지 사용자 확인 (파일명 접두어 등)
- AI가 합리적 default를 낼 수 있는데 선택지 나열
- 같은 질문 여러 Phase에서 반복

### 현재 상태 (v4.0.5)

- **활성 구현**: 위 현재 인스턴스 (주요 게이트 3개 + Triage + Phase 0/1a dialogue)
- **Aspiration path (v4.1+ 후보)**:
  - Autopilot 모드 — 기본 default 자동 채택, 사용자가 개입 필요 시만 gate
  - Smart defaults — learnings 기반 default 추천
  - Gate audit 주기화 — ROI 낮은 게이트 정기 검토·제거
- **외부 평가**: 축 4 (Human Gate Balance) 7.5/10 — 비전문가 UX 긴장 인정.
  v4.1 target ≥ 8.5 (리서치 제안치, v4.1 플래닝 단계에서 재확정).

**확장 규칙**: 새 게이트 추가 제안 시 위 **게이트 기준 3가지** 통과해야 한다.
"이 게이트 없으면 어떤 실패가 불가피한가?" 답이 약하면 게이트 아니다.

---

## 원칙 간 긴장 관계

원칙들은 대체로 상보적이지만, 일부 지점에서 서로 조율이 필요하다.

| 긴장 | 해소 패턴 |
|------|----------|
| **#3 Dogfooding Evolution × #5 Context as Investment** — 학습 축적이 컨텍스트 부풀림 | `sys-distill`로 주기 압축. 학습도 비용 대비 가치가 있어야 한다. |
| **#4 Resilient Continuity × #5 Context as Investment** — 방어 장치(hooks, backup)가 상시 overhead | < 1초/hour로 값 싼 보험. 고비용 장치(`--save-pane`)는 opt-in. |
| **#6 Gated Autonomy × (구 P1 정신)** — 게이트가 과잉이면 "누구나를 위한 오케스트레이션" 지향과 충돌 | 게이트 기준 3가지 통과 원칙. v4.1 autopilot 모드로 해소 예정 (외부 평가 축 4 = 7.5/10 → target ≥ 8.5). |
| **#2 Dialectic × 실행 속도** — Dialectic은 느리다 | 적용 범위를 sys-* 전용으로 제한. 일반 워크플로우는 #1 Deterministic Foundation + TDD 계열 장치가 담당. |
| **#1 Deterministic × #2 Dialectic** | 충돌 아닌 보완. Deterministic은 "판정" 영역, Dialectic은 "자기수정의 판단" 영역. 역할 분담. |

### 해소 원칙

긴장이 발생하면 **ROI를 우선 기준**으로 삼는다 (P0 Function over Form).
판단이 모호하면 **#6 Gated Autonomy의 사용자 게이트**로 돌린다
(구 v3 P8 "Human Gate, AI Execute" 정신 계승).

---

## v3 → v4 원칙 변경 이력

| v3 원칙 | v4 원칙 | 변경 |
|---------|---------|------|
| P0 Principle Zero | Principle Zero — Function over Form | 재정의 (ROI 프레임 추가, aspiration + falsifiable 이원화) |
| P1 Orchestration for All | — (삭제) | 46일 활동 증거 부재. 정신은 #6의 "게이트 최소화"에 흡수. |
| P2 Token Austerity | #5 Context as Investment (경제성 aspect) | 재정의 (최소 지상주의 → 비용 대비 가치) |
| P3 Self-Evolution | #3 Dogfooding Evolution | rename + dogfooding 통합 + amortization 명시 |
| P4 Dialectic Quality | #2 Dialectic for Self-Modification | 범위 명시 (sys-* 전용) |
| P5 AI-Native Artifacts | #5 Context as Investment (산출물 포맷 aspect) | 통합 |
| P6 Abstraction over Memorization | #5 Context as Investment (Composition aspect) | 통합 |
| P7 Deterministic Foundation | #1 Deterministic Foundation | 유지 + 강화 (verify.py, single-writer state rule) |
| P8 Human Gate, AI Execute | #6 Gated Autonomy | rename + 게이트 기준 3가지 명시 |
| P9 Resilient Continuity | #4 Resilient Continuity | 유지 + 확장 (4 hooks, phase-results 격리, --save-pane) |

변경 rationale과 각 결정의 상세 근거는 [MIGRATION.md#principle-changes](./MIGRATION.md#principle-changes) 참조.

---

*문서 체계 참조: [DESIGN.md](./DESIGN.md) (ADR) · [MIGRATION.md](./MIGRATION.md) (v3→v4 전환) · [CHANGELOG.md](./CHANGELOG.md) (버전 이력)*
