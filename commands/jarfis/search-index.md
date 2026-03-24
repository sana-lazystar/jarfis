# JARFIS Search Index

> 등록된 전체 Org의 wiki 시맨틱 인덱스를 일괄 생성/갱신합니다.

사용자 요청: $ARGUMENTS

---

## 사전 조건

- `/jarfis:search-setup` 완료 (sentence-transformers 설치)
- `/jarfis:org-init` 완료 (Org 등록 + wiki 구조 생성)

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

### 3. 전체 Org 일괄 인덱싱

모든 Org에 대해 순차 실행한다. 각 Org마다:

**3-1. 인덱스 상태 확인**:
```bash
python3 ~/.claude/scripts/jarfis_cli.py wiki status {org_root}
```

- `indexed: true`이고 `stale_files: 0` → 스킵 (최신 상태)
- `indexed: false` 또는 `stale_files > 0` → 인덱싱 실행

**3-2. 인덱싱 실행** (필요한 Org만):
```
⏳ {org_name} wiki 인덱싱 중...
```

```bash
python3 ~/.claude/scripts/jarfis_cli.py wiki index {org_root}
```

최초 실행 시 bge-m3 모델 다운로드 안내:
```
Note: 최초 실행 시 bge-m3 모델이 자동 다운로드됩니다 (~2GB).
```

### 4. 결과 보고

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Wiki Index 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✅ {org1_name} — {files}파일, {chunks}청크
  ✅ {org2_name} — {files}파일, {chunks}청크
  ⏭️ {org3_name} — 최신 (스킵)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

실패한 Org이 있으면 에러 메시지를 함께 표시:
```
  ❌ {org_name} — {에러 메시지}
```
