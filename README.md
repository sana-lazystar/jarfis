<p align="center">
  <strong>JARFIS</strong><br>
  <em>Just A Rather Foolish Integration System</em>
</p>

<p align="center">
  완벽한 시스템은 아닙니다.<br>
  더 나은 시스템이 되는 방향을 지향합니다.<br>
  명령어 한번에 IT 팀을 움직일 수 있는, 누구나를 위한 IT 팀 오케스트레이션
</p>

<p align="center">
  <sub>직접 써보면서 만들었고, 지금도 사용하면서 개선중입니다<br />by sanhalee</sub>
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#what-jarfis-does">What It Does</a> •
  <a href="#workflow">Workflow</a> •
  <a href="#commands">Commands</a> •
  <a href="./PHILOSOPHY.md">Philosophy</a>
</p>

---

## Quick Start

```bash
git clone https://github.com/sana-lazystar/jarfis.git ~/repos/jarfis
cd ~/repos/jarfis
bash install.sh
```

Claude Code를 열고:

```
/jarfis:work 게시판 CRUD + 댓글 기능 구현
```

JARFIS가 기획부터 구현, 리뷰까지 전체 워크플로우를 오케스트레이션하고, 더 나은 오케스트레이션을 위해 기록합니다.

---

## What JARFIS Does

Claude Code에 슬래시 명령어 하나를 치면, 진짜 IT 팀이 일하는 것과 같은 일이 벌어집니다.

PO가 "이거 정말 필요한 거 맞아?" 하고 역질문을 쏟아내고, Architect가 "기존 시스템에 이렇게 얹으면 됩니다" 하고 설계를 그리고, Tech Lead가 태스크를 쪼개서 나누면, BE·FE·DevOps 엔지니어가 각자 구현에 들어갑니다. 다 끝나면 QA와 Security가 엄격한 리뷰를해서 탄탄하게 만들고, 마지막으로 회고에서 "다음엔 이렇게 하자"를 기록합니다.

이게 전부 **하나의 명령어 안에서** 일어납니다.

```
/jarfis:work 결제 모듈 리팩토링
  ↓
기획 → 설계 → 구현 → 리뷰 → 회고
  ↓
코드 + PRD + 아키텍처 문서 + 리뷰 리포트
```

대부분의 Claude Code 확장 도구는 개별 명령어 모음이나 에이전트 컬렉션입니다. JARFIS는 그것들을 **하나의 파이프라인으로 엮어서**, 기획 요청이 들어오면 완성된 코드와 문서가 나오게 만드는 시스템입니다.

---

## Workflow

### The Full Pipeline

```
/jarfis:work [기획 내용]
  │
  ├─ Phase T: Triage ─────────── 요청 분류 → 워크플로우 필요 여부 판단
  ├─ Phase 0: Pre-flight ─────── Git 동기화 + 브랜치 생성 + 학습 로드
  ├─ Phase 1: Discovery ──────── PO 역질문 → Working Backwards → PRD + 실현가능성
  ├─ Phase 2: Architecture ────── 영향 분석 → 설계 + ADR → API 명세 → 태스크 분해
  ├─ Phase 3: UX Design ──────── (UI 필요 시만) 화면 설계
  ├─ Phase 4: Implementation ──── BE / FE / DevOps 병렬 구현 + 자동 커밋
  ├─ Phase 4.5: Ops Readiness ─── 배포 전략 + 롤백 계획
  ├─ Phase 5: Review & QA ────── API Contract 검증 + TL/QA/Security 병렬 리뷰
  └─ Phase 6: Retrospective ───── 학습 축적 → 다음 워크플로우에 반영
```

각 Phase에서 9개의 전문 에이전트가 자기 역할에 맞게 투입됩니다:

| Agent               | Role                                            |
| ------------------- | ----------------------------------------------- |
| Product Owner       | 역질문으로 요구사항 정제, Working Backwards PRD |
| Technical Architect | 실현가능성 검증, 시스템 설계, ADR               |
| Tech Lead           | 태스크 분해, 코드 리뷰                          |
| Backend Engineer    | 서버 구현                                       |
| Frontend Engineer   | 클라이언트 구현                                 |
| DevOps/SRE Engineer | 인프라, CI/CD, 배포                             |
| QA Engineer         | 테스트 전략, 품질 검증                          |
| Security Engineer   | 보안 리뷰                                       |
| UX Designer         | 화면 설계                                       |

