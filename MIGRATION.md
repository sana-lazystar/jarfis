# JARFIS v3 → v4 Migration Guide

> **Last aligned**: v4.0.5 · 2026-04-20
> **Audience**: v3 사용자 · 기여자 · v3 기반 블로그/자료 독자
> **본 문서의 역할**: v3 → v4 전환의 decision map. 원칙 변경 근거는 §Principle Changes, breaking changes는 §2, in-flight 작업 처리는 §3, 흔한 실수는 §6 Troubleshooting.

---

## 1. v3 vs v4 주요 차이점

| 영역 | v3 | v4 |
|------|----|----|
| **Orchestrator** | `work.md` 902 lines | `work.md` 255 lines (`work-legacy.md`로 archive) |
| **Phase 실행** | 단일 Claude 세션 Task 호출 | Phase별 dedicated tmux 세션 (ADR-16) |
| **Phase flow** | 9 phase 추상 | **13 steps** (T/0/1a/1b/G1/2∥3/G2/4/4.5/5/G3/6) |
| **검증** | `jarfis-black` LLM gate (~1400 tokens, non-deterministic) | `verify.py` Python deterministic gate (~10ms, 0 tokens) — ADR-15 |
| **Agent composition** | `domain.py::compose()` + LLM inference | `agent-composition.yaml` + `compose` CLI (결정적) — ADR-17 |
| **Executor** | `jarfis-white` | `jarfis-foreman` (tmux-scoped) |
| **State schema** | `project_name` 기반 flat | `sessionKey + scope[] + org{} + baseCommit` (v4.0.1 dual-emit) |
| **Skills 구조** | `domains/{web,desktop}/skills/` | `commands/jarfis/skills/` 평탄화 (16 skills) |
| **Ratchet** | 3종 (PRD + TDD + Fix) — "3종 Ratchet" 간판 | **TDD Ratchet 조건부만 활성**. PRD 제거 (v4.0.1), Fix legacy (ADR-21) |
| **Context 규모** | 메인 세션 ~100,000 tokens | 메인 세션 ~11,000 tokens (89% 감소) |
| **관측** | 없음 | `JARFIS_TRACE` opt-in (v4.0.5, ADR-20) |
| **단일 writer** | 암묵 | 명시 규칙 (ADR-18) — main=state, tmux=phase-results |
| **Triage** | Type A/B/C + Resume | Type A/C + Resume (B 제거, M7) |
| **Phase 4.5** | — | Operational Readiness 신설 (ADR-19) |
| **Dialectic** | 적용 범위 모호 | **sys-\* 전용** 명시 (F-14, ADR-13) |

---

<a id="principle-changes"></a>
## §Principle Changes — v3 원칙 → v4 원칙

[PHILOSOPHY.md v2](./PHILOSOPHY.md)의 v3→v4 원칙 변경 표 각주가 본 섹션으로 수렴한다. 각 원칙별 **무엇이 / 왜 / 어떻게** 바뀌었는지 기록.

### P0 Principle Zero — 재정의 (Aspiration only → Aspiration + Falsifiable)

**v3**: *"Aspiration over Implementation"* — 철학이 구현을 이끈다. 구현이 100% 못 충족해도 철학을 낮추지 않음.

**v4**: *"Function over Form — Philosophy as Tool · ROI Decides"*

**무엇이 바뀌었나**:
- aspirational framing만이 아니라 **falsifiable 조건** 추가: 원칙은 의사결정을 실제로 이끌어야 하고, ROI 낮은 원칙은 삭제 가능
- ROI (Return on Investment) 를 판단 기준으로 명시

**왜 바뀌었나**:
- v3 P1 "Orchestration for All" 같은 원칙이 46일 동안 실제 의사결정을 이끈 증거 부재 (CHANGELOG + 활동 기록)
- "죽은 장치는 해롭다"는 2차 원칙이 v4 실천 (PRD Ratchet 제거 = P0 채택의 첫 사례, ADR-21)

**영향**:
- 외부 평가 축 12 Design Traceability (8.5 → target 9+) — 원칙이 실제 결정 이끌었는지 검증 가능
- 후속 원칙 삭제/통합의 근거가 됨

### P1 Orchestration for All — **삭제**

**v3**: *"비전문가도 영구적으로 개발을 이어갈 수 있는 AI IT 팀. 사용자는 '무엇'만 말하면 된다."*

**v4**: — (삭제)

