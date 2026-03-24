# JARFIS System Index

> 이 파일은 `/jarfis:sys-implement` 실행 시 자동으로 읽히며, 수정 완료 후 자동 갱신됩니다.
> 수동 편집하지 마세요. Last updated: 2026-03-24 | Version: 2.1.0

## 파일 구조
```
~/.claude/commands/
├── jarfis.md                      # 메인 도우미 — 명령어 목록 + 예시 A/B (66줄)
└── jarfis/
    ├── jarfis-index.md            # 이 파일 — JARFIS 시스템 현황
    ├── sys-implement.md               # JARFIS 자체 수정 명령어 + Dialectic Review 게이트 + Python TDD 규칙 (240줄)
    ├── work-meeting.md                 # 기획 킥오프 미팅 + wiki 로딩 (PO/TL 토론, 201줄)
    ├── work.md                    # 핵심: 워크플로우 오케스트레이션 (587줄, v2: wiki, PO 추가 태스크, Phase 3 HTML 시안, Phase 5 UX 리뷰, Phase 6 wiki 갱신)
    ├── project-init.md            # 프로젝트 프로필 생성 (162줄)
    ├── project-update.md          # 프로필 증분 갱신 — commit hash 기반 변경 감지 (160줄)
    ├── sys-upgrade.md                 # 학습 항목 관리 + 3블록 독립 구조 + Dialectic Review + 에이전트 화이트리스트 보호 (296줄)
    ├── sys-distill.md                 # 프롬프트 증류 + 에이전트 화이트리스트 보호 + 커맨드 분석 전용 + Dialectic Review (312줄)
    ├── sys-version.md                 # 버전 관리/업데이트 (158줄)
    ├── work-continue.md                # 완료된 워크플로우 후속 작업 — Fix/Extend + wiki 2/4-Step (274줄)
    ├── org.md                     # Organization 전체 목록 — orgs.json 기반 + 미등록 Org 자동 발견 + CWD 하이라이트 (96줄)
    ├── org-init.md                # Organization 초기화 — 스캔 + wiki 생성 + 시맨틱 인덱스 안내 (114줄)
    ├── wiki-storyboard.md              # 디자인 카탈로그 브라우징 명령어 (48줄)
    ├── search-setup.md     # 시맨틱 검색 설치 — venv + sentence-transformers 원스텝 (57줄)
    ├── search-index.md    # Org wiki 시맨틱 인덱스 생성/갱신 (129줄)
    ├── sys-health.md                  # 좀비 프로세스 진단 (70줄)
    ├── prompts/                   # 외부화된 에이전트 프롬프트 (distill이 생성)
    │   ├── phase1.md              # Phase 1 Discovery 프롬프트 + PO wiki 참조 + 추가 태스크 (194줄)
    │   ├── phase2.md              # Phase 2&3 Architecture/UX 프롬프트 + wiki 참조 + HTML 시안 (214줄)
    │   ├── phase4.md              # Phase 4 Implementation 프롬프트 + Handoff + design/ 참조 (115줄)
    │   ├── phase4-5.md            # Phase 4.5 Operational Readiness + dev 서버 체크 (37줄)
    │   ├── phase5.md              # Phase 5 Review & QA + UX Designer playwright 리뷰 (225줄)
    │   ├── phase6.md              # Phase 6 Retrospective + wiki 2-트랙 갱신 + 시맨틱 인덱스 갱신 (115줄)
    │   ├── wiki-loading.md        # Wiki 로딩 공통 모듈 — 2-Step/4-Step + 시맨틱 검색 (44줄)
    │   └── continue-extend.md    # Continue Extend 모드 PO/Architect/TL 프롬프트 (69줄)
    └── templates/                 # 외부화된 산출물 템플릿 (distill이 생성)
        ├── jarfis-state-schema.md # .jarfis-state.json 구조 스키마 + status/key_decisions (115줄)
        ├── learnings.md           # jarfis-learnings.md 템플릿 — Universal/Project-Specific 구조 (43줄)
        ├── project-context.md     # project-context.md 템플릿 (17줄)
        ├── project-profile.md     # 프로젝트 프로필 템플릿 + org 역참조 (68줄)
        ├── meeting-artifacts.md   # 미팅 산출물 4종 템플릿 (86줄)
        ├── org-profile.md         # Organization 프로필 템플릿 (19줄) [NEW]
        ├── wiki-index.md          # Wiki INDEX.md 초기 템플릿 (34줄) [NEW]
        ├── wiki-section-index.md  # Wiki 섹션 _index.md 템플릿 (11줄) [NEW]
        ├── ux-direction.md        # UX 방향서 템플릿 (36줄) [NEW]
        └── design-html-meta.md    # HTML 시안 메타 주석 템플릿 (27줄) [NEW]

~/.claude/agents/jarfis/           # JARFIS 에이전트 프롬프트 (work.md에서 참조)
├── jarfis-advocate.md             # Dialectic Review — 변경 옹호 에이전트 (55줄)
├── jarfis-critic.md               # Dialectic Review — 변경 비판 에이전트 (56줄)
├── senior-backend-engineer.md     # BE 구현 에이전트 (102줄)
├── senior-frontend-engineer.md    # FE 구현 에이전트 (120줄)
├── senior-devops-sre-engineer.md  # DevOps 구현 에이전트 (92줄)
├── senior-product-owner.md        # PO 의사결정/PRD/UX방향서 에이전트 (142줄)
├── tech-lead.md                   # TL 코드베이스 건강 + 기술 판단 에이전트 (213줄)
├── technical-architect.md         # 아키텍처 설계 + 기술 전략 에이전트 (168줄)
├── senior-security-engineer.md    # 보안 리뷰 + 방어적 코딩 검증 에이전트 (191줄)
├── senior-qa-engineer.md          # QA 리뷰 + 리스크 판단 에이전트 (183줄)
└── senior-ux-designer.md          # UX/브랜드 디자인 + SVG 에셋 + 품질 게이트 에이전트 (237줄)
```

