# JARFIS Version — 버전 관리 및 업데이트

현재 설치된 JARFIS 버전을 확인하고, 업데이트를 관리합니다.

사용자 요청: $ARGUMENTS

---

## 실행 흐름

### Step 1: 현재 버전 표시

다음 파일들을 읽어 버전 정보를 수집하세요:

1. `~/.claude/.jarfis-version` — 설치된 버전
2. `~/.claude/.jarfis-source` — Git repo 경로
3. `~/.claude/commands/jarfis/jarfis-index.md` — 인덱스의 Version 표기

정보를 표시하세요:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Version Info
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Installed : v{버전}
  Source    : {repo 경로}
  Index     : {인덱스의 Version 표기}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

`.jarfis-version`이 없으면:
```
  [WARN] 버전 파일이 없습니다. install.sh를 실행하세요.
```

### Step 2: 액션 선택

AskUserQuestion으로 다음 중 하나를 선택하게 하세요:

```
question: "어떤 작업을 수행할까요?"
header: "Action"
options:
  - label: "업데이트 확인"
    description: "Git remote에서 최신 버전을 확인합니다"
  - label: "업데이트 실행"
    description: "최신 버전으로 업데이트합니다 (git pull + install.sh)"
  - label: "특정 버전 설치"
    description: "Git 태그에서 특정 버전을 선택하여 설치합니다"
  - label: "CHANGELOG 보기"
    description: "변경 이력을 표시합니다"
```

### Step 3: 액션별 처리

---

#### [업데이트 확인] 선택 시

1. `.jarfis-source`에서 repo 경로를 읽는다.
2. 해당 경로에서 `git fetch --tags` 실행.
3. 최신 태그와 현재 설치 버전을 비교:

```bash
cd {repo_path}
git fetch --tags 2>/dev/null
LATEST=$(git tag -l 'v*' | sort -V | tail -1 | sed 's/^v//')
```

4. 결과 표시:
```
  Installed : v{현재}
  Latest    : v{최신}
  Status    : {Up to date / Update available}
```

업데이트 가능하면 "업데이트 실행" 여부를 AskUserQuestion으로 확인.

---

#### [업데이트 실행] 선택 시

1. `.jarfis-source`에서 repo 경로를 읽는다.
2. repo의 git 상태를 확인한다:

```bash
cd {repo_path}
git status --porcelain
```

3. **dirty repo인 경우**: AskUserQuestion으로 처리 방법을 선택하게 한다:
```
question: "작업 중인 변경사항이 있습니다. 어떻게 처리할까요?"
header: "Dirty repo"
options:
  - label: "Stash & Update"
    description: "변경사항을 stash한 후 업데이트, 완료 후 stash pop"
  - label: "Force"
    description: "변경사항을 무시하고 강제 업데이트 (git checkout .)"
  - label: "Cancel"
    description: "업데이트를 취소합니다"
```

4. 업데이트 실행:
```bash
cd {repo_path}
git pull origin main
bash install.sh --force
```

5. 결과 표시:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Update Complete
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Previous : v{이전}
  Current  : v{현재}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

#### [특정 버전 설치] 선택 시

1. `.jarfis-source`에서 repo 경로를 읽는다.
2. 사용 가능한 태그 목록을 가져온다:

```bash
cd {repo_path}
git fetch --tags 2>/dev/null
git tag -l 'v*' | sort -rV | head -10
```

3. AskUserQuestion으로 설치할 버전을 선택하게 한다 (최근 4개 태그를 옵션으로).
4. 선택된 버전으로 설치:

```bash
cd {repo_path}
bash install.sh --version {선택된_버전} --force
```

---

#### [CHANGELOG 보기] 선택 시

1. `.jarfis-source`에서 repo 경로를 읽는다.
2. `{repo_path}/CHANGELOG.md`를 읽어 표시한다.
3. 파일이 없으면 "CHANGELOG.md가 없습니다"라고 안내.

---

## 주의사항

- `.jarfis-source` 파일이 없으면 repo 경로를 알 수 없으므로, 수동으로 경로를 입력하게 하거나 `install.sh`를 먼저 실행하라고 안내.
- Git 명령 실패 시 (네트워크 오류 등) 적절한 에러 메시지를 표시하고 계속할지 물어본다.
- 업데이트 후 현재 Claude Code 세션에서는 이전 버전의 프롬프트가 로드되어 있을 수 있음을 안내.
