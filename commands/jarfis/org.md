# JARFIS Org — Organization 목록 및 정보

등록된 전체 Organization 목록을 표시합니다.

사용자 요청: $ARGUMENTS

---

## 실행

1. orgs.json에서 등록된 Org 목록을 읽는다:
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
        print(json.dumps(json.load(f), ensure_ascii=False))
else:
    print(json.dumps({'orgs': []}))
"
```

2. 현재 CWD의 Org 컨텍스트도 확인한다:
```bash
python3 ~/.claude/scripts/jarfis_cli.py org info $(pwd)
```

3. 결과를 조합하여 출력한다:

### Org이 1개 이상 등록된 경우

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS Organizations
━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 등록된 Org: {count}개

  {org_name} ← 현재 (CWD가 이 Org 안일 때만 표시)
    📂 {root}
    📋 Projects: N개
    📚 Wiki: 있음/없음

  {org_name}
    📂 {root}
    📋 Projects: N개
    📚 Wiki: 있음/없음

━━━━━━━━━━━━━━━━━━━━━━━━━━
```

각 Org에 대해 `jarfis_cli.py org info {root}`를 실행하여 프로젝트 수와 wiki 여부를 확인한다.
CWD가 특정 Org의 root 하위에 있으면 해당 Org에 `← 현재` 표시를 붙인다.

### Org이 0개인 경우

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Organization 미등록
━━━━━━━━━━━━━━━━━━━━━━━━━━

등록된 Organization이 없습니다.

Organization을 등록하면:
  • 여러 프로젝트의 ADR·정책·디자인이 wiki에 누적됩니다
  • 새 워크플로우 시작 시 기존 지식이 자동 주입됩니다
  • 서비스 전체 디자인 카탈로그를 확인할 수 있습니다

등록하기: /jarfis:org-init
━━━━━━━━━━━━━━━━━━━━━━━━━━
```
