# JARFIS Design Spec — Supplied Design Mode Brief

> **Locale**: Render the output below in `$LOCALE` (ko/en/ja). Internal instructions in this file are English.

A read-only skill. When invoked, **render the spec sheet below verbatim** to the screen so the user can copy and forward it to an external worker (designer / outsourcer / another LLM). The worker produces design artifacts conforming to this spec; the user then starts `/jarfis:work` and inputs the artifact directory's absolute path at Phase 0 step 11 (`state.design.suppliedPath`).

## Behavior contract

1. **Output-only**. Do not create directories, do not validate any path, do not call other tools beyond the render. No subcommands.
2. **Self-contained**. The rendered output must be a complete brief that an external worker can act on without any other JARFIS context.
3. **Locale-aware**. Translate the spec text into `$LOCALE`. Keep file paths, code blocks, and JSON keys verbatim.
4. **Source of truth**. The directory contract and file requirements below are derived from `~/.claude/commands/jarfis/prompts/phase3.md:537-668` (Branch C — supplied path) and `phase3.md:7-15` (Triple SSOT). Re-sync this file when phase3.md supplied contract changes.

## Render this output

````markdown
# JARFIS Supplied-Mode Design Spec

> 이 문서를 그대로 복사해서 외부 작업자(디자이너 / 외주 / 다른 LLM)에게 전달하세요.
> 작업자가 아래 스펙대로 결과물을 만들어 디렉토리 형태로 돌려주면, 사용자는 받은 디렉토리의 절대경로를 `/jarfis:work` 시작 시 입력합니다.

---

## 1. 우리가 디자인을 소비하는 방식 (Triple SSOT)

JARFIS는 디자인 산출물 세 가지를 각자 다른 권위(authority)로 소비합니다. 한 가지로 대체할 수 없습니다.

| 산출물 | 권위 (authority) | 누가 어떻게 쓰는가 |
|---|---|---|
| `reference.png` (필수) | **Visual authority** | Phase 5에서 `compare_design` MCP가 픽셀 단위로 구현물과 diff. LLM은 PNG를 직접 보지 않음 — diff %와 diff-image만 소비. |
| `index.html` (필수) | **Markup authority** | Phase 4에서 프런트엔드 에이전트가 마크업/레이아웃 참조용으로 직접 읽음. **그대로 복사하지는 않음** (프로젝트 스택에 맞게 재구현). |
| `token-map.json` (선택) | **Design-token authority** | 프런트엔드 구현 시 raw hex보다 우선. CSS 변수로 매핑. |

**핵심 원칙**: 시안이 유일한 진실의 출처입니다. 시스템은 시안에 **없는 정보를 자동 생성하지 않습니다**. 누락된 항목은 누락된 채로 다운스트림에 전달됩니다.

---

## 2. 디렉토리 구조

```
<your-artifact-root>/                     ← 작업자가 만든 폴더 (이름·위치 자유)
  pages/
    {slug-1}/
      index.html                          [필수]
      reference.png                       [필수]
      reference-mobile.png                [선택; 미동봉 시 시스템이 자동 캡처]
      reference-tablet.png                [선택]
    {slug-2}/
      index.html
      reference.png
    ...
  assets/                                 [선택] 이미지·폰트·아이콘 — index.html 에서 상대경로 참조
  token-map.json                          [선택] 컬러·타이포 토큰 매핑
  sitemap.md                              [선택] 사람-읽기용 페이지 계층
  ia.json                                 [선택] IA manifest (L0+L1 권장)
```

**규칙**:
- `pages/{slug}/` 는 최소 1개 이상. `slug` 는 `^[a-z][a-z0-9-]*$` (소문자·숫자·하이픈만).
- 각 `slug` 폴더에 `index.html` + `reference.png` 가 모두 있어야 함 (둘 중 하나라도 누락 시 시스템 검증 실패).
- `assets/` 는 폴더가 비어있어도 무방. 시안 HTML이 외부 자산을 참조하지 않으면 생략 가능.
- 절대경로 강제 없음. 작업자는 자기 PC 어디든 위 구조로 만들면 됨 — 사용자가 받은 후 경로를 시스템에 알려줌.

