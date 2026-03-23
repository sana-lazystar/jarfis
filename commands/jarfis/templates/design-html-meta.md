# Design HTML Meta Template

각 HTML 시안 파일 최상단에 다음 메타 정보를 HTML 주석으로 삽입한다.

```html
<!--
owner: DESIGN
projects: [{project_name}]
url: {url_path}
last_updated: {date}
last_updated_by: {ticket}
summary: {page_description}
responsive: {PC / PC + Mobile / PC + Mobile + Tablet}
-->
```

## 필드 설명

| 필드 | 설명 |
|------|------|
| owner | 항상 `DESIGN` |
| projects | 이 시안이 관련된 프로젝트 목록 |
| url | 시안이 나타내는 URL 경로 |
| last_updated | 최종 수정일 |
| last_updated_by | 수정을 유발한 티켓/워크플로우 |
| summary | 페이지 한 줄 설명 |
| responsive | 반응형 지원 범위 |
