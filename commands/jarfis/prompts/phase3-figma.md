# Phase 3 Figma-Driven Design Path — Agent Prompts

> Executed when a Figma URL is provided in Phase 3 (i.e., when a designer is involved).
> The output contract is identical to the existing text path: `$DOCS_DIR/design/{path}/index.html`
>
> **v5 Update (2026-03-27)**: A/B test results confirmed that routing through HTML mockups
> significantly outperforms direct generation in layout accuracy. HTML mockups are retained,
> but **section-by-section split generation** improves efficiency/stability.
> Details: `~/UX-AI/workflow/figma-to-html-v5.md`
> **Locale**: Present ALL user-facing output in $LOCALE language. Internal reasoning: English.

---

## Multiple Figma Page Parallel Processing (v5)

> The `phases.3.figma_pages` array in `.jarfis-state.json` may contain multiple pages.
> Execute Steps 3-F0~3-F3 **in parallel** for each page (up to 5 pages concurrently).
> Each page produces independent deliverables in `$DOCS_DIR/design/{page_path}/`.
> `{page_path}` is the kebab-case conversion of figma_pages[].title (e.g., "Benefits Signup" → "benefits-signup").

```
figma_pages example:
[
  {"title": "Benefits Signup", "url": "https://figma.com/design/xxx?node-id=123-456"},
  {"title": "Membership History", "url": "https://figma.com/design/xxx?node-id=789-012"}
]
```

**Execute Steps 3-F0~3-F3 below independently for each page:**

---

## Step 3-F0: Figma Data Extraction (Orchestrator direct execution, per page)

1. **Figma URL Parsing**:
   - Extract `fileKey` and `nodeId` from figma_pages[].url
   - `{page_path}` = kebab-case of title

2. **Framelink MCP Call**:
   - `get_figma_data(fileKey, nodeId)` → YAML data
   - Save to `$DOCS_DIR/design/{page_path}/figma-spec.yaml`

3. **Figma Screenshot Download**:
   - Framelink `download_figma_images` or Figma REST API (scale=2)
   - Save to `$DOCS_DIR/design/{page_path}/reference.png`

4. **Common Component Detection** (first page only — subsequent pages reuse results):
   - Among top 1-2 level INSTANCE nodes in the YAML node tree:
     - Nodes whose names contain `Header/Footer/GNB/Navigation`
     - Name matching against shared components registered in project-profile.md
   - Confirm with user via AskUserQuestion:
     ```
     question: "The following components have been identified as common components. Please confirm which items should use existing project components and be excluded from Figma extraction."
     header: "Common Components"
     options: (list of detected components)
     multiSelect: true
     ```
   - Save to `.jarfis-state.json` as `phases.3.common_components_skip`

---

## Step 3-F1: Asset Detection & Download (Orchestrator direct execution)

1. **YAML Scan** — Search for `type: IMAGE` fills in the `styles` section:
   - Extract `imageRef` values from each `fill_XXXXX`
   - Map node IDs + names that reference each fill

2. **Download Manifest Generation** — `$DOCS_DIR/design/asset-manifest.json`:
   ```json
   [
     {"nodeId": "39286:42489", "imageRef": "abc123...", "fileName": "card-3d.png", "dimensions": {"width": 310, "height": 176}},
     ...
   ]
   ```

3. **Download Attempt** (in order):
   - Primary: Framelink MCP `download_figma_images` (localPath + nodes array)
   - Fallback (if primary fails): Figma REST API `GET /v1/images/{fileKey}?ids={nodeIds}&format=png&scale=2`
   - Save to: `$DOCS_DIR/design/assets/{fileName}`

4. **Verification and Logging** — `$DOCS_DIR/design/asset-verification.md`:
   ```markdown
   ## Asset Verification
   - Total in manifest: N
   - Successfully downloaded: M
   - Failed: K

   | fileName | nodeId | status | size |
   |----------|--------|--------|------|
   | card-3d.png | 39286:42489 | ✅ OK | 32KB |
   | missing.png | 39286:99999 | ❌ FAIL | 0KB |
   ```

---

## Step 3-F2: Token Map Generation (Orchestrator direct execution)

1. **Figma Value Extraction** — From the `styles` section of the YAML:
   - Collect all hex color values from `fill_XXXXX` (solid colors + each gradient stop)
   - Collect all typography values from `style_XXXXX` (fontFamily, fontSize, fontWeight, lineHeight, letterSpacing)