---

## 3. 파일별 요구사항

### `pages/{slug}/index.html` (필수)

- **Self-contained 권장**. inline `<style>` 사용 가능. 외부 CSS/JS 파일이 필요하면 같은 디렉토리 또는 상위 `../../assets/` 상대경로로만 참조.
- **목적**: 시스템이 마크업 구조와 의도된 레이아웃을 파악하기 위함. 실제 구현은 다른 기술 스택으로 재작성됨.
- **금지**: 외부 CDN URL 참조 (오프라인 렌더링 실패), `<script>`로 동적 생성되는 핵심 UI (정적 HTML이 SSOT임).
- **권장**: semantic HTML (`<header>`, `<nav>`, `<main>`, `<footer>` 등), 명시적 CSS 변수 (`--color-primary`, `--font-body` 등).

### `pages/{slug}/reference.png` (필수)

- **fullPage 스크린샷**. 페이지 전체가 한 장에 들어가야 함 (스크롤 영역 포함).
- **PC 베이스라인**: `1920×1080` 뷰포트 기준 캡처 권장. 가로 폭이 다르면 시스템이 비교 시 보정.
- **목적**: Phase 5의 픽셀 diff 기준. 폰트·간격·색상이 최종 시안과 일치해야 함.

### `pages/{slug}/reference-mobile.png` (선택)

- 미동봉 시 시스템이 `index.html` 을 Playwright `390×844` (iPhone 14 기준)로 자동 캡처.
- 동봉하면 시안 동봉본이 우선. responsive 디자인 의도를 보존하고 싶으면 동봉 권장.

### `pages/{slug}/reference-tablet.png` (선택)

- 동일 패턴. 시스템 자동 캡처는 `768×1024`.

### `token-map.json` (선택)

JSON 스키마 예시:

```json
{
  "colors": {
    "primary":   "#2C5282",
    "secondary": "#4A5568",
    "background":"#F7FAFC",
    "surface":   "#FFFFFF",
    "text-primary":   "#1A202C",
    "text-secondary": "#4A5568",
    "border":   "#E2E8F0"
  },
  "typography": {
    "font-family-base": "'Pretendard', -apple-system, sans-serif",
    "font-family-mono": "'JetBrains Mono', monospace",
    "scale": {
      "h1": "32px",
      "h2": "24px",
      "h3": "20px",
      "body": "16px",
      "caption": "14px"
    }
  },
  "spacing": {
    "xs": "4px",
    "sm": "8px",
    "md": "16px",
    "lg": "24px",
    "xl": "32px"
  },
  "radius": {
    "sm": "4px",
    "md": "8px",
    "lg": "16px"
  }
}
```

키 이름은 자유 — 단 일관성 유지. 미동봉 시 프런트엔드는 raw hex로 폴백.

### `sitemap.md` (선택)

사람-읽기용 페이지 계층 마크다운. 메타데이터는 `ia.json` 에 둠.

```markdown
# {Project Name} Sitemap

## Top-level pages
- [Home](pages/home/index.html)
- [Pricing](pages/pricing/index.html)

## Auth flow
- [Sign up](pages/signup/index.html)
- [Sign in](pages/signin/index.html)
  - [Forgot password](pages/forgot-password/index.html)
```

링크는 시안 내부 상대경로. 동적 라우트 (`/posts/:id`)는 placeholder 표기.

### `ia.json` (선택)

