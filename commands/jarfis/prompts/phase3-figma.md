# Phase 3 Figma-Driven Design Path — Agent Prompts

> Phase 3에서 Figma URL이 제공된 경우(디자이너가 있는 경우) 실행되는 경로.
> 출력 계약은 기존 텍스트 경로와 동일: `$DOCS_DIR/design/{path}/index.html`
>
> **v5 업데이트 (2026-03-27)**: A/B 테스트 결과 HTML 시안 경유가 직접 생성 대비
> 레이아웃 정확도에서 확연히 우위 확인. HTML 시안 유지하되 **섹션별 분할 생성**으로
> 효율/안정성 개선. 상세: `~/UX-AI/workflow/figma-to-html-v5.md`

---

## 복수 Figma 페이지 병렬 처리 (v5)

> `.jarfis-state.json`의 `phases.3.figma_pages` 배열에 여러 페이지가 있을 수 있다.
> 각 페이지를 **병렬로** Step 3-F0~3-F3를 실행한다 (최대 5페이지 동시).
> 각 페이지는 `$DOCS_DIR/design/{page_path}/`에 독립 산출물을 생성한다.
> `{page_path}`는 figma_pages[].title의 kebab-case 변환이다 (예: "혜택 소개" → "benefits-signup").

```
figma_pages 예시:
[
  {"title": "혜택 소개", "url": "https://figma.com/design/xxx?node-id=123-456"},
  {"title": "멤버십 내역", "url": "https://figma.com/design/xxx?node-id=789-012"}
]
```

**각 페이지에 대해 아래 Step 3-F0~3-F3를 독립 실행:**

---

## Step 3-F0: Figma 데이터 추출 (오케스트레이터 직접 실행, 페이지별)

1. **Figma URL 파싱**:
   - figma_pages[].url에서 `fileKey`와 `nodeId` 추출
   - `{page_path}` = title의 kebab-case

2. **Framelink MCP 호출**:
   - `get_figma_data(fileKey, nodeId)` → YAML 데이터
   - `$DOCS_DIR/design/{page_path}/figma-spec.yaml`에 저장

3. **Figma 스크린샷 다운로드**:
   - Framelink `download_figma_images` 또는 Figma REST API (scale=2)
   - `$DOCS_DIR/design/{page_path}/reference.png`에 저장

4. **공통 컴포넌트 감지** (첫 번째 페이지에서만 — 이후 페이지는 결과 재사용):
   - YAML 노드 트리에서 최상위 1-2레벨의 INSTANCE 노드 중:
     - 이름에 `헤더/Header/풋터/Footer/GNB/Navigation` 포함하는 노드
     - project-profile.md에 등록된 shared components와 이름 매칭
   - AskUserQuestion으로 사용자 확인:
     ```
     question: "다음 컴포넌트를 공통 컴포넌트로 인식했습니다. 프로젝트 기존 컴포넌트를 사용하고 Figma 추출에서 제외할 항목을 확인해주세요."
     header: "공통 컴포넌트"
     options: (감지된 컴포넌트 목록)
     multiSelect: true
     ```
   - `.jarfis-state.json`에 `phases.3.common_components_skip` 저장

---

## Step 3-F1: 에셋 탐지 & 다운로드 (오케스트레이터 직접 실행)

1. **YAML 스캔** — `styles` 섹션에서 `type: IMAGE` fill 탐색:
   - 각 `fill_XXXXX`의 `imageRef` 값 추출
   - 해당 fill을 참조하는 노드 ID + 이름 매핑

2. **다운로드 매니페스트 생성** — `$DOCS_DIR/design/asset-manifest.json`:
   ```json
   [
     {"nodeId": "39286:42489", "imageRef": "abc123...", "fileName": "card-3d.png", "dimensions": {"width": 310, "height": 176}},
     ...
   ]
   ```

3. **다운로드 시도** (순서):
   - 1차: Framelink MCP `download_figma_images` (localPath + nodes 배열)
   - 2차 (1차 실패 시): Figma REST API `GET /v1/images/{fileKey}?ids={nodeIds}&format=png&scale=2`
   - 저장: `$DOCS_DIR/design/assets/{fileName}`

4. **검증 및 기록** — `$DOCS_DIR/design/asset-verification.md`:
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

## Step 3-F2: 토큰 맵 생성 (오케스트레이터 직접 실행)

1. **Figma 값 추출** — YAML의 `styles` 섹션에서:
   - 모든 `fill_XXXXX`의 hex 색상값 수집 (단색 + 그라디언트의 각 stop)
   - 모든 `style_XXXXX`의 타이포그래피 값 (fontFamily, fontSize, fontWeight, lineHeight, letterSpacing)

