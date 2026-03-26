# Changelog

All notable changes to JARFIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.2.0] - 2026-03-26

- implement: Phase 3 Figma-Driven Design Path 분기 추가 (Framelink MCP + 에셋 다운로드 + 토큰맵 + UX 재현 + 리뷰 루프 max 20회)

## [2.1.3] - 2026-03-24

- implement: fix test isolation leak — TestOrg cleanup + jarfis_env usage

## [2.1.2] - 2026-03-24

- implement: fix sync to include scripts/tests/ directory

## [2.1.1] - 2026-03-24

- implement: fix venv detection bug + search-index batch all orgs

## [2.1.0] - 2026-03-24

- implement: add /jarfis:search-index command

## [2.0.1] - 2026-03-24

- implement: rename wiki-setup → search-setup

## [2.0.0] - 2026-03-24

JARFIS v2 LTS — v1.11.3에서 전면 재설계된 AI IT Team Workflow Orchestration 시스템.

### Agent 고도화
- 6개 에이전트(PO, UX, QA, Security, TL, Architect) v2 업그레이드 — Mindset & Disposition, Judgment Framework, Escalation Criteria 섹션 추가
- 에이전트 보호 규칙: 화이트리스트 방식 (`## Learned Rules`만 수정 가능, 나머지 전체 읽기 전용)
- Dialectic Review 시스템: Advocate/Critic 에이전트 토론 게이트 (implement, upgrade, distill)
- Learning 2-Layer 분리: `[universal]` → agent Learned Rules, `[project]` → project-context.md

### Organization & Wiki
- Org 개념 도입: org-profile.md, wiki/ 구조, 프로젝트 횡단 지식 관리
- Wiki Semantic Search: sentence-transformers bge-m3 기반 시맨틱 검색
- Org 자동 등록: preflight 시 Org 감지 → orgs.json 자동 등록 + 프로젝트 테이블 자동 추가
- Org 자동 발견: /jarfis:org 실행 시 등록된 Org의 형제 디렉토리 스캔

### 산출물 디렉토리 재구조화
- `.local/workspace` → `.personal/orgs/{org_name}/` Org별 워크스페이스 분리
- orgs.json 레지스트리 + `_standalone` 폴더 (Org 미등록 사용자)
- Org별 learnings.md 분리
- `.jarfis-works-dir` → `.jarfis-personal-dir` 설정 파일 변경

### 커맨드 체계
- resource-verb 패턴 통일: continue→work-continue, meeting→work-meeting, implement→sys-implement, upgrade→sys-upgrade, distill→sys-distill, version→sys-version, health→sys-health, wiki-search-setup→wiki-setup, storyboard→wiki-storyboard
- 커맨드 보호 규칙: distill은 커맨드 파일 분석만, 수정은 sys-implement만 가능
- /jarfis:org 전체 Org 목록 표시 (orgs.json 기반 + CWD 하이라이트)
- /jarfis:wiki-setup 원스텝 설치 커맨드

### 워크플로우 강화
- Phase 3 PO→Designer 핸드오프: ux-direction.md → HTML 시안 → 피드백 루프
- Phase 5 UX Designer 리뷰: playwright 시각적 비교 기반 디자인 QA
- Gate 1/2/3 명시적 AskUserQuestion 블록
- `.jarfis-state.json`에 status + key_decisions 필드 추가

### Python CLI & 테스트
- Bash → Python 마이그레이션: 8개 모듈 + jarfis_cli.py 디스패처
- pytest 테스트 176개 (전 모듈 커버, TDD 규칙 enforce)
- `get_workspace_dir` → `get_org_dir` 의미론적 리네이밍
- install.sh .personal 구조 마이그레이션 지원

### Infrastructure
- 4개 Hook 인프라: PreCompact, Safety(PreToolUse), Quality Gate(PostToolUse), SessionStart
- 9 Principles 문서 (PHILOSOPHY.md)
- Git-based versioning + Semantic Versioning

## [1.11.3] - 2026-03-19

- implement: upgrade.md 잔존 Learned Workflow Patterns 참조 제거 (F-1)

## [1.11.2] - 2026-03-19

- implement: 9 Principles 검수 반영 — upgrade.md Workflow Patterns SSOT 변경, PHILOSOPHY.md Principle Zero + 트레이드오프 추가

## [1.11.1] - 2026-03-19

- implement: 미비점 수정 (정본 표기 통일, index 잔여 텍스트 제거, version.py regex 보강)

## [1.11.0] - 2026-03-19