**왜 삭제했나**:
- 46일 활동 기간(2026-03-04 ~ 2026-04-20) 동안 이 원칙이 **구체적 의사결정을 이끈 기록 없음**
- 외부 평가 축 4 (Human Gate Balance) 7.5/10 — Gate 3개 + Phase T AskUserQuestion 때문에 비전문가 UX에 역행
- aspirational 선언만 있고 구현 경로 없는 "죽은 원칙" → P0 기준 삭제

**정신의 계승**:
- **#6 Gated Autonomy** — "게이트 최소화 + 합리적 default 자동화" 원칙이 P1의 정신을 흡수
- v4.1 Autopilot 모드 (aspirational path)로 점진적 접근 가능성 보존

**영향**:
- README v2에서 "비전문가 지원" 프레이밍 제거
- 대신 **Depth-first orchestration** 정체성 강조 (외부 평가 축 중 Design Traceability에 JARFIS 유일 clear lead)

### P2 Token Austerity → **#5 Context as Investment (경제성 aspect)** — 재정의

**v3**: *"AI는 사고/추론/학습/비판에만 쓴다. 기계적 작업(파일 검증, 상태 관리, 측정)은 Script가 담당."* — 최소 지상주의

**v4 #5 경제성**: *"같은 가치 얻는다면 비용 낮은 쪽을 택한다. 가치가 비례해 커지면 비용도 기꺼이 지불한다. 핵심은 '싼 것'이 아니라 비용 대비 가치."*

**왜 바뀌었나**:
- v3 framing은 "무조건 최소" 처럼 읽힘. v4에서 Phase 4 tmux-per-phase는 세션별 컨텍스트 중복으로 **역방향 투자** (비용 증가) 이지만 병렬성/격리 가치가 비용을 정당화 (v4.0.0 의식적 trade-off)
- 관측(`JARFIS_TRACE`)도 마찬가지 — opt-in default off지만 on 상태에서는 overhead 지불
- "비용 대비 가치" 프레이밍이 실제 v4 결정들을 더 정확히 설명

**통합 대상**:
- v3 P5 "AI-Native Artifacts" (산출물 포맷) → #5 aspect 2
- v3 P6 "Abstraction over Memorization" (Composition) → #5 aspect 3

### P3 Self-Evolution → **#3 Dogfooding Evolution** — rename + 통합

**v3**: *"매 워크플로우가 학습 데이터. 회고 → 학습 축적 → 에이전트 강화."*

**v4 #3**: *"Every Execution is Training Data · JARFIS Included"* — 사용자 프로젝트 워크플로우 + JARFIS 자체의 자기 수정 세션 모두 학습 데이터

**왜 바뀌었나**:
- JARFIS가 JARFIS 자체를 수정하는 sys-* 세션도 학습 데이터 pool에 명시 편입 → dogfooding 개념 통합
- **Amortization 명시**: 1회 초기 비용, N회 실행에 분할 상환. 대상이 적어도(1인 dogfooding) ROI 회복

**구현 매핑**:
- `learnings.md` (global) / `project-context.md` (project) / `workflow-metrics.tsv` (측정)
- `sys-upgrade` 반영 루프 + `sys-distill` 프롬프트 증류
- v3.0.0 "120회 래칫 수렴 + 11 병렬 에이전트 분석" — 역사적 dogfooding 사례

### P4 Dialectic Quality → **#2 Dialectic for Self-Modification** — 범위 명시

**v3**: *"모든 중요 결정에는 생산적 비판자가 존재한다."*

**v4 #2**: *"Dialectic은 시스템 자기수정에만"* — sys-* 전용

**왜 바뀌었나**:
- 사실 확인 (findings F-14): `prompts/phase*.md` 전체에 Dialectic 참조 **전무**. 실 적용은 `sys-implement`, `sys-upgrade`, `sys-distill` 3개 + 메타 파일(level-check, jarfis-index)
- v3 DESIGN ADR-13 원문 *"적용 범위: sys-implement.md, sys-upgrade.md, sys-distill.md"* 와 실제 코드가 일치
- v3 P4 framing이 실제보다 광범위하게 읽혔음 → "원칙의 해상도 상승"

**의미**:
- 일반 워크플로우의 품질 보장은 **#1 Deterministic Foundation + TDD Ratchet (조건부)** 담당
- 시스템 자기 수정처럼 파급력 큰 결정에만 Advocate/Critic 2인 토론 (라운드당 300단어, 최대 2라운드) 비용 지불

