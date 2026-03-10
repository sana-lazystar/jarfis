# Changelog

All notable changes to JARFIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
