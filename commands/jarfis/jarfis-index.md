# JARFIS System Index

> 이 파일은 `/jarfis:implement` 실행 시 자동으로 읽히며, 수정 완료 후 자동 갱신됩니다.
> 수동 편집하지 마세요. Last updated: 2026-03-11 | Version: 1.8.3

## 파일 구조
```
~/.claude/commands/
├── jarfis.md                      # 메인 도우미 — 명령어 목록 출력 (94줄)
└── jarfis/
    ├── jarfis-index.md            # 이 파일 — JARFIS 시스템 현황
    ├── implement.md               # JARFIS 자체 수정 명령어 + Dialectic Review 게이트 (215줄)
    ├── meeting.md                 # 기획 킥오프 미팅 (PO/TL 토론, 188줄)
    ├── work.md                    # 핵심: 워크플로우 오케스트레이션 (443줄, 프롬프트+템플릿 외부화 후)
    ├── project-init.md            # 프로젝트 프로필 생성 (157줄, 프로필 템플릿 외부화 후)
    ├── project-update.md          # 프로필 증분 갱신 (133줄)
    ├── upgrade.md                 # 학습 항목 관리 + Scope 분류 + Dialectic Review (371줄)
    ├── distill.md                 # 프롬프트 증류 + Dialectic Review 게이트 (305줄)
    ├── version.md                 # 버전 관리/업데이트
    ├── continue.md                # 완료된 워크플로우 후속 작업 — Fix/Extend 모드 + Agent Model Routing (261줄)
    ├── health.md                  # 좀비 프로세스 진단 (67줄)
    ├── prompts/                   # 외부화된 에이전트 프롬프트 (distill이 생성)
    │   ├── phase1.md              # Phase 1 Discovery 프롬프트 (143줄)
    │   ├── phase2.md              # Phase 2&3 Architecture/UX 프롬프트 (170줄)
    │   ├── phase4.md              # Phase 4 Implementation 프롬프트 (85줄)
    │   ├── phase4-5.md            # Phase 4.5 Operational Readiness 프롬프트 (35줄)
    │   ├── phase5.md              # Phase 5 Review & QA 프롬프트 (177줄)
    │   ├── phase6.md              # Phase 6 Retrospective 프롬프트 + 학습 scope 태깅 (46줄)
    │   └── continue-extend.md    # Continue Extend 모드 PO/Architect/TL 프롬프트 (69줄)
    └── templates/                 # 외부화된 산출물 템플릿 (distill이 생성)
        ├── jarfis-state-schema.md # .jarfis-state.json 구조 스키마 (80줄)
        ├── learnings.md           # jarfis-learnings.md 템플릿 — Universal/Project-Specific 구조 (43줄)
        ├── project-context.md     # project-context.md 템플릿 (17줄)
        ├── project-profile.md     # 프로젝트 프로필 템플릿 (66줄)
        └── meeting-artifacts.md   # 미팅 산출물 4종 템플릿 (86줄)

~/.claude/agents/jarfis/           # JARFIS 에이전트 프롬프트 (work.md에서 참조)
├── jarfis-advocate.md             # Dialectic Review — 변경 옹호 에이전트 (55줄) [NEW]
├── jarfis-critic.md               # Dialectic Review — 변경 비판 에이전트 (56줄) [NEW]
├── senior-backend-engineer.md     # BE 구현 에이전트 (102줄)
├── senior-frontend-engineer.md    # FE 구현 에이전트 (105줄)
├── senior-devops-sre-engineer.md  # DevOps 구현 에이전트 (92줄)
├── senior-product-owner.md        # PO 역질문/PRD 에이전트 (79줄)
├── tech-lead.md                   # TL 태스크 분해 에이전트 (154줄)
├── technical-architect.md         # 아키텍처 설계 에이전트 (128줄)
├── senior-security-engineer.md    # 보안 리뷰 에이전트 (105줄)
├── senior-qa-engineer.md          # QA 리뷰 에이전트 (95줄)
└── senior-ux-designer.md          # UX 리뷰 에이전트 (92줄)
```

