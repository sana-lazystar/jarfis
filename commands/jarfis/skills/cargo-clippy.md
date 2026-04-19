# Cargo Clippy Expertise

## Core Rules
- `cargo clippy -- -D warnings`: Treat all warnings as errors (CI/pipeline default)
- `#![deny(clippy::all)]`: Enforce clippy at the crate level
- `#![warn(clippy::pedantic)]`: Strict mode (optional, recommended for new projects)

## Decision Framework
- **Fix immediately**: `clippy::unwrap_used`, `clippy::expect_used` — Replace with `?` or pattern matching
- **Requires judgment**: `clippy::module_name_repetitions` — May be acceptable depending on module structure
- **Can ignore**: `clippy::must_use_candidate` — When it forces excessive `#[must_use]`

## Tauri Project Specifics
- `#[allow(clippy::needless_pass_by_value)]`: Needed for Tauri command `State<T>` parameters
- `#[allow(clippy::used_underscore_binding)]`: When command parameter naming conventions conflict
- Specify minimum Rust version in `clippy.toml` with `msrv = "1.70"` etc. to adjust version-specific lints

## Common Patterns
- Apply `#[allow(...)]` at the narrowest scope (function/block level). Avoid file-wide `#![allow]`
- `cargo clippy --fix`: Batch-fix auto-fixable warnings
- Target-specific lint configuration possible via `[target.'cfg(...)']` in `.cargo/config.toml`
