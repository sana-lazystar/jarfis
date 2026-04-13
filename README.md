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
  <a href="#core-concepts">Core Concepts</a> •
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

PO가 "이거 정말 필요한 거 맞아?" 하고 역질문을 쏟아내고, Architect가 "기존 시스템에 이렇게 얹으면 됩니다" 하고 설계를 그리고, Tech Lead가 태스크를 쪼개서 나누면, BE/FE/DevOps 엔지니어가 각자 구현에 들어갑니다. 다 끝나면 QA와 Security가 엄격한 리뷰를 해서 탄탄하게 만들고, 마지막으로 회고에서 "다음엔 이렇게 하자"를 기록합니다.

이게 전부 **하나의 명령어 안에서** 일어납니다.

```mermaid
flowchart TD
    A["/jarfis:work 결제 모듈 리팩토링"] --> B["기획 → 설계 → 구현 → 리뷰 → 회고"]
    B --> C["코드 + PRD + 아키텍처 문서 + 리뷰 리포트"]

    style A fill:#1a1a2e,color:#e0e0e0,stroke:#4a4a6a
    style B fill:#16213e,color:#e0e0e0,stroke:#4a4a6a
    style C fill:#533483,color:#e0e0e0,stroke:#4a4a6a
```

대부분의 Claude Code 확장 도구는 개별 명령어 모음이나 에이전트 컬렉션입니다. JARFIS는 그것들을 **하나의 파이프라인으로 엮어서**, 기획 요청이 들어오면 완성된 코드와 문서가 나오게 만드는 시스템입니다.

---

## Core Concepts

### Agent = Persona + Skills + Rules

JARFIS v3.0의 에이전트는 세 요소로 동적 합성됩니다:

| 요소 | 역할 | 예시 |
|------|------|------|
| **Persona** | 역할별 인지 프레임워크 (~1500 토큰) | `product-owner` — 비즈니스 가치, JTBD, 스코프 판단 |
| **Skills** | 기술 전문성 (가변, 예산 2500 토큰) | `react`, `nodejs`, `tauri-backend` |
| **Rules** | 학습 + 프로젝트 맥락 | `jarfis-learnings.md`, `project-context.md` |

Persona는 **어떤 관점으로 사고하는가**를, Skills는 **어떤 기술을 아는가**를, Rules는 **이 프로젝트에서 무엇을 기억하는가**를 결정합니다. 이 세 요소가 Phase마다 조합되어 에이전트가 만들어집니다.

### Domain Pack

프로젝트의 기술 스택에 따라 에이전트에게 다른 Skills가 부여됩니다:

| Domain | Skills | 자동 감지 |
|--------|--------|-----------|
| **Web** | react, vue, browser, nodejs, express, biome-lint | `package.json`, `tsconfig.json` |
| **Desktop (Tauri)** | rust, tauri-backend, tauri-webview, cargo-clippy | `tauri.conf.json`, `Cargo.toml` |

Domain은 프로젝트 루트의 파일(`package.json`, `tauri.conf.json` 등)을 기반으로 자동 감지됩니다. 각 Domain Pack은 `_schema.yaml` 규격을 따르며, Skills 디렉토리에 기술별 전문 프롬프트가 분리되어 있습니다.

---

## Workflow

### The Full Pipeline

