# Browser & Cross-Platform Expertise

## Engine Differences
- **Blink** (Chrome, Edge, Opera): 가장 넓은 API 지원
- **Gecko** (Firefox): 일부 CSS 구현 차이 (flexbox gap 등)
- **WebKit** (Safari, iOS): 가장 보수적. 특히 iOS Safari는 고유 버그 다수

## Common Cross-Browser Issues
- iOS Safari: safe-area-inset, 100vh 문제 (dvh/svh/lvh 사용), 스크롤 바운스
- Android: 키보드로 인한 뷰포트 변화, touch-action 처리
- Safari: flexbox/grid 렌더링 차이, date input 미지원 영역
- font-rendering: macOS 서브픽셀 안티앨리어싱 vs Windows ClearType

## Feature Detection
- `@supports` (CSS): 기능 지원 여부에 따른 스타일 분기
- Polyfill 전략: core-js, whatwg-fetch — 필요한 것만 선택적 적용
- Progressive Enhancement: 기본 기능 → 고급 기능 점진 추가

## Performance Patterns
- HTTP 캐싱: Cache-Control, ETag, content-hash 기반 캐시 버스팅
- 이미지 최적화: WebP/AVIF, srcset/sizes, lazy loading
- 폰트: font-display: swap, preload, WOFF2 우선
- Preconnect/Prefetch: crossorigin 속성 일치 필수 (불일치 시 연결 낭비)

## Mobile-Specific
- Touch events vs Pointer events: pointer events 선호 (통합 API)
- Viewport units: dvh > vh (모바일 주소바 대응)
- PWA: Service Worker, Web App Manifest, 오프라인 전략