### Meeting Mode

코딩 전에 기획부터 잡고 싶을 때:

```
/jarfis:meeting 실시간 채팅 기능 도입 검토
```

PO와 Tech Lead가 자유 토론을 벌이고, 필요하면 전문가(Security, DevOps 등)를 소환합니다.
토론 결과는 회의록 + 의사결정표 + 기술 조사 보고서로 정리됩니다.
나중에 `/jarfis:work`를 실행하면 이 미팅 결과를 자동으로 감지하여 활용합니다.

---

## Artifacts

하나의 워크플로우가 만들어내는 산출물:

```
.local/workspace/works/20260311-feat-결제-리팩토링/
├── .jarfis-state.json       # 워크플로우 상태 (중단 시 재개용)
├── press-release.md          # Working Backwards 프레스 릴리스
├── prd.md                    # 요구사항 정의서
├── impact-analysis.md        # 기존 코드 영향 분석
├── architecture.md           # 아키텍처 설계 + ADR
├── api-spec.md               # API 명세 (BE-FE 계약)
├── tasks.md                  # 태스크 분해표
├── test-strategy.md          # 테스트 전략
├── ux-spec.md                # UX 설계 (UI 있는 경우)
├── deployment-plan.md        # 배포 전략 + 롤백
├── review.md                 # TL/QA/Security 리뷰
└── retrospective.md          # 회고 + 학습
```

모든 산출물이 날짜 + 작업명으로 정리되어, 프로젝트의 의사결정 기록이 자연스럽게 쌓입니다.

---

## Learning System

JARFIS는 **매 워크플로우에서 학습하고, 다음 워크플로우에 적용**합니다.

```
Phase 6 회고
  → "Playwright로 네트워크 쓰로틀링 테스트 시 CDP가 필요하다"
  → jarfis-learnings.md에 기록

다음 /jarfis:work 실행
  → Phase 0에서 학습 로드
  → QA 에이전트가 해당 지식을 활용

/jarfis:upgrade
  → 학습 항목을 에이전트 프롬프트에 영구 적용
  → QA 에이전트가 항상 CDP 기반 테스트를 고려
```

**두 가지 레벨의 학습**:

- **전역 학습** (`jarfis-learnings.md`): 모든 프로젝트에 적용되는 에이전트 힌트 + 워크플로우 패턴
- **프로젝트 학습** (`context.md`): 특정 코드베이스에 대한 맥락 (컨벤션, 기술 스택, 히스토리)

---

## Context Resilience

Claude Code의 auto-compact로 컨텍스트가 압축되어도 워크플로우가 끊기지 않습니다.

- **`.jarfis-state.json`**: 현재 Phase, 완료된 태스크, 체크포인트를 실시간 기록
- **4개 Hook 인프라**:
  - **PreCompact**: auto-compact 직전에 워크플로우 상태를 자동 백업
  - **Safety (PreToolUse)**: 위험한 Bash 명령어 사전 차단
  - **Quality Gate (PostToolUse)**: Edit/Write 후 코드 품질 자동 검증
  - **Session Start**: 세션 시작 시 이전 컨텍스트 자동 복원
- **Phase 4 자동 커밋**: 구현 중 태스크 완료 시마다 `jarfis(BE-1):`, `jarfis(FE-2):` 형식으로 커밋
- **Resume**: 컨텍스트 유실 시 상태 파일에서 복원하여 중단 지점부터 재개

---

## Self-Evolution

JARFIS는 자기 자신을 개선하는 도구를 내장하고 있습니다.

| Command             | What it does                                                    |
| ------------------- | --------------------------------------------------------------- |
| `/jarfis:upgrade`   | 축적된 학습을 에이전트 프롬프트에 영구 반영                     |
| `/jarfis:distill`   | 프롬프트 토큰 효율을 측정하고 최적화 (중복 제거, 템플릿 외부화) |
| `/jarfis:implement` | JARFIS 자체의 명령어/구조를 수정                                |

