# JARFIS Level Check — AI-Native Developer Maturity Assessment

> 리서치 기반 프레임워크(AIDMM + AI-MM SET + Anthropic Agentic Coding Report)로 AI-native 개발자 성숙도를 평가합니다.

---

## 실행 흐름

### Step 1: 자동 수집 (로컬 데스크탑 조사)

`claude-profile`의 `collect.py`를 실행하여 기본 데이터를 수집한다.

```bash
python3 ~/.claude/skills/claude-profile/scripts/collect.py 2>/dev/null || \
python3 ~/.claude/skills/claude_profile/scripts/collect.py 2>/dev/null
```

수집 항목 (JSON 출력):
- `usage.sessions` — 총 세션 수
- `usage.avg_prompts` — 세션당 평균 프롬프트
- `usage.bash`, `usage.read`, `usage.edit` — 도구 호출 수
- `tree.skills_total` — 스킬 수
- `tree.hooks_total` — 훅 수
- `tree.memory_count` — 메모리 수
- `skill_usage` — 스킬별 사용 횟수
- `mcp_usage` — MCP 서버별 호출 횟수
- `agents` — 에이전트 위임 횟수/종류
- `models` — 모델 사용 비율
- `permissions` — 권한 모드

**collect.py 실패 시**: 사용자에게 안내하고 모든 항목을 Step 2에서 수동 입력으로 대체.

추가로 직접 조사:
```bash
# 커스텀 에이전트 수
find ~/.claude/agents/ -name "*.md" 2>/dev/null | wc -l

# 커맨드(스킬) 파일 수
find ~/.claude/commands/ -name "*.md" -type f 2>/dev/null | wc -l

# 프로젝트별 CLAUDE.md 총 줄 수
find ~/. -name "CLAUDE.md" -not -path "*node_modules*" -not -path "*.git*" -exec wc -l {} + 2>/dev/null | tail -1

# hooks 상세
cat ~/.claude/settings.json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); hooks=d.get('hooks',{}); print(f'events: {len(hooks)}, hooks: {sum(len(v) for v in hooks.values())}')" 2>/dev/null
```

자동 수집 결과를 `$AUTO_DATA`에 저장하고, 사용자에게 요약을 보여준다:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Level Check — 자동 수집 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 세션: {N}개 | 평균 프롬프트: {N}/세션
🔧 스킬: {N}개 | 훅: {N}개 | MCP: {N}개
🤖 에이전트: {N}종 ({N}회 위임)
🧠 메모리: {N}개
📁 CLAUDE.md: {N}줄 (전체 프로젝트 합산)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

→ Step 2로 진행

### Step 2: 수동 입력 (인터뷰)

자동 수집으로 파악 불가능한 항목을 AskUserQuestion으로 질문한다. **한 번에 모든 질문을 제시**하여 사용자가 한꺼번에 답변할 수 있게 한다.

```
아래 7개 질문에 답해주세요. 번호만 적고 간단히 답하셔도 됩니다.

1. AI를 SDLC 어느 단계까지 활용하시나요?
   a) 코딩만  b) 코딩+테스트  c) 기획~테스트  d) 기획~배포  e) 기획~모니터링 전체

2. 커스텀 에이전트를 직접 설계하고 운영한 경험이 있나요?
   a) 없음  b) 1~3개  c) 4~10개  d) 10개+  e) 오케스트레이션 시스템까지 구축

3. AI 에이전트가 자율적으로 작업하도록 위임하는 수준은?
   a) 위임 안 함  b) 단일 작업 위임  c) 멀티스텝 위임  d) 병렬 에이전트  e) End-to-End 자율

4. AI 출력의 품질 검증을 어떻게 하시나요? (복수 선택 가능)
   a) 눈으로 확인  b) 자동 테스트  c) CI/CD 연동  d) 변증법 리뷰 (찬반)  e) 자동 학습 축적

5. 세션 간 지식을 어떻게 유지하시나요? (복수 선택 가능)
   a) 유지 안 함  b) 메모리/CLAUDE.md  c) 도메인 인코딩(스킬/템플릿)  d) Wiki/문서화 시스템  e) 자동 회고+학습 루프

6. AI가 AI를 개선하는 자기 수정 루프가 있나요?
   a) 없음  b) 프롬프트 수동 개선  c) AI로 프롬프트 최적화  d) AI가 자체 시스템을 수정  e) 자율 진화 루프

7. 팀/조직 수준에서 AI-native 프로세스를 운영하시나요?
   a) 개인만  b) 팀 내 공유  c) 팀 표준으로 운영  d) 조직 전체 표준  e) 비엔지니어도 사용
```