**확장 규칙**: 향후 자기 수정 계열 명령 추가(예: `sys-evolve`)은 자동 포함.

### P5 AI-Native Artifacts → **#5 Context as Investment (산출물 포맷 aspect)** — 통합

**v3**: *"산출물은 AI가 읽고 재사용하기 좋은 형태로. 구조화된 마크다운 + JSON."*

**v4**: #5 경제성 원칙의 **aspect 2** 로 통합 — "산출물은 다음 실행이 재활용할 수 있는 구조화된 형태로 남긴다"

**통합 이유**: AI-Native format도 결국 **비용 대비 가치** 의 한 형태 — 자유 서술보다 고정 스키마가 재사용 비용을 낮춘다. 별도 원칙으로 분리해두기보다 #5 경제성과 묶는 게 정합적.

**v4 인스턴스**: `.jarfis-state.json` / `phase-results/phase{N}/attempt{K}.json` / `learnings.md` / `workflow-metrics.tsv` / `agent-composition.yaml` / `_schema.yaml` — 6종 고정 스키마.

### P6 Abstraction over Memorization → **#5 Context as Investment (Composition aspect)** — 통합

**v3**: *"프로젝트별 암기는 Coder. 패턴을 추상화하여 범용 원칙으로 승격하면 Developer."*

**v4**: #5 경제성 원칙의 **aspect 3** 로 통합 — "프로젝트별 암기 대신 재사용 가능한 합성 단위를 만든다. Persona + Skill + Rule 3계층은 도메인 간 재사용 가능한 자산이다."

**통합 이유**: Composition 단위를 만드는 것도 **재사용 비용 절감** — v3 P6과 P2의 본질은 같은 #5 경제성 원칙의 다른 면.

**v4 인스턴스**: Persona 9 + Skill 16 + Rule (learnings/project-context/project-rule) + `agent-composition.yaml` 결정적 합성 + Domain Pack 7 EP (`_schema.yaml` Published Language).

### P7 Deterministic Foundation → **#1 Deterministic Foundation** — 유지 + 강화

**v3**: *"결정적인 부분은 반드시 Script로. AI의 비결정성은 판단 필요한 곳에만."*

**v4 #1**: 동일 (강화) — Deterministic by Default · AI by Necessity

**무엇이 강화되었나**:
- `jarfis-black` (LLM gate, ~1,400 tokens) → `verify.py` (Python, ~10ms, 0 tokens) — 외부 평가자 3명 공통 "v4의 가장 큰 변화" 지목 (ADR-15)
- **Single-writer state rule** — 동시성 경합을 파일 경로 단위로 원천 차단 (ADR-18)
- `verify.py` 4 엔트리포인트 통합 (gate-check/phase-check/phase-verify/pattern-detect)
- LLM inference 제거된 `agent-composition.yaml` + compose CLI (ADR-17)

**핵심 진전**: "AI가 더 똑똑해지면 판단도 맡기자" 가 아니라 **"AI의 비결정성을 결정적 경계 안에 가두자"** — v4는 관측 계층까지 opt-in으로 확장 (ADR-20).

### P8 Human Gate, AI Execute → **#6 Gated Autonomy** — rename + 기준 명시

**v3**: *"의사결정 지점에서는 사람이 판단. 실행은 AI가 자율적으로."*

**v4 #6**: *"Gate the Irreversible · Automate the Rest"* — 되돌릴 수 없는 곳만 게이트 · 나머지는 자동

**왜 바뀌었나**:
- 게이트 기준 3가지 명시:
  1. 작업 방향 전체에 영향 주는 결정
  2. AI가 합리적 default를 추론할 수 없는 개인적 선택 (locale, 타겟 사용자, 브랜드 등)
  3. 잘못된 자율 실행의 복구 비용 > 사용자 개입 비용 (irreversible)
- 새 게이트 추가 제안 시 이 기준 통과 필수

**v4 현실 체크**: Gate 3개 + Phase T AskUserQuestion 이 비전문가 UX에 가파른 경사 (외부 평가 7.5/10). v4.1 Autopilot 모드로 해소 계획.

### P9 Resilient Continuity → **#4 Resilient Continuity** — 유지 + 확장

**v3**: *"세션이 죽어도, 컨텍스트가 압축되어도, 작업은 이어진다."*

