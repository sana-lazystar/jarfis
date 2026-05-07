# UX Direction Template

UX direction document from the PO to the UX Designer. Created as `$DOCS_DIR/ux-direction.md`.
Single-file structure — do not split.

```markdown
# UX Direction

## IA & URL Structure

| URL | Page | Description |
|-----|------|-------------|
| / | Home | |

## Tone & Voice

- Overall tone:
- Error message tone:
- CTA style:

## Pages

### / (Home)

**Heading**:
**Content**:
**Requirements**: What the user should be able to do
**Interaction Patterns**: (sync/async, loading strategy, etc.)

### /{url-path}

**Heading**:
**Content**:
**Requirements**:
**Interaction Patterns**:
```

## External Mockup Reference (supplied 모드 한정)

> `state.design.mode == "supplied"` 일 때만 채움. 다른 모드에서는 이 섹션 생략.

- 시안 위치 (`suppliedPath`): `<absolute path>`
- 페이지 수: `<M>`
- 브랜드 자산 디렉토리 (Org 공유 권장): `$ORG_ROOT/.jarfis-org/wiki/DESIGN/brand-assets/`
- 사이트맵: `pages/sitemap.md` (시안 동봉 시) 또는 `N/A`
- IA 메타: `pages/ia.json` (시안 동봉 시) 또는 `N/A`

> 이 섹션은 ux-designer 가 자동 생성하지 않는다 (SSOT — Critic blocker #3 흡수). supplied 모드 진입 시 jarfis-foreman 이 phase-results meta 와 동일한 정보를 기록.