2. **프로젝트 디자인 시스템 로드**:
   - `project-profile.md`의 "Design System" 또는 "Styles" 섹션에서 변수 파일 경로 확인
   - 해당 파일들 파싱하여 `{hex_value: [variable_names]}` 룩업 테이블 구축
   - 매칭 우선순위: semantic 변수 > theme 변수 > primitive 변수

3. **역방향 매칭 + delta-E fuzzy matching**:
   - 정확 매칭 시도 → 성공 시 `"exact": true`
   - 정확 매칭 실패 시 → delta-E ≤ 5 범위에서 최근접 변수 탐색 → `"exact": false, "deltaE": N`
   - 매칭 완전 실패 → `unmapped` 섹션에 기록

4. **저장** — `$DOCS_DIR/design/token-map.json`:
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
     "unmapped": {"colors": ["#AABBCC"], "note": "프로젝트 디자인 시스템에 매칭되는 변수 없음"}
   }
   ```

---

## Step 3-F2.5: 섹션 분할 맵 생성 (v5 신규 — 오케스트레이터 직접 실행)

1. **YAML 루트 children 파싱**:
   - YAML 루트 프레임의 직계 children 노드를 "섹션"으로 정의
   - 공통 컴포넌트(헤더/풋터)는 제외
   - 인접한 작은 노드(height ≤ 40px, 구분선/스페이서)는 이전 섹션에 병합

2. **섹션별 레퍼런스 crop**:
   - reference-cropped.png를 각 섹션의 y좌표/height로 crop
   - 저장: `$DOCS_DIR/design/sections/{section-id}/reference.png`

3. **저장** — `$DOCS_DIR/design/section-map.json`:
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

## Step 3-F3: UX Designer — 섹션별 Figma 재현 (v5 — senior-ux-designer)

> **v5 변경**: 전체 페이지를 한번에 생성하지 않고 **섹션별로 분할 생성+검증**.
> 실패 시 해당 섹션만 재작업하여 토큰 절약 + 안정성 향상.

### 3-F3a: 페이지 셸 생성

```
Task prompt:
"페이지 HTML 셸을 생성하세요.

입력: $DOCS_DIR/design/figma-spec.yaml (루트 프레임 정보만)
출력: $DOCS_DIR/design/{path}/index.html

내용:
- <!DOCTYPE html>, <head> (Pretendard CDN, 기본 리셋 스타일)
- 루트 컨테이너: YAML root의 width, background-color 적용
- 섹션 슬롯: section-map.json의 각 섹션에 대해
  <section id='section-{N}' class='section-slot'></section>
- 공통 컴포넌트 placeholder: <!-- COMMON: {name} --> (높이 확보)"
```

### 3-F3b: 섹션별 생성 + 즉시 검증 (반복)

각 섹션에 대해:

```
Task prompt:
"Figma 디자인의 '{section_name}' 섹션을 pixel-perfect HTML+CSS로 재현하세요.

입력 자료:
- Figma 스펙: $DOCS_DIR/design/figma-spec.yaml 중 해당 노드만
  (nodeIds: $SECTION_NODE_IDS)
- 섹션 참조 스크린샷: $DOCS_DIR/design/sections/{section-id}/reference.png
- 이미지 에셋: $DOCS_DIR/design/assets/
- 토큰 맵: $DOCS_DIR/design/token-map.json
- 공통 컴포넌트 스킵 목록: $COMMON_SKIP_LIST

─── 절대 금지 규칙 (Figma 모드) ───
1. 에이전트 추론 금지: Figma 스펙에 없는 스타일을 추론하지 마라.
   예: '다크 페이지이므로 헤더도 다크'는 금지. 스펙 데이터만 따라라.
2. 노드 순서 엄수: siblings 순서를 정확히 보존하라.
   같은 이름의 노드가 2번 등장하면 2번 렌더링. deduplicate 금지.
3. 이미지 에셋 필수: IMAGE/IMAGE-SVG 노드는 반드시 assets/ 참조.
   에셋 없으면 [MISSING_ASSET: {nodeId}] placeholder.
4. 복합 fill 정확 변환: gradient + opacity를 정확히 CSS 변환.
   단순화/근사값 금지.
5. 토큰 맵 적극 활용: hex 대신 CSS variable 우선.
6. YAML layout 속성 1:1 매핑: 아래 가이드 엄수.
   mode→flex-direction, gap→gap, padding→padding 그대로 사용.