**v4 #4**: 동일 (확장) — State Outlives Session

**무엇이 확장되었나**:
- `phase-results/phase{N}/attempt{K}.json` — tmux sub-agent 실행 결과 격리 보존
- `--save-pane` (v4.0.4) — tmux 세션 종료 직전 scrollback 캡처 (post-mortem)
- Single-writer state rule로 세션 간 격리 강화 (ADR-18)
- Triage Resume 분기 — v3 state 감지 시 안내 (F-08)

**원칙 진화**: v3은 "세션 죽음 방지" 중심, v4는 "세션이 죽어도 **어디서 왜 죽었는지 보존**" 까지 확장. Post-mortem capability 승격.

### 신규 긴장 관계

PHILOSOPHY v2에서 2개 긴장 관계 신설:

- **#5 경제성 × Observability** — `JARFIS_TRACE`는 opt-in 구조로 해소. default off가 핵심.
- **#1 Deterministic × #2 Dialectic** — 충돌 아닌 보완. Deterministic은 "판정" 영역, Dialectic은 "자기 수정의 판단" 영역. 역할 분담.

---

## 2. Breaking Changes

### 2.1 State schema 불호환

**v3 state 예시**:
```json
{
  "project_name": "my-project",
  "phase": "2",
  "tasks": [...]
}
```

**v4 state 예시**:
```json
{
  "sessionKey": "jf-a1b2c3d4",
  "work": { "name": "...", "docsDir": "...", "startedAt": "..." },
  "workspace": { "structure": "multi-project", "scope": [...] },
  "org": { "name": "...", "root": "..." },
  "domain": "web",
  "currentPhase": "3",
  "phases": { "1b": {...}, "2": {...} },
  "gates": { "1": "approved" },
  "tddEnabled": false,
  "locale": "ko"
}
```

**핵심 변경**:
- 최상위 identifier: `project_name` (flat) → `sessionKey` (v4)
- workspace scope 도입 — 다중 프로젝트 모노레포 지원
- org 스냅샷 — 감지 1회 (M10)
- phases/gates 별도 객체 — phase별 attempt/status 추적
- v4.0.1 dual-emit — v3 flat key들도 병존 (work-legacy.md 호환용)

**검증**: `state.py` 코드에서 최상위 key 감지로 버전 판별.

### 2.2 Agent 제거/rename

| v3 Agent | v4 처리 |
|----------|---------|
| `jarfis-black.md` | **제거** — `verify.py` (Python deterministic gate) 로 대체 |
| `jarfis-white.md` | **rename** → `jarfis-foreman.md` (tmux-scoped executor로 역할 강화) |
| `jarfis-advocate.md` | **유지** (sys-* 전용 범위 명시) |
| `jarfis-critic.md` | **유지** (sys-* 전용 범위 명시) |
| `jarfis-engineer.md` | **유지** (v4 migration persona로 사용) |

### 2.3 Verification 모델 전환

**v3**: `jarfis-black` LLM sub-agent가 Phase 산출물 기계적 검증.

**v4**: `jarfis_cli.py` top-level subcommands (Python):
- `gate-check {state_file} {1|2|3}`
- `phase-check {state_file} {phase_id}`
- `phase-verify {state_file} {phase_id}`
- `pattern-detect {review_file}`

### 2.4 Ratchet 축소 (findings F-09, ADR-21)

| Ratchet | v3 | v4 |
|---------|----|----|
| PRD | 활성 (5항목 채점) | **제거** (v4.0.1, producer 부재) |
| TDD | 활성 | **조건부** (`$TDD_ENABLED == 'true'` 시) |
| Fix | 활성 (Continue/Extend) | **legacy** (`jarfis-state-schema.md:204` 명시) |

"3종 Ratchet" 표현은 v4 실체와 괴리. 공식 표현: *"TDD Ratchet (조건부 활성), PRD/Fix는 legacy"*.

### 2.5 Triage 간소화 (findings F-07)

**v3**: Type A / B / C / Resume (4분기)

**v4**: **Type A / C / Resume** (3분기, B 제거 — M7)

- Type A: 새 기능 / 리팩터링 / 설계 — 자동 Phase 0 진행
- Type C: 단순 질문 / 디버그 / config — AskUserQuestion 분기
- Resume: Resume Dispatch (Phase T 이전)

### 2.6 Phase 구조 재정의

**v3 framing**: "9 Phase" (추상)

