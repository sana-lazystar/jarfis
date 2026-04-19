# Browser & Cross-Platform Expertise

## Engine Differences
- **Blink** (Chrome, Edge, Opera): Broadest API support
- **Gecko** (Firefox): Some CSS implementation differences (flexbox gap, etc.)
- **WebKit** (Safari, iOS): Most conservative. iOS Safari in particular has many unique bugs

## Common Cross-Browser Issues
- iOS Safari: safe-area-inset, 100vh issue (use dvh/svh/lvh), scroll bounce
- Android: Viewport changes caused by keyboard, touch-action handling
- Safari: Flexbox/grid rendering differences, unsupported date input areas
- font-rendering: macOS subpixel antialiasing vs Windows ClearType

## Feature Detection
- `@supports` (CSS): Style branching based on feature support
- Polyfill strategy: core-js, whatwg-fetch — Apply selectively, only what's needed
- Progressive Enhancement: Start with basic features, then gradually add advanced ones

## Performance Patterns
- HTTP caching: Cache-Control, ETag, content-hash based cache busting
- Image optimization: WebP/AVIF, srcset/sizes, lazy loading
- Fonts: font-display: swap, preload, prioritize WOFF2
- Preconnect/Prefetch: crossorigin attribute must match (mismatches waste connections)

## Mobile-Specific
- Touch events vs Pointer events: Prefer pointer events (unified API)
- Viewport units: dvh > vh (handles mobile address bar)
- PWA: Service Worker, Web App Manifest, offline strategies
