<p align="center">
  <strong>JARFIS</strong><br>
  <em>Just Another Really Fantastic Integration System</em>
</p>

<p align="center">
  Claude Code 위에서 동작하는 IT 팀 워크플로우 오케스트레이션 시스템.<br>
  한 줄의 기획 요청이 PRD, 아키텍처, 구현, 리뷰, 회고까지 이어지는 End-to-End 파이프라인.
</p>

<p align="center">
  <a href="#quick-start">Quick Start</a> •
  <a href="#what-jarfis-does">What It Does</a> •
  <a href="#workflow">Workflow</a> •
  <a href="#commands">Commands</a> •
  <a href="#why-jarfis">Why JARFIS</a>
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

끝. JARFIS가 기획부터 구현, 리뷰까지 전체 워크플로우를 오케스트레이션합니다.

---

## What JARFIS Does

대부분의 Claude Code 확장 도구는 **개별 명령어 모음**이나 **에이전트 컬렉션**을 제공합니다. JARFIS는 다릅니다.

JARFIS는 **하나의 기획 요청을 완성된 코드와 문서로 변환하는 파이프라인**입니다.

```
"결제 모듈을 리팩토링해줘"
  ↓
PO가 역질문으로 요구사항을 정제하고
Architect가 실현가능성을 검증하고
Tech Lead가 태스크를 분해하고
BE/FE/DevOps 엔지니어가 구현하고
QA + Security가 리뷰하고
회고에서 학습을 축적합니다
  ↓
코드 + PRD + 아키텍처 문서 + 테스트 + 리뷰 리포트
```

**핵심 아이디어**: 사람이 하는 것처럼 — 기획 회의를 열고, 설계를 검토하고, 구현하고, 리뷰하는 전체 프로세스를 Claude Code 안에서 재현합니다.

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

| Agent | Role |
|-------|------|
| Product Owner | 역질문으로 요구사항 정제, Working Backwards PRD |
| Technical Architect | 실현가능성 검증, 시스템 설계, ADR |
| Tech Lead | 태스크 분해, 코드 리뷰 |
| Backend Engineer | 서버 구현 |
| Frontend Engineer | 클라이언트 구현 |
| DevOps/SRE Engineer | 인프라, CI/CD, 배포 |
| QA Engineer | 테스트 전략, 품질 검증 |
| Security Engineer | 보안 리뷰 |
| UX Designer | 화면 설계 |

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
jarfis/works/20260304/결제-리팩토링/
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
- **PreCompact Hook**: auto-compact 직전에 상태를 자동 백업
- **Phase 4 자동 커밋**: 구현 중 태스크 완료 시마다 `jarfis(BE-1):`, `jarfis(FE-2):` 형식으로 커밋
- **Resume**: 컨텍스트 유실 시 상태 파일에서 복원하여 중단 지점부터 재개

---

## Self-Evolution

JARFIS는 자기 자신을 개선하는 도구를 내장하고 있습니다.

| Command | What it does |
|---------|-------------|
| `/jarfis:upgrade` | 축적된 학습을 에이전트 프롬프트에 영구 반영 |
| `/jarfis:distill` | 프롬프트 토큰 효율을 측정하고 최적화 (중복 제거, 템플릿 외부화) |
| `/jarfis:implement` | JARFIS 자체의 명령어/구조를 수정 |

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

## Commands

| Command | Description |
|---------|-------------|
| `/jarfis` | 전체 명령어 목록 |
| `/jarfis:work` | 워크플로우 실행 (Phase T→6) |
| `/jarfis:meeting` | 기획 킥오프 미팅 (PO + TL 토론) |
| `/jarfis:project-init` | 프로젝트 프로필 생성 |
| `/jarfis:project-update` | 프로필 증분 갱신 |
| `/jarfis:upgrade` | 학습 관리 + 에이전트 적용 |
| `/jarfis:distill` | 프롬프트 증류 (토큰 최적화) |
| `/jarfis:implement` | 시스템 자체 수정 |
| `/jarfis:version` | 버전 확인 / 업데이트 |
| `/jarfis:health` | 좀비 프로세스 진단 |

---

## Installation

### Requirements

- [Claude Code](https://claude.ai/code) CLI
- Git
- jq (hook 등록에 필요)

### Install

```bash
git clone https://github.com/sana-lazystar/jarfis.git ~/repos/jarfis
cd ~/repos/jarfis
bash install.sh
```

`install.sh`는 다음을 수행합니다:
- `commands/`, `agents/`, `hooks/`, `scripts/` → `~/.claude/`로 복사
- PreCompact hook 등록 (settings.json)
- 기존 에이전트의 Learned Rules 보존 (덮어쓰기 시에도 학습 유지)
- 버전 스탬프 기록

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

## Architecture

```
~/.claude/
├── commands/
│   ├── jarfis.md                    # Entry point
│   └── jarfis/
│       ├── work.md                  # Workflow orchestration (Phase T→6)
│       ├── meeting.md               # Meeting facilitation
│       ├── prompts/                 # Externalized agent prompts (per Phase)
│       └── templates/               # Artifact templates
├── agents/jarfis/                   # 9 specialized agent role prompts
│   ├── senior-backend-engineer.md
│   ├── senior-frontend-engineer.md
│   ├── senior-devops-sre-engineer.md
│   ├── senior-product-owner.md
│   ├── tech-lead.md
│   ├── technical-architect.md
│   ├── senior-security-engineer.md
│   ├── senior-qa-engineer.md
│   └── senior-ux-designer.md
└── hooks/
    └── jarfis-pre-compact.sh        # Auto-backup before context compression
```

**설계 원칙**:
- **워크플로우 흐름**은 `work.md`에, **에이전트 프롬프트**는 `prompts/`에, **산출물 양식**은 `templates/`에 분리
- 에이전트 역할 프롬프트(`agents/`)와 워크플로우 프롬프트(`prompts/`)는 별개 — 역할은 고정, 태스크는 Phase마다 다름
- 학습 데이터는 로컬에만 존재 (Git repo에 포함되지 않음)

---

## Versioning

Semantic Versioning을 따릅니다.

| Change | Bump |
|--------|------|
| 프롬프트/템플릿 수정 | PATCH |
| 새 명령어/에이전트 추가 | MINOR |
| Phase 구조 변경 | MAJOR |

`/jarfis:implement`, `/jarfis:upgrade`, `/jarfis:distill` 실행 시 자동으로 버전이 범프되고 CHANGELOG에 기록됩니다.

---

## License

MIT
