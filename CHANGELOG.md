# Changelog

All notable changes to JARFIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.3.0] - 2026-03-10

### Added
- **install.sh**: Workspace 디렉토리 설정 단계 추가 (Step 4/7) — `~/.jarfis-workspace` 기본값, `~/.claude/.jarfis-works-dir`에 경로 저장
- **work.md**: Phase 0에 Step 0-a-4 Workspace Detection 추가 — AskUserQuestion으로 프로젝트 구조(Monorepo/Multi-project/FE만/BE만) 명시적 확정
- **jarfis-state-schema.md**: `branches` 필드 추가 (multi-project Git 브랜치 지원)

### Changed
- **work.md**: `$DOCS_DIR` 경로를 CWD 기반(`CWD/.jarfis/works/`)에서 전용 디렉토리(`$JARFIS_WORKSPACE_DIR/works/`)로 변경
- **work.md**: Step 0-b Git 브랜치 로직을 monorepo/multi-project별 분기로 개선
- **work.md**: Execution Rules에서 workspace 설정을 "Phase 1 완료 후 PRD 파싱"에서 "Phase 0 Step 0-a-4 사용자 입력 기반"으로 변경
- **prompts/phase1.md**: PO 역질문에서 프로젝트 구조 질문 제거 (Phase 0에서 확정), Workspace 표를 `.jarfis-state.json` 자동 반영으로 변경
- **meeting.md**: meetings 디렉토리를 `$JARFIS_WORKSPACE_DIR/meetings/`로 변경
- **continue.md**: 워크플로우 탐색 경로를 `$JARFIS_WORKSPACE_DIR/works/`로 변경
- **jarfis-pre-compact.sh**: 상태파일/미팅 백업 경로를 `$JARFIS_WORKSPACE_DIR` 기반으로 변경
- **jarfis-state-schema.md**: `docs_dir` 예시를 절대경로로 변경

## [1.2.6] - 2026-03-10

### Changed
- **Distill: 에이전트 description 축소**: 9개 역할 에이전트의 YAML description에서 Examples 제거, 1-2문장으로 축소
  - 시스템 프롬프트 토큰 절감: ~3,294tok (매 대화마다 절감)
  - 에이전트 본문(역할/전문성/규칙)은 변경 없음
  - 대상: senior-frontend-engineer, tech-lead, technical-architect, senior-qa-engineer, senior-security-engineer, senior-backend-engineer, senior-ux-designer, senior-devops-sre-engineer, senior-product-owner

## [1.2.5] - 2026-03-10

### Changed
- **Learnings 적용**: 27개 학습 항목을 에이전트/워크플로우 프롬프트에 반영 (중복 3건 스킵)
  - senior-frontend-engineer.md: +10개 Learned Rules
  - senior-qa-engineer.md: +1개 Learned Rules
  - senior-devops-sre-engineer.md: +2개 Learned Rules (섹션 신규 생성)
  - senior-security-engineer.md: +1개 Learned Rules (섹션 신규 생성)
  - tech-lead.md: +4개 Learned Rules
  - work.md: +6개 Learned Workflow Patterns

## [1.2.4] - 2026-03-10

### Changed
- **Repo 동기화 자동화**: 수동 복사 → `jarfis-sync.sh` 스크립트 실행으로 전환
  - implement.md Step 4: 스크립트 한 줄 실행으로 교체 (AI 기억 의존 제거)
  - distill.md Repo 동기화: 동일 스크립트 호출로 교체
  - upgrade.md 3-A-8 Repo 동기화: 동일 스크립트 호출로 교체
  - 근본 원인: "사후 동기화" 패턴이 LLM의 긴 컨텍스트 후반 지시 누락에 취약

### Added
- **jarfis-sync.sh**: `~/.claude/` → `{repo_path}/` 단방향 자동 동기화 스크립트
  - diff 비교 후 변경분만 복사, 로컬 전용 파일 자동 제외
  - .jarfis-source에서 repo 경로 자동 결정

## [1.2.3] - 2026-03-10

### Added
- **Continue 프로젝트 프로필 로드**: `continue.md` Step 0에 project-profile.md 로드 추가
  - work.md Phase 0과 동일하게 `$BE_PROJECT_PROFILE`, `$FE_PROJECT_PROFILE` 변수 설정
  - Fix 모드 구현 에이전트(Step 3-2)에 프로필 전달 추가
  - Extend 모드 PO/Architect/Tech Lead(Step 4-1~4-2)에 `$PROJECT_CONTEXT` + 프로필 전달 추가
- **학습 항목 추가**: JARFIS 시스템 파일 수정 시 반드시 `/jarfis:implement` 경유 규칙 (jarfis-learnings.md)

## [1.2.2] - 2026-03-10

### Added
- **Continue Agent Model Routing**: `continue.md`에 모델 라우팅 규칙 추가
  - work.md Agent Mapping을 SSOT로 참조 (동기화 드리프트 방지)
  - 폴백 기본값 명시: 추론/분석(PO, Architect, TL) → Opus, 구현/실행(BE, FE, DevOps, QA, Security) → Sonnet
  - Fix/Extend 모드 모든 에이전트 호출 지점에 model 힌트 추가

## [1.2.1] - 2026-03-10

### Added
- **Continue 플래그 지원**: `--workflow {경로}` 워크플로우 직접 지정, `--mode fix|extend` 모드 명시 지정
  - 플래그 없으면 기존 자동 탐색/자동 분류 동작 유지
  - `--workflow` 지정 시 완료 여부 무관하게 해당 워크플로우 선택

## [1.2.0] - 2026-03-10

