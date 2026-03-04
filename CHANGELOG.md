# Changelog

All notable changes to JARFIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
