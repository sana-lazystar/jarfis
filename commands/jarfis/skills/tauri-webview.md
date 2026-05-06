# Tauri WebView Expertise

<!-- jarfis:context7
library_id: /websites/v2_tauri_app
query_topics: [webview API, custom protocols, window management, events]
-->

## Core Patterns

### invoke() — Calling Rust Commands
- `import { invoke } from '@tauri-apps/api/core'`
- Type safety: `invoke<ReturnType>('command_name', { arg1, arg2 })`
- Error handling: `try/catch` is mandatory — Rust errors are passed as strings
- Serialization: Both arguments and return values must be JSON-serializable (watch out for Date, Map, etc.)

### Event System
- `listen('event-name', callback)`: Receive unidirectional events from Rust to WebView
- `emit('event-name', payload)`: Send events from WebView to Rust
- `once()`: One-time listener (useful during initial load)
- Cleanup: Call the return value (unlisten) from `listen()` in React useEffect cleanup

### WebView Constraints (Differences from Browsers)
- **Local file access**: Only possible through `@tauri-apps/plugin-fs` (security sandbox)
- **HTTP requests**: `@tauri-apps/plugin-http` recommended (CORS bypass, native TLS)
- **window object**: Access Tauri API via `__TAURI__` global. Direct use of `window.__TAURI_INTERNALS__` is prohibited
- **Developer tools**: Only active in dev mode. Controlled by `devtools` feature flag
- **CSP**: Controlled via `security.csp` in `tauri.conf.json`. Restrictive by default

### React + Tauri Integration Patterns
- **Custom hook**: `useInvoke<T>(command, args)` — Manages loading/error/data state
- **Event hook**: `useTauriEvent(event, handler)` — Encapsulates listen + cleanup
- **Conditional rendering**: Detect Tauri environment by checking `window.__TAURI__` existence (for dual web build support)

## Common Pitfalls
- Argument names in `invoke()` not matching Rust command parameter names — Runtime error (no compile-time check)
- `listen()` called twice in React StrictMode — Duplicate event reception. Cleanup is mandatory
- Passing large data through invoke — IPC serialization bottleneck. Pass file paths for data over 1MB
- Setting state after component unmount from `async invoke` result — Memory leak. Use AbortController pattern or cleanup flag
