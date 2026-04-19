# Rust Expertise

## Core Patterns

### Ownership & Borrowing
- Single owner principle: A value can only be owned by one variable at a time. Deciding between move vs copy (Copy trait) is key
- `&T` (shared reference) vs `&mut T` (exclusive reference): Multiple `&T` allowed simultaneously, `&mut T` must be exclusive
- Lifetime elision rules: Explicit annotation usually unnecessary. Only use `'a` notation for complex cases

### Error Handling Decision Framework
- **Recoverable**: `Result<T, E>` — Propagate with `?` operator, define custom error types with `thiserror`
- **Unrecoverable**: `panic!` — Use only for programming errors (e.g., index out of bounds)
- **Absent value**: `Option<T>` — Avoid `unwrap()`, chain with `map/and_then/unwrap_or_default`
- **Error type unification**: `anyhow::Result` (applications), `thiserror::Error` (libraries)

### Concurrency Patterns
- `Arc<Mutex<T>>`: Shared state across threads (common in Tauri commands)
- `Arc<RwLock<T>>`: Frequent reads, rare writes (configuration, caches)
- `tokio::spawn`: Use `spawn_blocking` for CPU-bound tasks
- Channels: `tokio::sync::mpsc` (many-to-one), `broadcast` (many-to-many), `watch` (latest value only)

### Async Patterns
- `async fn` only returns a `Future`; it does not execute on call — `.await` is required
- `tokio::select!`: Process whichever Future completes first among multiple
- Never call blocking functions in an async context — use `spawn_blocking`

## Common Pitfalls
- `clone()` overuse: Using clone to dodge ownership issues causes performance degradation. Check if references can solve it first
- `unwrap()` / `expect()`: Avoid in production code. Propagate with `?` or use default values
- Deadlocks: Inconsistent lock ordering with nested `Mutex` locks. Document lock ordering or consolidate into a single lock
- `String` vs `&str`: Use `String` when ownership is needed, `&str` for read-only. Prefer `&str` for function parameters