→ Step 3으로 진행

### Step 3: 점수 산출

7개 차원별 10점 만점으로 평가한다. **자동 수집 데이터 + 수동 입력 답변**을 종합하여 점수를 산출한다.

#### 평가 프레임워크

| 차원 | 가중치 | 평가 기준 |
|------|--------|----------|
| **D1. AI Literacy & Tool Adoption** | 10% | 모델 선택 전략, 도구 수, 사용 빈도, bypass 비율, 세션 깊이 |
| **D2. Workflow & SDLC Integration** | 20% | 인터뷰 Q1 + 자동 수집(스킬 사용 패턴, SDLC 커버리지) |
| **D3. Agent Design & Orchestration** | 25% | 인터뷰 Q2+Q3 + 자동 수집(에이전트 수/종류/위임 횟수) |
| **D4. Tooling Infrastructure** | 15% | 자동 수집(MCP, 훅, 스킬, 커맨드, CLAUDE.md 줄 수) |
| **D5. Quality & Safety Governance** | 15% | 인터뷰 Q4 + 자동 수집(훅 중 safety/quality 관련, 테스트 에이전트) |
| **D6. Knowledge Persistence** | 10% | 인터뷰 Q5 + 자동 수집(메모리 수, 메모리 유형 분포) |
| **D7. Meta-Engineering** | 5% | 인터뷰 Q6 + 자동 수집(sys-implement 사용 횟수, 자기 수정 패턴) |

#### 채점 가이드 (각 차원 0~10점)

**D1. AI Literacy & Tool Adoption**
| 점수 | 기준 |
|------|------|
| 0~2 | AI 도구 미사용 또는 기본 ChatGPT만 |
| 3~4 | Copilot/Claude 기본 사용, 세션 <10 |
| 5~6 | 100+ 세션, MCP 2~3개, 프롬프트 <20/세션 |
| 7~8 | 100+ 세션, MCP 5+개, 프롬프트 30+/세션, 모델 전략적 선택 |
| 9~10 | 200+ 세션, MCP 7+개, 프롬프트 50+/세션, bypass 90%+, 최상위 모델 사용 |

**D2. Workflow & SDLC Integration**
| 점수 | 기준 |
|------|------|
| 0~2 | AI 미사용 또는 코딩 보조만 |
| 3~4 | 코딩+테스트에 AI 활용 |
| 5~6 | 기획~테스트까지 AI 활용, 일부 자동화 |
| 7~8 | 기획~배포까지 AI 통합, SDLC 파이프라인 구축 |
| 9~10 | 전체 SDLC를 AI 워크플로우로 운영, 선언적 프로세스 정의 |

**D3. Agent Design & Orchestration**
| 점수 | 기준 |
|------|------|
| 0~2 | 에이전트 미사용 |
| 3~4 | 기본 에이전트 활용 (general-purpose) |
| 5~6 | 커스텀 에이전트 1~3개, 단일 작업 위임 |
| 7~8 | 커스텀 에이전트 4~10개, 병렬 위임, 페르소나 설계 |
| 9~10 | 10개+ 에이전트, 오케스트레이션 시스템, 변증법 리뷰, End-to-End 자율 |

**D4. Tooling Infrastructure**
| 점수 | 기준 |
|------|------|
| 0~2 | 기본 설정만 |
| 3~4 | CLAUDE.md 작성, 기본 MCP 연동 |
| 5~6 | 커스텀 스킬 제작, 훅 3+개, MCP 3+개 |
| 7~8 | 도메인 스킬, 템플릿 시스템, CI 연동, CLAUDE.md 500줄+ |
| 9~10 | 풀스택 인프라 (스킬 30+, 훅 5+, MCP 7+, 도메인 팩, 커맨드 50+) |

**D5. Quality & Safety Governance**
| 점수 | 기준 |
|------|------|
| 0~2 | 검증 없이 AI 출력 수용 |
| 3~4 | 수동 리뷰만 |
| 5~6 | 자동 테스트 + CI 연동 |
| 7~8 | safety 훅, quality gate, 구조화된 검증 루프 |
| 9~10 | 변증법 리뷰(찬반), 자동 학습 축적, 래칫 수렴, 20+ 라운드 검증 |

