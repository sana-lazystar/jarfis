# Sitemap Template — Supplied Design Mode

> 외부 시안에 동봉되어 사용자가 작성하는 사이트맵 마크다운. supplied 모드에서 시스템이 자동 생성하지 않음 (SSOT 보존).

## 위치

`<suppliedPath>/sitemap.md` 또는 `<suppliedPath>/pages/sitemap.md`. Phase 6 Track B 가 `wiki/DESIGN/pages/{project}/sitemap.md` 로 sync.

## 권장 구조

```markdown
# {Project Name} Sitemap

## Top-level pages
- [Home](pages/home/index.html)
- [Pricing](pages/pricing/index.html)
- [About](pages/about/index.html)

## Auth flow
- [Sign up](pages/signup/index.html)
- [Sign in](pages/signin/index.html)
  - [Forgot password](pages/forgot-password/index.html)

## Account
- [Dashboard](pages/dashboard/index.html)
  - [Settings](pages/settings/index.html)
  - [Billing](pages/billing/index.html)
```

## 작성 원칙

- **사람이 읽기 위한 계층적 트리**. 메타데이터(route, depth, role)는 `ia.json` 에 둠.
- 링크는 시안 내부 상대경로 (`pages/{slug}/index.html`).
- 동적 라우트 (예: `/posts/:id`) 는 placeholder 로 표기.

## 미제공 시

- supplied 모드에서 sitemap.md 가 시안에 없으면 Phase 6 Track B 가 단순 page-listing 만 wiki 에 sync.
- 시스템이 자동 생성하지 않음 (SSOT 약속).
