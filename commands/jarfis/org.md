# JARFIS Org — Organization 정보 확인

현재 프로젝트가 속한 Organization 정보를 표시합니다.

사용자 요청: $ARGUMENTS

---

## 실행

```bash
python3 ~/.claude/scripts/jarfis_cli.py org info $(pwd)
```

JSON 출력의 `registered` 필드로 분기한다:

### `registered: true` — Org 등록됨

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Organization: {org_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Root: {org_root}
📋 Projects:
   - {name} ({type}) — {path}
   - {name} ({type}) — {path}
📚 Wiki: {wiki_file_count}개 파일
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### `registered: false` — 미등록

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Organization 미등록
━━━━━━━━━━━━━━━━━━━━━━━━━━

아직 Organization이 등록되지 않았습니다.

Organization을 등록하면:
  • 여러 프로젝트의 ADR·정책·디자인이 wiki에 누적됩니다
  • 새 워크플로우 시작 시 기존 지식이 자동 주입됩니다
  • 서비스 전체 디자인 카탈로그를 확인할 수 있습니다

등록하기: /jarfis:org-init
━━━━━━━━━━━━━━━━━━━━━━━━━━
```