**D6. Knowledge Persistence**
| 점수 | 기준 |
|------|------|
| 0~2 | 세션 간 지식 유지 없음 |
| 3~4 | CLAUDE.md만 사용 |
| 5~6 | 메모리 10+개, 프로젝트별 CLAUDE.md |
| 7~8 | 도메인 인코딩(스킬/템플릿), 문서화 시스템 |
| 9~10 | Wiki 시스템, 자동 회고+학습 루프, 메모리 25+개, 크로스 세션 연속성 |

**D7. Meta-Engineering**
| 점수 | 기준 |
|------|------|
| 0~2 | AI를 도구로만 사용 |
| 3~4 | 프롬프트를 수동으로 개선 |
| 5~6 | AI로 프롬프트/설정 최적화 (distill 등) |
| 7~8 | AI가 자체 시스템을 수정 (sys-implement) |
| 9~10 | 자율 진화 루프, AI가 AI를 위한 시스템을 만드는 재귀 구조 |

#### 가중 합산

```
총점 = D1×0.10 + D2×0.20 + D3×0.25 + D4×0.15 + D5×0.15 + D6×0.10 + D7×0.05
```

조직 보너스 (인터뷰 Q7):
- a) 개인만 → +0.0
- b) 팀 내 공유 → +0.1
- c) 팀 표준 → +0.2
- d) 조직 전체 → +0.3
- e) 비엔지니어도 사용 → +0.5

**최종 점수 = min(총점 + 조직 보너스, 10.0)**

→ Step 4로 진행

### Step 4: 결과 출력

#### 등급 체계

| Level | 명칭 | 점수 범위 | AIDMM 매핑 | AI-MM SET 매핑 |
|-------|------|----------|-----------|--------------|
| Lv.0 | Human-Only | 0 ~ 1.0 | Level 0 | - |
| Lv.1 | AI-Curious | 1.0 ~ 3.0 | Level 0~1 | Exploratory |
| Lv.2 | AI-Assisted | 3.0 ~ 5.0 | Level 1 | Applied |
| Lv.3 | AI-Collaborative | 5.0 ~ 6.5 | Level 2 | Standardized |
| Lv.4 | AI-Delegated | 6.5 ~ 8.0 | Level 3 | Strategic |
| Lv.5 | AI-Orchestrator | 8.0 ~ 9.5 | Level 3~4 | Strategic+ |
| Lv.6 | AI-Native | 9.5 ~ 10.0 | Level 4 | Transformational |

#### 출력 형식

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Level Check — AI-Native Maturity
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Lv.{N} {명칭}    {점수}/10
  {프로그레스 바 20칸}  {퍼센트}%

  ┌─ 차원별 점수 ──────────────────────────────┐
  │ D1 Tool Adoption      {점수}/10  {바}      │
  │ D2 SDLC Integration   {점수}/10  {바}      │
  │ D3 Agent Orchestration {점수}/10  {바}      │
  │ D4 Tooling Infra       {점수}/10  {바}      │
  │ D5 Quality Governance  {점수}/10  {바}      │
  │ D6 Knowledge Persist   {점수}/10  {바}      │
  │ D7 Meta-Engineering    {점수}/10  {바}      │
  └─────────────────────────────────────────────┘

  조직 보너스: +{N} ({수준})

  📊 자동 수집 요약:
     세션 {N} | 에이전트 {N}종 {N}회 | MCP {N}개
     스킬 {N} | 훅 {N} | 메모리 {N}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  참조: AIDMM (DEV Community) · AI-MM SET (Gigacore)
  참조: Anthropic 2026 Agentic Coding Trends Report
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

#### 다음 레벨 가이드

현재 레벨에서 다음 레벨로 올라가기 위한 구체적 제안을 1~3개 제시한다:

```
  🎯 Lv.{N+1} {다음 명칭}으로 가려면:
     1. {구체적 제안}
     2. {구체적 제안}
     3. {구체적 제안}
```

예시:
- Lv.2→3: "CLAUDE.md를 프로젝트에 추가하고, MCP 서버 2개 이상 연동해보세요"
- Lv.3→4: "커스텀 에이전트를 만들어 반복 작업을 위임해보세요"
- Lv.4→5: "멀티에이전트 오케스트레이션으로 SDLC 파이프라인을 구축해보세요"
- Lv.5→6: "팀/조직 전체에 AI-native 프로세스를 표준화하세요"
