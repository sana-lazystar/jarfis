# JARFIS Agents

> **Last aligned**: v4.0.5 · 2026-04-20
> **Audience**: 기여자 · 외부 평가자 · 미래의 자신
>
> **상위 설계**: [PHILOSOPHY.md](./PHILOSOPHY.md) #5 Context as Investment (Composition aspect) + #2 Dialectic for Self-Modification
> **ADR**: [DESIGN.md](./DESIGN.md) ADR-1 (Agent 합성), ADR-7 (Skill 설계), ADR-13 (Dialectic), ADR-17 (agent-composition.yaml)

---

## 1. 개요

JARFIS는 agent를 **3계층 동적 합성**으로 구성한다 (DESIGN ADR-1, ADR-17):

```
Persona (인지 프레임) + Skill (기술 전문성) + Rule (프로젝트 학습)
                              ↓
                  agent-composition.yaml (선언적 규칙)
                              ↓
                     compose CLI (결정적 조립)
                              ↓
                Task tool로 sub-agent spawn (tmux 내부)
```

### 1.1 체계 전체

| 계층 | 인벤토리 | 저장 위치 | 수 |
|------|---------|----------|---:|
| **Top-level Agent** | foreman · engineer · advocate · critic | `~/.claude/agents/jarfis/*.md` | 4 |
| **Persona** | product-owner · technical-architect · backend-/frontend-developer · devops-engineer · qa-/security-engineer · tech-lead · ux-designer | `~/.claude/agents/jarfis/personas/*.md` | 9 |
| **Skill** | react · vue · nodejs · rust · tauri-backend/webview · express · postgres · redis · s3 · aws-lambda · cognito · dynamodb · browser · biome-lint · cargo-clippy | `~/.claude/commands/jarfis/skills/*.md` | 16 |
| **Composition Role** | (9 personas + tech-lead 2분리) | `~/.claude/commands/jarfis/agent-composition.yaml` | 10 |
| **Rule** | learnings · project-context · project-rule | 프로젝트별 `.jarfis-project/` | N |

### 1.2 핵심 원칙

- **모든 합성은 결정적** — LLM inference 제거, agent-composition.yaml + compose CLI로 조립 (ADR-17)
- **Persona는 프로젝트 독립적** — 역할 정의만 담고, 특정 기술을 암기하지 않음
- **Skill은 패턴 > 지식** — 300 토큰 내외 개별 skill, 합산 2500 토큰 예산 (ADR-7)
- **Rule은 프로젝트별 학습** — `.jarfis-project/` 에 고정, 다음 실행이 재활용
- **합성 결과는 추적 가능** — `audit header` (v4.0.4) + meta 필드로 "왜 이 prompt가 이렇게 조립되었는가?" 역추적

---

## 2. Top-level Agents (4개)

`~/.claude/agents/jarfis/` 에 정의된 4개 public agent. Claude Code의 Agent tool에서 호출 가능한 최상위 단위.

### 2.1 `jarfis-foreman` — tmux Phase Executor

| 항목 | 값 |
|------|-----|
| 파일 | `jarfis-foreman.md` (4,550 bytes) |
| Model | `opus` |
| Color | `white` |
| 역할 | Per-phase tmux 세션의 실행자 |

**책임**:
- 해당 Phase 프롬프트 (`prompts/phase{N}.md`) 를 **정확히 쓰여진 대로** 수행
- Task tool로 sub-agent spawn. spawn 때마다 `jarfis_cli.py compose --agent <name> [--scope-index i] --state <state>` 로 prompt 조립 후 verbatim 주입
- sub-agent 출력을 지정된 artifact 파일에 병합
- phase prompt 지시에 따라 `jarfis_cli.py phase-verify` / `pattern-detect` 호출
- Completion Protocol 블록 작성 (매 Phase 마지막 tmux 출력)

**금지 사항**:
- 큰 source artifact (tasks.md 본문, architecture.md 전체) 직접 read 금지 — sub-agent가 주입받은 context로 처리
- 아키텍처/스코프/우선순위 결정 금지 — sub-agent 담당, Gate에서 사용자 승인
- `.jarfis-state.json` 쓰기 금지 — main session 전용 (ADR-18)
- `gate-check` / `phase-check` 호출 금지 — main session 전용