## 명령어 매핑
| 명령어 | 파일 | 역할 |
|--------|------|------|
| `/jarfis` | `jarfis.md` | 명령어 목록 출력 |
| `/jarfis:meeting` | `jarfis/meeting.md` | 기획 킥오프 미팅 (PO/TL 자유 토론 → 산출물 생성) |
| `/jarfis:work` | `jarfis/work.md` | 기획→설계→구현→리뷰 전체 워크플로우 |
| `/jarfis:project-init` | `jarfis/project-init.md` | 프로젝트 분석 → `./.jarfis/project-profile.md` 생성 |
| `/jarfis:project-update` | `jarfis/project-update.md` | 기존 프로필 증분 갱신 (git diff 기반) |
| `/jarfis:upgrade` | `jarfis/upgrade.md` | 학습항목 CRUD + 에이전트/워크플로우 프롬프트에 적용 |
| `/jarfis:health` | `jarfis/health.md` | 좀비 Claude 프로세스 진단/정리 |
| `/jarfis:distill` | `jarfis/distill.md` | 프롬프트 증류 — 토큰 효율 분석/최적화 |
| `/jarfis:continue` | `jarfis/continue.md` | 완료된 워크플로우 후속 작업 (Fix/Extend 모드, --workflow/--mode 플래그) |
| `/jarfis:implement` | `jarfis/implement.md` | JARFIS 시스템 자체 수정/기능 추가 + 버전 범프 |
| `/jarfis:version` | `jarfis/version.md` | 버전 확인/업데이트/특정 버전 설치 |

## 산출물/데이터 파일
- `{프로젝트경로}/.jarfis/project-profile.md` — project-init이 생성, work이 참조 (각 프로젝트 내부)
- `{프로젝트경로}/.jarfis/project-context.md` — work 실행 시 참조하는 컨텍스트 (각 프로젝트 내부, 선택적)
- `{JARFIS_SOURCE}/.local/jarfis-learnings.md` — 학습 항목 (upgrade가 관리, work이 참조)
- `~/.claude/.jarfis-works-dir` — 워크스페이스 디렉토리 경로 설정 파일 (install.sh가 생성)
- `$JARFIS_WORKSPACE_DIR/works/{YYYYMMDD}-{type}-{ticket-name}/` — work이 생성하는 워크플로우 산출물 디렉토리 ($DOCS_DIR, flat 구조)
- `$JARFIS_WORKSPACE_DIR/meetings/{YYYYMMDD}-{기획명}/` — meeting이 생성하는 미팅 산출물 디렉토리 (flat 구조):
  - `summary.md` — YAML frontmatter + 미팅 요약 (work.md 자동 감지용)
  - `meeting-notes.md` — 토픽별 정리된 회의록
  - `decisions.md` — 의사결정 표 + 근거 + 대안
  - `tech-research.md` — 전문가 조사 결과 (전문가 소환 시에만 생성)
- `~/.claude/scripts/jarfis_cli.py` — Python CLI 진입점 (아래 모든 명령어의 단일 인터페이스)
  - `jarfis_cli.py sync` — Repo 동기화 (`~/.claude/` → `{repo_path}/` 자동 diff+복사 + README 갱신)
  - `jarfis_cli.py measure` — 프롬프트 파일 토큰 측정 + 구조 진단 (distill D-0/D-1/D-4에서 사용)
  - `jarfis_cli.py version` — semver 버전 범프 자동화 (implement/distill/upgrade에서 사용)
  - `jarfis_cli.py meetings` — 최근 미팅 N개 JSON 출력 (work.md Phase 0 미팅 선택에서 사용)
  - `jarfis_cli.py preflight` — 사전 검증 (프로필/학습/컨텍스트/git 상태 JSON 출력, work/continue/meeting에서 사용)
  - `jarfis_cli.py state` — .jarfis-state.json CRUD (init/read/write/set/set-nested/list-workflows, work/continue에서 사용)
  - `jarfis_cli.py detect` — 프레임워크/언어 자동 감지 (파일 패턴 기반 JSON 출력, project-init/work에서 사용)
- `~/.claude/scripts/jarfis/` — Python 모듈 디렉토리 (jarfis_cli.py가 참조)
- `~/.claude/hooks/jarfis-pre-compact.sh` — PreCompact 훅 (auto-compact 전 상태 백업, shell-only)
- `$DOCS_DIR/.compact-backups/` — PreCompact 훅이 생성하는 상태 백업 디렉토리
- `~/.claude/.jarfis-version` — 설치된 버전 기록 (install.sh가 생성)
- `~/.claude/.jarfis-source` — Git repo 경로 기록 (install.sh가 생성)
- `~/.claude/.jarfis-works-dir` — 워크스페이스 디렉토리 경로 (install.sh가 생성, 기본: `{JARFIS_SOURCE}/.local/workspace`)
- `{JARFIS_SOURCE}/VERSION` — Git repo의 semver 버전
- `{JARFIS_SOURCE}/CHANGELOG.md` — Keep-a-Changelog 형식 변경 이력