IA manifest. L0 (위치) + L1 (목적) 만 필수, L2+는 비워둬도 다운스트림 PO가 보강함.

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
      "depth": 0
    },
    {
      "slug": "pricing",
      "route": "/pricing",
      "title": "Pricing",
      "role": "public",
      "parent": null,
      "depth": 0
    }
  ]
}
```

**필수 필드 per page**: `slug`, `route`, `title`, `role` (`public`|`auth`|`admin`), `parent` (null 또는 다른 slug), `depth` (정수). `slug` 중복 금지, `route` 중복 금지.

---

## 4. 작업자 자체 검증 체크리스트

제출 전 아래 항목을 확인하세요.

- [ ] `pages/` 폴더가 존재하고, 최소 1개 이상의 `{slug}/` 가 있다.
- [ ] 모든 `{slug}/` 폴더에 `index.html` 과 `reference.png` 가 둘 다 있다.
- [ ] `slug` 이름이 소문자·숫자·하이픈만 사용한다 (`^[a-z][a-z0-9-]*$`).
- [ ] `index.html` 을 브라우저로 직접 열어 렌더링이 정상이다 (오프라인 환경에서도).
- [ ] `index.html` 이 외부 CDN URL 을 참조하지 않는다 (자산은 `assets/` 또는 inline).
- [ ] `reference.png` 가 fullPage 캡처이다 (스크롤 영역 잘림 없음).
- [ ] (선택) `token-map.json` JSON 문법 오류 없음.
- [ ] (선택) `ia.json` 에서 `slug` / `route` 중복 없음, `parent` 가 실재 slug 또는 null.

---

## 5. 사용자에게 전달하는 방법

1. 위 구조로 결과물을 폴더 하나로 묶어 zip 또는 폴더 자체로 전달.
2. 사용자는 결과물을 자기 PC 임의 경로에 풀어둠 (예: `~/Downloads/proj-design/`, `/Users/foo/work/feature-xyz-design/`).
3. 사용자가 `/jarfis:work <description>` 실행 → Phase 0 step 11에서 supplied 모드 선택 → 위에서 풀어둔 폴더의 **절대경로** 입력.
4. 시스템이 디렉토리를 검증하고 (`pages/` + 각 페이지 `index.html`+`reference.png` 존재), Phase 3가 자동으로 픽업.

---

## 6. 자주 묻는 질문

**Q. 페이지가 정말 1개뿐인데 `pages/{slug}/` 형태가 꼭 필요한가요?**
네. 단일 페이지여도 `pages/home/index.html` + `pages/home/reference.png` 구조를 유지해주세요. 시스템 검증이 이 구조를 가정합니다.

**Q. 디자인 토큰 파일이 figma export와 호환되나요?**
네. Figma의 Variables / Tokens Studio export를 위 스키마에 맞게 변환만 하면 됩니다. 키 이름은 자유 — colors/typography/spacing/radius 같은 큰 카테고리만 분리해주세요.

**Q. `assets/` 경로는 어떻게 참조하나요?**
`pages/home/index.html` 에서 이미지를 쓸 때 `../../assets/logo.svg` 형태 상대경로로 참조. 시스템이 디렉토리 전체를 통째로 복사하므로 상대경로가 깨지지 않습니다.

**Q. brand 자산 (로고/폰트 파일/공식 컬러 팔레트) 은 어디에?**
이 디렉토리 안의 `assets/` 에 넣지 마세요. brand 자산은 조직 차원에서 공유되는 별도 위치(`$ORG_ROOT/.jarfis-org/wiki/DESIGN/brand-assets/`)에서 관리됩니다. 시안 안에는 brand 자산을 사용한 결과물만 넣어주세요.

---

## 7. JARFIS 내부 참조 (작업자가 알 필요 없음)

이 스펙의 원본 contract는 다음에 있습니다:

- 디렉토리 구조: `~/.claude/commands/jarfis/prompts/phase3.md:555-570`
- SSOT 원칙: `~/.claude/commands/jarfis/prompts/phase3.md:541-553`
- 검증 로직: `~/.claude/commands/jarfis/prompts/phase3.md:572-595`
- Triple SSOT: `~/.claude/commands/jarfis/prompts/phase3.md:7-15`
- IA manifest 스키마: `~/.claude/commands/jarfis/templates/ia-schema.md`
- Sitemap 템플릿: `~/.claude/commands/jarfis/templates/sitemap.md`
````

---

## Maintenance Notes (for JARFIS authors only — NOT rendered to user)

- This skill mirrors `prompts/phase3.md:537-668` (Branch C). When that contract changes, update the rendered output above.
- The "Triple SSOT" block (Section 1) must stay aligned with `prompts/phase3.md:7-15`.
- The `token-map.json` filename was reconciled in v4.20.0 — historical references to `tokens.json` are obsolete.
- No state file is written by this command. No `$DOCS_DIR` interaction. Purely a render.