**페르소나 특성**:
- Executor, not judge. 프롬프트 지시를 그대로 수행
- 모호성/진짜 blocker 발생 시 Completion Protocol `notes` / `blocked` 필드로 main에 에스컬레이션. 자율 결정 금지

### 2.2 `jarfis-engineer` — v4 Migration Domain Expert

| 항목 | 값 |
|------|-----|
| 파일 | `jarfis-engineer.md` (6,711 bytes) |
| Model | `opus` |
| Color | `cyan` |
| 역할 | JARFIS v3 → v4 마이그레이션 도메인 전문가 (메인 Claude의 persona로 로드) |

**사용 맥락**:
- **일반 `/jarfis:work` 워크플로우의 일부 아님** — v4 migration 작업 전용
- 메인 Claude가 **세션 시작 시 이 파일을 read** 해서 페르소나 + 안전망 적용
- 8개 milestone (M1~M8) + M0 bootstrap 안전 실행 담당

**보유 지식**:
- v3 vs v4 고수준 비교표
- Critical decisions — B1~B5 (Blockers), M1~M12 (Major milestones), S6 (swap)
- Safety principles 5개 (v3 호환성 / 회귀 베이스라인 / Atomic milestone / 백업 보존 / Rollback 즉시)
- Workflow pattern per session

**Anti-pattern** (엄격 금지):
- `architecture.md` / `phase-spec.md` / `interim-summary.md` 직접 read (system-spec.md 압축 버전 사용)
- 모든 milestone을 한 세션에 처리
- Sub-agent에 milestone 통째로 위임
- git push 자동
- `jarfis.v3.bak` 조기 삭제

### 2.3 `jarfis-advocate` — Dialectic Advocate

| 항목 | 값 |
|------|-----|
| 파일 | `jarfis-advocate.md` (2,900 bytes) |
| Model | `opus` |
| Color | `green` |
| 역할 | JARFIS Dialectic Review의 Advocate 측 |

