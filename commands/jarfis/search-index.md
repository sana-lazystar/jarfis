# JARFIS Search Index

> 등록된 Org의 wiki, meetings, works 시맨틱 인덱스를 일괄 생성/갱신합니다.

사용자 요청: $ARGUMENTS

---

## 사전 조건

- `/jarfis:search-setup` 완료 (sentence-transformers 설치)
- `/jarfis:org-init` 완료 (Org 등록 + wiki 구조 생성)

## 플래그 파싱

- `$ARGUMENTS`에 `--current` 플래그가 있으면 → 현재 Org만 인덱싱
- 플래그 없으면 → 전체 Org 인덱싱 (기본)

## 실행 흐름

### 1. venv 확인

```bash
test -d ~/.claude/.jarfis-venv && echo "OK" || echo "MISSING"
```

`MISSING`이면 안내하고 중단:
```
sentence-transformers가 설치되지 않았습니다.
먼저 /jarfis:search-setup 을 실행하세요.
```

### 2. Org 목록 로드

**`--current` 모드**: `jarfis_cli.py preflight`로 현재 Org만 확인
```bash
python3 ~/.claude/scripts/jarfis_cli.py preflight
```
JSON의 `org_root`와 `org_dir`을 사용하여 현재 Org 1개만 대상으로 한다.

**전체 모드** (기본):
```bash
python3 -c "
import json, os
personal_file = os.path.expanduser('~/.claude/.jarfis-personal-dir')
if os.path.isfile(personal_file):
    with open(personal_file) as f:
        personal = f.read().strip()
else:
    source_file = os.path.expanduser('~/.claude/.jarfis-source')
    if os.path.isfile(source_file):
        with open(source_file) as f:
            personal = os.path.join(f.read().strip(), '.personal')
    else:
        personal = os.path.expanduser('~/repos/jarfis/.personal')
orgs_path = os.path.join(personal, 'orgs', 'orgs.json')
if os.path.isfile(orgs_path):
    with open(orgs_path) as f:
        data = json.load(f)
    print(json.dumps(data, ensure_ascii=False))
else:
    print(json.dumps({'orgs': []}))
"
```

**Org가 0개인 경우** — 안내하고 중단:
```
등록된 Organization이 없습니다.
먼저 /jarfis:org-init 으로 Org을 등록하세요.
```

### 3. Org별 일괄 인덱싱

각 Org에 대해 **wiki, meetings, works** 3종을 순차 인덱싱한다:

**3-1. 인덱스 상태 확인**:
```bash
python3 ~/.claude/scripts/jarfis_cli.py search status --org-root {org_root}
```

**3-2. 인덱싱 실행** (stale이거나 미인덱싱인 scope만):

```bash
# Wiki
python3 ~/.claude/scripts/jarfis_cli.py search index wiki --org-root {org_root}

# Meetings
python3 ~/.claude/scripts/jarfis_cli.py search index meetings --org-root {org_root}

# Works
python3 ~/.claude/scripts/jarfis_cli.py search index works --org-root {org_root}
```

최초 실행 시 bge-m3 모델 다운로드 안내:
```
Note: 최초 실행 시 bge-m3 모델이 자동 다운로드됩니다 (~2GB).
```

### 4. 결과 보고

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Search Index 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {org_name}:
    ✅ wiki     — {files}파일, {chunks}청크
    ✅ meetings — {files}파일, {chunks}청크
    ✅ works    — {files}파일, {chunks}청크
    ⏭️ wiki     — 최신 (스킵)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

실패한 scope이 있으면 에러 메시지를 함께 표시:
```
  ❌ {scope} — {에러 메시지}
```