2. **Load Project Design System**:
   - Find variable file paths from the "Design System" or "Styles" section in `project-profile.md`
   - Parse those files to build a `{hex_value: [variable_names]}` lookup table
   - Matching priority: semantic variables > theme variables > primitive variables

3. **Reverse Matching + delta-E Fuzzy Matching**:
   - Attempt exact match → if successful, `"exact": true`
   - If exact match fails → search for nearest variable within delta-E ≤ 5 range → `"exact": false, "deltaE": N`
   - Complete match failure → record in `unmapped` section

4. **Save** — `$DOCS_DIR/design/token-map.json`:
   ```json
   {
     "colors": {
       "#1D77FF": {"scss": "$blue-600", "css": "var(--brand-primary-600)", "semantic": "var(--text-brand-primary)", "exact": true},
       "#702818": {"scss": "$red-900", "css": "var(--primitive-red-900)", "semantic": null, "exact": false, "deltaE": 3.2}
     },
     "typography": {
       "styles": {
         "Pretendard/18/700": {"fontSize": {"value": 18, "variable": "var(--font-size-lg)"}, "fontWeight": {"value": 700, "variable": "$font-weight-bold"}, ...}
       }
     },
     "unmapped": {"colors": ["#AABBCC"], "note": "No matching variables found in the project design system"}
   }
   ```

---

## Step 3-F2.5: Section Split Map Generation (v5 new — Orchestrator direct execution)

1. **Parse YAML Root Children**:
   - Define direct children nodes of the YAML root frame as "sections"
   - Exclude common components (header/footer)
   - Merge adjacent small nodes (height ≤ 40px, dividers/spacers) into the previous section

2. **Per-Section Reference Crop**:
   - Crop reference-cropped.png by each section's y-coordinate/height
   - Save to: `$DOCS_DIR/design/sections/{section-id}/reference.png`

3. **Save** — `$DOCS_DIR/design/section-map.json`:
   ```json
   {
     "root": { "width": 1440, "height": 6294 },
     "sections": [
       { "id": "section-0", "name": "hero", "nodeIds": ["39286:42348"], "y": 0, "height": 480 },
       { "id": "section-1", "name": "benefit-cards", "nodeIds": ["39286:42381"], "y": 480, "height": 1200 }
     ]
   }
   ```

---

## Step 3-F3: UX Designer — Section-by-Section Figma Reproduction (v5 — senior-ux-designer)

> **v5 Change**: Instead of generating the entire page at once, **generate and verify section by section**.
> On failure, only the affected section is reworked, saving tokens and improving stability.

> **Reminder**: All output in $LOCALE language.

### 3-F3a: Page Shell Generation

```
Task prompt:
"Generate the page HTML shell.

Input: $DOCS_DIR/design/figma-spec.yaml (root frame info only)
Output: $DOCS_DIR/design/{path}/index.html

Contents:
- <!DOCTYPE html>, <head> (Pretendard CDN, basic reset styles)
- Root container: apply YAML root's width, background-color
- Section slots: for each section in section-map.json
  <section id='section-{N}' class='section-slot'></section>
- Common component placeholder: <!-- COMMON: {name} --> (reserve height)"
```

### 3-F3b: Per-Section Generation + Immediate Verification (iterative)

For each section:

```
Task prompt:
"Reproduce the '{section_name}' section of the Figma design as pixel-perfect HTML+CSS.

Input materials:
- Figma spec: only the relevant nodes from $DOCS_DIR/design/figma-spec.yaml
  (nodeIds: $SECTION_NODE_IDS)
- Section reference screenshot: $DOCS_DIR/design/sections/{section-id}/reference.png
- Image assets: $DOCS_DIR/design/assets/
- Token map: $DOCS_DIR/design/token-map.json
- Common component skip list: $COMMON_SKIP_LIST

─── Absolute Forbidden Rules (Figma Mode) ───
1. No agent inference: Do not infer styles not present in the Figma spec.
   Example: 'header should be dark because the page is dark' is forbidden. Follow spec data only.
2. Strict node order: Preserve sibling order exactly.
   If a node with the same name appears twice, render it twice. No deduplication.
3. Image assets required: IMAGE/IMAGE-SVG nodes must reference assets/.
   If asset is missing, use [MISSING_ASSET: {nodeId}] placeholder.
4. Exact compound fill conversion: Convert gradient + opacity to CSS precisely.
   No simplification/approximation.
5. Actively use token map: Prefer CSS variables over hex values.
6. 1:1 YAML layout property mapping: Strictly follow the guide below.
   mode→flex-direction, gap→gap, padding→padding used as-is.
7. Vectors/icons as placeholders: No SVG approximation.
   .placeholder-icon (maintain dimensions, light background #E1E4EC / dark background #3D3E42)
8. Compound fills as placeholders: No multi-fill CSS reproduction.
   .placeholder-bg (use first solid color)
──────────────────────────────────

─── YAML → CSS Mapping Guide (v5 Extended) ───
Layout:
  mode: row → display:flex; flex-direction:row
  mode: column → display:flex; flex-direction:column
  gap → gap / padding → padding
  justifyContent/alignItems → justify-content/align-items
  sizing.horizontal: fill → width:100% (flex:1 in flex context)
  sizing.horizontal: fixed → width:{dimensions.width}px
  sizing.horizontal: hug → width:fit-content
  clipsContent:true → overflow:hidden
  borderRadius → border-radius

Text:
  fontFamily/fontSize/fontWeight → font-family/font-size/font-weight
  lineHeight → line-height
  letterSpacing → letter-spacing
  textAlign → text-align

Effects:
  dropShadow → box-shadow
  innerShadow → box-shadow: inset
  backgroundBlur → backdrop-filter:blur()

Borders:
  stroke + strokeWeight → border
  strokeAlign: inside → border (box-sizing:border-box)
  strokeAlign: outside → outline or box-shadow

Gradients:
  linearGradient → background: linear-gradient()
  radialGradient → background: radial-gradient()
────────────────────────────────────

Output: $DOCS_DIR/design/sections/{section-id}/content.html

Immediately verify upon completion:
1. Insert this section's content.html into the page shell
2. Take a screenshot with Playwright MCP
3. Crop to the relevant section area only
4. Visually compare with sections/{section-id}/reference.png
5. If differences exist, fix immediately (max 5 self-iterations per section)
6. On PASS, proceed to next section"
```

### 3-F3c: Asset Population + Full Assembly

```
After all sections PASS:
1. Replace placeholders with actual assets (photo→img, icon→img, bg→background-image)
2. Assemble all section content.html into the page shell
3. Finalize $DOCS_DIR/design/{path}/index.html
4. Generate $DOCS_DIR/design/_index.html (table of contents)
```

---

## Step 3-F4: PO + UX Full Review (v5 — after assembly)

> v5 Change: Per-section verification is already completed in 3-F3b. 3-F4 is the **final review of the assembled full page**.
> Iteration philosophy: A perfect result always takes absolute priority over token savings.

> **Reminder**: All output in $LOCALE language.

**Review target**: $DOCS_DIR/design/{path}/index.html (fully assembled version)

**Each round:**

PO (senior-product-owner):
```
Task prompt:
"Review the HTML mockups in the $DOCS_DIR/design/ directory.
Figma original screenshot: $DOCS_DIR/design/reference.png

Verification items:
- Whether the Figma design's content (text, images, order) is accurately reproduced
- Whether there are any missing sections or text
- Whether image assets are displayed in the correct positions
- Whether transitions between sections are natural (check seams from section-by-section generation)

If there is feedback, describe it specifically along with the relevant section ID."
```

UX Designer (senior-ux-designer) — Playwright comparison:
```
Task prompt:
"Compare and review $DOCS_DIR/design/reference.png against the HTML mockup using Playwright.

Comparison process:
1. Take a full-page screenshot of $DOCS_DIR/design/{path}/index.html with Playwright MCP
2. Measure pixel-diff against reference-cropped.png using mcp-design-comparison
3. If diff > 5%: use section-map.json to identify problem sections
4. Revise only problem sections (modify that section's content.html → reassemble)

Report format:
## Figma vs HTML Final Review (Round N)
- Full diff: {N}%
### Section: {section name} ({section-id})
- [PASS] / [REVISION] detailed description

If there are REVISION items, fix only those sections and reassemble to verify."
```

**Exit conditions:**
- Full diff ≤ 5% + PO content approval → Complete
- Max 10 rounds reached → Notify user with list of unresolved items:
  ```
  question: "HTML mockup full review has reached 10 rounds. The following unresolved items remain: [list]. How would you like to proceed?"
  header: "Max Iteration"
  options:
    - label: "Approve as-is"
    - label: "Manually fix then re-review"
    - label: "Abort"
  ```

**User Gate**: Same as the existing text path — `open $DOCS_DIR/design/_index.html`