- implement: jarfis validate 명령어 + jarfis_check.sh 구조 검증 스크립트

## [1.10.2] - 2026-03-19

- implement: health.md 외부 스크립트 가드 보강 + Hook 주석 영어 통일

## [1.10.1] - 2026-03-19

- implement: upgrade.md 3블록 독립 분리 + Dialectic Review 정본 참조 패턴

## [1.10.0] - 2026-03-19

- implement: state validate 서브커맨드 추가 + 미팅 라운드 카운터 상태 관리

## [1.9.12] - 2026-03-19

- implement: prompts Task prompt 레이블 통일 + install.sh TTY 자동 감지

## [1.9.11] - 2026-03-19

- implement: work.md Learned Workflow Patterns 제거 (~500tok 절감, jarfis-learnings.md가 SSOT)

## [1.9.10] - 2026-03-19

- implement: 에이전트 모델 frontmatter 통일 (QA/Security → opus) + 모델 라우팅 SSOT 강화

## [1.9.9] - 2026-03-19

- implement: version bump 시 __init__.py 버전도 함께 갱신하도록 개선

## [1.9.8] - 2026-03-18

- upgrade: API 마이그레이션 학습 적용 (FE 3건, QA 3건, WF 3건)

## [1.9.7] - 2026-03-16

- upgrade: 학습 적용 — FE 7건(API 전환 패턴), WF 4건(전환 워크플로우)

## [1.9.6] - 2026-03-12

- implement: senior-ux-designer 전면 개편 (브랜드 디자인 + SVG 에셋 제작 + 디자인 토큰 + 비평 루프)

## [1.9.5] - 2026-03-12

- implement: project-update 변경 감지를 commit hash 기반으로 개선

## [1.9.4] - 2026-03-12

- upgrade: 학습 적용 (FE 5건, TL 2건, WF 3건)

## [1.9.3] - 2026-03-11

- implement: agent model routing 통일 (UX/QA/Security → opus)

## [1.9.2] - 2026-03-11

- implement: implement/distill/upgrade 완료 시 commit+push 명령어 제공

## [1.9.1] - 2026-03-11

- implement: LICENSE 파일 추가 + README Philosophy 링크

## [1.9.0] - 2026-03-11

- implement: Hook infrastructure (safety/quality-gate/session-start) + workflow handoff + learning candidates

## [1.8.4] - 2026-03-11

- implement: remove deprecated sh scripts replaced by py modules

## [1.8.3] - 2026-03-11

- implement: 명령어 .md 파일 스크립트 참조를 .sh → Python CLI(jarfis_cli.py)로 일괄 전환

## [1.8.2] - 2026-03-11

- implement: 스텝 강제 실행 규칙, 수정 위치 명시, 동기화 방향 경고, 스텝 간 흐름 연결 강화

## [1.8.1] - 2026-03-11

- implement: CHANGELOG 버전 범프 로직 개선 — [Unreleased] → [X.Y.Z] 릴리스 섹션 자동 전환

## [1.8.0] - 2026-03-11

### Changed
- **Bash → Python 마이그레이션**: 9개 Bash 스크립트 중 8개를 Python stdlib-only 패키지로 전환
- **jarfis-detect-project.sh**: `grep` 기반 JSON 파싱 → `json.load()` 정확 파싱
- **jarfis-state.sh**: Bash + `python3 -c` 인라인 혼합 → 순수 Python 모듈
- **workspace 경로 해석**: 4개 스크립트에 중복되던 로직을 `utils.py`로 통합
- **jarfis-sync.sh + jarfis-readme-update.sh**: `sync.py`로 병합 (`--readme-only` 플래그)
- **install.sh**: Python 패키지(`scripts/jarfis/`, `jarfis_cli.py`) 백업/설치 로직 추가

### Added
- `scripts/jarfis/` Python 패키지 (8 모듈 + utils)
- `scripts/jarfis_cli.py` CLI 디스패처
- `PHILOSOPHY.md` — JARFIS 9 Principles 문서

## [1.7.1] - 2026-03-11

### Changed
- JARFIS 약어를 **Just A Rather Foolish Integration System**으로 확정
- README.md 현행화: Artifacts 경로 `.local/` 반영, python3 요구사항 추가, jq optional 변경, (NEW) 태그 제거

## [1.7.0] - 2026-03-11

