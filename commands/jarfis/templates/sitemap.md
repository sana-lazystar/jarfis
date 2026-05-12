# Sitemap Template — Supplied Design Mode

> 외부 시안에 동봉되어 사용자가 작성하는 사이트맵 마크다운. **supplied 모드 한정** — 시스템이 자동 생성하지 않음 (SSOT 보존).
>
> **IA 일원화 약속 (v4.14+, Stage 7)**: 사이트맵의 정량 메타데이터 (route, depth, role, parent, navigation) 는 **IA SSOT 가 담당** (`templates/ia-schema.md`). 이 sitemap.md 는 사람-읽기용 계층 트리만 담는다.
> Phase 1b PO 가 IA `manifest.json` 을 author 한 뒤, 필요 시 manifest 로부터 sitemap.md 를 자동 렌더할 수도 있다 (Stage 4+ TBD).

## 위치

`<suppliedPath>/sitemap.md` 또는 `<suppliedPath>/pages/sitemap.md`. Phase 6 Track B 가 `wiki/DESIGN/pages/{project}/sitemap.md` 로 단순 rsync (자동 생성 X).

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
