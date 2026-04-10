# Rust Expertise

## Core Patterns

### Ownership & Borrowing
- 단일 소유자 원칙: 값은 한 번에 하나의 변수만 소유. 이동(move) vs 복사(Copy trait) 판단이 핵심
- `&T` (공유 참조) vs `&mut T` (배타적 참조): 동시에 여러 `&T` 가능, `&mut T`는 단독
- 라이프타임 생략 규칙(elision): 대부분 명시 불필요. 복잡한 경우만 `'a` 표기

### Error Handling Decision Framework
- **복구 가능**: `Result<T, E>` — `?` 연산자로 전파, `thiserror`로 커스텀 에러 타입
- **복구 불가**: `panic!` — 프로그래밍 에러(인덱스 범위 초과 등)에만 사용
- **값 부재**: `Option<T>` — `unwrap()` 지양, `map/and_then/unwrap_or_default` 체이닝
- **에러 타입 통합**: `anyhow::Result`(앱), `thiserror::Error`(라이브러리)

### Concurrency Patterns
- `Arc<Mutex<T>>`: 멀티스레드 공유 상태 (Tauri command에서 빈번)
- `Arc<RwLock<T>>`: 읽기 빈번, 쓰기 드문 경우 (설정, 캐시)
- `tokio::spawn`: CPU 바운드 작업은 `spawn_blocking` 사용
- 채널: `tokio::sync::mpsc` (다대일), `broadcast` (다대다), `watch` (최신값만)

### Async Patterns
- `async fn`은 `Future`를 반환할 뿐, 호출 시 실행 안 됨 — `.await` 필수
- `tokio::select!`: 여러 Future 중 먼저 완료된 것 처리
- 블로킹 함수를 async 컨텍스트에서 호출 금지 — `spawn_blocking` 사용

## Common Pitfalls
- `clone()` 남용: 소유권 문제를 clone으로 회피하면 성능 저하. 참조로 해결 가능한지 먼저 확인
- `unwrap()` / `expect()`: 프로덕션 코드에서 지양. `?`로 전파하거나 기본값 사용
- 데드락: `Mutex` 중첩 잠금 순서 불일치. 잠금 순서를 문서화하거나 단일 잠금으로 통합
- `String` vs `&str`: 소유 필요 시 `String`, 읽기만 필요 시 `&str`. 함수 매개변수는 `&str` 선호