## 내부 참조 관계
- `jarfis.md` → 모든 명령어 참조 (도우미 텍스트)
- `meeting.md` → 독립 (project-profile, context, learnings 선택적 참조) + compact 대비 중간 저장
- `work.md` → `/jarfis:project-init` 참조 (프로필 로드 안내) + meetings 산출물 참조 (Phase 0에서 `jarfis_cli.py meetings`로 워크스페이스 미팅 조회 + AskUserQuestion 선택) + `.compact-backups/` 참조 (Resume 시) + `prompts/*.md` 참조 (Phase별 에이전트 프롬프트)
- `prompts/*.md` → work.md에서 외부화된 에이전트 프롬프트 (distill이 생성, work.md가 Phase 진입 시 로드)
- `templates/*.md` → work.md/meeting.md에서 외부화된 산출물 템플릿 (distill이 생성, 해당 Phase에서 필요 시 로드)
- `project-update.md` → `/jarfis:project-init` 참조 (프로필 없을 때 안내, 분석 기준 참조)
- `project-init.md` → `templates/project-profile.md` 참조 (프로필 산출물 양식)
- `distill.md` → `jarfis-index.md` 먼저 읽어 현황 파악 → `jarfis_cli.py measure`로 토큰 측정 → commands/jarfis/*.md + agents/jarfis/*.md 분석, jarfis-index.md 갱신
- `agents/jarfis/*.md` → work.md에서 Agent 도구로 참조 (BE/FE/DevOps/QA/PO/TL/Architect/Security/UX)
- `agents/jarfis/jarfis-advocate.md` → implement.md/upgrade.md/distill.md에서 Dialectic Review 시 참조 (변경 옹호)
- `agents/jarfis/jarfis-critic.md` → implement.md/upgrade.md/distill.md에서 Dialectic Review 시 참조 (변경 비판)
- `continue.md` → `.jarfis-state.json` 읽기 (이전 워크플로우 탐색) + work.md의 Phase 4/5/6 재활용 + `prompts/phase4.md`, `prompts/phase5.md`, `prompts/phase6.md` 참조 + `prompts/continue-extend.md` 참조 (Extend 모드) + work.md Agent Mapping 참조 (모델 라우팅 SSOT) + project-profile.md/project-context.md 로드 (work.md Phase 0과 동일)
- `implement.md` → `jarfis-index.md` 읽기/갱신 + VERSION/CHANGELOG 범프
- `version.md` → `.jarfis-version`, `.jarfis-source`, Git repo VERSION/CHANGELOG 참조
- `distill.md` → 완료 후 `jarfis_cli.py version patch` 호출
- `upgrade.md` → 학습 적용 후 `jarfis_cli.py version patch` 호출
- `implement.md` → 완료 후 `jarfis_cli.py version <type>` 호출 (사용자 선택)
- `jarfis_cli.py measure` → distill.md D-0/D-1/D-4에서 파일 토큰 측정 + 진단 데이터 수집
- `jarfis_cli.py version` → implement.md/distill.md/upgrade.md에서 VERSION/CHANGELOG 자동 갱신
- `jarfis_cli.py sync` → README 갱신 포함 (jarfis-index.md + CHANGELOG.md → README.md 섹션 갱신)
- `jarfis_cli.py meetings` → work.md Phase 0에서 최근 미팅 N개 JSON 조회 (AskUserQuestion 미팅 선택용)
- `jarfis_cli.py preflight` → work.md Phase 0 / continue.md Step 0 / meeting.md M-0에서 프로필/학습/컨텍스트/git 상태 사전 검증
- `jarfis_cli.py state` → work.md 전체 Phase / continue.md Step 0에서 .jarfis-state.json CRUD (init/read/set/set-nested/list-workflows)
- `jarfis_cli.py detect` → project-init.md Step 0 / work.md Phase 0에서 프레임워크/언어 자동 감지
- `jarfis-pre-compact.sh` → `$JARFIS_WORKSPACE_DIR`에서 `.jarfis-state.json` 백업 + meeting 파일 백업 (auto-compact 시 자동 실행, shell-only hook)

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
- **버전 관리**: implement/distill/upgrade 완료 후 → VERSION + .jarfis-version + jarfis-index.md Version + CHANGELOG 갱신
- **Repo 동기화**: implement/distill/upgrade 완료 후 → `python3 ~/.claude/scripts/jarfis_cli.py sync` 실행 (수동 복사 금지)
- **Git repo**: `~/.claude/.jarfis-source`에서 경로 확인 (기본: `~/repos/jarfis`)