**v4 실체**: **13 steps** — `T → 0 → 1a → 1b → G1 → 2 ∥ 3 → G2 → 4 → 4.5 → 5 → G3 → 6`

핵심 변경:
- Phase 1 분할: **1a (main, PO dialogue) + 1b (tmux, foreman processing)**
- Phase 2 ∥ 3 병렬 tmux 실행 (B1 isolation, ADR-16)
- **Phase 4.5 신설** — Operational Readiness, DevOps first-class (ADR-19)
- Gate 1/2/3 명시 배치

### 2.7 Skills 구조 평탄화

| v3 | v4 |
|----|----|
| `domains/web/skills/react.md` | `commands/jarfis/skills/react.md` |
| `domains/desktop/skills/tauri-webview.md` | `commands/jarfis/skills/tauri-webview.md` |
| `domains/*/skills/` | **제거** (빈 디렉토리 cleanup) |

Domain pack YAML이 skill을 이름으로만 참조 (예: `external_skills: [web/react]` 같은 v3 scheme은 더 이상 주 경로 아님).

### 2.8 기타

- **Global locale** (M12): `~/.claude/.jarfis-locale` 전역 파일 도입
- **phase-results 서브디렉토리** (B3): `attempt1.json`, `attempt2.json` 각 독립 (디버깅 보존)
- **sessionKey 포맷**: `jf-` + uuid4 앞 8자
- **baseCommit 기록** (B2): Phase 0 branch cut 시 `git rev-parse HEAD` 저장 → Phase 5 git diff 기준

---

## 3. 전환 경로

### 3.1 In-flight v3 워크플로우 (진행 중)

**정책**: v3에서 완료하거나 v4에서 재시작. **Silent migration 금지** (findings F-08).

**시나리오**:

1. **v3 작업 완료 후 v4 사용**: 기존 v3 워크플로우를 `/jarfis:work-legacy` 로 끝까지 실행 → 완료 후 새 작업은 `/jarfis:work` (v4)
2. **v3 버리고 v4로 재시작**: 새 `docsDir` 에서 `/jarfis:work` 시작 — v3 state 파일은 별도 위치에 보존 or 수동 삭제

### 3.2 Silent migration 금지 — v3 state 감지 시 안내

`/jarfis:work` 진입 시 Resume Dispatch가 state 파일을 검사:

- `sessionKey` 있음 → v4 state, 일반 Resume
- **`project_name` 있음 (no `sessionKey`) → v3 state 감지**

v3 감지 시 사용자 안내 (`$LOCALE`):

> "v3 workflow state detected at this path. Continue with the legacy `/jarfis:work-legacy` (v3) for this work; start v4 work in a new directory."

**자동 이관 금지** — 결정권은 사용자에게. 이유: v3 ↔ v4 state 차이가 구조적으로 크고(workspace scope, org snapshot, phases 구조), 잘못 이관하면 데이터 손실 위험.

### 3.3 새 워크플로우

단순히 `/jarfis:work` 사용. 새 `docsDir` 에서 v4 state 생성 — 기존 v3 작업과 독립.

---

## 4. work-legacy.md 처리 (F-02)

### 4.1 현재 상태 (2026-04-20)

v3 orchestrator (`work.md` 902 lines) 를 `work-legacy.md` 로 archive한 상태. `hotfix/v4.0.6` commit `e309b94` 에서 DEPRECATED 배너 추가.

### 4.2 삽입된 배너

```markdown
> ⚠️ **DEPRECATED (v3 orchestrator) — DO NOT USE FOR NEW WORKFLOWS**
>
> - Archived at M7 swap (2026-04-19, JARFIS v4.0.0 release).
> - Maintained until **2026-05-03** for v3 rollback safety (2-week insurance window).
> - For new work: use `/jarfis:work` (v4).
> - Removal target: v4.0.9+ release (post-expiry).
> - `state.py` still emits v3 flat keys for this file's consumption — dual-shape compat until this file is removed.
```

### 4.3 의미

- **만료일**: 2026-05-03 — M7 swap (2026-04-19) 기준 2주 insurance window. 긴급 v3 rollback 가능성 보존.
- **슬래시 커맨드 생존**: `/jarfis:work-legacy` 명령어 유지 → 기존 v3 사용자가 긴급 상황에 사용 가능.
- **state.py dual-shape 호환**: v3 flat key 병존 emit 유지 — work-legacy.md 의 기대 state 형태 충족.