```mermaid
flowchart TD
    T["Phase T: Triage\n요청 분류"] --> P0["Phase 0: Pre-flight\nGit 동기화 + 학습 로드"]
    P0 --> P1["Phase 1: Discovery\nPO 역질문 → PRD"]
    P1 --> G1{{"🔒 Gate 1\nPRD 승인"}}
    G1 --> P2["Phase 2: Architecture\n설계 + ADR + 태스크 분해"]
    G1 --> P3["Phase 3: UX Design\n(UI 필요 시만)"]
    P2 --> G2{{"🔒 Gate 2\n설계 승인"}}
    P3 --> G2
    G2 --> P4["Phase 4: Implementation\nBE/FE/DevOps 병렬 구현\n+ TDD Ratchet"]
    P4 --> P45["Phase 4.5: Ops Readiness\n배포 전략 + 롤백"]
    P45 --> P5["Phase 5: Review & QA\nTL/QA/Security 병렬 리뷰"]
    P5 --> G3{{"🔒 Gate 3\n리뷰 승인"}}
    G3 --> P6["Phase 6: Retrospective\n학습 축적 → 다음 반영"]

    style T fill:#1a1a2e,color:#e0e0e0,stroke:#4a4a6a
    style P0 fill:#16213e,color:#e0e0e0,stroke:#4a4a6a
    style P1 fill:#16213e,color:#e0e0e0,stroke:#4a4a6a
    style P2 fill:#0f3460,color:#e0e0e0,stroke:#4a4a6a
    style P3 fill:#0f3460,color:#e0e0e0,stroke:#4a4a6a
    style P4 fill:#533483,color:#e0e0e0,stroke:#4a4a6a
    style P45 fill:#533483,color:#e0e0e0,stroke:#4a4a6a
    style P5 fill:#0f3460,color:#e0e0e0,stroke:#4a4a6a
    style P6 fill:#1a1a2e,color:#e0e0e0,stroke:#4a4a6a
    style G1 fill:#e94560,color:#e0e0e0,stroke:#4a4a6a
    style G2 fill:#e94560,color:#e0e0e0,stroke:#4a4a6a
    style G3 fill:#e94560,color:#e0e0e0,stroke:#4a4a6a
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

### 3가지 모드

| 모드 | 명령어 | 용도 |
|------|--------|------|
| **Full Workflow** | `/jarfis:work` | 기획부터 회고까지 전체 파이프라인 |
| **Meeting** | `/jarfis:work-meeting` | 코딩 전 기획 토론 (PO/TL 자유 토론 → 산출물) |
| **Continue** | `/jarfis:work-continue` | 완료된 워크플로우 후속 작업 (Fix/Extend) |

Meeting 모드에서 PO와 Tech Lead가 자유 토론을 벌이고, 필요하면 전문가(Security, DevOps 등)를 소환합니다. 토론 결과는 회의록 + 의사결정표 + 기술 조사 보고서로 정리되며, 나중에 `/jarfis:work`를 실행하면 이 미팅 결과를 자동으로 감지하여 활용합니다.

---

## Artifacts

하나의 워크플로우가 만들어내는 산출물:

```
.personal/orgs/{org}/works/20260311-feat-결제-리팩토링/
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

## Key Features

### Learning System

JARFIS는 **매 워크플로우에서 학습하고, 다음 워크플로우에 적용**합니다.

```mermaid
flowchart LR
    A["Phase 6 회고\n학습 발견"] --> B["learnings.md\n기록"]
    B --> C["다음 /jarfis:work\nPhase 0에서 로드"]
    C --> D["에이전트 활용"]
    D --> E["/jarfis:sys-upgrade\n영구 적용"]

    style A fill:#1a1a2e,color:#e0e0e0,stroke:#4a4a6a
    style B fill:#16213e,color:#e0e0e0,stroke:#4a4a6a
    style C fill:#0f3460,color:#e0e0e0,stroke:#4a4a6a
    style D fill:#533483,color:#e0e0e0,stroke:#4a4a6a
    style E fill:#e94560,color:#e0e0e0,stroke:#4a4a6a
```

**두 가지 레벨의 학습**:

- **전역 학습** (`$JARFIS_ORG_DIR/learnings.md`): 모든 프로젝트에 적용되는 에이전트 힌트 + 워크플로우 패턴
- **프로젝트 학습** (`project-context.md`): 특정 코드베이스에 대한 맥락 (컨벤션, 기술 스택, 히스토리)

### Context Resilience

Claude Code의 auto-compact로 컨텍스트가 압축되어도 워크플로우가 끊기지 않습니다.

- **`.jarfis-state.json`**: 현재 Phase, 완료된 태스크, 체크포인트를 실시간 기록
- **4개 Hook 인프라**:
  - **PreCompact**: auto-compact 직전에 워크플로우 상태를 자동 백업
  - **Safety (PreToolUse)**: 위험한 Bash 명령어 사전 차단
  - **Quality Gate (PostToolUse)**: Edit/Write 후 코드 품질 자동 검증
  - **Session Start**: 세션 시작 시 이전 컨텍스트 자동 복원
