# JARFIS — 사용 가능한 명령어 도움말

JARFIS 명령어 도우미입니다. 아래 사용 가능한 명령어 목록을 사용자에게 보여주세요.

---

다음을 그대로 출력하세요:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  JARFIS - IT Team Workflow Orchestration
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  사용 가능한 명령어:

  /jarfis:org
    Organization 정보 확인 (미등록 시 등록 안내)
  /jarfis:org-init
    Organization 신규 생성 (프로젝트 스캔 + wiki 구조)
    wiki 지식 누적 → 프로젝트 간 ADR·정책·디자인 자동 공유
  /jarfis:project-init [--depth basic|medium|deep]
    프로젝트 프로필 생성 (최초 1회, 각 프로젝트에서)
  /jarfis:project-update
    프로필 증분 갱신 (Git 이력 기반, 수시)
  /jarfis:work-meeting [기획 주제]
    PO+TL 기획 킥오프 미팅 (아이디어 탐색, 선택)
  /jarfis:work [기획 내용]
    전체 워크플로우 실행 (기획→설계→구현→리뷰→회고)
  /jarfis:work-continue [후속 작업] [--mode fix|extend]
    완료된 워크플로우 이어서 작업 (버그 수정 / 기능 확장)
  /jarfis:wiki-storyboard                          [Org]
    서비스 전체 디자인 카탈로그 브라우저 확인

  /jarfis:search-setup                              [Org]
    시맨틱 검색 활성화 (sentence-transformers 설치)
  /jarfis:search-index                              [Org]
    전체 Org wiki 시맨틱 인덱스 일괄 생성/갱신

  /jarfis:sys-upgrade     학습 항목 관리 + 에이전트 적용
  /jarfis:sys-distill     토큰 효율 분석 + 최적화
  /jarfis:sys-implement   JARFIS 시스템 자체 수정
  /jarfis:sys-version     버전 확인 + 업데이트
  /jarfis:sys-health      좀비 프로세스 진단/정리

  [Org] = Organization 등록 필요
    Org 등록 시 work/work-continue/work-meeting에 wiki 지식 자동 주입,
    Phase 6 회고에서 산출물이 wiki에 자동 누적됩니다.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  예시 A — Organization 사용 (권장):
    cd ~/your-company-name
    /jarfis:org-init                      ← Org 등록 (최초 1회)
    cd ~/your-company-name/my-project
    /jarfis:project-init                  ← 프로젝트별 최초 1회
    /jarfis:work-meeting 결제 시스템 리뉴얼
    /jarfis:work 결제 시스템 리뉴얼
    /jarfis:work-continue 카드 결제 오류 수정
    /jarfis:wiki-storyboard              ← 디자인 카탈로그 확인
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  예시 B — Org 없이 바로 시작:
    cd ~/my-project
    /jarfis:project-init
    /jarfis:work 게시판 CRUD + 댓글
    /jarfis:work-continue 댓글 알림 기능 추가 --mode extend
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```