### 4.4 만료 이후 계획

**2026-05-03 이후 (v4.0.9+)**:
1. `work-legacy.md` 파일 삭제
2. `state.py` v3 dual-shape 제거 (cleanup item 단일 묶음)
3. `/jarfis:work-legacy` 슬래시 커맨드 사용 불가

**사용 제한 권장**: "긴급 rollback 시나리오" 로 한정. 일상 작업은 모두 `/jarfis:work` (v4) 사용.

### 4.5 rollback 시 흐름

```
1. 문제 상황 발생 (v4 버그 / v3에서만 동작하는 기능 필요 등)
2. 사용자가 `/jarfis:work-legacy` 명령 실행
3. v3 work.md 본문이 로드됨 (flat state 기대)
4. state.py dual-emit 덕분에 기존 v4 state도 v3 일부 key 읽기 가능
5. v3 로직으로 작업 진행
6. 작업 완료 후 → 사용자는 v4로 복귀
```

**경고**: 2026-05-03 이후에는 위 흐름이 작동하지 않는다. 미리 v4로 완전히 전환 권장.

---

## 5. v3 기능 → v4 매핑

| v3 기능 | v4 매핑 | 비고 |
|---------|---------|------|
| `/jarfis:work-continue` | `/jarfis:work` Resume Dispatch | 자동 감지 → AskUserQuestion |
| `jarfis-black` sub-agent | `verify.py` 4 subcommands | machine-verifiable output |
| `jarfis-white` agent | `jarfis-foreman.md` | tmux-scoped executor |
| PRD Ratchet | — (제거) | v4.0.1 producer 부재 |
| Fix Ratchet | legacy (정지) | jarfis-state-schema.md:204 |
| Phase 1 Discovery (단일) | Phase 1a (main) + Phase 1b (tmux) | F-03 |
| Phase 4 → Phase 5 직결 | Phase 4 → Phase 4.5 → Phase 5 | F-05 |
| Triage Type B | — (제거) | M7 — Type A/C/Resume만 |
| `work.md` (902 lines) | `work.md` (255 lines) + `prompts/phase*.md` | 외부화 (ADR-14) |
| `domain.py::compose()` LLM inference | `agent-composition.yaml` + `compose` CLI | 결정적 (ADR-17) |
| audit 없음 / `traces.jsonl` always-on | `audit.jsonl` (유지) / `trace.py` opt-in | ADR-3 Updated, ADR-20 |
| v3 state flat (`project_name`, `phase`) | v4 state nested (`sessionKey`, `phases.{N}`) | §2.1 |

---

## 6. Troubleshooting

### 6.1 v3 state 실수로 v4 연 경우

**증상**: `/jarfis:work` 실행 시 *"v3 workflow state detected"* 메시지 + halt.

**복구**:
1. 메시지대로 `/jarfis:work-legacy` 사용하여 v3에서 작업 완료
2. 또는 새 디렉토리에서 `/jarfis:work` 로 새 v4 워크플로우 시작 (v3 state 파일은 별도 보존)

**금지**: state 파일 수동 변조로 v4 스키마 맞추기 시도. 데이터 손실 위험 (workspace scope / baseCommit 등 v4 필수 필드 누락).

### 6.2 `v4 state detected` 인데 Resume 불가 (v4 내부 버그)

**증상**: v4 state 파일 존재하나 Resume 옵션 선택 후 에러.

**진단**:
- `.jarfis-state.json` JSON parse error → backup(`.compact-backups/state_*.json`) 에서 복원
- 최신 backup 선택 → `state.json` 으로 copy → 재시도

### 6.3 Ratchet 관련 에러 ("PRD ratchet producer 부재")

**증상**: v3.x 기간에 시작된 state에 `phases.1.ratchet.prd_score` 필드 있으나 v4.0.1 이후 producer 제거됨.

**조치**:
- v4.0.1+ 에서는 PRD Ratchet 자체가 제거됨 (v4.0.1 `verify.py` / `jarfis-state-schema.md` / `phase6.md workflow-metrics.tsv` 일괄 정리)
- 기존 state의 해당 필드는 **무시됨** (에러 안 남). 새 워크플로우에선 생성되지 않음

### 6.4 Phase 1 가이드 참조가 없음 ("phase1.md not found")

**증상**: v3 시대 문서 / 블로그가 `phase1.md` 참조.