7. 벡터/아이콘은 placeholder: SVG 근사 금지.
   .placeholder-icon (dimensions 유지, 밝은 배경 #E1E4EC / 어두운 배경 #3D3E42)
8. 복합 fill은 placeholder: 다중 fill CSS 재현 금지.
   .placeholder-bg (첫 번째 단색 사용)
───────────────────────────────

─── YAML → CSS 매핑 가이드 (v5 확장) ───
레이아웃:
  mode: row → display:flex; flex-direction:row
  mode: column → display:flex; flex-direction:column
  gap → gap / padding → padding
  justifyContent/alignItems → justify-content/align-items
  sizing.horizontal: fill → width:100% (flex 컨텍스트면 flex:1)
  sizing.horizontal: fixed → width:{dimensions.width}px
  sizing.horizontal: hug → width:fit-content
  clipsContent:true → overflow:hidden
  borderRadius → border-radius

텍스트:
  fontFamily/fontSize/fontWeight → font-family/font-size/font-weight
  lineHeight → line-height
  letterSpacing → letter-spacing
  textAlign → text-align

이펙트:
  dropShadow → box-shadow
  innerShadow → box-shadow: inset
  backgroundBlur → backdrop-filter:blur()

보더:
  stroke + strokeWeight → border
  strokeAlign: inside → border (box-sizing:border-box)
  strokeAlign: outside → outline 또는 box-shadow

그라디언트:
  linearGradient → background: linear-gradient()
  radialGradient → background: radial-gradient()
────────────────────────────────────

출력: $DOCS_DIR/design/sections/{section-id}/content.html

완료 후 즉시 검증:
1. 페이지 셸에 이 섹션 content.html을 삽입
2. Playwright MCP로 스크린샷 촬영
3. 해당 섹션 영역만 crop
4. sections/{section-id}/reference.png과 시각 비교
5. 차이점이 있으면 즉시 수정 (최대 5회 자체 반복/섹션)
6. PASS 시 다음 섹션으로"
```

### 3-F3c: 에셋 채우기 + 전체 조립

```
모든 섹션 PASS 후:
1. placeholder를 실제 에셋으로 교체 (photo→img, icon→img, bg→background-image)
2. 페이지 셸에 모든 섹션 content.html 조립
3. $DOCS_DIR/design/{path}/index.html 완성
4. $DOCS_DIR/design/_index.html (목차) 생성
```

---

## Step 3-F4: PO + UX 전체 리뷰 (v5 — 조립 후)

> v5 변경: 섹션별 검증은 3-F3b에서 이미 완료. 3-F4는 **조립된 전체 페이지**에 대한 최종 리뷰.
> 반복 철학: 토큰 절약보다 완벽한 결과물이 절대 우선.

**리뷰 대상**: $DOCS_DIR/design/{path}/index.html (전체 조립 완료본)

**각 라운드:**

PO (senior-product-owner):
```
Task prompt:
"$DOCS_DIR/design/ 디렉토리의 HTML 시안을 검토하세요.
Figma 원본 스크린샷: $DOCS_DIR/design/reference.png

확인 항목:
- Figma 디자인의 콘텐츠(텍스트, 이미지, 순서)가 정확히 재현되었는가
- 누락된 섹션이나 텍스트가 없는가
- 이미지 에셋이 올바른 위치에 표시되는가
- 섹션 간 연결부가 자연스러운가 (섹션별 생성으로 인한 이음새 확인)

피드백이 있으면 해당 섹션 ID와 함께 구체적으로 기술하세요."
```

UX Designer (senior-ux-designer) — Playwright 비교:
```
Task prompt:
"$DOCS_DIR/design/reference.png와 HTML 시안을 Playwright로 비교 리뷰하세요.

비교 프로세스:
1. Playwright MCP로 $DOCS_DIR/design/{path}/index.html 전체 스크린샷 촬영
2. mcp-design-comparison으로 reference-cropped.png과 pixel-diff 측정
3. diff > 5% 시: section-map.json 활용하여 문제 섹션 특정
4. 문제 섹션만 리비전 (해당 섹션의 content.html 수정 → 재조립)

리포트 형식:
## Figma vs HTML Final Review (Round N)
- Full diff: {N}%
### Section: {섹션명} ({section-id})
- [PASS] / [REVISION] 상세 설명

REVISION 항목이 있으면 해당 섹션만 수정 후 재조립하여 확인."
```

**종료 조건:**
- 전체 diff ≤ 5% + PO 콘텐츠 승인 → 완료
- max 10회 도달 → 사용자에게 미해결 항목 목록과 함께 알림:
  ```
  question: "HTML 시안 전체 리뷰 10회 도달. 아래 미해결 항목이 있습니다: [목록]. 어떻게 진행할까요?"
  header: "Max Iteration"
  options:
    - label: "현재 상태로 승인"
    - label: "수동 수정 후 재검토"
    - label: "중단"
  ```

**사용자 Gate**: 기존 텍스트 경로와 동일 — `open $DOCS_DIR/design/_index.html`