**적용 범위 — sys-* 전용** (DESIGN ADR-13, PHILOSOPHY #2):
- `sys-implement`, `sys-upgrade`, `sys-distill` (JARFIS 자기 수정 명령) 에서만 호출
- 일반 `/jarfis:work` 워크플로우에서는 호출되지 않음

**페르소나 특성**:
- **Verdict first** — 첫 문장에 결론
- **Evidence only** — 모든 주장에 구체적 시나리오/과거 사례
- **Trade-off eliminator** — pros/cons 나열 대신 "trade-off 최소화하는 답" 제시
- **No soft language** — "improve할 수도 있다" 대신 "X를 고친다, 이유는 Y"
- **Risks absorbed** — Critic의 risk를 인식하고 왜 넘어가는지 설명

**Output format**:
```
## Advocate Opinion
### Verdict
[한 문장]
### Evidence
1. [Claim]: [시나리오]
### Risks Absorbed
### Additional Opportunity
```

**Discussion rules**:
- 라운드당 최대 300단어
- Consensus / Disagreement / Deadlock 3분기 (Deadlock → 사용자 판단)

### 2.4 `jarfis-critic` — Dialectic Critic

| 항목 | 값 |
|------|-----|
| 파일 | `jarfis-critic.md` (3,130 bytes) |
| Model | `opus` |
| Color | `red` |
| 역할 | JARFIS Dialectic Review의 Critic 측 |

**적용 범위**: 2.3과 동일 — sys-* 전용.

**페르소나 특성**:
- **Find the flaw** — 결함이 있으면 명명, 없으면 "no objection"
- **Concrete failures only** — "WILL happen" (not MIGHT) 수준의 구체 시나리오
- **No vague concerns** — "issues 일으킬 수도" 대신 "Y 시 Z 때문에 X 깨짐"
- **Kill or approve** — blocker + 구체 대안 / 아니면 no objection
- **No softening** — 좋은 변경엔 "no objection" 직접 명시. fake concern 패딩 금지
- **System consistency enforcer** — 모든 변경은 JARFIS 기존 설계 원칙과 대조

**Output format**:
```
## Critic Opinion
### Verdict
["Blocked — [reason]" / "No objection" / "Conditional — [fix]"]
### Failure Scenarios (if blocking)
### Required Fix (if conditional)
### Acknowledged Merits
```

---

## 3. Persona Inventory (9개)

`~/.claude/agents/jarfis/personas/` 에 정의된 역할별 인지 프레임. Top-level agent와 달리 Claude Code의 Agent tool에서 직접 호출되지 않으며, **compose CLI가 합성하여 sub-agent로 spawn** 한다.

| Persona | File size | Primary Phase | Scope | 모델 |
|---------|----------:|---------------|-------|------|
| `product-owner` | 1,825 | Phase 1a/1b | work-wide | `opus` |
| `technical-architect` | 1,943 | Phase 1b, 2 | work-wide | `opus` |
| `frontend-developer` | 2,884 | Phase 2, 4 | per-project | `sonnet` |
| `backend-developer` | 3,032 | Phase 2, 4 | per-project | `sonnet` |
| `devops-engineer` | 1,677 | Phase 4, 4.5 | work-wide | `sonnet` (composition.yaml override: `opus`, M4) |
| `qa-engineer` | 1,667 | Phase 2, 5 | per-project | `opus` |
| `security-engineer` | 1,826 | Phase 2, 5 | work-wide | `opus` |
| `tech-lead` | 1,716 | Phase 5, 6 | per-project (5) / work-wide (6) | `opus` |
| `ux-designer` | 1,465 | Phase 1b, 3, 5 | work-wide | `opus` |

### 3.1 Persona 특성

- **프레임 중심**: 역할의 사고 프레임만 담음. 특정 프레임워크(React, Tauri 등) 지식 없음
- **크기**: 1,465 ~ 3,032 bytes (대부분 2KB 이하)
- **모델 분포**: **opus 6개 (판단 중심 — PO, TA, tech-lead, security, QA, UX)** vs **sonnet 3개 (실행 중심 — FE/BE dev, devops)**. devops는 M4 결정으로 composition.yaml에서 `opus` 강제 (AWS 리서치 등 무거운 추론)

### 3.2 tech-lead 2분리 (M4)

단일 `tech-lead.md` 파일이지만 composition.yaml에서 **두 역할로 분리 사용**:

| Composition role | Phase | scope | 목적 |
|------------------|-------|-------|------|
| `tech-lead-reviewer` | Phase 5 | per-project | 코드 리뷰 (project-profile.md Architecture/Conventions/Caveats) |
| `tech-lead-strategist` | Phase 6 | work-wide | 회고 (docsDir 산출물 기반, project-profile는 bonus) |

이유: Phase 5는 프로젝트별 리뷰, Phase 6는 워크 전체 회고라 **같은 persona지만 다른 context injection**이 필요.

---

## 4. agent-composition.yaml — Declarative Composition (ADR-17)

`~/.claude/commands/jarfis/agent-composition.yaml` 은 agent 합성의 **단일 진실 원천**. `jarfis-foreman`이 `jarfis_cli.py compose` CLI를 통해 참조.

### 4.1 Schema

각 composition role은 아래 필드를 가진다:

| 필드 | 값 | 설명 |
|------|-----|------|
| `persona` | personas/* 파일 stem | 'senior-' 접두사 없음 (옵션 B 결정) |
| `scope` | `per-project` / `work-wide` | scope[i]마다 spawn vs 전체 1번 |
| `skills_from_domain` | boolean | domain.yaml의 skills 로드 여부 |
| `model` (선택) | `sonnet` / `opus` / `haiku` | persona 기본값 override |
| `context[]` | context entries | 주입할 파일 지정 |

**context entry 필드**:
- `base`: `project` / `all-projects` / `docs` / `org` / `org_wiki` (M9 신규)
- `path`: base 기준 상대 경로
- `sections`: Markdown `## 헤딩` 리스트 (50줄 초과 파일 권장)
- `optional`: 파일 미존재 시 skip 허용 (기본 false)
- `importance`: `required` / `recommended` / `optional`

**`importance` 효과**:
- `required` 누락 시 → 메인 Claude가 사용자에게 경고 (soft warning)
- `recommended` 누락 시 → meta 기록 (silent)
- `optional` 누락 시 → debug 레벨만

### 4.2 10 Composition Roles

```yaml
agents:
  product-owner:         { scope: work-wide,   skills_from_domain: false }
  technical-architect:   { scope: work-wide,   skills_from_domain: false }
  tech-lead-reviewer:    { scope: per-project, skills_from_domain: true  }   # Phase 5
  tech-lead-strategist:  { scope: work-wide,   skills_from_domain: true  }   # Phase 6
  qa-engineer:           { scope: per-project, skills_from_domain: true  }
  security-engineer:     { scope: work-wide,   skills_from_domain: true  }   # OBS-3: 단일 spawn
  ux-designer:           { scope: work-wide,   skills_from_domain: false }
  devops-engineer:       { scope: work-wide,   skills_from_domain: true,  model: opus }   # M4
  frontend-developer:    { scope: per-project, skills_from_domain: true  }
  backend-developer:     { scope: per-project, skills_from_domain: true  }
```

### 4.3 Skills 로드 4-단계 fallback chain (system-spec §5.5)

1. **Step 1**: `scope[i].skills[]` (state에 명시) — 가장 정확
2. **Step 2**: `.jarfis-project/project-profile.md` 의 `## Active Skills` 섹션 파싱
3. **Step 3**: `extra_skills_by_framework` (composition.yaml의 framework→skill 매핑)
4. **Step 4**: `domain.yaml roles[].skills` — framework 무관, 마지막 fallback

**Step 3 — extra_skills_by_framework** (v4 추가):

```yaml
extra_skills_by_framework:
  # Frontend
  vue: [vue]
  react: [react, browser]
  nextjs: [react, browser]       # nextjs는 react 기반
  svelte: [browser]              # svelte 전용 skill 없음

  # Backend
  express: [express, nodejs]
  nestjs: [express, nodejs]
  fastify: [nodejs]
  serverless: [aws-lambda, nodejs]

  # Languages
  typescript: [biome-lint]
  javascript: [biome-lint]
  rust: [rust]

  # Desktop
  tauri: [tauri-backend, tauri-webview, rust]
```

### 4.4 Context Injection Matrix

각 role이 어떤 파일의 어떤 섹션을 받는가는 composition.yaml의 `context[]` 에 선언. v4.0.4 N-3 audit에서 확정:

| Role 그룹 | 주입 파일 | 주입 섹션 |
|----------|----------|----------|
| BE/FE developer | `project-profile.md` | Tech Stack + Coding Conventions + Reusable Components + Scripts & Commands + Notes & Caveats |
| architect/reviewer | `project-profile.md` | Architecture + Conventions + Caveats |
| qa | `project-profile.md` | Conventions + Scripts |
| security/devops | `project-profile.md` | Tech Stack + Architecture + Config |
| PO/ux-designer | (project-profile 미주입) | 기획/디자인 문서 사용 |

**compose 동작**: yaml에 선언된 섹션이 실제 파일에 없으면 stderr 경고 + `meta.context_files[].missing_sections` 기록 (N-3 audit).

---

## 5. Skill Inventory (16개)

`~/.claude/commands/jarfis/skills/*.md` 에 정의. ADR-7 "패턴 > 지식" 원칙에 따라 개별 파일 21~33줄 (평균 27.4줄, ~220 토큰).

| 범주 | Skills |
|------|--------|
| **Frontend** | `react` · `vue` |
| **Backend** | `nodejs` · `express` |
| **Language** | `rust` |
| **Desktop** | `tauri-backend` · `tauri-webview` |
| **Cloud/AWS** | `aws-lambda` · `cognito` · `dynamodb` · `s3` |
| **Storage/Cache** | `postgres` · `redis` |
| **Runtime/Lint** | `browser` · `biome-lint` · `cargo-clippy` |

### 5.1 Skill 구조 (ADR-7)

각 skill 파일은 3-part 구조:
1. **Core Patterns** — 해당 기술의 핵심 설계 패턴
2. **Decision Framework** — 상황별 선택 기준
3. **Common Pitfalls** — 자주 발생하는 실수와 회피법

**크기 기준**:
- 개별 skill: 300 토큰 이내 목표 (실측 ~220 토큰, 기준 충족)
- 역할당 합산: 2,500 토큰 예산 (domain.yaml `max_skill_tokens`, domain.py:339)
- 첫 skill 보장 (W1-1): 예산 초과해도 첫 번째 skill은 반드시 로드

### 5.2 CJK 토큰 추정 (W1-2)

Skill 파일에 한국어/중국어/일본어 포함 시 토큰 추정 보정:

```python
chars_per_token = 4 - (2 * cjk_ratio)  # ASCII 4 ~ CJK 2
```

---

## 6. Rule — Project 학습 (Cascading Specificity, ADR-11)

프로젝트별 학습은 `.jarfis-project/` 에 저장되며 composition.yaml에서 `importance` 기준으로 주입.

### 6.1 Rule 파일 3종

| 파일 | 내용 | 사용 Phase |
|------|------|-----------|
| `.jarfis-project/project-profile.md` | Tech Stack / Architecture / Coding Conventions / Scripts / Active Skills / etc. | 거의 모든 Phase |
| `.jarfis-project/project-rule.md` | 프로젝트별 강제 규칙 | BE/FE dev, qa, tech-lead-reviewer |
| `.jarfis-project/project-context.md` | 작업 이력 / 맥락 / 경험 | BE/FE dev (optional importance) |

### 6.2 Global 학습

- `learnings.md` — JARFIS 전역 학습 (sys-upgrade로 반영, 모든 워크플로우 적용)
- `workflow-metrics.tsv` — Phase별 시간/토큰/에러 기록 (v2.5.5 AutoResearch pattern)

### 6.3 Cascading Specificity 우선순위

```
$DOCS_DIR (이번 작업 산출물) > project/.jarfis-project/ > .jarfis-org/wiki/ > INDEX.md
```

이번 태스크가 다루는 주제: `$DOCS_DIR` 우선. 안 다루는 주제: wiki/project 유효.

---

## 7. 모델 전략

v4 기준 모델 사용 분포 (코드 검증). **원칙: opus = 판단, sonnet = 실행** (#5 경제성, ADR-8).

| 레벨 | 모델 지정 | 비고 |
|------|----------|------|
| **Top-level Agent** (4개) | 전원 `opus` — foreman / engineer / advocate / critic | foreman이 사실상 실행자이나 phase prompt 해석 + sub-agent spawn 판단이 필요해 opus |
| **Persona (판단 중심, 6개)** | `opus` — product-owner, technical-architect, tech-lead, security-engineer, qa-engineer, ux-designer | Deep reasoning, 결정/리뷰/전략 |
| **Persona (실행 중심, 3개)** | `sonnet` — frontend-developer, backend-developer, devops-engineer | 대량 코드 구현, 반복 작업 |
| **Composition override** (1개) | `devops-engineer` → `opus` | M4 결정: AWS 리서치 등 워크로드별 heavy reasoning 필요 |
| **Main session** | 사용자 선택 (일반적으로 opus or sonnet) | — |

### 7.1 모델 선택 원칙

- **opus** — 판단 (architecture, review, dialectic, strategy, migration)
- **sonnet** — 실행 (code implementation, repetitive tasks)
- **haiku** — v4.0 기준 정의된 사용처 없음 (향후 최소 운영 유틸 후보)

### 7.2 경향성

JARFIS는 AI 토큰을 **판단 (opus)** 에 집중한다 (#5 경제성, ADR-8). 기계적 판정은 `verify.py` (Python, no LLM) 로 이관 (ADR-15). 실행 중심 persona(FE/BE/devops)는 sonnet으로 비용 효율 확보, 무거운 추론이 필요하면 composition.yaml에서 `opus` override.

---

## 8. Dialectic 적용 범위 (sys-* 전용)

PHILOSOPHY #2 Dialectic for Self-Modification + DESIGN ADR-13 Scope Clarification (2026-04-20).

### 8.1 포함

JARFIS 자기 수정 (self-modification) 계열 명령 — JARFIS가 JARFIS 자체의 **프롬프트·에이전트·워크플로우·도메인 팩 구조**를 변경하는 행위:

| 명령 | 목적 |
|------|------|
| `/jarfis:sys-implement` | 단일 시스템 변경 (추가/수정/삭제) |
| `/jarfis:sys-upgrade` | 학습 반영을 통한 시스템 강화 |
| `/jarfis:sys-distill` | 프롬프트 증류 (토큰 최적화) |

### 8.2 제외

의도적으로 Dialectic 없이 실행되는 영역:

- `/jarfis:sys-health` — 진단/운영 유틸
- `/jarfis:sys-version` — 버전 번프
- `/jarfis:level-check` — **AI-Native Developer Maturity 평가**. advocate/critic을 참조하긴 하나 JARFIS 자신을 변경하지 않고 개발자를 평가함
- `/jarfis:jarfis-index` — 문서 index, 메타 설명
- `/jarfis:work` 일반 워크플로우 (Phase 0~6) — 품질 보장은 **#1 Deterministic Foundation + TDD Ratchet (조건부)** 담당
- 사용자 프로젝트 코드 수정

### 8.3 확장 규칙

향후 추가되는 자기 수정 계열 명령 (가상의 `sys-evolve` 등) 은 위 정의에 부합하면 **자동 포함**. 새 명령 추가 시 Dialectic 여부는 명령 문서 첫 섹션에 명시.

### 8.4 Dialectic 작동 방식 (요약)

1. Round 1: `jarfis-advocate` 분석 → `jarfis-critic` 반론 (각 ≤ 300 단어)
2. Round 2 (미합의 시): advocate 재반론 → critic 재반론
3. Round 2 후 미합의 → **사용자에게 양측 요약 + AskUserQuestion**

**합의 판단**:
- ✅ 합의: 양측 동의
- ⚠️ 조건부 합의: 한쪽만 동의하지만 설득력 있음
- ❌ 사용자 판단 필요: deadlock

상세는 [DESIGN.md ADR-13](./DESIGN.md#adr-13) 참조.

---

## 9. v3 → v4 Agent 변경 요약

| v3 Agent | v4 대응 | 변경 |
|----------|---------|------|
| `jarfis-white` | `jarfis-foreman` | **rename + tmux-scoped executor** (실행자 역할 강화) |
| `jarfis-black` (LLM verifier) | `verify.py` (Python deterministic gate) | **대체 + 제거**. LLM → deterministic (ADR-15) |
| `jarfis-advocate` | `jarfis-advocate` | **유지** (sys-* 전용으로 범위 명시) |
| `jarfis-critic` | `jarfis-critic` | **유지** (sys-* 전용으로 범위 명시) |
| `jarfis-engineer` | `jarfis-engineer` | **유지** (v4 migration persona로 사용) |

**상세 전환 history**: [MIGRATION.md §2 Breaking Changes](./MIGRATION.md#2-breaking-changes) 참조.

---

## 10. 합성 예시 (Phase 4 Implementation)

Phase 4에서 `jarfis-foreman`이 `frontend-developer` sub-agent를 spawn하는 흐름:

```
1. 메인 세션이 Phase 4 prompt를 조립 → tmux_claude.py 실행
                            ↓
2. tmux 세션에서 jarfis-foreman 기동
                            ↓
3. jarfis-foreman이 prompts/phase4.md 읽음
                            ↓
4. jarfis_cli.py compose --agent frontend-developer --scope-index 0 --state .jarfis-state.json
                            ↓
5. compose CLI:
   a. agent-composition.yaml → frontend-developer 규칙 로드
   b. persona: personas/frontend-developer.md read
   c. skills: scope[0].framework=react 판정 → react, browser skill 로드 (step 3)
      또는 project-profile.md의 Active Skills 섹션 (step 2)
   d. context: scope[0].path/.jarfis-project/project-{profile,rule,context}.md 주입
   e. prompt 조립 → stdout 반환
                            ↓
6. jarfis-foreman이 Task tool로 sub-agent spawn (조립된 prompt + 태스크 지시)
                            ↓
7. sub-agent: 구현 → 코드 변경 → 커밋
                            ↓
8. jarfis-foreman이 결과 수집 → phase-results/phase4/attempt1.json 기록
                            ↓
9. Completion Protocol 출력 (tmux 종료)
```

---

## 11. 참조

- **agent-composition.yaml**: `~/.claude/commands/jarfis/agent-composition.yaml`
- **compose CLI source**: `~/.claude/scripts/jarfis/compose/`
- **system-spec §5**: agent-composition.yaml + compose CLI 상세
- **domain.py::compose()**: v3 compose 함수 (v4 CLI와 일부 로직 공유, DESIGN ADR-1)
- **persona files**: `~/.claude/agents/jarfis/personas/*.md` (9개)
- **skill files**: `~/.claude/commands/jarfis/skills/*.md` (16개)
- **Top-level agent files**: `~/.claude/agents/jarfis/{foreman,engineer,advocate,critic}.md`
- **Dialectic scope (DESIGN ADR-13)**: [DESIGN.md#adr-13](./DESIGN.md#adr-13)
- **v4 migration context**: `~/Upscales/jarfis-v4-migration/system-spec.md` (jarfis-engineer가 참조)

---

*이 문서는 v4.0.5 시점의 agent 인벤토리와 합성 규칙을 기록한다. agent-composition.yaml + persona/skill 디렉토리의 실제 파일이 1차 source이며, drift 발생 시 이 문서보다 코드가 우선한다.*