**실체**: v4에서 `phase1.md` 파일 **없음**. Phase 1 은 다음으로 분할:
- **Phase 1a**: `work.md` 본문에 직접 포함 (main session)
- **Phase 1b**: `prompts/phase1b.md` (tmux foreman)

v3 자료를 v4에 적용하려면 Phase 1a/1b 분리를 반영하여 재해석.

### 6.5 tmux 세션 고아 발생

**증상**: 워크플로우 비정상 종료 후 `jf-*-phase*` tmux 세션이 남아있음. `tmux ls` 에서 확인.

**조치**:
```bash
/jarfis:sys-health
```

진단 + kill 제안. 자세한 배경은 [INFRASTRUCTURE.md §9.1 좀비 tmux 세션](./INFRASTRUCTURE.md#tradeoffs-zombie-tmux).

### 6.6 Dialectic 예상 위치에 없음 (workflow phase)

**증상**: v3 문서 기준으로 Phase 5 review에서 Advocate/Critic 대립을 기대했으나 발동 안 됨.

**실체**: v4에서 Dialectic은 **sys-* 명령 전용** (findings F-14, DESIGN ADR-13). 일반 `/jarfis:work` 워크플로우에서는 호출되지 않음.

**사용처**:
- `/jarfis:sys-implement` — 단일 시스템 변경
- `/jarfis:sys-upgrade` — learnings 반영
- `/jarfis:sys-distill` — 프롬프트 증류

### 6.7 skill 파일을 domains/ 경로에서 찾을 수 없음

**증상**: v3 스크립트/블로그가 `domains/web/skills/react.md` 참조.

**실체**: v4에서 skill이 `commands/jarfis/skills/` 로 평탄화됨 (v4.0.0 변경).

**신 경로**: `~/.claude/commands/jarfis/skills/react.md`

### 6.8 `work.md` 902 lines 가정이 깨짐 (external reference)

**증상**: 외부 자료 (jarfis-index.md v3, 블로그 포스트) 가 *"work.md ~890 lines"* 표현 사용.

**실체**: v4 `work.md` 는 **255 lines** (findings F-12, ~1/4 축소). prompt 외부화 (ADR-14) + verify.py 승격 (ADR-15) 덕분.

---

## 7. CHANGELOG Cross-reference

v4 주요 변경은 [CHANGELOG.md](./CHANGELOG.md) 에 기록. 본 문서와 CHANGELOG가 모순되면 **CHANGELOG 우선** (ground truth).

### 7.1 주요 v4 릴리스

- **v4.0.0** (2026-04-19) — tmux orchestration + Python verification 핵심 전환
- **v4.0.1** (2026-04-19) — M8 E2E 3라운드 핫픽스 + PRD Ratchet 전면 제거
- **v4.0.2** (2026-04-20) — 6 OBS/SPEC 핫픽스 (observability 정합)
- **v4.0.3** (2026-04-20) — UX-1 progress tracking, UX-2 Bash description, N-5/N-6 prompt docs
- **v4.0.4** (2026-04-20) — N-1 `--save-pane`, N-3 `agent-composition.yaml` audit header
- **v4.0.5** (2026-04-20) — N-2 trace subsystem opt-in (`JARFIS_TRACE`)

### 7.2 v4.0.6+ (계획)

- v4.0.9+ 에 `work-legacy.md` 삭제 + `state.py` v3 dual-shape 제거 (§4 참조)
- trace 파일 auto-cleanup 정책 (ADR-20 open question)
- workflow-metrics.tsv 대시보드 (aspiration path)

---

## 끝

v3 → v4 전환은 JARFIS 설계의 **첫 대규모 self-refactoring** 이다. 외부 평가 3라운드 (ChatGPT + Claude, 2026-04-19) 에서 공통 지적한 최대 약점 — *"시스템은 v4로 전진, 문서는 v3에 고정"* — 해소가 본 문서 + PHILOSOPHY v2 + DESIGN v2 의 공동 목표.

**원칙 drift 재발 방지**: 향후 새 원칙 추가/변경 시 본 §Principle Changes 섹션 동반 업데이트 필수 (DESIGN.md "문서 관리" 규칙 참조).

*v3 → v4 는 완료된 전환이 아니라 **연속선 상의 정착 중** 상태. 본 문서도 v4.0.5 시점 스냅샷이며, 후속 릴리스에서 필요 시 갱신.*
