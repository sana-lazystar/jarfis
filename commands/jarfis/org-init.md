# JARFIS Org Init — Organization 초기화

새 Organization을 초기화합니다. 하위 프로젝트를 자동 스캔하고 wiki 구조를 생성합니다.

사용자 요청: $ARGUMENTS

---

## Step 1: 경로 결정

AskUserQuestion:
```
question: "Organization root 경로를 선택하세요 (하위 프로젝트들을 포함하는 상위 디렉토리)"
header: "Org Root"
options:
  - label: "현재 디렉토리"
    description: "{현재 CWD 절대경로}"
  - label: "경로 직접 입력"
    description: "다른 경로를 지정합니다"
```

"경로 직접 입력" 선택 시 → AskUserQuestion으로 경로 입력받기 (Other 사용)

`$ORG_ROOT` 변수에 선택된 절대경로를 저장한다.

---

## Step 2: Organization 이름 결정

`$ORG_ROOT`의 디렉토리명을 기본값으로 제안한다.

AskUserQuestion:
```
question: "Organization 이름을 정해주세요"
header: "Org Name"
options:
  - label: "{$ORG_ROOT의 디렉토리명}"
    description: "디렉토리 이름을 그대로 사용합니다"
  - label: "직접 입력"
    description: "다른 이름을 지정합니다"
```

"직접 입력" 선택 시 → AskUserQuestion으로 이름 입력받기 (Other 사용)

`$ORG_NAME` 변수에 저장한다.

---

## Step 3: 프로젝트 스캔

```bash
python3 ~/.claude/scripts/jarfis_cli.py org init "$ORG_ROOT"
```

JSON 출력의 `projects` 배열을 사용자에게 표시:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Organization 초기화: {$ORG_NAME}
━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 Root: {$ORG_ROOT}
🔍 감지된 프로젝트:
   - {name} ({type}) — {relative_path}
   - {name} ({type}) — {relative_path}
━━━━━━━━━━━━━━━━━━━━━━━━━━
```

프로젝트가 0개이면:
```
하위 프로젝트가 감지되지 않았습니다.
각 프로젝트에서 /jarfis:project-init을 먼저 실행해주세요.
```
출력 후 종료.

---

## Step 4: 확인 및 생성

AskUserQuestion:
```
question: "위 프로젝트들로 Organization '{$ORG_NAME}'을 생성할까요?"
header: "Confirm"
options:
  - label: "생성"
    description: "org-profile.md + wiki 구조를 생성합니다"
  - label: "취소"
    description: "초기화를 취소합니다"
```

"생성" 선택 시:
```bash
python3 ~/.claude/scripts/jarfis_cli.py org init "$ORG_ROOT" --confirm --name "$ORG_NAME"
```

결과 배너:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━
  Organization 생성 완료
━━━━━━━━━━━━━━━━━━━━━━━━━━
📂 {$ORG_ROOT}/.jarfis/org-profile.md
📚 {$ORG_ROOT}/.jarfis/wiki/
   ├── INDEX.md
   ├── PO/_index.md
   ├── DESIGN/_index.md
   ├── TA/_index.md
   └── QA/_index.md

다음 단계:
  1. cd {project_path} && /jarfis:project-init
  2. Wiki 시맨틱 검색 활성화 (선택):
     /jarfis:wiki-search-setup
━━━━━━━━━━━━━━━━━━━━━━━━━━
```