- **Phase 4 자동 커밋**: 구현 중 태스크 완료 시마다 `jarfis(BE-1):`, `jarfis(FE-2):` 형식으로 커밋
- **Resume**: 컨텍스트 유실 시 상태 파일에서 복원하여 중단 지점부터 재개

### Self-Evolution

JARFIS는 자기 자신을 개선하는 도구를 내장하고 있습니다.

| Command | What it does |
|---------|-------------|
| `/jarfis:sys-upgrade` | 축적된 학습을 에이전트 프롬프트에 영구 반영 |
| `/jarfis:sys-distill` | 프롬프트 토큰 효율을 측정하고 최적화 (중복 제거, 템플릿 외부화) |
| `/jarfis:sys-implement` | JARFIS 자체의 명령어/구조를 수정 |

프롬프트를 사용할수록 학습이 쌓이고, 학습이 프롬프트에 반영되고, 프롬프트가 다시 최적화됩니다.

### Wiki Semantic Search

Organization 레벨의 Wiki가 커질수록, "어떤 파일이 지금 기획과 관련 있는가?"를 정확하게 찾는 것이 중요해집니다.

JARFIS는 [sentence-transformers](https://sbert.net/)의 **BAAI/bge-m3** 모델을 사용하여 Wiki 문서를 임베딩하고, 코사인 유사도(score >= 0.5) 기반 시맨틱 검색을 제공합니다. 한국어와 영어가 혼용된 마크다운 문서에서도 의미 기반으로 관련 문서를 찾아냅니다.

```
/jarfis:work 결제 환불 정책 변경
  → Phase 0: Wiki 시맨틱 검색 → "refund", "payment cancellation" 관련 ADR 3건 자동 로드
  → Phase 1: PO가 기존 환불 정책 ADR을 참조하여 역질문
```

자세한 내용: **[WIKI_SEARCH.md](./WIKI_SEARCH.md)**

### Project Awareness

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

| Command                   | Description                                            |
| ------------------------- | ------------------------------------------------------ |
| `/jarfis:work-meeting`    | 기획 킥오프 미팅 (PO/TL 자유 토론 → 산출물 생성)                       |
| `/jarfis:work`            | 기획→설계→구현→리뷰 전체 워크플로우                                   |
| `/jarfis:project-init`    | 프로젝트 분석 → `./.jarfis/project-profile.md` 생성            |
| `/jarfis:project-update`  | 기존 프로필 증분 갱신 (commit hash 기반, 날짜 fallback)             |
| `/jarfis:sys-upgrade`     | 학습항목 CRUD + 에이전트/워크플로우 프롬프트에 적용                        |
| `/jarfis:sys-health`      | 좀비 Claude 프로세스 진단/정리                                   |
| `/jarfis:sys-distill`     | 프롬프트 증류 — 토큰 효율 분석/최적화                                 |
| `/jarfis:work-continue`   | 완료된 워크플로우 후속 작업 (Fix/Extend 모드, --workflow/--mode 플래그) |
| `/jarfis:org`             | 등록된 전체 Org 목록 (orgs.json 기반, CWD 하이라이트)                |
| `/jarfis:org-init`        | Organization 초기화 (스캔 + wiki 생성)                        |
| `/jarfis:wiki-storyboard` | 디자인 카탈로그 브라우징 (wiki/DESIGN → 브라우저)                     |
| `/jarfis:search-setup`    | 시맨틱 검색 설치 (venv + sentence-transformers 원스텝)           |
| `/jarfis:search`          | 시맨틱 통합 검색 (meetings+works+wiki, 필터 가능)                 |
| `/jarfis:search-index`    | 전체 Org 시맨틱 인덱스 일괄 생성/갱신 (wiki+meetings+works)          |
| `/jarfis:level-check`     | AI-native 개발자 성숙도 평가 (자동 수집 + 인터뷰, 7차원 10점)            |
| `/jarfis:locale`          | 현재 locale 설정 조회                                        |
| `/jarfis:locale-set`      | locale 설정 변경 (ko/en/ja)                                |
| `/jarfis:sys-implement`   | JARFIS 시스템 자체 수정/기능 추가 + 버전 범프                         |
| `/jarfis:sys-version`     | 버전 확인/업데이트/특정 버전 설치                                    |
<!-- JARFIS-COMMANDS-END -->

---

## Installation

### Requirements

| Dependency | Version | Purpose | Required |
|------------|---------|---------|----------|
| [Claude Code](https://claude.ai/code) | Latest | CLI 런타임 | **필수** |
| Git | 2.x+ | 브랜치 관리, 자동 커밋 | **필수** |
| Python | 3.9+ | 상태 관리, CLI, Hook 인프라 | **필수** |
| jq | Any | Hook 등록 자동화 | 선택 |
| [sentence-transformers](https://sbert.net/) | Any | Wiki Semantic Search (bge-m3) | 선택 |

> **sentence-transformers**는 [Wiki Semantic Search](./WIKI_SEARCH.md) 기능을 위한 선택적 의존성입니다.
> 미설치 시에도 JARFIS는 정상 작동하며, Wiki 로딩 시 기존 LLM 판단 방식으로 폴백합니다.
> 설치: `pip3 install sentence-transformers`

### Install

```bash
git clone https://github.com/sana-lazystar/jarfis.git ~/repos/jarfis
cd ~/repos/jarfis
bash install.sh
```

`install.sh`는 다음을 수행합니다:

1. 기존 설치 백업
2. 에이전트의 Learned Rules 추출 (학습 보존)
3. `commands/`, `agents/`, `hooks/`, `scripts/` → `~/.claude/`로 파일 설치
4. `.personal/` 개인 설정 적용
5. 추출한 Learned Rules 재적용
6. 4개 Hook 등록 (settings.json): PreCompact, PreToolUse(Safety), PostToolUse(Quality Gate), SessionStart
7. 버전 스탬프 기록

### Data Directory

런타임 데이터는 repo 내 `.personal/` 디렉토리에 저장됩니다 (`.gitignore`에 의해 추적 제외):

```
~/repos/jarfis/.personal/
├── orgs/
│   ├── {org-name}/
│   │   ├── works/        # 워크플로우 산출물
│   │   ├── meetings/     # 미팅 산출물
│   │   └── learnings.md  # 학습 항목
│   └── _standalone/      # Org 미등록 시 기본
│       ├── works/
│       ├── meetings/
│       └── learnings.md
└── orgs.json              # Org 레지스트리
```

### Update

```bash
cd ~/repos/jarfis && git pull && bash install.sh
```

또는 Claude Code 안에서:

```
/jarfis:sys-version
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
├── jarfis.md                      # 메인 도우미 — 명령어 목록 + 예시 A/B
└── jarfis/
    ├── jarfis-index.md            # 이 파일 — JARFIS 시스템 현황
    ├── sys-implement.md               # JARFIS 자체 수정 명령어 + Dialectic Review 래칫 수렴 (분석→검증→이력→개선 루프) + Python TDD 규칙
    ├── work-meeting.md                 # 기획 킥오프 미팅 + wiki 로딩 + --prev-meeting 이전 미팅 참조 (PO/TL 토론, 230줄)
    ├── work.md                    # 핵심: 워크플로우 오케스트레이션 (~830줄, v2.5.4: PRD Ratchet, v2.5.5: Workflow Metrics, v2.5.6: TDD Code Ratchet, v3.0: Domain 분기)
    ├── project-init.md            # 프로젝트 프로필 생성
    ├── project-update.md          # 프로필 증분 갱신 — commit hash 기반 변경 감지
    ├── sys-upgrade.md                 # 학습 항목 관리 + 3블록 독립 구조 + Dialectic Review + 에이전트 화이트리스트 보호
    ├── sys-distill.md                 # 프롬프트 증류 + 에이전트 화이트리스트 보호 + 커맨드 분석 전용 + Dialectic Review
    ├── sys-version.md                 # 버전 관리/업데이트
    ├── work-continue.md                # 완료된 워크플로우 후속 작업 — Fix/Extend + Fix 테스트 래칫 + wiki 2/4-Step + Workflow Metrics
    ├── org.md                     # Organization 전체 목록 — orgs.json 기반 + 미등록 Org 자동 발견 + CWD 하이라이트
    ├── org-init.md                # Organization 초기화 — 스캔 + wiki 생성 + 시맨틱 인덱스 안내
    ├── wiki-storyboard.md              # 디자인 카탈로그 브라우징 명령어
    ├── search.md                 # 시맨틱 통합 검색 — meetings/works/wiki 필터링 + 메모리 부족 LLM 폴백
    ├── search-setup.md     # 시맨틱 검색 설치 — venv + sentence-transformers 원스텝
    ├── search-index.md    # 전체 Org 시맨틱 인덱스 일괄 생성/갱신 — wiki+meetings+works + --current + 메모리 가드
    ├── level-check.md                 # AI-native 개발자 성숙도 평가 — level_check.py 자체 수집 + 인터뷰, 7차원 10점
    ├── sys-health.md                  # 좀비 프로세스 진단
    ├── locale.md                      # Locale 조회 — 현재 워크플로우 언어 설정 표시
    ├── locale-set.md                  # Locale 설정 — ko/en/ja 언어 변경
    ├── prompts/                   # 외부화된 에이전트 프롬프트 (distill이 생성)
    │   ├── phase1.md              # Phase 1 Discovery 프롬프트 + PO wiki 참조 + 추가 태스크 + $MEETING_EXTRA 주입 + PRD Ratchet 규칙
    │   ├── phase2.md              # Phase 2&3 Architecture/UX 프롬프트 + wiki 참조 + HTML 시안
    │   ├── phase3-figma.md       # Phase 3 Figma-Driven Design Path 프롬프트 (복수 Figma 페이지 병렬 처리, 섹션별 v5 생성, Step 3-F0~3-F4)
    │   ├── phase4.md              # Phase 4 Implementation 프롬프트 + TDD Step 4-0.5 + Ratchet + TEST_RESULT/TEST_MODIFIED 보고
    │   ├── phase4-5.md            # Phase 4.5 Operational Readiness + dev 서버 체크
    │   ├── phase5.md              # Phase 5 Review & QA + Phase 4 Agent Status 주입 + TDD 경량화 + test_modifications 검증 + Fix 원설계 참조 + UX Designer 이중 비교
    │   ├── phase6.md              # Phase 6 Retrospective + Workflow Metrics + wiki 2-트랙 갱신 + 시맨틱 인덱스 갱신
    │   ├── wiki-loading.md        # Wiki 로딩 공통 모듈 — 2-Step/4-Step + 시맨틱 검색
    │   └── continue-extend.md    # Continue Extend 모드 PO/Architect/TL/QA 프롬프트
    ├── domains/                   # v3.0 Domain Pack 인프라
    │   ├── _schema.yaml           # Domain Pack 규격 (Published Language, EP1-7)
    │   ├── web.yaml               # Web Development 도메인 팩
    │   ├── web/skills/            # Web 도메인 Skills
    │   │   ├── react.md           # React 패턴 + 상태관리 + Next.js
    │   │   ├── vue.md             # Vue 3 Composition API + Pinia + Nuxt
    │   │   ├── browser.md         # 크로스 브라우저 + 성능 + 모바일
    │   │   ├── nodejs.md          # Node.js 런타임 + TypeScript + DB
    │   │   ├── express.md         # Express/NestJS + API 설계
    │   │   └── biome-lint.md      # Biome 린팅/포매팅 패턴
    │   ├── desktop.yaml           # Desktop Development (Tauri) 도메인 팩
    │   └── desktop/skills/        # Desktop 도메인 Skills
    │       ├── rust.md            # Ownership/borrowing, error handling, async
    │       ├── tauri-backend.md   # #[tauri::command], IPC, serde, plugins
    │       ├── tauri-webview.md   # @tauri-apps/api, invoke(), events, WebView 제약
    │       └── cargo-clippy.md    # Clippy 규칙, deny 설정
    └── templates/                 # 외부화된 산출물 템플릿 (distill이 생성)
        ├── jarfis-state-schema.md # .jarfis-state.json 구조 스키마 + PRD ratchet + Phase 4 TDD ratchet + Fix ratchet + workflow-metrics.tsv
        ├── learnings.md           # jarfis-learnings.md 템플릿 — Universal/Project-Specific 구조
        ├── project-context.md     # project-context.md 템플릿
        ├── project-profile.md     # 프로젝트 프로필 템플릿 + org 역참조
        ├── meeting-artifacts.md   # 미팅 산출물 4종 템플릿
        ├── org-profile.md         # Organization 프로필 템플릿
        ├── wiki-index.md          # Wiki INDEX.md 초기 템플릿
        ├── wiki-section-index.md  # Wiki 섹션 _index.md 템플릿
        ├── ux-direction.md        # UX 방향서 템플릿
        └── design-html-meta.md    # HTML 시안 메타 주석 템플릿

~/.claude/agents/jarfis/           # JARFIS agent prompts (referenced by work.md) — ALL ENGLISH + $LOCALE output
├── personas/                      # v3.0 Persona — role-specific cognitive frameworks
│   ├── product-owner.md           # PO perspective (business value, JTBD)
│   ├── technical-architect.md     # Architect perspective (system design, trade-offs)
│   ├── tech-lead.md               # TL perspective (code quality, technical judgment)
│   ├── frontend-developer.md      # FE perspective (browser/UI, design fidelity)
│   ├── backend-developer.md       # BE perspective (systems thinking, DB, API)
│   ├── devops-engineer.md         # DevOps perspective (infra, reliability, cost)
│   ├── ux-designer.md             # UX perspective (user empathy, visual hierarchy)
│   ├── qa-engineer.md             # QA perspective (quality, risk, compatibility)
│   └── security-engineer.md       # Security perspective (threat modeling, defensive coding)
├── jarfis-advocate.md             # Dialectic Review — change advocate agent
├── jarfis-critic.md               # Dialectic Review — change critic agent
├── senior-backend-engineer.md     # BE implementation agent
├── senior-frontend-engineer.md    # FE implementation agent
├── senior-devops-sre-engineer.md  # DevOps implementation agent
├── senior-product-owner.md        # PO decision-making / PRD / UX direction agent
├── tech-lead.md                   # TL codebase health + technical judgment agent
├── technical-architect.md         # Architecture design + technical strategy agent
├── senior-security-engineer.md    # Security review + defensive coding verification agent
├── senior-qa-engineer.md          # QA review + risk assessment agent
└── senior-ux-designer.md          # UX/brand design + SVG assets + quality gate + Figma rules agent
```

**설계 원칙**:

- **워크플로우 흐름**은 `work.md`에, **에이전트 프롬프트**는 `prompts/`에, **산출물 양식**은 `templates/`에 분리
- 에이전트 역할 프롬프트(`agents/`)와 워크플로우 프롬프트(`prompts/`)는 별개 — 역할은 고정, 태스크는 Phase마다 다름
- 학습 데이터는 로컬에만 존재 (Git repo에 포함되지 않음)
<!-- JARFIS-ARCHITECTURE-END -->

---

## Versioning

Semantic Versioning을 따릅니다.

| Change | Bump |
|--------|------|
| 프롬프트/템플릿 수정 | PATCH |
| 새 명령어/에이전트 추가 | MINOR |
| Phase 구조 변경 | MAJOR |

`/jarfis:sys-implement`, `/jarfis:sys-upgrade`, `/jarfis:sys-distill` 실행 시 자동으로 버전이 범프되고 CHANGELOG에 기록됩니다.

---

<!-- JARFIS-LATEST-CHANGES-START -->
## Latest Changes

> 전체 변경 이력은 [CHANGELOG.md](./CHANGELOG.md)를 참조하세요.

## [3.4.0] - 2026-04-13

- implement: Agent personas migrated to English — all 20 agent files (11 senior + 9 persona) converted with $LOCALE directive
<!-- JARFIS-LATEST-CHANGES-END -->

---

## License

[AGPL-3.0](./LICENSE)
