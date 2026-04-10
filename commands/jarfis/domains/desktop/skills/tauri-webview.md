# Tauri WebView Expertise

## Core Patterns

### invoke() — Rust Command 호출
- `import { invoke } from '@tauri-apps/api/core'`
- 타입 안전: `invoke<ReturnType>('command_name', { arg1, arg2 })`
- 에러 처리: `try/catch` 필수 — Rust 에러가 string으로 전달됨
- 직렬화: 인자/반환값 모두 JSON 직렬화 가능해야 함 (Date, Map 등 주의)

### Event System
- `listen('event-name', callback)`: Rust → WebView 단방향 이벤트 수신
- `emit('event-name', payload)`: WebView → Rust 이벤트 발신
- `once()`: 일회성 수신 (초기 로드 시 유용)
- cleanup: `listen()` 반환값(unlisten)을 React useEffect cleanup에서 호출

### WebView 제약 (브라우저와의 차이)
- **로컬 파일 접근**: `@tauri-apps/plugin-fs` 통해서만 가능 (보안 샌드박스)
- **HTTP 요청**: `@tauri-apps/plugin-http` 권장 (CORS 우회, 네이티브 TLS)
- **window 객체**: `__TAURI__` 글로벌로 Tauri API 접근. `window.__TAURI_INTERNALS__` 직접 사용 금지
- **개발자 도구**: dev 모드에서만 활성화. `devtools` feature flag 제어
- **CSP**: `tauri.conf.json`의 `security.csp`로 제어. 기본 제한적

### React + Tauri 통합 패턴
- **커스텀 훅**: `useInvoke<T>(command, args)` — loading/error/data 상태 관리
- **이벤트 훅**: `useTauriEvent(event, handler)` — listen + cleanup 캡슐화
- **조건부 렌더링**: `window.__TAURI__` 존재 여부로 Tauri 환경 감지 (웹 빌드 겸용 시)

## Common Pitfalls
- `invoke()` 인자명이 Rust command 매개변수명과 불일치 → 런타임 에러 (컴파일 타임 체크 없음)
- React StrictMode에서 `listen()` 두 번 호출 → 이벤트 중복 수신. cleanup 필수
- 대용량 데이터를 invoke로 전달 → IPC 직렬화 병목. 1MB 이상은 파일 경로로 전달
- `async invoke` 결과를 컴포넌트 언마운트 후 setState → 메모리 누수. AbortController 패턴 또는 cleanup flag 사용
