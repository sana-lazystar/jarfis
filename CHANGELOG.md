# Changelog

All notable changes to JARFIS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
- **Data 경로 통합**: workspace/learnings를 `{JARFIS_SOURCE}/.local/`로 이동 (기존 `~/.jarfis/` → `.local/workspace`, `.local/jarfis-learnings.md`)
- **install.sh**: `.local/` 마이그레이션 로직 추가 (기존 `~/.jarfis/`, `~/.jarfis-workspace` 자동 감지 및 복사)
- **jarfis-state.sh**: 모든 Python inline 코드를 환경변수 방식으로 변경 — single quote 인젝션 취약점 해결
- **jarfis-pre-compact.sh**: jq → python3 → 기본값 3단계 fallback (jq 미설치 환경 대응)
- **statusline-command.sh**: jq → python3 → 기본값 3단계 fallback
- **jarfis-version-bump.sh**: `sed -i ''` → `sed -i.bak` + `rm *.bak` (macOS/Linux 크로스플랫폼)
- **jarfis-sync.sh**: `claude-cleanup.sh`도 동기화 대상에 포함
- **health.md**: 존재하지 않는 `/jarfis:pack` 참조 → `install.sh`/`/jarfis:version`으로 수정
- **jarfis-index.md**: version.md의 (NEW) 태그 제거

### Added
- flat 디렉토리 구조 전환 + 미팅 선택 기능 + source_meeting 필드 (v1.5.0~v1.6.0 미커밋 변경 포함)
- README.md 자동 갱신 기능 — jarfis-readme-update.sh + sync.sh 연동
- Batch 1+2 스크립트: jarfis-measure.sh, jarfis-version-bump.sh, jarfis-preflight.sh, jarfis-state.sh, jarfis-detect-project.sh

## [1.6.0] - 2026-03-11

### Changed
- **workspace 경로**: `~/.jarfis-workspace` → `~/.jarfis/workspace`로 통합
- **learnings 경로**: `~/.claude/jarfis-learnings.md` → `~/.jarfis/jarfis-learnings.md`로 이동
- **install.sh**: 기존 경로 → 신규 경로 자동 마이그레이션 로직 추가

## [1.5.0] - 2026-03-11

### Changed
- **디렉토리 구조 flat 전환**: `meetings/{YYYYMMDD}/{name}/` → `meetings/{YYYYMMDD}-{name}/`, `works/` 동일
- **work.md**: Phase 0에서 AskUserQuestion으로 최근 미팅 3개 선택 기능 추가
- **pre-compact.sh**: meetings 탐색 버그 수정 (maxdepth 조정)

### Added
- **jarfis-recent-meetings.sh**: 최근 미팅 N개 JSON 출력 스크립트
- `.jarfis-state.json`에 `source_meeting`, `work_input` 필드 추가

## [1.4.2] - 2026-03-11

### Added
- **jarfis-readme-update.sh**: jarfis-index.md + CHANGELOG.md 기반 README.md 섹션 자동 갱신 (HTML 마커 기반)
- jarfis-sync.sh에서 동기화 시 자동 호출 연동

## [1.4.1] - 2026-03-10

### Added
- **Batch 1 스크립트**: jarfis-measure.sh (토큰 측정), jarfis-version-bump.sh (버전 범프)
- **Batch 2 스크립트**: jarfis-preflight.sh (사전검증), jarfis-state.sh (상태 CRUD), jarfis-detect-project.sh (프로젝트 감지)
- command md 5종 스크립트 연동으로 교체 (work, continue, meeting, project-init, implement)

### Changed
- jarfis-index.md 줄 수 10건 실제값으로 갱신

## [1.3.5] - 2026-03-10

### Changed
- **phase4.md**: BE/FE/DevOps 공통 구현 규칙(Git Auto-Commit 등)을 Common Implementation Rules 섹션으로 통합 — ~578tok 절감
- **phase2.md**: API spec 형식 49줄→12줄 압축, 태스크 분해 형식 78줄→16줄 압축 — ~809tok 절감
- **continue.md**: 5개 출력 포맷 코드블록을 1줄 설명으로 압축, 프로필/컨텍스트 로드 절차를 work.md Phase 0 참조로 간소화 — ~601tok 절감
- **meeting.md**: 전문가 소환 프로토콜 47줄→7줄, 3개 출력 포맷 블록 1줄 압축 — ~1,100tok 절감
- **phase1.md**: Required Roles/Workspace/Performance Budget 표를 1줄 지시로 압축, Completeness Check 30줄→5줄 — ~394tok 절감
- **phase5.md**: BE/FE fix 프롬프트 공통화(2→1), 병리 패턴 감지 30줄→8줄 — ~484tok 절감
- **work.md**: Phase 0 로드 절차 압축, Adaptive Skip 가이드 5줄→2줄 — ~130tok 절감

## [1.3.4] - 2026-03-10

### Fixed
- **work.md**: distill 압축 시 누락된 규칙 2건 복원 — Skip Rules에 "최소 1파트 실행" 제약 추가, State Management에 "종료 시 current_phase=done" 규칙 추가

## [1.3.3] - 2026-03-10

### Changed
- **work.md**: Phase 0 Workspace Detection/Meeting/Git 압축, Workflow Overview 4줄 압축, Gate 메시지 1줄 압축, Skip Rules/Workspace Dir Resolution을 Execution Rules로 통합, State Management 압축 (schema.md 참조) — ~5,000tok 절감
- **continue.md**: Extend 모드 PO/Architect/TL 프롬프트를 `prompts/continue-extend.md`로 외부화, Agent Model Routing 중복 제거 (work.md SSOT 참조) — ~530tok 절감
- **senior-frontend-engineer.md**: moreden-pcweb commitlint → 범용 commitlint 확인 규칙, CartWidget.tsx → 범용 대형 파일 확인 규칙, Write/Edit 중복 제거 — ~60tok 절감
- **tech-lead.md**: CartWidgetCallbacks → 범용 shared interface 규칙으로 추상화 — ~15tok 절감

### Added
- **prompts/continue-extend.md**: continue.md에서 외부화된 Extend 모드 PO/Architect/TL 프롬프트 (69줄)

## [1.3.2] - 2026-03-10

### Added
- **distill.md**: D-1 진단에 "6. 에이전트 추상화 분석" 기준 추가 — 프로젝트 한정 규칙 탐지, 상위 패턴 부재 탐지, 에이전트 간 규칙 중복 검출
- **distill.md**: D-2 액션에 `abstract-rule` (프로젝트 규칙→범용 원칙 추출) + `deduplicate-agent-rule` (에이전트 간 중복 규칙 통합) 추가
- **distill.md**: D-3 실행에 abstract-rule/deduplicate-agent-rule 실행 지침 추가

## [1.3.1] - 2026-03-10

### Added
- **distill.md**: D-1 진단에 "5. 표현 밀도 분석" 기준 추가 — 출력 포맷 과다, 저밀도 섹션, `<!-- no-condense -->` 마커 지원
- **distill.md**: D-2 액션에 `condense-section` (장황한 섹션 핵심만 압축) + `compress-expression` (출력 예시 최소화) 추가
- **distill.md**: D-3 실행에 condense-section/compress-expression 실행 지침 추가

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
