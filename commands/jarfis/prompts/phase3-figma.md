# Phase 3 Figma-Driven Design Path — Agent Prompts

> Phase 3에서 Figma URL이 제공된 경우(디자이너가 있는 경우) 실행되는 경로.
> 출력 계약은 기존 텍스트 경로와 동일: `$DOCS_DIR/design/{path}/index.html`

---

## Step 3-F0: Figma 데이터 추출 (오케스트레이터 직접 실행)

1. **Figma URL 파싱**:
   - URL에서 `fileKey`와 `nodeId` 추출
   - `.jarfis-state.json`에 `phases.3.mode: "figma"`, `phases.3.figma_url`, `phases.3.figma_node_id` 저장

2. **Framelink MCP 호출**:
   - `get_figma_data(fileKey, nodeId)` → YAML 데이터
   - `$DOCS_DIR/design/figma-spec.yaml`에 저장

3. **Figma 스크린샷 다운로드**:
   - Figma REST API: `GET /v1/images/{fileKey}?ids={nodeId}&format=png&scale=2`
   - `$DOCS_DIR/design/reference.png`에 저장

4. **공통 컴포넌트 감지**:
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

## Step 3-F3: UX Designer — Figma 재현 (senior-ux-designer)

```
Task prompt:
"Figma 디자인을 pixel-perfect HTML+CSS로 재현하세요.

입력 자료:
- Figma 스펙: $DOCS_DIR/design/figma-spec.yaml
- Figma 참조 스크린샷: $DOCS_DIR/design/reference.png
- 이미지 에셋: $DOCS_DIR/design/assets/
- 토큰 맵: $DOCS_DIR/design/token-map.json
- 에셋 검증: $DOCS_DIR/design/asset-verification.md
- 공통 컴포넌트 스킵 목록: $COMMON_SKIP_LIST

─── 절대 금지 규칙 (Figma 모드) ───
1. 에이전트 추론 금지: Figma 스펙에 없는 스타일을 추론하지 마라.
   예: '다크 페이지이므로 헤더도 다크'는 금지. 스펙 데이터만 따라라.
2. 노드 순서 엄수: siblings 순서를 정확히 보존하라.
   같은 이름의 노드가 2번 등장하면 2번 렌더링. deduplicate 금지.
3. 이미지 에셋 필수: IMAGE/IMAGE-SVG 노드는 반드시 assets/ 디렉토리의 파일을 참조.
   에셋이 없으면 [MISSING_ASSET: {nodeId}] 플레이스홀더로 대체.
4. 복합 fill 정확 변환: 그라디언트 + opacity 조합을 정확히 CSS로 변환.
   단순화하거나 근사값으로 대체 금지.
5. 토큰 맵 적극 활용: hex 값 대신 token-map.json의 CSS variable을 우선 사용.
   unmapped 값만 raw hex 허용.
───────────────────────────────

공통 컴포넌트 처리:
- 스킵 목록의 컴포넌트는 <!-- COMMON: {component_name} --> 주석으로 대체
- 해당 영역의 높이만 placeholder로 확보 (Figma 스펙의 dimensions 참조)

출력 형식:
- $DOCS_DIR/design/{path}/index.html (단독 실행 가능, 에셋은 상대경로 ../assets/)
- 상단에 templates/design-html-meta.md 메타 주석 삽입
- $DOCS_DIR/design/_index.html (전체 시안 목차)

완료 후 자가 검증:
1. reference.png를 열어 확인
2. 생성한 HTML을 Playwright MCP로 열어 스크린샷 촬영
3. 두 이미지를 비교하여 차이점 목록 작성
4. 차이점이 있으면 즉시 수정 (1회 자체 반복)"
```

---

## Step 3-F4: PO + UX 리뷰 루프 (max 20회)

> 반복 철학: 토큰 절약보다 완벽한 결과물이 절대 우선.
> max 20회 도달 시에도 불완전하면 사용자에게 미해결 항목 명시적 알림.

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

피드백이 있으면 구체적으로 기술하세요 (섹션별)."
```

UX Designer (senior-ux-designer) — Playwright 비교:
```
Task prompt:
"$DOCS_DIR/design/reference.png와 HTML 시안을 Playwright로 비교 리뷰하세요.

비교 프로세스:
1. Playwright MCP로 $DOCS_DIR/design/{path}/index.html 스크린샷 촬영
2. reference.png와 나란히 비교
3. 섹션별 PASS/REVISION 판정

리포트 형식:
## Figma vs HTML Comparison (Round N)
### Section: {섹션명} (y: {시작}~{끝}px)
- [PASS] / [REVISION] 상세 설명

REVISION 항목이 있으면 즉시 HTML 수정 후 재촬영하여 확인."
```

**종료 조건:**
- 전체 섹션 PASS + PO 콘텐츠 승인 → 완료
- max 20회 도달 → 사용자에게 미해결 항목 목록과 함께 알림:
  ```
  question: "HTML 시안 리뷰 20회 도달. 아래 미해결 항목이 있습니다: [목록]. 어떻게 진행할까요?"
  header: "Max Iteration"
  options:
    - label: "현재 상태로 승인"
    - label: "수동 수정 후 재검토"
    - label: "중단"
  ```

**사용자 Gate**: 기존 텍스트 경로와 동일 — `open $DOCS_DIR/design/_index.html`
