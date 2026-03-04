# Changelog

All notable changes to JARFIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