## 명령어 매핑
| 명령어 | 파일 | 역할 |
|--------|------|------|
| `/jarfis` | `jarfis.md` | 명령어 목록 출력 |
| `/jarfis:work-meeting` | `jarfis/work-meeting.md` | 기획 킥오프 미팅 (PO/TL 자유 토론 → 산출물 생성) |
| `/jarfis:work` | `jarfis/work.md` | 기획→설계→구현→리뷰 전체 워크플로우 |
| `/jarfis:project-init` | `jarfis/project-init.md` | 프로젝트 분석 → `./.jarfis/project-profile.md` 생성 |
| `/jarfis:project-update` | `jarfis/project-update.md` | 기존 프로필 증분 갱신 (commit hash 기반, 날짜 fallback) |
| `/jarfis:sys-upgrade` | `jarfis/sys-upgrade.md` | 학습항목 CRUD + 에이전트/워크플로우 프롬프트에 적용 |
| `/jarfis:sys-health` | `jarfis/sys-health.md` | 좀비 Claude 프로세스 진단/정리 |
| `/jarfis:sys-distill` | `jarfis/sys-distill.md` | 프롬프트 증류 — 토큰 효율 분석/최적화 |
| `/jarfis:work-continue` | `jarfis/work-continue.md` | 완료된 워크플로우 후속 작업 (Fix/Extend 모드, --workflow/--mode 플래그) |
| `/jarfis:org` | `jarfis/org.md` | 등록된 전체 Org 목록 (orgs.json 기반, CWD 하이라이트) |
| `/jarfis:org-init` | `jarfis/org-init.md` | Organization 초기화 (스캔 + wiki 생성) |
| `/jarfis:wiki-storyboard` | `jarfis/wiki-storyboard.md` | 디자인 카탈로그 브라우징 (wiki/DESIGN → 브라우저) |
| `/jarfis:search-setup` | `jarfis/search-setup.md` | 시맨틱 검색 설치 (venv + sentence-transformers 원스텝) |
| `/jarfis:search-index` | `jarfis/search-index.md` | Org wiki 시맨틱 인덱스 생성/갱신 |
| `/jarfis:sys-implement` | `jarfis/sys-implement.md` | JARFIS 시스템 자체 수정/기능 추가 + 버전 범프 |
| `/jarfis:sys-version` | `jarfis/sys-version.md` | 버전 확인/업데이트/특정 버전 설치 |

