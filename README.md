# JARFIS — IT Team Workflow Orchestration

JARFIS는 Claude Code 위에서 동작하는 IT 팀 워크플로우 오케스트레이션 시스템입니다.

## 설치

```bash
git clone <repo-url> ~/repos/jarfis
cd ~/repos/jarfis
bash install.sh
```

## 업데이트

```bash
cd ~/repos/jarfis
git pull
bash install.sh
```

또는 Claude Code 내에서:

```
/jarfis:version
```

## 특정 버전 설치

```bash
bash install.sh --version 1.0.0
```

## 구조

```
jarfis/
├── VERSION                    # Semantic version (e.g. 1.0.0)
├── CHANGELOG.md               # 변경 이력
├── install.sh                 # 설치 스크립트
├── commands/
│   ├── jarfis.md              # 메인 도우미
│   └── jarfis/                # 서브 명령어들
│       ├── work.md            # 워크플로우 오케스트레이션
│       ├── meeting.md         # 기획 킥오프 미팅
│       ├── implement.md       # 시스템 자체 수정
│       ├── version.md         # 버전 관리
│       ├── upgrade.md         # 학습 관리
│       ├── distill.md         # 프롬프트 증류
│       ├── pack.md            # 포터블 아카이브
│       ├── health.md          # 헬스체크
│       ├── project-init.md    # 프로젝트 프로필 생성
│       ├── project-update.md  # 프로필 증분 갱신
│       ├── prompts/           # 외부화된 에이전트 프롬프트
│       └── templates/         # 외부화된 산출물 템플릿
├── agents/jarfis/             # 9개 에이전트 역할 프롬프트
├── hooks/                     # Git/Claude hooks
├── scripts/                   # 유틸리티 스크립트
└── statusline-command.sh      # 상태 표시줄
```

## 주요 명령어

| 명령어 | 설명 |
|--------|------|
| `/jarfis` | 명령어 목록 |
| `/jarfis:work` | 워크플로우 실행 |
| `/jarfis:meeting` | 기획 킥오프 미팅 |
| `/jarfis:version` | 버전 확인/업데이트 |
| `/jarfis:upgrade` | 학습 관리 |
| `/jarfis:implement` | 시스템 수정 |
| `/jarfis:distill` | 프롬프트 최적화 |
| `/jarfis:pack` | 포터블 아카이브 |

## 버전 관리

- `VERSION` 파일: repo root에 semver (prefix 없음)
- Git tags: `v1.0.0` 형식 (v prefix는 태그에만)
- `~/.claude/.jarfis-version`: 설치된 버전 기록
- `~/.claude/.jarfis-source`: Git repo 경로 기록

### Bump 규칙

| 변경 유형 | Bump |
|-----------|------|
| 새 명령어/에이전트 추가 | MINOR |
| 프롬프트/템플릿 내용 변경 | PATCH |
| Phase 구조 변경/호환 깨짐 | MAJOR |
