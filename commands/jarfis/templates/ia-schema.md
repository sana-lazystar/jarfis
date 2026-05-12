# IA Schema (v2.0) — PO SSOT

> **Information Architecture** 의 단일 진실 (Single Source of Truth). Phase 1b PO 가 항상 author 한다 (디자인 모드 무관).
> **이 문서는 reference. 진실은 `~/.claude/scripts/jarfis/ia.py` 의 `validate_ia` 가 정의 + enforce 한다.** 충돌 시 코드가 우선.

## 저장 구조

```
docs/discovery/ia/
├── manifest.json         # L0 위치 + L1 목적 (요약 메타)
├── pages/{slug}.md       # L2 데이터/API + L3 컴포넌트 (페이지별 frontmatter + Notes body)
└── shared.json           # L4 cross-cutting (optional — design tokens, layout shells, global state)
```

Phase 6 가 work IA 를 Org IA (`.jarfis-org/wiki/PO/projects/{slug}/ia/`) 로 3-way merge.

## L0~L4 계층 (audit:38-62 매핑)

| Layer | 위치 | 내용 |
|-------|------|------|
| L0 — Location | `manifest.pages[].slug` + `route` + `parent` + `depth` | 페이지 식별, URL, 트리 위치 |
| L1 — Purpose | `manifest.pages[].title` + `pages/{slug}.md` frontmatter `purpose` / `user_tasks` | 페이지가 존재하는 이유 |
| L2 — Data/API | `pages/{slug}.md` frontmatter `data_sources` / `api_endpoints` | 페이지가 부르는 데이터 계약 |
| L3 — Components | `pages/{slug}.md` frontmatter `components` + `navigation.entry_from` / `exits_to` | 페이지 내부 컴포넌트 + 진입/탈출 흐름 |
| L4 — Shared | `shared.json` | 페이지 cross-cutting (design tokens, layout shells, global state) |

## `manifest.json` 스키마

```json
{
  "version": "2.0",
  "project": "string",
  "pages": [
    {
      "slug": "home",
      "route": "/",
      "title": "Home",
      "role": "public",
      "parent": null,
      "depth": 0,
      "detail": "pages/home.md",
      "tags": ["landing"]
    },
    {
      "slug": "dashboard",
      "route": "/dashboard",
      "title": "Dashboard",
      "role": "auth",
      "parent": null,
      "depth": 0,
      "detail": "pages/dashboard.md"
    }
  ]
}
```

### 필수 필드

- top-level: `version`, `project`, `pages[]`
- `version` 은 `"2.0"` (R2). v1.0 은 deprecated — `validate_ia` 가 R2 violation 으로 reject.
- 각 page entry: `slug`, `route`, `title`, `role`, `parent`, `depth`
- `slug` regex `^[a-z][a-z0-9-]*$` (R3, 중복 금지 R4)
- `route` 중복 금지 (R5)
- `parent` 는 다른 page 의 `slug` 또는 `null` (R6)
- `role` 허용값: `public` | `auth` | `admin`
- `depth` 정수, `parent` chain 최대 8 (R12 — strict warning over 8)

### 선택 필드

- `detail` — page 상세 파일 경로 (`pages/{slug}.md` default)
- `tags` — 자유 label

## `pages/{slug}.md` 스키마

```markdown
---
slug: home
route: /
title: Home
role: public
depth: 0
parent: null
purpose: "방문자가 제품 가치를 1분 안에 이해하도록 한다"
user_tasks:
  - "Sign up 으로 이동"
  - "Pricing 페이지로 이동"
data_sources: []
api_endpoints: []
components:
  - hero
  - feature-grid
  - pricing-cta
navigation:
  entry_from: []
  exits_to: [pricing, signup]
---

## Notes
<자유 본문 — Pages 디테일 (Heading/Content/Requirements/Interaction Patterns 흡수)>
```

### Frontmatter 필수 필드 (R10 — strict)

- `slug`, `route`, `title`, `role`, `depth`
- `slug` 는 manifest entry 의 `slug` 와 정확히 일치 (R8)
- 파일명 stem 도 manifest 에 등록된 slug 와 1:1 (R9 — orphan 금지)

### Frontmatter 선택 필드

- `parent`, `purpose`, `user_tasks[]`, `data_sources[]`, `api_endpoints[]`, `components[]`
- `navigation.entry_from[]` / `navigation.exits_to[]` — 각 ref 는 valid slug (R11 — strict)

### Notes body