## 산출물/데이터 파일
- `{프로젝트경로}/.jarfis/project-profile.md` — project-init이 생성, work이 참조 (각 프로젝트 내부)
- `{프로젝트경로}/.jarfis/project-context.md` — work 실행 시 참조하는 컨텍스트 (각 프로젝트 내부, 선택적)
- `$JARFIS_ORG_DIR/learnings.md` — Org별 학습 항목 (upgrade가 관리, work이 참조. `.personal/orgs/{org}/learnings.md`)
- `~/.claude/.jarfis-personal-dir` — .personal 디렉토리 경로 설정 파일 (install.sh가 생성)
- `$JARFIS_ORG_DIR/works/{YYYYMMDD}-{type}-{ticket-name}/` — work이 생성하는 워크플로우 산출물 디렉토리 ($DOCS_DIR, flat 구조)
- `$JARFIS_ORG_DIR/meetings/{YYYYMMDD}-{기획명}/` — meeting이 생성하는 미팅 산출물 디렉토리 (flat 구조):
  - `summary.md` — YAML frontmatter + 미팅 요약 (work.md 자동 감지용)
  - `meeting-notes.md` — 토픽별 정리된 회의록
  - `decisions.md` — 의사결정 표 + 근거 + 대안
  - `tech-research.md` — 전문가 조사 결과 (전문가 소환 시에만 생성)
- `~/.claude/scripts/jarfis_cli.py` — Python CLI 진입점 (아래 모든 명령어의 단일 인터페이스)
  - `jarfis_cli.py sync` — Repo 동기화 (`~/.claude/` → `{repo_path}/` 자동 diff+복사 + README 갱신)
  - `jarfis_cli.py measure` — 프롬프트 파일 토큰 측정 + 구조 진단 (distill D-0/D-1/D-4에서 사용)
  - `jarfis_cli.py version` — semver 버전 범프 자동화 (implement/distill/upgrade에서 사용)
  - `jarfis_cli.py meetings` — 최근 미팅 N개 JSON 출력 (work.md Phase 0 미팅 선택에서 사용)
  - `jarfis_cli.py preflight` — 사전 검증 + Org 자동 등록 + 프로젝트 테이블 자동 추가 (Org 감지 시 orgs.json 미등록→자동 등록, org-profile.md 프로젝트 테이블 미등록→자동 행 추가)
  - `jarfis_cli.py state` — .jarfis-state.json CRUD (init/read/write/set/set-nested/validate/list-workflows, work/continue에서 사용)
  - `jarfis_cli.py detect` — 프레임워크/언어 자동 감지 (파일 패턴 기반 JSON 출력, project-init/work에서 사용)
  - `jarfis_cli.py quality-gate` — 파일별 린트/타입체크 실행 (PostToolUse hook에서 사용)
  - `jarfis_cli.py validate` — 워크플로우 상태 + 산출물 + Git 검증 (수동 도구, A-3)
  - `jarfis_cli.py org` — Organization 관리 (init --name/scan/info, v2 신규. info는 미등록 시 exit 0 + registered:false 반환)
  - `jarfis_cli.py wiki` — Wiki 시맨틱 검색 (index/search/status, sentence-transformers bge-m3 기반. venv 자동 감지 — `~/.claude/.jarfis-venv/` 존재 시 자동 사용, 미설치 시 폴백 안내)
- `~/.claude/scripts/jarfis/` — Python 모듈 디렉토리 (jarfis_cli.py가 참조)
  - `quality_gate.py` — Quality Gate 모듈 (biome/prettier 감지, 확장자별 체크)
  - `validate.py` — 워크플로우 검증 모듈 (상태 검증 + 산출물 존재 + wiki 구조 + Git 상태)
  - `organization.py` — Organization 관리 모듈 (init/scan/info, v2 신규)
  - `wiki_search.py` — Wiki 시맨틱 검색 모듈 (sentence-transformers bge-m3, index/search/status, venv 감지 에러 메시지, 358줄)
