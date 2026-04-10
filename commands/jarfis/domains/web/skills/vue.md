# Vue Expertise

## Core Patterns
- **Composition API**: setup(), ref/reactive, computed, watch/watchEffect
- **Options API**: data, computed, methods, watch — 레거시 프로젝트에서 여전히 사용
- **Script Setup**: `<script setup>` 문법으로 보일러플레이트 최소화

## State Management
- **Pinia**: Vue 3 공식 상태 관리. 타입 추론 우수, devtools 지원.
- **Vuex**: Vue 2 레거시. mutations/actions 패턴.
- **Vue Query (TanStack Query)**: 서버 상태 관리

## Routing
- **Vue Router**: 중첩 라우트, 가드(beforeEach), 레이지 로딩
- **Nuxt.js**: 파일 기반 라우팅, SSR/SSG, auto-imports

## Common Pitfalls
- 전역 등록 컴포넌트(app.component())는 정적 분석 도구가 탐지 못함 → 텍스트 검색으로 수동 검증
- reactive()로 원시값 래핑 불가 → ref() 사용
- Options → Composition 전환 시 defineComponent() + setup() 하이브리드 주의
- v-if/v-for 동시 사용 금지 (Vue 3에서 v-if 우선)