프롬프트를 사용할수록 학습이 쌓이고, 학습이 프롬프트에 반영되고, 프롬프트가 다시 최적화됩니다.

---

## Project Awareness

JARFIS는 프로젝트의 컨텍스트를 이해하고 활용합니다.

```
/jarfis:project-init
```

프로젝트의 기술 스택, 디렉토리 구조, 코딩 컨벤션, 배포 환경을 분석하여 프로필을 생성합니다. 이후 워크플로우에서 에이전트들이 이 프로필을 참조하여 프로젝트에 맞는 결정을 내립니다.

```
/jarfis:project-update
```

`git diff` 기반으로 변경된 부분만 증분 갱신합니다.

---

<!-- JARFIS-COMMANDS-START -->
## Commands

| Command                  | Description                                            |
| ------------------------ | ------------------------------------------------------ |
| `/jarfis:meeting`        | 기획 킥오프 미팅 (PO/TL 자유 토론 → 산출물 생성)                       |
| `/jarfis:work`           | 기획→설계→구현→리뷰 전체 워크플로우                                   |
| `/jarfis:project-init`   | 프로젝트 분석 → `./.jarfis/project-profile.md` 생성            |
| `/jarfis:project-update` | 기존 프로필 증분 갱신 (commit hash 기반, 날짜 fallback)             |
| `/jarfis:upgrade`        | 학습항목 CRUD + 에이전트/워크플로우 프롬프트에 적용                        |
| `/jarfis:health`         | 좀비 Claude 프로세스 진단/정리                                   |
| `/jarfis:distill`        | 프롬프트 증류 — 토큰 효율 분석/최적화                                 |
| `/jarfis:continue`       | 완료된 워크플로우 후속 작업 (Fix/Extend 모드, --workflow/--mode 플래그) |
| `/jarfis:implement`      | JARFIS 시스템 자체 수정/기능 추가 + 버전 범프                         |
| `/jarfis:version`        | 버전 확인/업데이트/특정 버전 설치                                    |
<!-- JARFIS-COMMANDS-END -->

---

## Installation

### Requirements