- `~/.claude/scripts/tests/` — pytest 테스트 디렉토리 (148 tests, 1500줄)
  - `conftest.py` — 공유 fixture (jarfis_env, state_file, project_dir — tmpdir 기반 격리)
  - `test_utils.py` — utils.py 인터페이스 테스트
  - `test_state.py` — state.py CRUD + validate 테스트
  - `test_detect.py` — detect.py 프레임워크/언어 감지 테스트
  - `test_meetings.py` — meetings.py 미팅 목록 테스트
  - `test_quality_gate.py` — quality_gate.py 린트/타입체크 테스트
  - `test_version.py` — version.py 시맨틱 버전 범프 테스트
  - `test_preflight.py` — preflight.py 사전 검증 테스트
  - `test_measure.py` — measure.py 토큰 측정 테스트
  - `test_sync.py` — sync.py 파일 동기화 테스트
  - `test_validate.py` — validate.py 워크플로우 검증 테스트
  - `test_organization.py` — organization.py Org 관리 테스트
  - `test_wiki_search.py` — wiki_search.py 유틸리티 함수 테스트 (임베딩 제외)
  - `test_jarfis_cli.py` — jarfis_cli.py 디스패처 테스트 (subprocess)
- `~/.claude/scripts/jarfis_check.sh` — grep 기반 JARFIS 구조 검증 스크립트 (Phase 헤딩, 프롬프트 파일, 버전 일치, 모델 정합성)
- `~/.claude/hooks/jarfis-pre-compact.sh` — PreCompact 훅 (auto-compact 전 상태 백업, shell-only)
- `~/.claude/hooks/jarfis-safety.sh` — PreToolUse 훅 (Bash 위험 명령 차단/경고, 100줄)
- `~/.claude/hooks/jarfis-quality-gate.sh` — PostToolUse 훅 (Edit/Write 후 린트/타입체크, 85줄)
- `~/.claude/hooks/jarfis-session-start.sh` — SessionStart 훅 (in-progress 워크플로우 컨텍스트 복원, 98줄)
- `$DOCS_DIR/.compact-backups/` — PreCompact 훅이 생성하는 상태 백업 디렉토리
- `~/.claude/.jarfis-version` — 설치된 버전 기록 (install.sh가 생성)
- `~/.claude/.jarfis-source` — Git repo 경로 기록 (install.sh가 생성)
- `~/.claude/.jarfis-personal-dir` — .personal 디렉토리 경로 (install.sh가 생성, 기본: `{JARFIS_SOURCE}/.personal`)
- `{JARFIS_SOURCE}/.personal/orgs/orgs.json` — Org 레지스트리 (org-init 시 자동 등록)
- `{JARFIS_SOURCE}/.personal/orgs/{org_name}/` — Org별 워크스페이스 (works/, meetings/, learnings.md)
- `{JARFIS_SOURCE}/.personal/orgs/_standalone/` — Org 미등록 사용자 워크스페이스
- `{JARFIS_SOURCE}/VERSION` — Git repo의 semver 버전
- `{JARFIS_SOURCE}/CHANGELOG.md` — Keep-a-Changelog 형식 변경 이력

