# /jarfis:storyboard — 디자인 카탈로그 브라우징

사용자가 디자인 카탈로그를 열려고 합니다: $ARGUMENTS

## 목적
워크플로우 외 시점에서도 서비스의 전체 디자인 현황을 브라우저에서 확인.

## 전제 조건
- Organization 등록 완료 (`org-profile.md` 존재)
- `wiki/DESIGN/pages/{project}/` 에 시안 존재 (최소 1회 이상 워크플로우 완료)

## 흐름

1. **Org 확인**
   ```bash
   python3 ~/.claude/scripts/jarfis_cli.py org info $(pwd)
   ```
   - 실패 시: "Organization이 등록되지 않았습니다. `/jarfis:work`를 먼저 실행하세요." 출력 후 종료

2. **FE 프로젝트 목록 추출**
   - `org info` JSON의 `projects` 배열에서 FE/Fullstack 타입 프로젝트만 필터링
   - 프로젝트가 0개면: "FE 프로젝트가 없습니다." 출력 후 종료

3. **프로젝트 선택** (AskUserQuestion)
   ```
   question: "디자인 카탈로그를 열 프로젝트를 선택하세요:"
   header: "Design"
   options:
     - label: "{project_1}"
       description: "{project_1_path}"
     - label: "{project_2}"
       description: "{project_2_path}"
   ```
   - 프로젝트가 1개면 자동 선택

4. **카탈로그 열기**
   ```bash
   open {org_root}/.jarfis/wiki/DESIGN/pages/{selected_project}/_index.html
   ```
   - `_index.html` 미존재 시: "시안이 아직 없습니다. `/jarfis:work`에서 Phase 3을 완료하세요." 출력

5. **결과 표시**
   ```
   ━━━━━━━━━━━━━━━━━━━━━━━━━━
   📖 Design Catalog: {project}
   📂 {path_to_index_html}
   ━━━━━━━━━━━━━━━━━━━━━━━━━━
   ```
