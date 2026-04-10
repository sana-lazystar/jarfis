# React Expertise

## Core Patterns
- **Hooks**: useState, useEffect, useCallback, useMemo, useRef — 각각의 용도와 최적화 시점 판단
- **Context API**: 크로스커팅 상태에 적합. 빈번한 업데이트에는 비적합 (리렌더링 전파)
- **Suspense + Error Boundaries**: 비동기 로딩과 에러 처리의 선언적 구성
- **Server Components (RSC)**: 데이터 fetching은 서버, 인터랙션은 클라이언트. "use client" 경계 판단이 핵심
- **Concurrent Features**: startTransition, useDeferredValue — 우선순위 기반 렌더링

## State Management Decision Framework
- **단순 로컬**: useState/useReducer
- **크로스 컴포넌트 공유**: Zustand (가볍고 보일러플레이트 적음)
- **원자적 상태**: Jotai (파생 상태 편리)
- **서버 상태**: TanStack Query (캐시 무효화, 리페칭, 옵티미스틱 업데이트)
- **복잡한 미들웨어**: Redux Toolkit (사가/썽크 필요 시)

## Next.js Patterns
- App Router: 레이아웃 중첩, 로딩/에러 UI, 병렬 라우트
- Pages Router: getServerSideProps, getStaticProps
- API Routes → Server Actions 전환 판단

## Common Pitfalls
- useEffect 의존성 배열 누락 → 무한 루프
- key prop에 index 사용 → 리스트 재정렬 시 상태 꼬임
- 불필요한 리렌더링 → React.memo는 측정 후 적용 (premature optimization 경계)
- RSC/RCC 경계 혼동 → 이벤트 핸들러 있으면 반드시 "use client"