## 내부 참조 관계
- `jarfis.md` → 모든 명령어 참조 (도우미 텍스트)
- `work-meeting.md` → 독립 (project-profile, context, learnings 선택적 참조) + compact 대비 중간 저장
- `work.md` → `/jarfis:project-init` 참조 (프로필 로드 안내) + meetings 산출물 참조 (Phase 0에서 `jarfis_cli.py meetings`로 워크스페이스 미팅 조회 + AskUserQuestion 선택) + `.compact-backups/` 참조 (Resume 시) + `prompts/*.md` 참조 (Phase별 에이전트 프롬프트)
- `prompts/*.md` → work.md에서 외부화된 에이전트 프롬프트 (distill이 생성, work.md가 Phase 진입 시 로드)
- `templates/*.md` → work.md/work-meeting.md에서 외부화된 산출물 템플릿 (distill이 생성, 해당 Phase에서 필요 시 로드). v2 신규: org-profile, wiki-index, wiki-section-index, ux-direction, design-html-meta
- `project-update.md` → `/jarfis:project-init` 참조 (프로필 없을 때 안내, 분석 기준 참조)
- `project-init.md` → `templates/project-profile.md` 참조 (프로필 산출물 양식)
- `sys-distill.md` → `jarfis-index.md` 먼저 읽어 현황 파악 → `jarfis_cli.py measure`로 토큰 측정 → commands/jarfis/*.md + agents/jarfis/*.md 분석, jarfis-index.md 갱신
- `agents/jarfis/*.md` → work.md에서 Agent 도구로 참조 (BE/FE/DevOps/QA/PO/TL/Architect/Security/UX)
- `agents/jarfis/jarfis-advocate.md` → sys-implement.md/sys-upgrade.md/sys-distill.md에서 Dialectic Review 시 참조 (변경 옹호)
- `agents/jarfis/jarfis-critic.md` → sys-implement.md/sys-upgrade.md/sys-distill.md에서 Dialectic Review 시 참조 (변경 비판)
- `work-continue.md` → `.jarfis-state.json` 읽기 (이전 워크플로우 탐색) + work.md의 Phase 4/5/6 재활용 + `prompts/phase4.md`, `prompts/phase5.md`, `prompts/phase6.md` 참조 + `prompts/continue-extend.md` 참조 (Extend 모드) + work.md Agent Mapping 참조 (모델 라우팅 SSOT) + project-profile.md/project-context.md 로드 (work.md Phase 0과 동일)
- `sys-implement.md` → `jarfis-index.md` 읽기/갱신 + VERSION/CHANGELOG 범프
- `sys-version.md` → `.jarfis-version`, `.jarfis-source`, Git repo VERSION/CHANGELOG 참조
- `sys-distill.md` → 완료 후 `jarfis_cli.py version patch` 호출
- `sys-upgrade.md` → 학습 적용 후 `jarfis_cli.py version patch` 호출
- `sys-implement.md` → 완료 후 `jarfis_cli.py version <type>` 호출 (사용자 선택)
- `jarfis_cli.py measure` → sys-distill.md D-0/D-1/D-4에서 파일 토큰 측정 + 진단 데이터 수집
- `jarfis_cli.py version` → sys-implement.md/sys-distill.md/sys-upgrade.md에서 VERSION/CHANGELOG/__init__.py 자동 갱신
- `jarfis_cli.py sync` → README 갱신 포함 (jarfis-index.md + CHANGELOG.md → README.md 섹션 갱신)
- `jarfis_cli.py meetings` → work.md Phase 0에서 최근 미팅 N개 JSON 조회 (AskUserQuestion 미팅 선택용)
- `jarfis_cli.py preflight` → work.md Phase 0 / work-continue.md Step 0 / work-meeting.md M-0에서 프로필/학습/컨텍스트/git 상태 사전 검증
- `jarfis_cli.py state` → work.md 전체 Phase / work-continue.md Step 0에서 .jarfis-state.json CRUD (init/read/set/set-nested/list-workflows)
- `jarfis_cli.py detect` → project-init.md Step 0 / work.md Phase 0에서 프레임워크/언어 자동 감지
- `jarfis-pre-compact.sh` → `$JARFIS_ORG_DIR`에서 `.jarfis-state.json` 백업 + meeting 파일 백업 (auto-compact 시 자동 실행, shell-only hook)
- `jarfis-safety.sh` → PreToolUse(Bash) 차단: force push, --no-verify, main/master 직접 커밋 | 경고: .env, rm -rf, credentials, curl|bash (킬 스위치: JARFIS_SAFETY_HOOK=0)
- `jarfis-quality-gate.sh` → PostToolUse(Edit/Write/MultiEdit) 린트/타입체크 경고 (절대 차단 안함, 킬 스위치: JARFIS_QUALITY_GATE=0)
- `jarfis-session-start.sh` → SessionStart에서 in-progress 워크플로우 탐색 → stdout 컨텍스트 주입 (킬 스위치: JARFIS_SESSION_RESTORE=0)
- `quality_gate.py` → jarfis-quality-gate.sh가 호출, biome/prettier + tsc 실행 (프로젝트 루트 자동 감지)
- `phase4.md` → Phase 2 handoff 읽기/쓰기 지침 (key_decisions, warnings, unresolved)
- `phase5.md` → Learning Candidate Detection (동일 fix 카테고리 2건+ 반복 시 learning_candidates 기록)
- `phase6.md` → Suggested Learnings 섹션 (learning_candidates 기반 학습 후보 자동 생성) + Wiki 갱신 후 `jarfis_cli.py wiki index` 리인덱싱 (best-effort)
- `wiki-loading.md` → 4-Step Step 3에서 `jarfis_cli.py wiki search` 호출 (폴백: LLM 판단)
- `wiki_search.py` → wiki-loading.md/phase6.md/org-init.md에서 참조 (sentence-transformers 선택적 의존성, 미설치 시 `/jarfis:search-setup` 안내)
- `search-setup.md` → 독립 실행 (venv 생성 + sentence-transformers 설치), 완료 후 `/jarfis:search-index` 안내. org-init.md/wiki-loading.md/wiki_search.py에서 안내 참조
- `search-index.md` → orgs.json에서 Org 선택 → `jarfis_cli.py wiki index` 실행. search-setup.md/org-init.md에서 안내 참조
- `org-init.md` → 생성 완료 후 `/jarfis:search-setup` → `/jarfis:search-index` 안내 표시
- `tests/` → sys-implement.md Step 2 Python TDD 규칙에서 참조 (148개 테스트, 전 Python 모듈 커버). `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short`로 실행

## Git Auto-Commit 기능
- Phase 4 (구현): BE/FE/DevOps 각 agent가 태스크 완료 시마다 자동 커밋
  - 형식: `jarfis(BE-N):`, `jarfis(FE-N):`, `jarfis(DevOps-N):`
- Phase 5 Step 5-3 (수정): 이슈 그룹별 자동 커밋
  - 형식: `jarfis(fix/BE):`, `jarfis(fix/FE):`
- Continue Fix 모드: Fix 태스크 완료 시마다 자동 커밋
  - 형식: `jarfis(fix/BE-N):`, `jarfis(fix/FE-N):`
- Continue Extend 모드: Extension 태스크 완료 시마다 자동 커밋
  - 형식: `jarfis(ext/BE-N):`, `jarfis(ext/FE-N):`
- git index.lock 충돌 대비 3초 대기 후 재시도 (최대 3회)

## 수정 시 체크리스트
- 명령어 이름 변경: 파일 rename + 모든 파일에서 참조 grep/replace
- 새 명령어 추가: `jarfis/` 아래 md 파일 생성 + `jarfis.md` 목록에 추가 + 이 인덱스 갱신
- work.md가 가장 크고 복잡 — Phase 0~6 구조로 워크플로우 정의
- **외부화 구조** (distill v10~v12):
  - work.md = 워크플로우 흐름/규칙만 보유
  - 에이전트 Task prompt → `prompts/phase{N}.md` 수정
  - 산출물 템플릿 → `templates/*.md` 수정
  - Phase 추가/삭제 시 → work.md + 대응하는 prompts/ + templates/ 파일 동시 갱신
  - `agents/jarfis/*.md`는 Agent 도구의 역할 프롬프트 (work.md와 별개)
- **버전 관리**: implement/distill/upgrade 완료 후 → VERSION + .jarfis-version + __init__.py + jarfis-index.md Version + CHANGELOG 갱신
- **Repo 동기화**: implement/distill/upgrade 완료 후 → `python3 ~/.claude/scripts/jarfis_cli.py sync` 실행 (수동 복사 금지)
- **Python TDD**: `scripts/jarfis/*.py` 수정 시 → 테스트 먼저 작성/수정 → 코드 수정 → `python3 -m pytest ~/.claude/scripts/tests/ -v --tb=short` 전체 통과 확인
- **Git repo**: `~/.claude/.jarfis-source`에서 경로 확인 (기본: `~/repos/jarfis`)