- 페이지 디테일 (Stage 8 — ux-direction.md Pages 섹션 흡수) 를 담는다.
- frontmatter 의 정량 정보와 별개의 사람-읽기용 노트.
- **권장 sub-headings** (audit R-22 mitigation — 디자이너 brief 의 strict format 보존):
  ```markdown
  ## Notes

  **Heading**: <페이지 상단 제목 + sub-copy>
  **Content**: <주요 콘텐츠 블록 — 위에서 아래 순서>
  **Requirements**: <사용자가 이 페이지에서 할 수 있어야 하는 것>
  **Interaction Patterns**: <sync/async, loading strategy, error handling, animation 등>
  ```
- 위 4개 sub-headings 은 권장이며 강제 아님. 페이지 성격에 따라 추가/생략 가능.

## `shared.json` 스키마 (optional, L4)

```json
{
  "design_tokens": { "color": {...}, "spacing": {...} },
  "layout_shells": [...],
  "global_state": [...]
}
```

키 구조는 프로젝트가 자유롭게 정의. `validate_ia` 가 schema 검증하지 않음 (L4 free-form).

## Validation Rules (R1~R12)

`scripts/jarfis/ia.py:24-36` enumeration. **이 문서가 아닌 코드가 진실.**

| Rule | 검증 | Strict only |
|------|------|-------------|
| R1 | `manifest.json` 존재 | always |
| R2 | `manifest.version == "2.0"` | always |
| R3 | slug regex `^[a-z][a-z0-9-]*$` | always |
| R4 | 중복 slug 금지 | always |
| R5 | 중복 route 금지 | always |
| R6 | `parent` 가 slug set 또는 `null` | always |
| R7 | `pages/{slug}.md` 가 각 manifest entry 마다 존재 | always |
| R8 | frontmatter `slug == manifest.slug` | always |
| R9 | orphan `pages/*.md` 금지 (manifest 와 1:1) | always |
| R10 | frontmatter 필수 필드 (slug, route, title, role, depth) | strict |
| R11 | `navigation.entry_from` / `exits_to` ref 가 valid slug | strict |
| R12 | parent chain 비순환 (error) + depth ≤ 8 (warning) | always (cycle) / strict (depth) |

호출:
```bash
python3 ~/.claude/scripts/jarfis_cli.py ia validate <ia_dir> [--non-strict]
```
실패 시 exit code 2.

## 모드별 흐름

### supplied 모드 (외부 시안 동봉본 활용)

- 시안 제작자가 `<suppliedPath>/ia.json` 을 동봉할 수 있다 — **보조 reference** (audit:435 D8).
- Phase 1b PO 가 동봉 `ia.json` 을 **import** 해서 자체 `discovery/ia/manifest.json` 을 author. SSOT 는 `discovery/ia/`.
- Phase 3 jarfis-foreman 은 동봉 `ia.json` 을 `wiki/DESIGN/pages/{project}/ia.json` 으로 단순 rsync — **자동 생성 금지** (history reference 용).
- 동봉본이 없으면 PO 가 zero-base author.

### designed-here 모드 (시스템이 디자인 직접 진행)

- Phase 1b PO 가 zero-base author. supplied 흐름과 동일하지만 시안 import 단계 없음.

## v1.0 → v2.0 migration

- v1.0 schema (route/depth 평탄, 단일 ia.json) 는 **deprecated** (Stage 1 verdict.json:34).
- `validate_ia` 가 `version == "1.0"` 을 R2 violation 으로 reject — error message: `"R2: manifest.version is '1.0', expected '2.0'"`.
- 잠재 v1.0 `ia.json` 발견 시: pages 를 `manifest.json` + `pages/{slug}.md` 로 split, frontmatter 채우기.

## SSOT 약속 (D1, D2, D3, D8 매핑)

- **D1** — IA = PO 의 SSOT. design.mode 무관 author.
- **D2** — L0~L4 계층 분리 (이 문서 상단 표).
- **D3** — `manifest.json` + `pages/` + `shared.json` 분리 저장.
- **D8** — supplied 동봉 `ia.json` 은 보조 reference. PO 가 import 후 자체 manifest 로 author.

## 관련 문서

- `~/.claude/scripts/jarfis/ia.py` — schema enforcement (코드 진실)
- `~/.claude/commands/jarfis/templates/sitemap.md` — supplied 모드 sitemap.md (사람-읽기 트리; metadata 는 ia 가 담당)
- `~/.claude/commands/jarfis/prompts/phase1b.md` — PO IA author 흐름 (Stage 4 에서 보강 예정)
- `~/.claude/commands/jarfis/prompts/phase6.md` — Org IA 3-way merge (Stage 6a DONE)
- `~/repos/jarfis/.personal/sys-implements/ia-as-po-ssot-v2-spine/validation/audit-report.md` — 전체 ADR 흐름 (D1~D12)