### Changed
- **Data 경로 통합**: workspace/learnings를 `{JARFIS_SOURCE}/.local/`로 이동
- **install.sh**: `.local/` 마이그레이션 로직 추가
- **jarfis-state.sh**: 환경변수 방식으로 변경 — single quote 인젝션 취약점 해결
- **jarfis-pre-compact.sh**: jq → python3 → 기본값 3단계 fallback
- **statusline-command.sh**: jq → python3 → 기본값 3단계 fallback

### Added
- flat 디렉토리 구조 전환 + 미팅 선택 기능 + source_meeting 필드
- README.md 자동 갱신 기능

## [1.6.0] - 2026-03-11

### Changed
- **workspace 경로**: `~/.jarfis-workspace` → `~/.jarfis/workspace`로 통합
- **learnings 경로**: `~/.claude/jarfis-learnings.md` → `~/.jarfis/jarfis-learnings.md`로 이동

## [1.5.0] - 2026-03-11

### Changed
- **디렉토리 구조 flat 전환**: `meetings/{YYYYMMDD}/{name}/` → `meetings/{YYYYMMDD}-{name}/`

### Added
- **jarfis-recent-meetings.sh**: 최근 미팅 N개 JSON 출력 스크립트

## [1.4.2] - 2026-03-11

### Added
- **jarfis-readme-update.sh**: README.md 섹션 자동 갱신

## [1.4.1] - 2026-03-10

### Added
- **Batch 1+2 스크립트**: jarfis-measure.sh, jarfis-version-bump.sh, jarfis-preflight.sh, jarfis-state.sh, jarfis-detect-project.sh

## [1.3.5] - 2026-03-10

### Changed
- Distill: phase4/phase2/continue/meeting/phase1/phase5/work.md 토큰 절감 (~3,596tok)

## [1.3.4] - 2026-03-10

### Fixed
- work.md: distill 압축 시 누락된 규칙 2건 복원

## [1.3.3] - 2026-03-10

### Changed
- Distill: work.md ~5,000tok 절감, continue.md ~530tok, agent 규칙 추상화

### Added
- prompts/continue-extend.md: Extend 모드 프롬프트 외부화

## [1.3.2] - 2026-03-10

### Added
- distill.md: 에이전트 추상화 분석 (abstract-rule, deduplicate-agent-rule)

## [1.3.1] - 2026-03-10

### Added
- distill.md: 표현 밀도 분석 (condense-section, compress-expression)

## [1.3.0] - 2026-03-10

### Added
- install.sh: Workspace 디렉토리 설정
- work.md: Workspace Detection (AskUserQuestion)

## [1.2.6] - 2026-03-10

### Changed
- Distill: 에이전트 description 축소 (~3,294tok 절감)

## [1.2.5] - 2026-03-10

### Changed
- Learnings 적용: 27개 학습 항목 반영

## [1.2.4] - 2026-03-10

### Changed
- Repo 동기화 자동화: jarfis-sync.sh

## [1.2.3] - 2026-03-10

### Added
- Continue 프로젝트 프로필 로드

## [1.2.2] - 2026-03-10

### Added
- Continue Agent Model Routing

## [1.2.1] - 2026-03-10

### Added
- Continue 플래그 지원 (--workflow, --mode)

## [1.2.0] - 2026-03-10

### Added
- **Continue Command** (`/jarfis:work-continue`): Fix/Extend 모드

## [1.1.1] - 2026-03-10

### Changed
- jarfis.md 도움말에 Dialectic Review 반영

## [1.1.0] - 2026-03-10

### Added
- **Dialectic Review System**: Advocate/Critic 에이전트
- **Learning 2-Layer 분리**: universal vs project-specific

## [1.0.7] - 2026-03-05

### Added
- Agent Learned Rules 머지 + work.md 강화

## [1.0.6] - 2026-03-04

### Changed
- 산출물 디렉토리 `./jarfis/` → `./.jarfis/`

## [1.0.5] - 2026-03-04

### Fixed
- claude-cleanup.sh bash set -u 버그 수정

## [1.0.4] - 2026-03-04

### Changed
- README.md 소개 섹션 개선

## [1.0.3] - 2026-03-04

### Changed
- README.md public release 용 재작성

## [1.0.2] - 2026-03-04

### Added
- Repo 동기화 step (implement/upgrade/distill)

## [1.0.1] - 2026-03-04

### Removed
- /jarfis:pack command

## [1.0.0] - 2026-03-04

### Added
- Git-based version management with Semantic Versioning
- install.sh, /jarfis:sys-version, VERSION, CHANGELOG.md

### Migration
- Previous v17 (Ouroboros) → 1.0.0 (first Git-tracked release)
