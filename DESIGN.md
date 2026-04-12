# JARFIS Design Document

> JARFIS v3.0 아키텍처 결정 기록 (Architecture Decision Records)
>
> 각 ADR은 Context → Decision → Consequences 형식을 따른다.
> PHILOSOPHY.md 원칙을 `P{N}`으로 인용한다.

---

## 목차

1. [ADR-1: Agent 합성 (모놀리식 → Persona+Skill+Rule)](#adr-1)
2. [ADR-2: Domain Pack Published Language](#adr-2)
3. [ADR-3: 하이브리드 상태 관리](#adr-3)
4. [ADR-4: 래칫 수렴](#adr-4)
5. [ADR-5: 기존 에이전트 유지 (Fallback)](#adr-5)
6. [ADR-6: Phase 4만 전환](#adr-6)
7. [ADR-7: Skill 설계 원칙](#adr-7)
8. [ADR-8: Script vs Prompt 경계](#adr-8)
9. [ADR-9: Human Gate 배치](#adr-9)
10. [ADR-10: Resilient Continuity](#adr-10)
11. [ADR-11: Cascading Specificity](#adr-11)
12. [ADR-12: Leaky Abstraction 검증](#adr-12)
13. [ADR-13: Dialectic Review](#adr-13)
14. [ADR-14: 프롬프트 외부화 & 증류](#adr-14)
15. [부록: v2.5→v3.0 전환 맵](#transition-map)

---

<a id="adr-1"></a>
## ADR-1: Agent 합성 (모놀리식 → Persona+Skill+Rule)

### Context

v2.5까지 에이전트는 모놀리식 프롬프트였다. 역할(persona), 기술 지식(skill), 프로젝트 규칙(rule)이 하나의 프롬프트에 혼재되어 도메인 확장 시 전체 프롬프트를 복제해야 했다.

### Decision

`compose()` 함수로 3개 레이어를 런타임에 합성한다 (P6 적용 — Abstraction over Memorization).

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

**Fallback**: 도메인 설정 로드 실패 시 `_FALLBACK_PERSONAS` 매핑으로 persona-only 실행.

```python
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

- **장점**: 도메인 추가 시 YAML+Skill 파일만 작성. 코어 코드 수정 불필요.
- **단점**: 합성 과정에서 토큰 추정 오차 (ASCII ±20%, 혼합 ±30%).
- **기각된 대안**: 에이전트별 전용 프롬프트 파일 — 도메인 N개 x 역할 M개 = N*M개 파일 관리 비용.

---

<a id="adr-2"></a>
## ADR-2: Domain Pack Published Language

### Context

도메인별 에이전트 구성, 감지 규칙, 품질 게이트 등을 표현할 공통 스키마가 필요했다. 각 도메인 팩이 제각기 다른 구조를 사용하면 코어 코드가 도메인별 분기로 오염된다.

### Decision

`_schema.yaml`에 7개 Extension Point(EP1~EP7)를 정의하고, 모든 도메인 팩이 이 스키마를 따르도록 한다 (P7 적용 — Deterministic Foundation).

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
- **기각된 대안**: JSON Schema — YAML의 주석/가독성 이점이 AI-Native 환경에서 더 유리 (P5).

---

<a id="adr-3"></a>
## ADR-3: 하이브리드 상태 관리

### Context

워크플로우 상태를 단일 파일로 관리하면 디버깅이 어렵고, 이벤트 기반으로만 관리하면 현재 상태 조회에 전체 리플레이가 필요하다.

### Decision

3개 파일로 관심사를 분리한다 (P9 적용 — Resilient Continuity).

| 파일 | 형식 | 용도 | 실패 시 |
|------|------|------|---------|
| `.jarfis-state.json` | JSON | 현재 상태 CRUD (Phase, Gate, Ratchet 결과) | 워크플로우 중단 |
| `audit.jsonl` | JSONL (append-only) | 이벤트 로그 (14개 타입) | 무시 (P9) |
| `traces.jsonl` | JSONL (append-only) | 성능 메트릭 (토큰, 소요시간) | 무시 (P9) |

**audit.jsonl 이벤트 타입** (14개):

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
    """Best-effort audit logging. Failures are silently ignored (P9)."""
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

---

<a id="adr-4"></a>
## ADR-4: 래칫 수렴

### Context

AI 에이전트가 수정할 때 이전에 통과한 항목을 퇴행시키는 문제가 발생했다. 품질이 단조증가하도록 보장하는 메커니즘이 필요했다.

### Decision

3종 래칫을 도입한다. 래칫은 "한번 통과한 기준은 다시 내려가지 않는다"는 원칙이다 (P4 적용 — Dialectic Quality).

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

### Consequences

- **장점**: 품질 단조증가 보장, 무한 루프 방지 (회수 제한).
- **단점**: 래칫 위반 감지는 오케스트레이터(AI)의 판단에 의존.
- **기각된 대안**: 무제한 재시도 — 토큰 낭비 + 무한 루프 위험 (P2 위반).

---

<a id="adr-5"></a>
## ADR-5: 기존 에이전트 유지 (Fallback)

### Context

v3.0에서 Domain Pack 시스템을 도입하지만, 도메인 미설정 프로젝트도 지원해야 한다.

### Decision

`$DOMAIN`이 null일 때 v2.5 하드코딩 에이전트 매핑으로 fallback한다 (work.md:578-582).

```
$DOMAIN이 null인 경우 (기존 방식 — fallback):
- 아래 하드코딩 에이전트 매핑으로 실행

Backend (senior-backend-engineer),
Frontend (senior-frontend-engineer),
DevOps (senior-devops-sre-engineer)
```

### Consequences

- **장점**: v2.5 프로젝트와 100% 하위 호환.
- **단점**: fallback 경로의 유지보수 비용 (두 가지 실행 경로 공존).
- **기각된 대안**: 강제 마이그레이션 — 기존 사용자 경험 파괴 (P1 위반).

---

<a id="adr-6"></a>
## ADR-6: Phase 4만 전환

### Context

Domain Pack 시스템이 전 Phase에 영향을 미치면 변경 범위가 너무 크다. v3.0 최소 전환 범위를 결정해야 했다.

### Decision

Phase 0에서 도메인을 감지하고, Phase 4(구현)에서만 `if $DOMAIN` 분기를 적용한다(work.md:566-582).

```
$DOMAIN이 null이 아닌 경우 (domain.yaml 기반):
1. jarfis_cli.py domain agents "$DOMAIN" implement → 역할 목록 JSON 로드
2. hooks.phase4.before 실행 (있으면)
3. 각 역할에 대해 domain compose 호출 → Agent 도구 호출
4. hooks.phase4.after 실행 (있으면)
5. pipeline.test.runner로 래칫 체크
```

Plan/Design/Review Phase는 기존 에이전트를 그대로 사용한다.

### Consequences

- **장점**: 전환 범위 최소화, Phase 1~3/5~6 안정성 유지.
- **단점**: Plan/Design에서도 도메인 특화 에이전트를 쓰고 싶은 경우 추후 확장 필요.
- **기각된 대안**: 전 Phase 동시 전환 — 검증 범위가 너무 넓어 래칫 수렴 불가.

---

<a id="adr-7"></a>
## ADR-7: Skill 설계 원칙

### Context

Skill 파일에 API 문서 수준의 지식을 넣으면 토큰이 폭발하고, 추상적 원칙만 넣으면 실용성이 없다.

### Decision

"패턴 > 지식" 원칙을 채택한다 (P6 적용 — Abstraction over Memorization).

**Skill 구조**:
1. **Core Patterns** — 해당 기술의 핵심 설계 패턴
2. **Decision Framework** — 상황별 선택 기준
3. **Common Pitfalls** — 자주 발생하는 실수와 회피법

**크기 기준**:
- `react.md`: 26줄 (~246 토큰)
- `rust.md`: 31줄 (~306 토큰)
- 목표: 개별 스킬 300토큰 이내, 역할당 2~3개 스킬 합산 2500토큰 예산 내

### Consequences

- **장점**: 토큰 효율적 (P2), 다른 프로젝트에서도 유효한 범용 패턴.
- **단점**: 프로젝트 특화 지식은 Rules(learnings.md)로 분리 관리 필요.
- **기각된 대안**: API 레퍼런스 포함 — 토큰 예산 초과, LLM이 이미 학습한 지식 중복 (P2 위반).

---

<a id="adr-8"></a>
## ADR-8: Script vs Prompt 경계

### Context

AI 에이전트가 모든 작업을 수행하면 토큰 낭비가 심하고 결과가 비결정적이다. 어떤 작업을 Script로, 어떤 작업을 AI 판단으로 배분할지 기준이 필요했다.

### Decision

기계적 작업은 Script, 판단이 필요한 작업은 AI Prompt (P2, P7 적용).

**Script 영역** — `jarfis_cli.py` 13개 서브커맨드:

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
- PRD 채점 (5항목 0-2점)
- TDD 래칫 판정 (pass_rate 비교)
- Gate 승인/수정/중단 결정 보조

### Consequences

- **장점**: 결정적 작업의 재현성 보장, AI 토큰을 판단에 집중.
- **단점**: 경계가 모호한 작업 존재 (예: 도메인 감지 — Script가 후보 제시, AI가 최종 선택).
- **기각된 대안**: 전부 AI — 토큰 비용 폭발 + 비결정적 결과 (P7 위반).

---

<a id="adr-9"></a>
## ADR-9: Human Gate 배치

### Context

AI가 전체 워크플로우를 자율 실행하면 잘못된 방향으로 깊이 들어간 후에야 문제를 발견한다. 인간 검토 시점의 최적 배치가 필요했다.

### Decision

3개 Gate를 주요 Phase 전환점에 배치한다 (P8 적용 — Human Gate, AI Execute).

| Gate | 위치 | 검토 내용 |
|------|------|----------|
| Gate 1 | Phase 1 후 | PRD + Working Backwards + PRD Score |
| Gate 2 | Phase 2&3 후 | 아키텍처 + 태스크 분해 + UX 시안 |
| Gate 3 | Phase 5 후 | 코드리뷰 + QA + 보안 + 배포 리뷰 |

**강제 규칙** (work.md:816):

> 반드시 AskUserQuestion을 사용하여 사용자의 명시적 선택을 받는다 (텍스트 출력만으로 자동 진행하지 않는다).

Gate 옵션: "승인" → 다음 Phase, "수정" → 해당 Phase 재실행, "중단" → 즉시 종료.

### Consequences

- **장점**: 구현 전(Gate 2)에 방향 수정 가능, 배포 전(Gate 3)에 품질 확인.
- **단점**: 3회 인간 개입이 자동화 속도를 제한 (P1과의 긴장).
- **기각된 대안**: Gate 없음 — 잘못된 구현 전체 폐기 리스크 (P8 위반). 5개 Gate — 과도한 중단으로 UX 저하 (P1 위반).

---

<a id="adr-10"></a>
## ADR-10: Resilient Continuity

### Context

Claude Code 세션은 auto-compact, 크래시, 수동 종료로 언제든 중단될 수 있다. 중단 후 컨텍스트 복원이 불가능하면 처음부터 다시 시작해야 한다.

### Decision

4개 Hook으로 세션 연속성을 보장한다 (P9 적용 — Resilient Continuity).

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
4. `/jarfis:work-continue` 안내

### Consequences

- **장점**: 세션 중단 후 자동 컨텍스트 복원, 백업으로 상태 복구 가능.
- **단점**: Hook 실행 시간이 세션 시작을 지연 (미미).
- **기각된 대안**: 수동 상태 복구 — 사용자 부담 과대 (P1 위반).

---

<a id="adr-11"></a>
## ADR-11: Cascading Specificity

### Context

프로젝트 프로필, 위키, 산출물 등 여러 정보 소스가 있을 때 충돌이 발생할 수 있다. 어떤 정보를 우선할지 규칙이 필요했다.

### Decision

4단계 우선순위 체계를 적용한다 (work.md:213).

```
정보 우선순위: $DOCS_DIR > project/.jarfis > wiki/ > INDEX.md
이번 태스크가 다루는 주제: $DOCS_DIR 우선. 안 다루는 주제: wiki 유효.
```

**로딩 모드**:

| 모드 | 사용처 | 로딩 범위 |
|------|--------|----------|
| 4-Step 전체 로딩 | Work/Extend | INDEX.md → 4개 _index.md → 관련 파일 최대 5개 |
| 2-Step 경량 로딩 | Fix | INDEX.md → 관련 _index.md 최대 2개 (개별 파일 읽지 않음) |

### Consequences

- **장점**: 정보 충돌 시 명확한 해소 규칙, Fix 모드에서 토큰 절약 (P2).
- **단점**: 4-Step 로딩은 최대 10개 파일 읽기로 Phase 0 시간 증가.
- **기각된 대안**: 전체 위키 로딩 — 토큰 예산 초과 (P2 위반). 위키 미참조 — 기존 결정 무시 위험.

---

<a id="adr-12"></a>
## ADR-12: Leaky Abstraction 검증

### Context

코어 모듈이 특정 프레임워크(React, Tauri 등)를 직접 참조하면 도메인 독립성이 깨진다. 도메인 팩 간 교차 참조도 격리를 위반한다.

### Decision

`test_architecture.py`로 경계 위반을 자동 검증한다 (P7 적용).

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
- **기각된 대안**: 코드 리뷰만으로 검증 — 인간 실수 가능성 (P7 위반).

---

<a id="adr-13"></a>
## ADR-13: Dialectic Review

### Context

JARFIS 시스템 자체의 변경(implement, upgrade, distill)에서 단일 관점 검토는 맹점을 만든다.

### Decision

Advocate(green) + Critic(red) 2인 토론 구조로 변경을 검증한다 (P4 적용 — Dialectic Quality).

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

**적용 범위**: sys-implement.md, sys-upgrade.md, sys-distill.md (JARFIS 자체 수정 시)

**게이트 진입 조건**:
- `--review=major` → 필수, `--review=patch` → 스킵
- 자동 판단: 파일 2개 이상 또는 구조 변경 → 토론 실행

### Consequences

- **장점**: 맹점 감소, 변경 품질 향상 (distill에서 30%+ 개선 보고).
- **단점**: 토론 2라운드 = 추가 에이전트 호출 2~4회 (토큰 비용).
- **기각된 대안**: 3인 이상 패널 — 토큰 비용 대비 한계 효용 감소. 토론 없음 — 단일 관점 맹점 (P4 위반).

---

<a id="adr-14"></a>
## ADR-14: 프롬프트 외부화 & 증류

### Context

work.md에 모든 에이전트 프롬프트가 인라인되면 파일이 비대해지고, 프롬프트 수정 시 워크플로우 로직까지 건드려야 한다.

### Decision

에이전트 프롬프트를 `prompts/` 디렉토리로 외부화하고, `templates/`로 산출물 템플릿을 분리한다 (P2 적용 — Token Austerity).

**prompts/** (9개):

| 파일 | 용도 |
|------|------|
| phase1.md | Phase 1 Discovery 에이전트 프롬프트 |
| phase2.md | Phase 2 Architecture 에이전트 프롬프트 |
| phase3-figma.md | Phase 3 Figma 연동 프롬프트 |
| phase4.md | Phase 4 Implementation 에이전트 프롬프트 |
| phase4-5.md | Phase 4.5 Operational Readiness 프롬프트 |
| phase5.md | Phase 5 Review & QA 에이전트 프롬프트 |
| phase6.md | Phase 6 Retrospective 에이전트 프롬프트 |
| continue-extend.md | Continue/Extend 모드 프롬프트 |
| wiki-loading.md | Wiki 로딩 공통 모듈 (2-Step/4-Step) |

**templates/** (10개):
`design-html-meta.md`, `jarfis-state-schema.md`, `learnings.md`, `meeting-artifacts.md`, `org-profile.md`, `project-context.md`, `project-profile.md`, `ux-direction.md`, `wiki-index.md`, `wiki-section-index.md`

**증류 프로세스** (sys-distill.md):
1. Measure — 현재 프롬프트 토큰 측정
2. 6가지 진단 — 중복/인라인/비효율 식별
3. 8가지 액션 — 외부화/압축/분리/병합 등
4. Dialectic Review — 증류 계획 검증 (30%+ 개선 목표)
5. 실행 — 프롬프트 수정
6. 재측정 — 효과 확인

### Consequences

- **장점**: work.md는 워크플로우 로직만, prompts/는 에이전트 지시만 담당.
- **단점**: 참조 정합성 관리 필요 (work.md의 `📄 프롬프트:` 참조와 실제 파일).
- **기각된 대안**: 모든 프롬프트 인라인 — work.md 1000줄+ 비대화 (P2 위반).

---

<a id="transition-map"></a>
## 부록: v2.5→v3.0 전환 맵

### v2.5.x 래칫 기반 구축

| 버전 | 내용 | 관련 ADR |
|------|------|----------|
| v2.5.4 | PRD Ratchet 도입 (5항목 채점 + 단조증가) | ADR-4 |
| v2.5.5 | Workflow Metrics Recording (AutoResearch results.tsv 패턴) | ADR-8 |
| v2.5.6 | TDD Ratchet (pass_rate baseline + git stash 원복) | ADR-4 |
| v2.5.7 | Fix Ratchet (Continue 모드 1회 재시도) | ADR-4 |

### v3.0.0 주요 변경

- 120회 래칫 수렴을 통한 시스템 안정화
- 11개 병렬 에이전트 분석 기반 Domain Pack 설계
- `_schema.yaml` Published Language 확립
- `compose()` 함수 기반 Agent 합성
- 4개 Hook 기반 Resilient Continuity
- `test_architecture.py` 경계 검증 자동화

---

*이 문서는 JARFIS v3.0 시점의 아키텍처 결정을 기록한다. 각 ADR은 실제 코드와 정합성이 검증되었다.*
