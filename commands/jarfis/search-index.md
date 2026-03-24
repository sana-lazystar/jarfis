# JARFIS Search Index

> 등록된 Org의 wiki 시맨틱 인덱스를 생성/갱신합니다.

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

### 3. Org 선택

**Org가 0개인 경우** — 안내하고 중단:
```
등록된 Organization이 없습니다.
먼저 /jarfis:org-init 으로 Org을 등록하세요.
```

**Org가 1개인 경우** — 자동 선택 (확인만 표시):
```
📂 {org_name} ({root}) — 자동 선택
```

**Org가 2개 이상인 경우** — AskUserQuestion으로 선택:
```
question: "어떤 Organization의 wiki를 인덱싱할까요?"
header: "Org"
options:
  - label: "{org1_name}"
    description: "{org1_root}"
  - label: "{org2_name}"
    description: "{org2_root}"
  ...
```

### 4. 인덱스 상태 확인

선택된 Org에 대해 기존 인덱스 상태를 확인한다:
```bash
python3 ~/.claude/scripts/jarfis_cli.py wiki status {org_root}
```

결과에서 `indexed: true`이고 `stale_files: 0`이면:
```
✅ {org_name} 인덱스가 최신 상태입니다. (파일: N개, 청크: M개)
   마지막 인덱싱: {indexed_at}
```
이 경우에도 AskUserQuestion으로 재인덱싱 여부를 확인:
```
question: "인덱스가 최신입니다. 재인덱싱하시겠어요?"
header: "Reindex"
options:
  - label: "스킵 (Recommended)"
    description: "현재 인덱스를 유지합니다"
  - label: "재인덱싱"
    description: "인덱스를 처음부터 다시 빌드합니다"
```

`indexed: false`이거나 `stale_files > 0`이면 바로 인덱싱 진행.

### 5. 인덱싱 실행

```
⏳ {org_name} wiki 인덱싱을 시작합니다...
   최초 실행 시 bge-m3 모델 다운로드로 수 분 소요될 수 있습니다.
```

```bash
python3 ~/.claude/scripts/jarfis_cli.py wiki index {org_root}
```

### 6. 결과 보고

성공 시:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Wiki Index 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Org: {org_name}
  📂 {org_root}
  📄 파일: {total_files}개
  🔖 청크: {total_chunks}개
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

실패 시: 에러 메시지를 그대로 사용자에게 보여준다.
