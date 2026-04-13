# Vue Expertise

## Core Patterns
- **Composition API**: setup(), ref/reactive, computed, watch/watchEffect
- **Options API**: data, computed, methods, watch — Still used in legacy projects
- **Script Setup**: `<script setup>` syntax to minimize boilerplate

## State Management
- **Pinia**: Official Vue 3 state management. Excellent type inference, devtools support.
- **Vuex**: Vue 2 legacy. mutations/actions pattern.
- **Vue Query (TanStack Query)**: Server state management

## Routing
- **Vue Router**: Nested routes, guards (beforeEach), lazy loading
- **Nuxt.js**: File-based routing, SSR/SSG, auto-imports

## Common Pitfalls
- Globally registered components (app.component()) are undetectable by static analysis tools -> Verify manually with text search
- Cannot wrap primitives with reactive() -> Use ref()
- Be careful with defineComponent() + setup() hybrid when migrating from Options to Composition API
- Do not use v-if and v-for together (v-if takes priority in Vue 3)
