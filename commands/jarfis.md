# JARFIS - IT Team Workflow Orchestration

JARFIS 명령어 도우미입니다. 아래 사용 가능한 명령어 목록을 사용자에게 보여주세요.

---

다음을 그대로 출력하세요:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS - IT Team Workflow Orchestration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  사용 가능한 명령어:

  /jarfis:project-init [--depth basic|medium|deep]
    현재 프로젝트 디렉토리를 분석하여 프로필을 생성합니다.
    기본 깊이: deep. 산출물: ./.jarfis/project-profile.md
    /jarfis:work 시 서브에이전트가 자동 참조 → 토큰 절약 + 컨벤션 준수

  /jarfis:project-update
    기존 프로필을 기반으로 변경된 부분만 감지하여 증분 갱신합니다.
    Git 이력 기반으로 변경 섹션만 재분석 → init 대비 토큰 대폭 절약
    ※ 프로필이 없으면 /jarfis:project-init을 먼저 실행하라고 안내

  /jarfis:meeting [기획 주제]
    아이디어 탐색을 위한 기획 킥오프 미팅을 시작합니다.
    PO와 Tech Lead가 사용자와 자유롭게 토론하며 아이디어를 구체화합니다.
    산출물: ./.jarfis/meetings/{기획명}/ (summary, 회의록, 결정사항, 기술조사)
    ※ /jarfis:work 실행 시 미팅 산출물을 자동으로 감지/참조합니다.

  /jarfis:work [기획 내용]
    기획을 입력하면 전체 개발 워크플로우를 자동 실행합니다.
    Phase 0~6: 학습 로드 → 기획 구체화 → 설계 → UX → 구현 → 리뷰 → 회고

  /jarfis:upgrade
    JARFIS 학습 파일(~/.claude/jarfis-learnings.md)을 관리합니다.
    학습 항목 CRUD + universal/project scope 자동 분류 + 에이전트 적용
    [universal] → agent Learned Rules, [project] → .jarfis/context.md
    애매한 항목은 Advocate/Critic 토론으로 scope 확정

  /jarfis:health [--clean]
    시스템 헬스체크: 좀비 Claude 프로세스 진단 및 정리
    --clean: 바로 정리 실행 (좀비 없으면 알림, 있으면 정리 후 결과 표시)

  /jarfis:distill [파일명]
    JARFIS 프롬프트 파일의 토큰 효율을 분석하고 최적화합니다.
    중복 제거 + 템플릿 외부화 + 규칙 통합 → Before/After 리포트
    파일명 생략 시 토큰 비용 상위 3개 파일을 자동 선택
    절감률 30%↑ 시 Advocate/Critic Dialectic Review 자동 실행

  /jarfis:version
    JARFIS 버전 확인, 업데이트 체크, 업데이트 실행, 특정 버전 설치
    Git 기반 배포 관리

  /jarfis:implement [수정 내용] [--review=major|minor|patch]
    JARFIS 시스템 자체를 수정/기능 추가합니다.
    인덱스 파일을 읽고 → 수정 → 인덱스 자동 갱신 → 버전 범프
    --review 플래그로 Advocate/Critic Dialectic Review 수준 지정

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  권장 순서:
    1. cd my-project && /jarfis:project-init     ← 프로젝트 프로필 생성 (최초 1회)
    2. /jarfis:project-update                    ← 변경사항 반영 (수시)
    3. /jarfis:meeting 결제 시스템 리뉴얼  ← 아이디어 탐색 (선택)
    4. /jarfis:work 결제 시스템 리뉴얼    ← 워크플로우 실행
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  예시:
    /jarfis:project-init
    /jarfis:project-init --depth medium
    /jarfis:project-update
    /jarfis:meeting 결제 시스템 리뉴얼
    /jarfis:work 결제 시스템 리뉴얼
    /jarfis:work 결제 시스템 리뉴얼 --meeting 결제-시스템-리뉴얼
    /jarfis:upgrade
    /jarfis:distill
    /jarfis:distill work.md
    /jarfis:version
    /jarfis:health
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
