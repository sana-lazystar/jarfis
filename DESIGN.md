# JARFIS Design Document

> **Last aligned**: v4.0.5 · 2026-04-20
> JARFIS v4 아키텍처 결정 기록 (v2.5-v4 ADR 통합)
>
> 각 ADR은 Context → Decision → Consequences 형식을 따른다.
> PHILOSOPHY.md 원칙은 `P0`, `#1`~`#6`으로 인용한다 (v2 체계).
>
> **Status 표기**:
> - **Active** — v3 결정이 v4에서도 유효. P-ref 갱신만 (v4 하위 섹션 불필요).
> - **Updated** — v3 결정 유효하되 v4 맥락 추가 (`### v4 Update` 하위 섹션). 강화·부분 교체·범위 명시·P-ref rebrand 모두 포함.
> - **Superseded** — 상위 배너로 교체 ADR 지시. 원문은 history로 보존.

---

## 목차

### v2.5~v3 ADR (history + v4 updates)

1. [ADR-1: Agent 합성 (모놀리식 → Persona+Skill+Rule)](#adr-1) — *Updated*
2. [ADR-2: Domain Pack Published Language](#adr-2) — *Active*
3. [ADR-3: 하이브리드 상태 관리](#adr-3) — *Updated*
4. [ADR-4: 래칫 수렴](#adr-4) — *Superseded by ADR-21*
5. [ADR-5: 기존 에이전트 유지 (Fallback)](#adr-5) — *Updated (P-ref rebrand)*
6. [ADR-6: Phase 4만 전환](#adr-6) — *Superseded by ADR-19*
7. [ADR-7: Skill 설계 원칙](#adr-7) — *Active*
8. [ADR-8: Script vs Prompt 경계](#adr-8) — *Updated*
9. [ADR-9: Human Gate 배치](#adr-9) — *Updated*
10. [ADR-10: Resilient Continuity](#adr-10) — *Updated*
11. [ADR-11: Cascading Specificity](#adr-11) — *Active*
12. [ADR-12: Leaky Abstraction 검증](#adr-12) — *Active*
13. [ADR-13: Dialectic Review](#adr-13) — *Updated*
14. [ADR-14: 프롬프트 외부화 & 증류](#adr-14) — *Active*

### v4 신규 ADR

15. [ADR-15: verify.py — Deterministic Gate](#adr-15)
16. [ADR-16: tmux-per-phase Orchestration](#adr-16)
17. [ADR-17: agent-composition.yaml — Deterministic Composition](#adr-17)
18. [ADR-18: Single-writer State Rule](#adr-18)
19. [ADR-19: Phase 4.5 Operational Readiness](#adr-19)
20. [ADR-20: JARFIS_TRACE Opt-in Observability](#adr-20)
21. [ADR-21: Ratchet Reality](#adr-21)

### 부록

- [부록 A: v2.5 → v3 → v4 전환 맵](#transition-map)
- [부록 B: 원칙 참조 매핑 (v3 P{N} → v4 #{N})](#principle-map)
- [부록 C: 분산 ADR 링크](#distributed-adr)

---

<a id="adr-1"></a>
## ADR-1: Agent 합성 (모놀리식 → Persona+Skill+Rule)

> **Status**: Updated (2026-04-20)
> **Principle**: **#5 Context as Investment (Composition aspect)** ← v3 P6 Abstraction over Memorization
> **Also references**: #1 Deterministic Foundation (via ADR-17)

### Context

v2.5까지 에이전트는 모놀리식 프롬프트였다. 역할(persona), 기술 지식(skill), 프로젝트 규칙(rule)이 하나의 프롬프트에 혼재되어 도메인 확장 시 전체 프롬프트를 복제해야 했다.

### Decision

`compose()` 함수로 3개 레이어를 런타임에 합성한다.

```python
# domain.py
def compose(domain_name, role_name, task,
            learnings_path=None, project_context_path=None,
            domains_dir=None):
```

**토큰 예산**: `max_skill_tokens=2500` (domain.yaml에서 설정, domain.py:339에서 적용).

**첫 스킬 보장 (W1-1)**: 토큰 예산 초과 시에도 첫 번째 스킬은 반드시 로드한다.

```python
if token_used + skill_tokens > token_budget:
    if i == 0 and not loaded_skills:
        pass  # Load first skill even if over budget
    else:
        truncated_skills.append(...)
        continue
```

**CJK 토큰 추정 (W1-2)**: 한국어/중국어/일본어 비율에 따라 chars_per_token을 동적 조정한다.

```python
chars_per_token = 4 - (2 * cjk_ratio)  # 4 (ASCII) ~ 2 (CJK)
```

**Fallback**: 도메인 설정 로드 실패 시 `_FALLBACK_PERSONAS` 매핑으로 persona-only 실행 (ADR-5 참조).

### Consequences

- **장점**: 도메인 추가 시 YAML+Skill 파일만 작성. 코어 코드 수정 불필요.
- **단점**: 합성 과정에서 토큰 추정 오차 (ASCII ±20%, 혼합 ±30%).
- **기각된 대안**: 에이전트별 전용 프롬프트 파일 — 도메인 N개 x 역할 M개 = N*M개 파일 관리 비용.

### v4 Update (2026-04-20)

v4에서 합성 진입점이 **독립 CLI 패키지**로 이관되었다 (ADR-17 참조).

- **신규 진입점**: `compose` CLI (`~/.claude/scripts/jarfis/compose/`, 독립 패키지 — `__main__.py` + `assembler.py` + `config.py` + `reader.py` + `resolver.py` + `skills.py` + `validate.py` + `errors.py` + `models.py`) + `agent-composition.yaml` 선언적 규칙
- **v3 `domain.py::compose()` 관계**: v4 CLI가 `domain.py::compose()`를 호출하지 않음. 단 일부 로직이 v4 CLI에서 재사용 가능하도록 `domain.py:329` 주변에서 **추출**되어 v3 함수도 존속 (backward compat + 재사용)
- **LLM inference 제거**: v3에서 일부 합성 분기가 LLM 판단에 의존하던 부분을 **결정적 규칙(YAML)** 으로 대체 — #1 Deterministic Foundation과 교차
- **Persona 인벤토리 확정 (v4.0.0)**: product-owner, technical-architect, backend-developer, frontend-developer, devops-engineer, qa-engineer, security-engineer, tech-lead, ux-designer
- **Skill 인벤토리 확장**: react, vue, nodejs, tauri-backend/webview, rust, cargo-clippy, biome-lint, express, aws-lambda, cognito, dynamodb, redis, postgres, s3, browser 등 16개

**원칙 매핑 변경**: v3 P6 Abstraction over Memorization은 v4에서 **#5 Context as Investment의 Composition aspect**로 통합되었다 (PHILOSOPHY v2). Composition 단위는 프로젝트별 암기를 대체하는 **재사용 자산**으로 자리매김.

---

<a id="adr-2"></a>
## ADR-2: Domain Pack Published Language

> **Status**: Active (2026-04-20)
> **Principle**: **#1 Deterministic Foundation** ← v3 P7

### Context

도메인별 에이전트 구성, 감지 규칙, 품질 게이트 등을 표현할 공통 스키마가 필요했다. 각 도메인 팩이 제각기 다른 구조를 사용하면 코어 코드가 도메인별 분기로 오염된다.

### Decision

`_schema.yaml`에 7개 Extension Point(EP1~EP7)를 정의하고, 모든 도메인 팩이 이 스키마를 따르도록 한다.

| EP | 이름 | 역할 |
|----|------|------|
| EP1 | Agent Composition | roles (plan/design/implement/review) + max_skill_tokens + rules |
| EP2 | Framework Detection | detect.indicators (file/manifest/key/confidence) |
| EP3 | Quality Gates | linters + type_checker |
| EP4 | Commit Format | implementation/fix 커밋 프리픽스 |
| EP5 | MCP Integration | required/optional MCP 서버 |
| EP6 | Test & Build Pipeline | test runner + build check |
| EP7 | Domain Lifecycle | install/init/upgrade 훅 |

**현재 도메인 팩**:

| 도메인 | implement roles | detect indicators | external_skills |
|--------|----------------|-------------------|-----------------|
| web | 3 (backend, frontend, devops) | 6 (react, vue, nextjs, svelte, typescript, nodejs) | 없음 |
| desktop | 2 (rust, webview) | 4 (tauri.conf.json x2, Cargo.toml, package.json) | `["web/react"]` |

### Consequences

- **장점**: 새 도메인 추가 시 YAML 파일 1개 + skills/ 디렉토리로 완결.
- **단점**: 스키마 변경 시 모든 도메인 팩 마이그레이션 필요 (schema_version으로 관리).
- **기각된 대안**: JSON Schema — YAML의 주석/가독성 이점이 AI-Native 환경에서 더 유리 (v3 P5, v4 #5 산출물 포맷).

---

<a id="adr-3"></a>
## ADR-3: 하이브리드 상태 관리

> **Status**: Updated (2026-04-20)
> **Principle**: **#4 Resilient Continuity** ← v3 P9
> **Related ADRs**: ADR-18 (state.json single-writer rule), ADR-20 (traces.jsonl → trace.py opt-in)
> **Preserved from v3**: `.jarfis-state.json` 중앙 state + `audit.jsonl` best-effort 이벤트 로그 패턴

### Context

워크플로우 상태를 단일 파일로 관리하면 디버깅이 어렵고, 이벤트 기반으로만 관리하면 현재 상태 조회에 전체 리플레이가 필요하다.

### Decision (v3 원안)

3개 파일로 관심사를 분리한다.

| 파일 | 형식 | 용도 | 실패 시 |
|------|------|------|---------|
| `.jarfis-state.json` | JSON | 현재 상태 CRUD (Phase, Gate, Ratchet 결과) | 워크플로우 중단 |
| `audit.jsonl` | JSONL (append-only) | 이벤트 로그 (14개 타입) | 무시 |
| `traces.jsonl` | JSONL (append-only) | 성능 메트릭 (토큰, 소요시간) | 무시 |

**audit.jsonl 이벤트 타입** (14개, v3 설계):

```python
EVENT_TYPES = [
    "WorkflowStarted", "WorkflowCompleted", "WorkflowAborted",
    "PhaseStarted", "PhaseCompleted",
    "AgentInvoked", "AgentCompleted", "AgentFailed",
    "QualityGateEvaluated", "GateApproved",
    "RatchetChecked",
    "AutoCommit",
    "FallbackTriggered", "CircuitBreakerChanged",
]
```

**Best-effort 패턴**: audit 기록 실패는 상태 변경을 차단하지 않는다.

```python
def _try_audit(audit_path, event_type, **data):
    """Best-effort audit logging. Failures are silently ignored (#4)."""
    if not audit_path:
        return
    try:
        global _audit_module
        if _audit_module is None:
            from . import audit as _mod
            _audit_module = _mod
        _audit_module.append_event(audit_path, event_type, **data)
    except Exception:
        pass  # Audit is not a recovery source — never block state ops
```

### Consequences

- **장점**: state.json은 즉시 조회 가능, audit.jsonl은 시간순 이벤트 추적/디버깅에 최적.
- **단점**: 3개 파일 간 정합성 보장이 없다 (설계 의도 — audit/trace는 복구 소스가 아님).
- **기각된 대안**: SQLite — 단일 사용자 CLI 환경에서 과도한 복잡성.

### v4 Update (2026-04-20)

v4에서 세 파일의 역할이 분화되었다:

| 파일 | v4 상태 | 관련 ADR |
|------|---------|---------|
| `.jarfis-state.json` | **Single-writer rule 적용** — main 세션만 쓰기, tmux sub-agent는 읽기 전용 | ADR-18 (신설) |
| `audit.jsonl` | **유지** — `state.py::_try_audit` + `audit.py` (80줄) 여전히 활성. best-effort 패턴 보존 | — |
| `traces.jsonl` | **대체** — 고정 경로 traces.jsonl 대신 `trace.py` opt-in 서브시스템(JSONL at caller-supplied path). `JARFIS_TRACE=1`일 때만 활성 | ADR-20 (신설) |

v3 원안의 **관심사 분리 철학**(현재 상태 / 이벤트 로그 / 성능 메트릭)은 v4에서도 유효하다. 바뀐 것은 구현 수준의 경계 규칙(동시성, opt-in gating)이다.

---

<a id="adr-4"></a>
## ADR-4: 래칫 수렴

> **Status**: **Superseded by ADR-21** (2026-04-20)
> **Rationale**: "3종 래칫" 프레임이 v4 실체와 괴리 — PRD Ratchet은 v4.0.1에서 **전면 제거** (producer 부재), Fix Ratchet은 legacy 명시, TDD Ratchet만 조건부 생존 (findings F-09)
> **v3 Principle**: P4 Dialectic Quality (v4에서는 #2 Dialectic for Self-Modification으로 범위 축소되어 Ratchet과 분리)
>
> 원문은 history로 보존한다. 현 정책은 [ADR-21](#adr-21) 참조.

### Context (v3, preserved)

AI 에이전트가 수정할 때 이전에 통과한 항목을 퇴행시키는 문제가 발생했다. 품질이 단조증가하도록 보장하는 메커니즘이 필요했다.

### Decision (v3, preserved)

3종 래칫을 도입한다. 래칫은 "한번 통과한 기준은 다시 내려가지 않는다"는 원칙이다.

**1. PRD Ratchet** (Phase 1):
- 5개 항목 x 0-2점 = 총 10점
- 항목: 모호 표현, KPI 측정 가능성, Performance Budget, Required Roles 근거, 스코프 경계
- 이전에 Pass(2점)였던 항목이 Fail로 변하면 래칫 위반 → 경고 후 재지시
- 최대 2회 재시도, 이후 사용자 판단

**2. TDD Ratchet** (Phase 4):
- `current_pass_rate >= baseline_pass_rate` 필수
- REJECT 시: `git stash` → 에이전트 재지시 → 태스크당 최대 2회
- 2회 실패 시: `git stash pop` → 원복 → 다음 태스크 진행 → Phase 5에서 진단

**3. Fix Ratchet** (Continue/Extend 모드):
- `fix_current_pass_rate >= fix_baseline_pass_rate` 필수
- 최대 1회 재시도
- 실패 시: AskUserQuestion ("계속 진행" / "중단")

### Consequences (v3, preserved)

- **장점**: 품질 단조증가 보장, 무한 루프 방지 (회수 제한).
- **단점**: 래칫 위반 감지는 오케스트레이터(AI)의 판단에 의존.
- **기각된 대안**: 무제한 재시도 — 토큰 낭비 + 무한 루프 위험.

---

<a id="adr-5"></a>
## ADR-5: 기존 에이전트 유지 (Fallback)

> **Status**: Updated (P-ref rebrand, 2026-04-20)
> **Principle**: **P0 Function over Form (ROI pragmatism)** + **#6 Gated Autonomy (합리적 default 영역)** ← v3 P1 Orchestration for All (삭제)
> **Mechanism status**: **Active** — `_FALLBACK_PERSONAS`가 `domain.py:314, 470`에 여전히 존재

### Context

v3.0에서 Domain Pack 시스템을 도입하지만, 도메인 미설정 프로젝트도 지원해야 한다.

### Decision

`$DOMAIN`이 null일 때 v2.5 하드코딩 에이전트 매핑으로 fallback한다 (work.md v3:578-582 / work.md v4 compose fallback).

```python
# domain.py:314 (2026-04-20 현재)
_FALLBACK_PERSONAS = {
    "backend_engineer": "backend-developer",
    "frontend_engineer": "frontend-developer",
    "devops_engineer": "devops-engineer",
    "rust_engineer": "backend-developer",
    "webview_engineer": "frontend-developer",
    "security_engineer": "security-engineer",
    "qa_engineer": "qa-engineer",
}
```

### Consequences

- **장점**: 도메인 설정 부재 프로젝트와도 hybrid-compat. 합성 실패 시 crash 대신 persona-only 실행으로 연속성 확보.
- **단점**: fallback 경로의 유지보수 비용 (두 가지 실행 경로 공존).
- **기각된 대안**: 강제 domain 요구 — 기존 프로젝트 경험 파괴 + 신규 프로젝트 onboarding 비용 증가.

### v4 Update (2026-04-20) — Principle Rebrand

v3의 P-ref는 **P1 Orchestration for All**(비전문가도 영구적 개발)이었다. v4에서 P1은 46일 활동 증거 부재로 **삭제**되었다 (PHILOSOPHY v2, [MIGRATION §Principle Changes]). 그러나 `_FALLBACK_PERSONAS` 메커니즘 자체는 유지된다.

**새로운 rationale**:
- **P0 Function over Form** — 메커니즘이 실제로 작동하고 (domain-less 프로젝트의 실행을 보장) ROI가 입증되므로 유지. "비전문가 지원"이라는 aspirational framing을 제거하고 "실용적 하위 호환"이라는 function-first framing으로 재정립.
- **#6 Gated Autonomy (합리적 default)** — Fallback은 AI가 합리적으로 추론할 수 있는 default 영역이므로 사용자 게이트를 거치지 않아도 된다.

메커니즘은 동일, 원칙 framing만 달라진다.

---

<a id="adr-6"></a>
## ADR-6: Phase 4만 전환

> **Status**: **Superseded by ADR-19** (2026-04-20)
> **Rationale**: v4에서 Phase 1a/1b 분리 + Phase 2 ∥ 3 병렬 tmux + Phase 4.5 신설로 "Phase 4만 전환" 프레임 자체가 무효화됨. Domain pack 기반 분기는 전체 phase로 확산됨 (findings F-03, F-04, F-05)
> **v3 Principle**: — (v4에서는 #1, #4, #6 교차 참조)
>
> 원문은 history로 보존한다. 현 phase 구조는 WORKFLOW.md + [ADR-19](#adr-19) 참조.

### Context (v3, preserved)

Domain Pack 시스템이 전 Phase에 영향을 미치면 변경 범위가 너무 크다. v3.0 최소 전환 범위를 결정해야 했다.

### Decision (v3, preserved)

Phase 0에서 도메인을 감지하고, Phase 4(구현)에서만 `if $DOMAIN` 분기를 적용한다 (work.md v3:566-582).

```
$DOMAIN이 null이 아닌 경우 (domain.yaml 기반):
1. jarfis_cli.py domain agents "$DOMAIN" implement → 역할 목록 JSON 로드
2. hooks.phase4.before 실행 (있으면)
3. 각 역할에 대해 domain compose 호출 → Agent 도구 호출
4. hooks.phase4.after 실행 (있으면)
5. pipeline.test.runner로 래칫 체크
```

Plan/Design/Review Phase는 기존 에이전트를 그대로 사용한다.

### Consequences (v3, preserved)

- **장점**: 전환 범위 최소화, Phase 1~3/5~6 안정성 유지.
- **단점**: Plan/Design에서도 도메인 특화 에이전트를 쓰고 싶은 경우 추후 확장 필요.
- **기각된 대안**: 전 Phase 동시 전환 — 검증 범위가 너무 넓어 래칫 수렴 불가.

---

<a id="adr-7"></a>
## ADR-7: Skill 설계 원칙

> **Status**: Active (2026-04-20)
> **Principle**: **#5 Context as Investment (Composition aspect + 경제성)** ← v3 P6

### Context

Skill 파일에 API 문서 수준의 지식을 넣으면 토큰이 폭발하고, 추상적 원칙만 넣으면 실용성이 없다.

### Decision

"패턴 > 지식" 원칙을 채택한다.

**Skill 구조**:
1. **Core Patterns** — 해당 기술의 핵심 설계 패턴
2. **Decision Framework** — 상황별 선택 기준
3. **Common Pitfalls** — 자주 발생하는 실수와 회피법

**크기 기준**:
- 개별 스킬 300토큰 이내 목표
- 역할당 2~3개 스킬 합산 2500토큰 예산 내 (ADR-1 max_skill_tokens)

### Consequences

- **장점**: 토큰 효율적, 다른 프로젝트에서도 유효한 범용 패턴.
- **단점**: 프로젝트 특화 지식은 Rules(learnings.md)로 분리 관리 필요.
- **기각된 대안**: API 레퍼런스 포함 — 토큰 예산 초과, LLM이 이미 학습한 지식 중복.

---

<a id="adr-8"></a>
## ADR-8: Script vs Prompt 경계

> **Status**: Updated (strengthened, 2026-04-20)
> **Principle**: **#1 Deterministic Foundation** + **#5 Context as Investment (경제성)** ← v3 P2 + P7
> **Strengthened by**: ADR-15 (verify.py — Deterministic Gate)

### Context

AI 에이전트가 모든 작업을 수행하면 토큰 낭비가 심하고 결과가 비결정적이다. 어떤 작업을 Script로, 어떤 작업을 AI 판단으로 배분할지 기준이 필요했다.

### Decision

기계적 작업은 Script, 판단이 필요한 작업은 AI Prompt.

**Script 영역** — `jarfis_cli.py` 서브커맨드 (v3 기준 13개):

| 커맨드 | 역할 |
|--------|------|
| state | 상태 파일 CRUD |
| detect | 프레임워크/언어 감지 |
| measure | 토큰 측정 |
| preflight | 사전 검증 |
| meetings | 미팅 목록 |
| version | 버전 관리 |
| sync | 저장소 동기화 |
| quality-gate | 린트/타입체크 |
| validate | 상태/산출물 검증 |
| org | Organization 관리 |
| wiki | 위키 시맨틱 검색 (deprecated) |
| search | 시맨틱 검색 |
| domain | 도메인 팩 관리 |

**AI Prompt 영역** — work.md의 Gate/Ratchet 판정:
- PRD 채점 (v3: 5항목 0-2점)
- TDD 래칫 판정 (pass_rate 비교)
- Gate 승인/수정/중단 결정 보조

### Consequences

- **장점**: 결정적 작업의 재현성 보장, AI 토큰을 판단에 집중.
- **단점**: 경계가 모호한 작업 존재 (예: 도메인 감지 — Script가 후보 제시, AI가 최종 선택).
- **기각된 대안**: 전부 AI — 토큰 비용 폭발 + 비결정적 결과.

### v4 Update (2026-04-20) — Deterministic Strengthening

v4.0.0 핵심 전환으로 Script 영역이 극단화되었다:

- **LLM gate 제거**: v3의 `jarfis-black` (LLM 기반 Phase 검증, ~1400 tokens, non-deterministic) → v4의 `verify.py` (Python, deterministic, ~10ms) — 상세는 [ADR-15](#adr-15)
- **Script 영역 확장**: `verify.py`의 4개 엔트리 (`gate-check`, `phase-check`, `phase-verify`, `pattern-detect`)가 v3에서 LLM 판정이었거나 존재하지 않던 영역을 deterministic으로 흡수
- **규모 변화**: `verify.py` 1,349줄, `domain.py` 883줄, `state.py` 372줄 — Script 영역이 더 커졌으나 AI 호출 수는 감소
- **AI Prompt 영역 축소**: Gate/Ratchet 판정 중 기계적 부분은 모두 verify.py로 이관. 남은 AI 영역은 **nuanced 판단**(아키텍처 설계, 코드 리뷰, 회고, sys-* Dialectic)

**원칙의 방향**: "AI가 더 똑똑해지면 판단도 맡기자"가 아니라 **"AI의 비결정성을 결정적 경계 안에 가두자"**. v4는 이 원칙을 관측 계층까지 확장 (ADR-20).

---

<a id="adr-9"></a>
## ADR-9: Human Gate 배치

> **Status**: Updated (2026-04-20)
> **Principle**: **#6 Gated Autonomy** ← v3 P8 Human Gate, AI Execute

### Context

AI가 전체 워크플로우를 자율 실행하면 잘못된 방향으로 깊이 들어간 후에야 문제를 발견한다. 인간 검토 시점의 최적 배치가 필요했다.

### Decision

3개 Gate를 주요 Phase 전환점에 배치한다.

| Gate | 위치 | 검토 내용 |
|------|------|----------|
| Gate 1 | Phase 1 후 | PRD + Working Backwards + PRD Score (v3) / Discovery 산출물 (v4) |
| Gate 2 | Phase 2&3 후 | 아키텍처 + 태스크 분해 + UX 시안 |
| Gate 3 | Phase 5 후 | 코드리뷰 + QA + 보안 + 배포 리뷰 |

**강제 규칙** (work.md):

> 반드시 AskUserQuestion을 사용하여 사용자의 명시적 선택을 받는다 (텍스트 출력만으로 자동 진행하지 않는다).

Gate 옵션: "승인" → 다음 Phase, "수정" → 해당 Phase 재실행, "중단" → 즉시 종료.

### Consequences

- **장점**: 구현 전(Gate 2)에 방향 수정 가능, 배포 전(Gate 3)에 품질 확인.
- **단점**: 3회 인간 개입이 자동화 속도를 제한 (v3 P1과의 긴장, v4에서는 #6 내부 긴장으로 축소).
- **기각된 대안**: Gate 없음 — 잘못된 구현 전체 폐기 리스크. 5개 Gate — 과도한 중단으로 UX 저하.

### v4 Update (2026-04-20)

**게이트 기준 3가지 명시** (PHILOSOPHY v2 §#6):
1. 작업 방향 전체에 영향 주는 결정
2. AI가 합리적 default를 추론할 수 없는 개인적 선택
3. 잘못된 자율 실행의 복구 비용 > 사용자 개입 비용 (irreversible 영역)

Gate 1/2/3은 세 기준을 모두 충족. 새 게이트 추가 제안 시 이 기준 통과 필수.

**Triage (Phase T) 추가 게이트화**:
- v4의 Phase T는 `$ARGUMENTS` 분류의 첫 암묵 게이트
- Type A (full workflow) → 자동 Phase 0 진행
- Type C (direct answer) → AskUserQuestion 분기
- Resume → 기존 워크플로우 재개
- Type B는 M7에서 제거 (findings F-07)

**v4.1 방향** (aspirational):
- Autopilot 모드 — learnings 기반 default 자동 채택
- Smart defaults — 사용자 선택 이력 기반 추천
- Gate audit 주기화 — ROI 낮은 게이트 정기 검토

외부 평가 축 4 (Human Gate Balance) 7.5/10 → v4.1 target ≥ 8.5.

---

<a id="adr-10"></a>
## ADR-10: Resilient Continuity

> **Status**: Updated (expanded, 2026-04-20)
> **Principle**: **#4 Resilient Continuity** ← v3 P9

### Context

Claude Code 세션은 auto-compact, 크래시, 수동 종료로 언제든 중단될 수 있다. 중단 후 컨텍스트 복원이 불가능하면 처음부터 다시 시작해야 한다.

### Decision

4개 Hook으로 세션 연속성을 보장한다.

| Hook | 트리거 | 역할 |
|------|--------|------|
| `jarfis-session-start.sh` | 세션 시작 | 미완료 워크플로우 감지 → stdout으로 컨텍스트 주입 |
| `jarfis-pre-compact.sh` | auto-compact 전 | state 백업 (최대 10개), meeting 백업 (최대 20개) |
| `jarfis-quality-gate.sh` | Edit/Write/MultiEdit 후 | 린트/타입체크 경고 (차단하지 않음) |
| `jarfis-safety.sh` | Bash 실행 전 | 위험 명령 차단 (force push, --no-verify, main 직접 커밋) |

**pre-compact.sh 백업 정책**:

```bash
# state 백업 — 최근 10개 유지
ls -t "$BACKUP_DIR"/state_*.json | tail -n +11 | xargs rm -f

# meeting 백업 — 최근 20개 유지
ls -t "$MEETING_BACKUP"/*_*.md | tail -n +21 | xargs rm -f
```

**session-start.sh 복원 흐름**:
1. `jarfis_cli.py state list-workflows` 실행
2. `status != "completed"` 워크플로우 필터링
3. work_name, current_phase, last_checkpoint, key_decisions 표시
4. `/jarfis:work` Resume Dispatch 안내

### Consequences

- **장점**: 세션 중단 후 자동 컨텍스트 복원, 백업으로 상태 복구 가능.
- **단점**: Hook 실행 시간이 세션 시작을 지연 (미미).
- **기각된 대안**: 수동 상태 복구 — 사용자 부담 과대.

### v4 Update (2026-04-20)

v4에서 방어 경계 지점이 확장되었다. 4 hooks는 그대로 유지하되, 아래 장치가 추가되었다:

- **Single-writer state rule** — 동시성 경합 자체를 구조적으로 배제 (ADR-18)
- **phase-results 격리** — tmux sub-agent 실행 결과가 `phase-results/phase{N}/attempt{K}.json`에 격리. main의 idempotence 판정 재료
- **`--save-pane` post-mortem 캡처 (v4.0.4)** — tmux 세션이 죽어도 scrollback이 보존되어 진단 가능
- **Triage Resume 분기** — Phase T에서 `project_name` flat key 감지 시 v3 state 안내 (ADR-18 + MIGRATION §3)

**원칙 진화**: v3은 "세션 죽음 방지" 중심, v4는 "세션이 죽어도 **어디서 왜 죽었는지 보존**" 까지 확장. Post-mortem capability가 원칙의 일부로 승격.

---

<a id="adr-11"></a>
## ADR-11: Cascading Specificity

> **Status**: Active (2026-04-20)
> **Principle**: **#5 Context as Investment (경제성)** ← v3에서는 명시 P-ref 없음, v4에서 #5 경제성으로 귀속

### Context

프로젝트 프로필, 위키, 산출물 등 여러 정보 소스가 있을 때 충돌이 발생할 수 있다. 어떤 정보를 우선할지 규칙이 필요했다.

### Decision

4단계 우선순위 체계를 적용한다.

```
정보 우선순위: $DOCS_DIR > project/.jarfis-project/ > .jarfis-org/wiki/ > INDEX.md
```

이번 태스크가 다루는 주제: `$DOCS_DIR` 우선. 안 다루는 주제: wiki 유효.

**전제조건** (v4): `state.org != null` 인 Org 등록 프로젝트에서만 동작. `{state.org.root}/.jarfis-org/wiki/INDEX.md` 존재 필요.

**로딩 모드**:

| 모드 | 사용처 | 로딩 범위 |
|------|--------|----------|
| 4-Step 전체 로딩 | Work/Extend | INDEX.md → 4개 section _index.md (PO, DESIGN, TA, QA) → semantic search (`jarfis_cli.py search wiki --top-k 5`, score ≥ 0.5) 기반 관련 파일 최대 5개 |
| 2-Step 경량 로딩 | Fix | INDEX.md → 관련 _index.md 최대 2개 (개별 파일 읽지 않음) |

**Fallback** (v4): semantic search 실패 시 (index 부재 / 메모리 부족 등) 사용자에게 경고 후 `_index.md` summary 기반 LLM 판단으로 파일 선정 (WIKI_SEARCH.md 참조).

**v4 구현 위치**: `~/.claude/commands/jarfis/prompts/wiki-loading.md` (공유 모듈, ADR-14의 프롬프트 외부화 규칙 적용)

### Consequences

- **장점**: 정보 충돌 시 명확한 해소 규칙, Fix 모드에서 토큰 절약.
- **단점**: 4-Step 로딩은 최대 10개 파일 읽기로 Phase 0 시간 증가.
- **기각된 대안**: 전체 위키 로딩 — 토큰 예산 초과. 위키 미참조 — 기존 결정 무시 위험.

---

<a id="adr-12"></a>
## ADR-12: Leaky Abstraction 검증

> **Status**: Active (2026-04-20)
> **Principle**: **#1 Deterministic Foundation** ← v3 P7

### Context

코어 모듈이 특정 프레임워크(React, Tauri 등)를 직접 참조하면 도메인 독립성이 깨진다. 도메인 팩 간 교차 참조도 격리를 위반한다.

### Decision

`test_architecture.py`로 경계 위반을 자동 검증한다.

**3개 테스트 클래스**:

1. **TestLeakyAbstraction** — 코어 모듈에 도메인 용어 누출 금지
   - DOMAIN_TERMS: 15개 (`react`, `vue`, `svelte`, `angular`, `nextjs`, `unity`, `godot`, `unreal`, `tauri`, `electron`, `django`, `flask`, `fastapi`, `csharp`, `c#`)
   - CORE_MODULES: 8개 (`state.py`, `measure.py`, `preflight.py`, `meetings.py`, `version.py`, `sync.py`, `validate.py`, `organization.py`) — `domain.py`는 브릿지이므로 제외

2. **TestCrossDomainReferences** — 도메인 팩 간 교차 참조 금지
   - `external_skills` 참조는 허용 (예: desktop이 `web/react` 참조)

3. **TestDomainYamlSchema** — 모든 domain.yaml이 필수 필드 보유
   - 필수: `schema_version`, `domain`, `roles`
   - `domain` 내 필수: `name`

### Consequences

- **장점**: CI에서 아키텍처 경계 위반을 자동 감지.
- **단점**: 새 프레임워크 추가 시 DOMAIN_TERMS 수동 갱신 필요.
- **기각된 대안**: 코드 리뷰만으로 검증 — 인간 실수 가능성.

---

<a id="adr-13"></a>
## ADR-13: Dialectic Review

> **Status**: Updated (scope clarified, 2026-04-20)
> **Principle**: **#2 Dialectic for Self-Modification** ← v3 P4 Dialectic Quality

### Context

JARFIS 시스템 자체의 변경(implement, upgrade, distill)에서 단일 관점 검토는 맹점을 만든다.

### Decision

Advocate(green) + Critic(red) 2인 토론 구조로 변경을 검증한다.

**토론 규칙**:
- 라운드당 최대 300단어 (간결성)
- 최대 2라운드
- Round 1: Advocate 분석 → Critic 반론
- Round 2 (미합의 시): Advocate 재반론 → Critic 재반론
- Round 2 후에도 미합의 → 사용자에게 양측 요약 + AskUserQuestion

**합의 판단**:
- ✅ 합의: 양측 동의
- ⚠️ 조건부 합의: 한쪽만 동의하지만 설득력 있는 근거
- ❌ 사용자 판단 필요: 양측 모두 양보 불가

**적용 범위**: `sys-implement.md`, `sys-upgrade.md`, `sys-distill.md` (JARFIS 자체 수정 시)

**게이트 진입 조건**:
- `--review=major` → 필수, `--review=patch` → 스킵
- 자동 판단: 파일 2개 이상 또는 구조 변경 → 토론 실행

### Consequences

- **장점**: 맹점 감소, 변경 품질 향상 (distill에서 30%+ 개선 보고).
- **단점**: 토론 2라운드 = 추가 에이전트 호출 2~4회 (토큰 비용).
- **기각된 대안**: 3인 이상 패널 — 토큰 비용 대비 한계 효용 감소. 토론 없음 — 단일 관점 맹점.

### v4 Update (2026-04-20) — Scope Clarification

v3의 P4 "Dialectic Quality"는 "모든 중요 결정에 생산적 비판자"로 오해될 여지가 있었다. v4에서 이를 **명확화**한다.

**사실 확인** (findings F-14):
- `prompts/phase*.md` 전체에 Dialectic 참조 **전무**
- Dialectic 실 적용 파일: `sys-implement.md`, `sys-upgrade.md`, `sys-distill.md`, `level-check.md`, `jarfis-index.md` 5개
- v4 PHILOSOPHY §#2: "시스템 자기수정(self-modification) 계열 명령"에 한정

**정확한 적용 범위 (v4.0.5 기준)**:
- **포함**: `sys-implement`, `sys-upgrade`, `sys-distill` — JARFIS가 JARFIS 자체의 프롬프트·에이전트·워크플로우·도메인 팩 구조를 변경하는 행위
- **제외**:
  - `sys-health` — 진단/운영 유틸
  - `sys-version` — 버전 번프
  - `level-check` — **AI-Native Developer Maturity 평가**. Advocate/Critic 참조는 있으나 JARFIS 자신을 변경하지 않고 개발자를 평가함. self-modification이 아니므로 의도적 제외
  - `jarfis-index` — 문서 index, Dialectic 관련 서술 메타 설명일 뿐 실행 주체 아님
  - Phase 2~5 일반 워크플로우, 사용자 프로젝트 코드 수정 — self-modification과 무관
- **확장 규칙**: 향후 추가되는 자기수정 계열 명령(예: 가상의 `sys-evolve`)은 정의에 부합하면 자동 포함

**일반 워크플로우의 품질 보장**:
- #1 Deterministic Foundation (verify.py, gate-check, phase-verify)
- TDD 계열 장치 (ADR-21 참조, 조건부 활성)

**의미**: 이는 축소가 아니라 **원칙의 해상도 상승** — "비판이 필요한 곳 vs 결정론이 가능한 곳"의 구분이 명확해졌다.

---

<a id="adr-14"></a>
## ADR-14: 프롬프트 외부화 & 증류

> **Status**: Active (2026-04-20)
> **Principle**: **#5 Context as Investment (경제성)** ← v3 P2 Token Austerity

### Context

work.md에 모든 에이전트 프롬프트가 인라인되면 파일이 비대해지고, 프롬프트 수정 시 워크플로우 로직까지 건드려야 한다.

### Decision

에이전트 프롬프트를 `prompts/` 디렉토리로 외부화하고, `templates/`로 산출물 템플릿을 분리한다.

**prompts/** (v4 기준):

| 파일 | 용도 |
|------|------|
| phase1b.md | Phase 1b Discovery Processing 프롬프트 (v4에서 분리) |
| phase2.md | Phase 2 Architecture 프롬프트 |
| phase3.md | Phase 3 Design (figma + text unified) 프롬프트 |
| phase4.md | Phase 4 Implementation 프롬프트 |
| phase4-5.md | Phase 4.5 Operational Readiness 프롬프트 |
| phase5.md | Phase 5 Review & QA 프롬프트 |
| phase6.md | Phase 6 Retrospective + Wiki Sync 프롬프트 |
| wiki-loading.md | Wiki 로딩 공통 모듈 (2-Step/4-Step, ADR-11 구현) |

**templates/** (10개):
`design-html-meta.md`, `jarfis-state-schema.md`, `learnings.md`, `meeting-artifacts.md`, `org-profile.md`, `project-context.md`, `project-profile.md`, `ux-direction.md`, `wiki-index.md`, `wiki-section-index.md`

**증류 프로세스** (sys-distill.md):
1. Measure — 현재 프롬프트 토큰 측정
2. 6가지 진단 — 중복/인라인/비효율 식별
3. 8가지 액션 — 외부화/압축/분리/병합 등
4. Dialectic Review — 증류 계획 검증 (ADR-13 적용, 30%+ 개선 목표)
5. 실행 — 프롬프트 수정
6. 재측정 — 효과 확인

### Consequences

- **장점**: work.md는 워크플로우 로직만, prompts/는 에이전트 지시만 담당. 현재 work.md 255줄 (v3 902줄 대비 ~1/4 축소 — findings F-12).
- **단점**: 참조 정합성 관리 필요 (work.md의 `📄 프롬프트:` 참조와 실제 파일).
- **기각된 대안**: 모든 프롬프트 인라인 — work.md 1000줄+ 비대화.

---

<a id="adr-15"></a>
## ADR-15: verify.py — Deterministic Gate

> **Status**: Accepted (2026-04-20)
> **Principle**: **#1 Deterministic Foundation**
> **Date introduced**: v4.0.0 (M7 swap, 2026-04-19)
> **Supersedes**: `jarfis-black` LLM gate (v3)

### Context

v3에서 Phase 검증은 `jarfis-black` 서브 에이전트가 수행했다. Claude 기반 LLM 판정이라:

- **비결정성**: 동일 산출물에 대해 run-to-run 판정 결과가 미세하게 달랐음
- **토큰 비용**: Phase당 ~1,400 토큰 ($0.008~0.04 규모, 워크플로우당 8~10회)
- **속도**: 2-5초 (네트워크 + inference)
- **디버깅 난이도**: 판정 실패 원인이 LLM prose에 묻혀 있음

v4에서는 "AI의 비결정성을 결정적 경계 안에 가두자"는 원칙을 극단까지 밀어붙이기 위해 LLM gate를 제거해야 했다.

### Decision

**`~/.claude/scripts/jarfis/verify.py`** (Python, 1,349줄) 로 `jarfis-black`을 완전 대체한다. verify.py는 4개 엔트리포인트를 단일 CLI로 통합한다:

| 엔트리 | 역할 |
|--------|------|
| `gate-check` | Gate 1/2/3 필수 산출물 존재 검증 |
| `phase-check` | Phase별 산출물 완전성 검증 (attempt별) |
| `phase-verify` | Phase 산출물 내용 수준 검증 (스키마, schema_version, 필수 필드) |
| `pattern-detect` | 회귀 패턴 감지 (review_round 루프에서 활용) |

**판정 원칙**:
- **존재 기반** — 파일 있나? 필드 있나? 값이 valid range 안인가?
- **품질 판단 금지** — "이 PRD는 좋은가?"는 AI 담당. "이 PRD에 `performance_budget` 필드가 있는가?"는 verify.py 담당
- **Machine-verifiable output** — exit code + JSON stdout, LLM prose 없음

### Consequences

**정량 효과 (v4.0.0 릴리스 기준)**:
- **비결정성**: 사라짐 (동일 입력 → 동일 출력)
- **실행 시간**: ~2-5초 → ~10ms (~300x 빠름)
- **토큰 비용**: ~1,400 → 0 (gate 호출당)
- **디버깅**: JSON 출력 + stack trace (vs LLM prose)

**외부 평가**:
> 세 AI 평가자(ChatGPT + Claude, 3라운드 교차 검증)가 v4의 가장 큰 변화로 공통 지목. 14축 rubric 축 12 Design Traceability(8.5) 상승 요인.

**단점**:
- 판정 규칙 변경 시 `verify.py` 코드 수정 필요 (vs LLM 프롬프트 수정)
- 새 산출물 스키마 추가 시 verify 로직도 추가 필요
- 품질 판단이 필요한 영역은 여전히 AI 담당 (Gate는 mechanical, Review는 AI)

**기각된 대안**:
- LLM gate 유지 + caching — 결정성 확보 못함
- 일부 판정만 Script화 — 경계가 모호해져 운영 비용 증가
- 전용 DSL (e.g., JSON Schema only) — 복잡 조건(schema + cross-file consistency) 표현 부족

### 관련 파일

- `~/.claude/scripts/jarfis/verify.py` (1,349줄)
- `~/.claude/commands/jarfis/prompts/phase*.md` — 각 phase prompt 끝에 Completion Protocol로 verify.py 호출 명시

---

<a id="adr-16"></a>
## ADR-16: tmux-per-phase Orchestration

> **Status**: Accepted (2026-04-20)
> **Principle**: **#4 Resilient Continuity** + **#1 Deterministic Foundation** (via B1 isolation)
> **Date introduced**: v4.0.0 (M7 swap)
> **Supersedes**: 단일 Claude 세션 내 Task tool 호출 (v3)

### Context

v3에서 Phase 실행은 메인 Claude 세션 내부의 Task tool 호출로 이루어졌다. 문제점:

- **컨텍스트 누적**: 모든 Phase 출력이 메인 세션에 누적 → auto-compact 위협
- **격리 부재**: Phase 간 상호 오염 (어느 Phase에서 만든 변수인지 불명)
- **병렬 불가**: 단일 세션이라 Phase 2와 3를 동시 실행 불가
- **복구 어려움**: 메인 세션이 죽으면 모든 Phase 결과 소실

v4에서는 Phase별로 **독립 프로세스(tmux 세션)** 를 띄워 격리·병렬·복구를 동시 달성해야 했다.

### Decision

**Phase별 dedicated tmux 세션** 에 `jarfis-foreman` executor agent를 띄워 실행한다.

**세션 네이밍**:
- `{sessionKey}-phase{N}` — 예: `jf-a1b2c3d4-phase3`
- `sessionKey` = `jf-` + UUID 앞 8자 (Phase 0에서 발급)

**실행 경계**:

| 실행 주체 | 담당 Phase |
|-----------|-----------|
| Main session (direct) | T, 0, 1a, Gate 1/2/3 |
| tmux + foreman | 1b, 2, 3, 4, 4.5, 5, 6 |

**B1 Isolation 규칙** (`tmux_claude.py::kill_existing_session`):

```python
# 세션 kill은 exact name match만 허용
# prefix 기반 대량 kill 금지 — Phase 2 ∥ 3 병렬 실행 시 서로 죽이는 버그 방지
if session_alive(name):   # name 정확 일치 시에만
    kill_session(name)
```

**Phase 2 ∥ 3 병렬**:
- Architecture (Phase 2) 와 UX Design (Phase 3) 는 독립 tmux 세션으로 **동시 실행**
- Phase 3는 `state.design.mode != null` 시에만 실행 (조건부)
- B1 isolation으로 세션 간 간섭 원천 차단

**tmux_claude.py 설계 원칙**:
- **"JARFIS를 모르는" 범용 유틸리티** — tmux 세션 생성 → 폴링 → kill만 담당
- Phase 의미는 모른다. 프롬프트 파일 경로 + 결과 JSON 경로만 받음
- 크래시/타임아웃 시 pane 캡처하여 result JSON 대신 작성

**결과 통신**:
- tmux sub-agent → `{docsDir}/phase-results/phase{N}/attempt{K}.json` 작성
- Main session 이를 읽고 `.jarfis-state.json`에 반영 (단방향, ADR-18 참조)

### Consequences

**정량 효과**:
- **메인 컨텍스트**: v3 ~100,000 tokens → v4 ~11,000 tokens (~89% 감소)
- **병렬성**: Phase 2 + Phase 3 동시 실행 (wall-clock 시간 감소)
- **복구**: 세션 죽어도 `attempt{K}.json` 보존 → 다음 시도에 재활용

**운영 비용 (findings F-10)**:
- **좀비 세션 가능성** — `/jarfis:sys-health` 명령으로 진단 필요
- **디버깅 복잡도** — 어느 tmux에서 무슨 일이 일어났는지 추적하는 비용
- **Post-mortem 지원**: `tmux_claude.py --save-pane` (v4.0.4)로 scrollback 보존

**단점**:
- 1인 dogfooding pool의 제한된 운영 경험 (아직 정착 중)
- tmux 의존성 (tmux 없는 환경에서 작동 불가)
- 세션별 Claude 초기화 비용 (5-10초)

**기각된 대안**:
- worker thread — Python GIL + Claude CLI 프로세스 모델과 부정합
- subprocess만 (tmux 없이) — scrollback/pane 캡처 기능 부재로 post-mortem 어려움
- Docker 컨테이너 per-phase — 설치 장벽 + 리소스 오버헤드 과다

### 관련 파일

- `~/.claude/scripts/jarfis/tmux_claude.py` (세션 수명 관리)
- `~/.claude/agents/jarfis/jarfis-foreman.md` (tmux 내부 executor)
- `~/.claude/commands/jarfis/sys-health.md` (좀비 세션 진단)

---

<a id="adr-17"></a>
## ADR-17: agent-composition.yaml — Deterministic Composition

> **Status**: Accepted (2026-04-20)
> **Principle**: **#1 Deterministic Foundation** + **#5 Context as Investment (Composition aspect)**
> **Date introduced**: v4.0.0
> **Relates to**: ADR-1 (v3 compose() 함수 확장)

### Context

v3의 `compose()` 함수는 persona + skill + rule 3계층을 합성했으나, **합성 규칙 일부가 LLM inference에 의존**했다. 예:
- "이 role에 어떤 skill이 필요한가?" — domain.yaml의 명시 규칙 + LLM 유추
- Context 파일 중 어떤 섹션을 role에 주입할지 — 암묵적 판단

이는 #1 Deterministic Foundation 관점에서 불완전한 영역이었다.

### Decision

**`~/.claude/commands/jarfis/agent-composition.yaml`** 을 단일 진실 원천(Single Source of Truth)으로 삼는 **선언적 합성 규칙** 을 도입한다.

**구성 요소**:
- **Persona inventory** — 역할별 인지 프레임 고정 리스트
- **Skill assignment** — role → skill set 결정적 매핑
- **Context injection matrix** — 파일별 · 역할별 주입 섹션 명시
- **Audit header** (v4.0.4) — 합성 결과에 어떤 규칙이 적용되었는지 메타데이터 기록

**실행 경로**:
- `compose` CLI (`~/.claude/scripts/jarfis/compose/__main__.py`) → YAML 규칙 로드 → 결정적 조립
- tmux 내부의 `jarfis-foreman`이 phase prompt 시작 시 compose CLI 호출

**LLM 개입 제거**:
- 모든 합성 분기는 YAML에 미리 선언
- "추론"이 필요한 곳은 없음 — 없으면 규칙 추가 (decision surface에 노출)

### Consequences

**장점**:
- **결정성**: 동일 input → 동일 합성 결과 (verify 가능)
- **추적성**: audit header로 "이 prompt가 왜 이렇게 조립되었는가?" 역추적 가능
- **확장성**: 새 persona/skill 추가 시 YAML 업데이트만. 코드 수정 불필요

**단점**:
- YAML 규칙 작성 초기 비용 (v3 inference 기반은 "알아서 잘 동작")
- 규칙 누락 시 합성 실패 (vs v3: LLM이 대충 조립)
- YAML 규모 증가 (새 domain/role 추가마다 regulation 추가)

**기각된 대안**:
- LLM inference 유지 — #1 위반
- 코드(Python)로 하드코딩 — 확장성 부족, 도메인 팩 분리 원칙 위반
- 다중 설정 파일 (domain.yaml + compose.yaml + ...) — 검색 비용 증가, SSOT 위반

### 관련 파일

- `~/.claude/commands/jarfis/agent-composition.yaml`
- `~/.claude/scripts/jarfis/compose/__main__.py`
- `~/.claude/scripts/jarfis/domain.py` (v3 compose() 함수, 내부적으로 compose CLI의 로직 호출)

---

<a id="adr-18"></a>
## ADR-18: Single-writer State Rule

> **Status**: Accepted (2026-04-20)
> **Principle**: **#4 Resilient Continuity** + **#1 Deterministic Foundation**
> **Date introduced**: v4.0.0
> **Source**: findings F-06 + `work.md:22` (State write rule 정식 선언) + `architecture.md §1 설계 원칙` 6번째 bullet "쓰기 주체 분리"
> **Relates to**: ADR-3 (v3 하이브리드 상태 관리 update), ADR-16 (tmux-per-phase)

### Context

v4에서 Phase 실행이 **여러 tmux 세션 병렬**로 나뉘면서 (ADR-16), 상태 파일(`.jarfis-state.json`)에 대한 동시 쓰기 경합 위험이 발생했다.

선행 유사 시스템에서의 실패 패턴:
- 여러 writer가 동일 JSON을 쓰면 lost update / partial write
- Lock 기반 해결은 deadlock / 성능 저하 / debugger 복잡도
- 트랜잭션 DB 도입은 solo dev CLI 환경에 과잉

JARFIS는 동시성을 **락 없이 구조적으로 해소**할 필요가 있었다.

### Decision

**단일 writer 원칙** 을 파일 경로 단위로 강제한다.

**쓰기 권한 분리**:

| 파일 경로 | Writer | Reader |
|-----------|--------|--------|
| `.jarfis-state.json` | **Main session only** | Main + tmux (read-only) |
| `phase-results/phase{N}/attempt{K}.json` | **tmux sub-agent only** (또는 tmux_claude.py의 lifecycle 폴백) | Main |
| `discovery/`, `planning/`, `design/`, `review/`, `ops/`, `retrospective.md` | **해당 Phase 실행 주체만** (direct=Main, tmux=Sub) | 모두 |

**쓰기 경로 분리의 물리적 의미**:
- Main은 자기 파일만 씀 — state.json
- Sub는 자기 파일만 씀 — phase-results, phase 출력 디렉토리
- **경쟁 조건이 파일 경로 수준에서 원천 불가능**

**통신 방향**:
```
tmux sub (writes phase-results)
    → main (reads phase-results)
    → main (writes state.json, reflecting selected fields)
```

**Main의 반영 규칙**:
- phase-results의 모든 필드를 state에 복사하지 않음
- 분기 결정에 필요한 필드만 선별 반영
- 나머지는 phase-results에 원본 보존 (디버깅 용)

### Consequences

**장점**:
- **Lock 없이 동시성 안전** — 경합이 발생할 수 없음 (상수 시간 증명)
- **디버깅 용이** — 어느 프로세스가 무슨 파일을 썼는지 명확
- **테스트 용이** — 각 writer의 출력을 독립 검증 가능

**단점**:
- Main이 반영할 필드를 선별하는 로직이 필요 (vs 단순 복사)
- Sub가 state의 읽기 전용 뷰를 갖는다 — 실행 중 변경된 state를 보려면 재시작 필요
- 디렉토리 경계 위반 시 탐지 비용 — 현재 Grep/테스트로만 검증 (자동화 여지)

**기각된 대안**:
- 파일 락 (fcntl) — 디버깅 복잡도 + 실패 시 좀비 락
- 트랜잭션 DB — 과잉
- 공유 메모리 (mmap) — tmux 프로세스 격리 이점 훼손
- "알아서 조심" 규약 — 구조적 보장 부재 → 회귀 가능

### 관련 파일

- `~/.claude/commands/jarfis/work.md:22` (State write rule 정식 선언)
- `~/Upscales/jarfis-v4-migration/architecture.md §1 설계 원칙` ("쓰기 주체 분리" bullet — 원 설계 동기)
- `~/.claude/scripts/jarfis/state.py` (main writer)
- `~/.claude/scripts/jarfis/tmux_claude.py` (sub writer lifecycle 폴백)

---

<a id="adr-19"></a>
## ADR-19: Phase 4.5 Operational Readiness

> **Status**: Accepted (2026-04-20)
> **Principle**: **#6 Gated Autonomy** + **#4 Resilient Continuity** (DevOps as first-class)
> **Date introduced**: v4.0.0
> **Source**: findings F-05
> **Supersedes**: ADR-6 (Phase 4만 전환)

### Context

v3에서는 Phase 4 (Implementation) → Phase 5 (Review) 로 직접 전이했다. DevOps는 Phase 4 내부 role 중 하나였고, 운영 준비(runbook, deployment plan, infra doc)는 **암묵적 산출물**이었다.

이로 인한 문제:
- Implementation 완료 후 배포 가능 여부가 불명 (누가 언제 "배포 준비 완료" 선언?)
- Review 단계에서 운영 이슈가 늦게 발견됨 (인프라 수정은 re-implementation 필요)
- 외부 평가 축 3 (Workflow/State Machine)에서 "DevOps 위치 불명확" 지적

v4에서는 DevOps를 **별도 Phase로 승격**하여 운영 준비를 first-class 단계로 만들어야 했다.

### Decision

**Phase 4.5 (Operational Readiness)** 을 Phase 4와 Phase 5 사이에 삽입한다.

**Phase flow (v4)**:
```
T → 0 → 1a → 1b → G1 → 2 ∥ 3 → G2 → 4 → 4.5 → 5 → G3 → 6
                                       ^^^^^
                                       신규
```

**Phase 4.5의 책임**:
- DevOps 관점 운영 준비 산출물 생성
- `ops/infra-runbook.md` — 운영 절차
- `ops/deployment-plan.md` — 배포 계획
- DevOps가 일시적 first-class owner (Phase 4의 한 role이 아닌, Phase 주체)

**Phase ID 표기 규칙** (technical detail):
- Phase 4.5는 파일/경로/식별자에서 `4-5` (하이픈) 사용
- 이유: `.`은 파일 경로/URL에서 확장자·도메인 구분자와 충돌
- `prompts/phase4-5.md`, `phase-results/phase4-5/attempt1.json`
- State 내부 key는 `"4-5"` (문자열)

**실행 주체**:
- tmux + jarfis-foreman (다른 non-direct phase와 동일)
- DevOps persona 중심 합성 (agent-composition.yaml)

### Consequences

**장점**:
- **Explicit DevOps checkpoint** — 배포 준비 완료 여부를 기계적으로 확인 가능
- **Review 전 보정 기회** — 운영 이슈를 Phase 5 전에 발견
- **14축 rubric 축 3 상승** — Workflow/State Machine 명확도 증가

**단점**:
- Phase 개수 증가 (구 9 → 실질 13 steps)
- 작은 작업(solo dev web feature)에서 overhead 가능 — scope 판단 필요
- `4-5` 표기의 혼동 가능성 (하이픈 vs 점) — 문서에 명시 필요

**기각된 대안**:
- Phase 5 내부로 DevOps 병합 — 기존 Review가 과부하
- Phase 4 하위 단계 (4a/4b) — 병렬 실행 이득 없음, 오히려 Phase 경계 모호
- 옵션 Phase (scope 판단에 따라 skip) — M-test 신뢰성 저하 위험 (추후 v4.1 고려)

### 관련 파일

- `~/.claude/commands/jarfis/prompts/phase4-5.md`
- `~/.claude/commands/jarfis/work.md` (flow 정의)

---

<a id="adr-20"></a>
## ADR-20: JARFIS_TRACE Opt-in Observability

> **Status**: Accepted (2026-04-20)
> **Principle**: **#5 Context as Investment (경제성)** — opt-in default off
> **Date introduced**: v4.0.5 (sub-batch 5a/5b/5c)
> **Source**: `~/Upscales/jarfis-v4-migration/adr/v4.0.5-trace-design.md` (분산 ADR 원문, 부록 C 참조)

### Context

v4 tmux-per-phase 아키텍처(ADR-16)에서 Phase 경계를 넘는 구조화 관측 데이터가 부재했다.

사용 가능했던 신호:
- `tmux capture-pane` (text-only, agent prose + tool 호출 혼합, 세션 kill 시 소실)
- `--save-pane` (v4.0.4, scrollback 보존 — 진전이지만 비구조화)

미래 Monitor App (v4.2+) 은 **구조화된 span 데이터** 를 소비할 예정. 관측 계층을 **지금 만들되 안전하게(off-by-default)** 만들어야 했다.

### Decision

`trace.py`를 **opt-in subsystem**으로 활성화. 환경변수 `JARFIS_TRACE`로 제어.

**Gate 함수**:
```python
def is_enabled() -> bool:
    return os.getenv("JARFIS_TRACE", "0") != "0"
```

**5 핵심 원칙**:
1. **Gate function** — `trace.is_enabled()` / 기본값 off
2. **Failure isolation** — 모든 I/O/JSON 경로에 `try/except Exception: pass`. 추적 실패가 Phase 결과에 영향 금지
3. **On-path instrumentation (5b)** — 3개 hot path (`tmux_claude.py`, `verify.py::cmd_phase_verify`, `compose/__main__.py`) 에 gated trace 호출
4. **Output format** — JSONL at caller-supplied path. 기본 경로 관례: `{docsDir}/trace/phase{N}.jsonl`
5. **Kill switch** — `export JARFIS_TRACE=0` or `unset` → 다음 프로세스 경계에서 적용. 코드 revert 불필요

**API 표면**:
- `trace_agent(path, trace_id, phase, persona, skills)` — context manager
- `trace_phase(path, trace_id, phase, duration_ms)` — phase 완료 이벤트

### Consequences

**정량 효과 (v4.0.5 측정)**:
- **`JARFIS_TRACE` unset** — overhead ~0.008% (baseline ±20% 안) 실측
- **`JARFIS_TRACE=1`** — overhead < 20% (postflight 테스트 enforced)
- **Zero overhead path** — gate는 `os.getenv` 호출 1회

**장점**:
- Monitor App 구현 전에 데이터 수집 파이프라인 확보
- Opt-in이라 user 영향 없음 — default 행동 무변경
- Reversibility — sub-batch 단위로 revert 가능 (5a/5b/5c)

**단점**:
- Hot-path instrumentation 3개소 (각 3-5줄) — 유지보수 표면 증가
- JSONL unbounded growth — 수동 cleanup 필요 (v4.0.6+ audit cmd 후보)
- 테스트 표면 2배 (off path + on path per function)

**기각된 대안**:
- Default on — overhead 미측정 상태에서 모든 사용자에게 영향
- Out-of-process trace daemon — tmux 격리에 추가 프로세스 관리 복잡도
- Keep trace.py dead — drift 위험 (Monitor App 도착 시 surface 불일치)
- 새 API (`start_span`/`log_event`/`flush`) — 기존 context manager로 충분

### 관련 파일

- `~/.claude/scripts/jarfis/trace.py` (158줄)
- `~/Upscales/jarfis-v4-migration/adr/v4.0.5-trace-design.md` (분산 ADR 원문)

---

<a id="adr-21"></a>
## ADR-21: Ratchet Reality

> **Status**: Accepted (2026-04-20) — Honesty clause
> **Principle**: **P0 Function over Form** (죽은 장치는 해롭다)
> **Source**: findings F-09, CHANGELOG v4.0.1
> **Supersedes**: ADR-4 (3종 래칫 수렴)

### Context

v3에서 "3종 래칫 (PRD / TDD / Fix)" 은 JARFIS의 대표 간판 기능으로 소개되었다. 외부 평가자와 독자도 이를 JARFIS의 차별점으로 인식했다.

그러나 v4 실체는 달랐다 (findings F-09):

- **PRD Ratchet**: v4.0.1에서 **전면 제거** — producer(채점 주체) 부재로 "죽은 장치"화. 현재 `work-legacy.md:301` (v3 archive)에만 존재
- **Fix Ratchet**: `jarfis-state-schema.md:204`에 "**legacy**" 명시. Continue/Extend 모드가 v4에서 재설계되면서 용도 상실
- **TDD Ratchet**: 살아있음. 단 `phase4.md:273` "CONDITIONAL on `$TDD_ENABLED == 'true'`" — default 비활성

**문제**:
- README / 외부 자료의 "3종 래칫" 표현이 **사실과 괴리** → 허위 주장 수준
- 죽은 원칙 유지는 Design Traceability(14축 rubric 축 12)를 훼손 — JARFIS의 유일한 clear lead 축

v4 철학은 P0 Function over Form("이름뿐인 허울은 해롭다")을 채택했으므로, 이 괴리를 **honesty clause**로 문서화해야 했다.

### Decision

**"Ratchet 현실" 을 공식 ADR로 기록**한다. 외부 자료의 "3종 래칫" 표현을 정정하고, v4 현 상태를 정직하게 선언.

**v4.0.5 Ratchet 상태**:

| Ratchet | 상태 | Activation | 위치 |
|---------|------|-----------|------|
| PRD Ratchet | **제거** (v4.0.1) | — | `work-legacy.md:301` (v3 archive only) |
| TDD Ratchet | **조건부 활성** | `$TDD_ENABLED == 'true'` | `prompts/phase4.md:273` |
| Fix Ratchet | **legacy** | 정지 | `jarfis-state-schema.md:204` (legacy 주석) |

**공식 표현 규칙** (tone guide, foundation §5):
- ❌ "3종 Ratchet" — 금지
- ✅ "v4 기준 TDD Ratchet (조건부 활성), PRD/Fix는 legacy"
- ✅ "래칫 수렴은 v3의 핵심 개념이었으며 v4에서는 TDD 영역에 한정 적용"

**왜 제거하지 않고 ADR화하는가**:
- 완전 제거는 Design Traceability 끊김 (과거 외부 자료가 지시하는 맥락이 없어짐)
- ADR-21은 "3종 Ratchet" 검색 진입점 역할 — 독자가 현 상태를 즉시 확인 가능
- `work-legacy.md`의 v3 참조도 2026-05-03 만료 (MIGRATION §4 / work-legacy banner) 로 자연 정리

### Consequences

**장점**:
- **Honesty** — 외부 평가자의 "3종 Ratchet 실체 부재" 지적에 정면 대응
- **Design Traceability 복원** — v3 Ratchet 언급의 현 상태 추적 가능
- **Future-proof** — 향후 Ratchet을 다시 확장할 경우 (PRD v2 등) 본 ADR이 기저 reference

**단점**:
- 외부에 "3종 Ratchet이 간판이 아님" 을 알려야 함 (마케팅 비용)
- P0 채택의 첫 수혜(?) — 다른 "죽은 장치" 도 발굴 시 추가 honesty ADR 필요 가능

**기각된 대안**:
- **조용히 제거** — 외부 자료 drift 유지, 정직성 훼손
- **3종 모두 복원** — producer 부재 문제 재발
- **원칙 수준에서 Ratchet 금지** — TDD는 살아있는 가치 ROI 존재, 과잉 정제

### 향후 정책

- Ratchet 계열 장치 추가 제안 시 **producer 명시** 필수 (누가 언제 채점하는가)
- `sys-*` 주기 audit에서 active use 증거를 점검. 장기간 미사용 시 ADR-21 방식(honesty clause)으로 현 상태 선언 검토 — 자동 편입 규칙 강제는 없음, 판단은 사용자
- `work-legacy.md` 2026-05-03 만료 시 PRD Ratchet reference 완전 정리 (v4.0.9+ cleanup item)

### 관련 파일

- `~/.claude/commands/jarfis/prompts/phase4.md:273` (TDD Ratchet)
- `~/.claude/commands/jarfis/work-legacy.md:301` (PRD Ratchet 역사)
- `~/.claude/commands/jarfis/templates/jarfis-state-schema.md:204` (Fix Ratchet legacy)

---

<a id="transition-map"></a>
## 부록 A: v2.5 → v3 → v4 전환 맵

### v2.5.x — 래칫 기반 구축 (v3 기초)

| 버전 | 내용 | 관련 ADR |
|------|------|----------|
| v2.5.4 | PRD Ratchet 도입 (5항목 채점 + 단조증가) | ADR-4 (현 Superseded) |
| v2.5.5 | Workflow Metrics Recording (AutoResearch results.tsv 패턴) | ADR-8 |
| v2.5.6 | TDD Ratchet (pass_rate baseline + git stash 원복) | ADR-4 → ADR-21 |
| v2.5.7 | Fix Ratchet (Continue 모드 1회 재시도) | ADR-4 → ADR-21 |

### v3.0.0 — Domain Pack 수립

- 120회 래칫 수렴을 통한 시스템 안정화
- 11개 병렬 에이전트 분석 기반 Domain Pack 설계
- `_schema.yaml` Published Language 확립 (ADR-2)
- `compose()` 함수 기반 Agent 합성 (ADR-1)
- 4개 Hook 기반 Resilient Continuity (ADR-10)
- `test_architecture.py` 경계 검증 자동화 (ADR-12)

### v4.0.0 (2026-04-19) — Deterministic 극단화 + tmux 오케스트레이션

- **Primary executor 전환**: `jarfis-white` → `jarfis-foreman` (tmux-scoped: compose invocation + sub-agent spawn + artifact merge)
- **Gate 전환**: LLM `jarfis-black` 제거 → `verify.py` Python deterministic gate로 대체 (ADR-15)
- **Top-level agent 체계 확립**: `jarfis-foreman`(실행) + `jarfis-engineer`(도메인 전문) + `jarfis-advocate`/`jarfis-critic`(Dialectic pair) 4인. advocate/critic/engineer는 v3부터 존재했으나 v4에서 top-level agent로 정리
- **Execution model**: 단일 Claude 세션 Task → Phase별 tmux 세션 (ADR-16)
- **Composition**: `domain.py::compose() + inference` → `agent-composition.yaml + compose CLI` (ADR-17)
- **State schema**: project/work 중심 → `scope[] + org{} + baseCommit` (architecture §4)
- **Skills 구조**: `domains/{web,desktop}/skills/` → `commands/jarfis/skills/` 평탄화
- **State rule**: Single-writer (ADR-18)
- **Phase**: 4.5 신설 (ADR-19), 1a/1b 분리, 2 ∥ 3 병렬

### v4.0.1 (2026-04-20)

- **PRD Ratchet 전면 제거** (producer 부재 → 죽은 코드) → ADR-21
- M8 E2E round 1/2/3 핫픽스 (Task tool `working_dir` workaround)

### v4.0.2 — 4 (2026-04-20)

- v4.0.2: OBS 6건 핫픽스 (observability)
- v4.0.3: UX/N item
- v4.0.4: `tmux_claude --save-pane` post-mortem (ADR-10 update) + `agent-composition.yaml` audit header (ADR-17)

### v4.0.5 (2026-04-20)

- **Trace subsystem opt-in** — `JARFIS_TRACE` env gate, `trace.log_event` API, hot-path instrumentation (ADR-20)
- Default off (기존 동작 무변경)

---

<a id="principle-map"></a>
## 부록 B: 원칙 참조 매핑 (v3 P{N} → v4 #{N})

| v3 Principle | v4 Principle | 변경 유형 |
|--------------|--------------|-----------|
| P0 Principle Zero (Aspiration over Implementation) | P0 Function over Form | 재정의 (ROI 프레임 추가) |
| P1 Orchestration for All | — (삭제) | 46일 활동 증거 부재. 정신은 #6에 흡수 |
| P2 Token Austerity | #5 Context as Investment (경제성) | 재정의 (최소 → 비용 대비 가치) |
| P3 Self-Evolution | #3 Dogfooding Evolution | rename + amortization 명시 |
| P4 Dialectic Quality | #2 Dialectic for Self-Modification | 범위 명시 (sys-* 전용) |
| P5 AI-Native Artifacts | #5 Context as Investment (산출물 포맷) | 통합 |
| P6 Abstraction over Memorization | #5 Context as Investment (Composition) | 통합 |
| P7 Deterministic Foundation | #1 Deterministic Foundation | 유지 + 강화 (verify.py, single-writer) |
| P8 Human Gate, AI Execute | #6 Gated Autonomy | rename + 게이트 기준 3가지 |
| P9 Resilient Continuity | #4 Resilient Continuity | 유지 + 확장 (hooks, phase-results, --save-pane) |

상세 rationale은 [MIGRATION.md#principle-changes](./MIGRATION.md#principle-changes) 참조.

### ADR별 P-ref 변경 요약

| ADR | v3 P-ref | v4 P-ref |
|-----|----------|----------|
| ADR-1 | P6 | #5 Composition (+ #1 via ADR-17) |
| ADR-2 | P7 | #1 |
| ADR-3 | P9 | #4 (+ ADR-18, ADR-20 revised parts) |
| ADR-4 | P4 | Superseded by ADR-21 (#2는 sys-* 전용이라 Ratchet과 분리) |
| ADR-5 | P1 | P0 + #6 합리적 default (P1 삭제로 rebrand) |
| ADR-6 | — | Superseded by ADR-19 |
| ADR-7 | P6 | #5 Composition + 경제성 |
| ADR-8 | P2, P7 | #5 경제성 + #1 (strengthened) |
| ADR-9 | P8 | #6 Gated Autonomy |
| ADR-10 | P9 | #4 |
| ADR-11 | (명시 없음) | #5 경제성 |
| ADR-12 | P7 | #1 |
| ADR-13 | P4 | #2 (sys-* scope clarified) |
| ADR-14 | P2 | #5 경제성 |
| ADR-15 (신규) | — | #1 |
| ADR-16 (신규) | — | #4 + #1 (B1 isolation) |
| ADR-17 (신규) | — | #1 + #5 Composition |
| ADR-18 (신규) | — | #4 + #1 |
| ADR-19 (신규) | — | #6 + #4 |
| ADR-20 (신규) | — | #5 경제성 (opt-in) |
| ADR-21 (신규) | — | P0 Function over Form |

---

<a id="distributed-adr"></a>
## 부록 C: 분산 ADR 링크

v4 릴리스별 분산 ADR 문서는 `~/Upscales/jarfis-v4-migration/adr/` 에 보존된다. DESIGN.md는 이를 **요약 + 링크** 하고, 세부 rationale은 원문을 참조한다.

| ADR 원문 | 요약 위치 | 비고 |
|---------|----------|------|
| `v4.0.5-trace-design.md` | [ADR-20](#adr-20) | Trace subsystem activation (sub-batch 5a/b/c) 상세 |

향후 v4.0.6+ 릴리스에서 새 분산 ADR이 등장하면 본 부록에 행 추가 + 해당 내용을 DESIGN.md 본문에 `ADR-{N+1}` 로 흡수.

---

## 문서 관리

- **ADR 번호는 재사용 금지** — Superseded 시에도 번호 유지 (history 추적 가치)
- **신규 ADR은 번호 증가 순** — 현 최대 ADR-21, 다음은 ADR-22
- **P-ref 변경**은 PHILOSOPHY.md v{X} 업데이트와 동반 (MIGRATION §Principle Changes에 근거 기록)
- **Supersede 관계**는 양방향 기록 — 원문 배너 + 신규 ADR Supersedes 절

---

*이 문서는 JARFIS v4.0.5 시점의 아키텍처 결정을 v2.5→v3→v4 연속선상에서 기록한다. 각 ADR은 실제 코드와의 정합성이 findings.md (F-01~F-14) 를 통해 검증되었다.*
