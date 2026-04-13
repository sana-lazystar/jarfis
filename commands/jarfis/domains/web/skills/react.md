# React Expertise

## Core Patterns
- **Hooks**: useState, useEffect, useCallback, useMemo, useRef — Understand each purpose and when to optimize
- **Context API**: Suitable for cross-cutting state. Not suitable for frequent updates (re-render propagation)
- **Suspense + Error Boundaries**: Declarative composition of async loading and error handling
- **Server Components (RSC)**: Data fetching on server, interactions on client. Deciding the "use client" boundary is key
- **Concurrent Features**: startTransition, useDeferredValue — Priority-based rendering

## State Management Decision Framework
- **Simple local**: useState/useReducer
- **Cross-component sharing**: Zustand (lightweight, minimal boilerplate)
- **Atomic state**: Jotai (convenient derived state)
- **Server state**: TanStack Query (cache invalidation, refetching, optimistic updates)
- **Complex middleware**: Redux Toolkit (when sagas/thunks are needed)

## Next.js Patterns
- App Router: Nested layouts, loading/error UI, parallel routes
- Pages Router: getServerSideProps, getStaticProps
- Deciding when to transition from API Routes to Server Actions

## Common Pitfalls
- Missing useEffect dependency array -> Infinite loop
- Using index as key prop -> State corruption on list reordering
- Unnecessary re-renders -> Apply React.memo only after measuring (beware premature optimization)
- RSC/RCC boundary confusion -> Event handlers require "use client"
