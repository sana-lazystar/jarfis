# JARFIS Org — Organization 관리

Organization 정보를 확인하거나 새로 초기화합니다.

사용자 요청: $ARGUMENTS

---

## 플래그 파싱

- `--init` → **초기화 모드**
- 플래그 없음 → **정보 모드** (기본)

---

## 정보 모드 (기본)

현재 프로젝트가 속한 Organization 정보를 표시한다.

1. `jarfis_cli.py org info $(pwd)` 실행
2. 성공 시: Org 정보 배너 표시
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
3. 실패 시 (Org 미등록):
   ```
   Organization이 등록되지 않았습니다.
   등록하려면: /jarfis:org --init
   ```

---

## 초기화 모드 (--init)

새 Organization을 초기화한다.

**Step 1: 경로 결정**

AskUserQuestion:
```
question: "Organization root 경로를 선택하세요 (하위 프로젝트들을 포함하는 상위 디렉토리)"
header: "Org Root"
options:
  - label: "현재 디렉토리"
    description: "{현재 CWD 경로}"
  - label: "경로 직접 입력"
    description: "다른 경로를 지정합니다"
```

"경로 직접 입력" 선택 시 → AskUserQuestion으로 경로 입력받기

**Step 2: 프로젝트 스캔**

```bash
python3 ~/.claude/scripts/jarfis_cli.py org init "$ORG_ROOT"
```

JSON 출력의 `projects` 배열을 사용자에게 표시:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Organization 초기화
━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Root: {org_root}
🔍 감지된 프로젝트:
   - {name} ({type}) — {relative_path}
   - {name} ({type}) — {relative_path}
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Step 3: 확인 및 생성**

AskUserQuestion:
```
question: "위 프로젝트들로 Organization을 생성할까요?"
header: "Confirm"
options:
  - label: "생성"
    description: "org-profile.md + wiki 구조를 생성합니다"
  - label: "취소"
    description: "초기화를 취소합니다"
```

"생성" 선택 시:
```bash
python3 ~/.claude/scripts/jarfis_cli.py org init "$ORG_ROOT" --confirm
```

결과 배너:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Organization 생성 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 {org_root}/.jarfis/org-profile.md
📚 {org_root}/.jarfis/wiki/
   ├── INDEX.md
   ├── PO/_index.md
   ├── DESIGN/_index.md
   ├── TA/_index.md
   └── QA/_index.md
━━━━━━━━━━━━━━━━━━━━━━━━━━

다음 단계:
  cd {project_path} && /jarfis:project-init
```