### Added
- **Continue Command** (`/jarfis:continue`): 완료된 워크플로우의 후속 작업 지원
  - **Fix 모드**: 테스트 후 발견된 버그/수정사항을 기존 산출물 기반으로 빠르게 처리 (Phase 4→5→6 경량 실행)
  - **Extend 모드**: 기존 설계 위에 추가 기능 개발 (Phase 1→2→4→5→6 경량 실행)
  - 이전 워크플로우의 PRD, 아키텍처, 태스크, 브랜치를 자동 재활용
  - `.jarfis-state.json`에 `follow_up` 필드 추가 (모드, iteration 추적)
  - 반복 실행 시 iteration 자동 증가

## [1.1.1] - 2026-03-10

### Changed
- jarfis.md 도움말에 v1.1.0 Dialectic Review 기능 반영 (implement --review 플래그, upgrade scope 분류, distill 토론 게이트 설명 추가)

## [1.1.0] - 2026-03-10

### Added
- **Dialectic Review System**: Advocate/Critic 에이전트 2개 신규 생성 (`jarfis-advocate.md`, `jarfis-critic.md`)
  - implement.md: Step 1과 Step 2 사이에 토론 게이트 추가 (`--review=major|minor|patch` 플래그 지원)
  - upgrade.md: 학습 scope 자동 분류 + ambiguous 항목에 대해 토론 실행
  - distill.md: 예상 토큰 절감률 30% 이상 시 토론 게이트 실행
- **Learning 2-Layer 분리**: universal vs project-specific 학습 구분
  - learnings.md 템플릿에 Universal/Project-Specific 하위 섹션 추가
  - phase6.md 회고 프롬프트에 `[universal]`/`[project]` scope 태깅 지시 추가
  - upgrade.md에 scope별 적용 경로 분기 (`[universal]` → agent Learned Rules, `[project]` → `.jarfis/context.md`)

## [1.0.7] - 2026-03-05

### Added
- Agent Learned Rules 머지: senior-backend-engineer(+16), senior-frontend-engineer(+10), senior-security-engineer(+4), senior-qa-engineer(+6) — 로컬 환경에서 축적된 실전 학습 항목 통합
- work.md: Type B 브랜치 규칙 (기존 피처 브랜치 기반 분기 + base_branch 추적)
- work.md: Multi-project Git 검증 (`git rev-parse --show-toplevel`)
- work.md: Adaptive Skip 경험 가이드 (UX/DevOps 스킵 조건, Phase 4.5 경량 모드, diagnosis 그룹핑 효과)
- prompts/phase4.md: BE/FE Self-Checklist (Phase 5 진입 전 자가 검증)
- prompts/phase4.md: BE/FE 데이터 정합성 규칙 (seed/mock 단일 소스 원칙)
- prompts/phase4.md: FE 태스크 배칭 규칙 (15개 초과 시 분할) + 체크박스 진행 추적
- prompts/phase5.md: UI 교차검증 (ux-spec.md 참조) + 재리뷰 효율화 규칙

## [1.0.6] - 2026-03-04

### Changed
- 산출물 디렉토리 `./jarfis/` → `./.jarfis/`로 변경 (dotfile 디렉토리로 숨김 처리)
  - work.md, meeting.md, project-init.md, project-update.md, jarfis.md, templates/project-profile.md 내 경로 참조 갱신
  - `jarfis-pre-compact.sh` 훅 경로 갱신

## [1.0.5] - 2026-03-04

### Fixed
- `claude-cleanup.sh` line 262: `$killed개` → `${killed}개` — bash `set -u`에서 한글이 변수명에 포함되어 unbound variable 경고 발생하던 버그 수정

## [1.0.4] - 2026-03-04

### Changed
- README.md 상단 소개 섹션 개선 — 더 생동감 있는 톤으로 JARFIS 파이프라인 설명

## [1.0.3] - 2026-03-04

### Changed
- README.md rewritten for public release — feature showcase with workflow pipeline, learning system, context resilience, self-evolution sections

## [1.0.2] - 2026-03-04

### Added
- Repo 동기화 step in `implement.md` (Step 4) — syncs modified files from `~/.claude/` to Git repo
- Repo 동기화 step in `upgrade.md` (3-A-8) — syncs applied agent/workflow files to Git repo
- Repo 동기화 step in `distill.md` (D-4 step 5) — syncs distilled files to Git repo
- Repo 동기화 entry in `jarfis-index.md` 수정 시 체크리스트 and 내부 참조 관계

## [1.0.1] - 2026-03-04

### Removed
- `/jarfis:pack` command — Git-based distribution (`git clone` + `install.sh`) fully replaces portable archive

### Changed
- `distill.md` meta-tool exclusion list: replaced `pack.md` with `version.md`

## [1.0.0] - 2026-03-04

### Added
- Git-based version management with Semantic Versioning
- `install.sh` — enhanced installer with `--version`, `--force`, auto-backup, Learned Rules preservation
- `/jarfis:version` — version check, update, rollback command
- `VERSION` file at repo root (semver, no prefix)
- `CHANGELOG.md` (this file)
- `.jarfis-version` and `.jarfis-source` version stamps
- Version bump step in `implement.md` (Step 3.5)
- PATCH auto-bump in `distill.md` and `upgrade.md`
- Version-based archive naming in `pack.md`

### Changed
- Version notation from informal "v17" to Semantic Versioning "1.0.0"
- `jarfis-index.md` now shows `Version: X.Y.Z` instead of `vN`
- `pack.md` archive name includes version: `jarfis-v{X.Y.Z}-portable.tar.gz`

### Migration
- Previous v17 (Ouroboros) → 1.0.0 (first Git-tracked release)
- All existing functionality preserved; this release adds versioning infrastructure only
