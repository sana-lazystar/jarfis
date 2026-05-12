# UX Direction Template

UX direction document from the PO to the UX Designer. Created as `$DOCS_DIR/ux-direction.md`.
Single-file structure — do not split.

> **Stage 8 (v4.17+)**: IA & URL Structure 메타데이터는 `$DOCS_DIR/discovery/ia/manifest.json` 에 (PO SSOT, Stage 1+). Pages 디테일 (Heading/Content/Requirements/Interaction Patterns) 은 `$DOCS_DIR/discovery/ia/pages/{slug}.md` 의 `## Notes` body 로 흡수됨. ux-direction.md 는 페이지-비특이적 톤 + (supplied 모드 한정) 외부 시안 reference 만 담는다.

```markdown
# UX Direction

## Tone & Voice

- Overall tone:
- Error message tone:
- CTA style:
```

## External Mockup Reference (supplied 모드 한정)

> `state.design.mode == "supplied"` 일 때만 채움. 다른 모드에서는 이 섹션 생략.

- 시안 위치 (`suppliedPath`): `<absolute path>`
- 페이지 수: `<M>`
- 브랜드 자산 디렉토리 (Org 공유 권장): `$ORG_ROOT/.jarfis-org/wiki/DESIGN/brand-assets/`
- 사이트맵: `pages/sitemap.md` (시안 동봉 시) 또는 `N/A`
- IA 메타: `pages/ia.json` (시안 동봉 시) 또는 `N/A`

> 이 섹션은 ux-designer 가 자동 생성하지 않는다 (SSOT — Critic blocker #3 흡수). supplied 모드 진입 시 jarfis-foreman 이 phase-results meta 와 동일한 정보를 기록.