- [Claude Code](https://claude.ai/code) CLI
- Git
- Python 3 (상태 관리, CLI, Hook 인프라)
- jq (선택 — 없으면 hook 등록을 수동으로 설정)

### Install

```bash
git clone https://github.com/sana-lazystar/jarfis.git ~/repos/jarfis
cd ~/repos/jarfis
bash install.sh
```

`install.sh`는 다음을 수행합니다:

- `commands/`, `agents/`, `hooks/`, `scripts/` → `~/.claude/`로 복사
- Python 패키지(`scripts/jarfis/`, `jarfis_cli.py`) 설치
- `statusline-command.sh` 설치
- 워크스페이스와 학습 데이터를 `.local/`로 통합 (기존 `~/.jarfis/`에서 자동 마이그레이션)
- 4개 Hook 등록 (settings.json): PreCompact, PreToolUse(Safety), PostToolUse(Quality Gate), SessionStart
- statusLine 등록 (settings.json)
- 기존 에이전트의 Learned Rules 보존 (덮어쓰기 시에도 학습 유지)
- 버전 스탬프 기록

### Data Directory

런타임 데이터는 repo 내 `.local/` 디렉토리에 저장됩니다 (`.gitignore`에 의해 추적 제외):

```
~/repos/jarfis/.local/
├── workspace/
│   ├── works/        # 워크플로우 산출물
│   └── meetings/     # 미팅 산출물
└── jarfis-learnings.md  # 학습 항목
```

### Update

```bash
cd ~/repos/jarfis && git pull && bash install.sh
```

또는 Claude Code 안에서:

```
/jarfis:version
```

### Install Specific Version

```bash
bash install.sh --version 1.0.0
```

---

<!-- JARFIS-ARCHITECTURE-START -->
## Architecture

```
~/.claude/commands/
├── jarfis.md                      # 메인 도우미 — 명령어 목록 출력
└── jarfis/
    ├── jarfis-index.md            # 이 파일 — JARFIS 시스템 현황
    ├── implement.md               # JARFIS 자체 수정 명령어 + Dialectic Review 게이트
    ├── meeting.md                 # 기획 킥오프 미팅 (PO/TL 토론, 188줄)
    ├── work.md                    # 핵심: 워크플로우 오케스트레이션
    ├── project-init.md            # 프로젝트 프로필 생성
    ├── project-update.md          # 프로필 증분 갱신 — commit hash 기반 변경 감지
    ├── upgrade.md                 # 학습 항목 관리 + Scope 분류 + Dialectic Review
    ├── distill.md                 # 프롬프트 증류 + Dialectic Review 게이트
    ├── version.md                 # 버전 관리/업데이트
    ├── continue.md                # 완료된 워크플로우 후속 작업 — Fix/Extend 모드 + Agent Model Routing
    ├── health.md                  # 좀비 프로세스 진단
    ├── prompts/                   # 외부화된 에이전트 프롬프트 (distill이 생성)
    │   ├── phase1.md              # Phase 1 Discovery 프롬프트
    │   ├── phase2.md              # Phase 2&3 Architecture/UX 프롬프트
    │   ├── phase4.md              # Phase 4 Implementation 프롬프트 + Handoff 주입
    │   ├── phase4-5.md            # Phase 4.5 Operational Readiness 프롬프트
    │   ├── phase5.md              # Phase 5 Review & QA 프롬프트 + Learning Candidate 감지
    │   ├── phase6.md              # Phase 6 Retrospective 프롬프트 + Suggested Learnings
    │   └── continue-extend.md    # Continue Extend 모드 PO/Architect/TL 프롬프트
    └── templates/                 # 외부화된 산출물 템플릿 (distill이 생성)
        ├── jarfis-state-schema.md # .jarfis-state.json 구조 스키마 + handoff 필드
        ├── learnings.md           # jarfis-learnings.md 템플릿 — Universal/Project-Specific 구조
        ├── project-context.md     # project-context.md 템플릿
        ├── project-profile.md     # 프로젝트 프로필 템플릿
        └── meeting-artifacts.md   # 미팅 산출물 4종 템플릿

~/.claude/agents/jarfis/           # JARFIS 에이전트 프롬프트 (work.md에서 참조)
├── jarfis-advocate.md             # Dialectic Review — 변경 옹호 에이전트
├── jarfis-critic.md               # Dialectic Review — 변경 비판 에이전트
├── senior-backend-engineer.md     # BE 구현 에이전트
├── senior-frontend-engineer.md    # FE 구현 에이전트
├── senior-devops-sre-engineer.md  # DevOps 구현 에이전트
├── senior-product-owner.md        # PO 역질문/PRD 에이전트
├── tech-lead.md                   # TL 태스크 분해 에이전트
├── technical-architect.md         # 아키텍처 설계 에이전트
├── senior-security-engineer.md    # 보안 리뷰 에이전트
├── senior-qa-engineer.md          # QA 리뷰 에이전트
└── senior-ux-designer.md          # UX 리뷰 에이전트
```

**설계 원칙**:

- **워크플로우 흐름**은 `work.md`에, **에이전트 프롬프트**는 `prompts/`에, **산출물 양식**은 `templates/`에 분리
- 에이전트 역할 프롬프트(`agents/`)와 워크플로우 프롬프트(`prompts/`)는 별개 — 역할은 고정, 태스크는 Phase마다 다름
- 학습 데이터는 로컬에만 존재 (Git repo에 포함되지 않음)
<!-- JARFIS-ARCHITECTURE-END -->

---

## Versioning

Semantic Versioning을 따릅니다.

| Change                  | Bump  |
| ----------------------- | ----- |
| 프롬프트/템플릿 수정    | PATCH |
| 새 명령어/에이전트 추가 | MINOR |
| Phase 구조 변경         | MAJOR |

`/jarfis:implement`, `/jarfis:upgrade`, `/jarfis:distill` 실행 시 자동으로 버전이 범프되고 CHANGELOG에 기록됩니다.

---

<!-- JARFIS-LATEST-CHANGES-START -->
## Latest Changes

> 전체 변경 이력은 [CHANGELOG.md](./CHANGELOG.md)를 참조하세요.

## [1.9.5] - 2026-03-12

- implement: project-update 변경 감지를 commit hash 기반으로 개선
<!-- JARFIS-LATEST-CHANGES-END -->

---

## License

[MIT](./LICENSE)
