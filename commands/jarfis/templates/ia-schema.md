# ia.json Schema — Supplied Design Mode

> 외부 시안에 동봉되어 사용자가 작성하는 IA(Information Architecture) JSON. supplied 모드에서 시스템이 자동 생성하지 않음.

## 위치

`<suppliedPath>/ia.json` 또는 `<suppliedPath>/pages/ia.json`. Phase 6 Track B 가 `wiki/DESIGN/pages/{project}/ia.json` 으로 sync.

## 스키마

```json
{
  "version": "1.0",
  "project": "string",
  "pages": [
    {
      "slug": "home",
      "path": "pages/home/index.html",
      "title": "Home",
      "route": "/",
      "depth": 0,
      "parent": null,
      "role": "public",
      "tags": ["landing"],
      "primary_cta": "Sign up",
      "linked_pages": ["pricing", "signup"]
    },
    {
      "slug": "dashboard",
      "path": "pages/dashboard/index.html",
      "title": "Dashboard",
      "route": "/dashboard",
      "depth": 1,
      "parent": null,
      "role": "auth",
      "linked_pages": ["settings", "billing"]
    }
  ]
}
```

## 필수 필드

- `version`, `project`, `pages[]`
- 각 page: `slug`, `path`, `title`, `route`, `depth`, `role`
- `role` 허용값: `public` | `auth` | `admin`

## 선택 필드

- `parent`, `tags`, `primary_cta`, `linked_pages`

## 미제공 시

- supplied 모드에서 ia.json 이 시안에 없으면 wiki sync 시 ia.json 생략.
- **시스템 자동 생성 금지** (SSOT 약속). 사용자가 직접 작성.

## Validation

- Phase 6 Track B 는 ia.json 존재 시 단순 rsync 만 수행. 스키마 검증은 v4.7+ 에서 도입 예정.
