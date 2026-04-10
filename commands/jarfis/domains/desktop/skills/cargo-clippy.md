# Cargo Clippy Expertise

## Core Rules
- `cargo clippy -- -D warnings`: 모든 경고를 에러로 처리 (CI/pipeline 기본)
- `#![deny(clippy::all)]`: 크레이트 레벨에서 clippy 강제
- `#![warn(clippy::pedantic)]`: 엄격 모드 (선택적, 새 프로젝트 권장)

## Decision Framework
- **즉시 수정**: `clippy::unwrap_used`, `clippy::expect_used` — `?` 또는 매칭으로 대체
- **판단 필요**: `clippy::module_name_repetitions` — 모듈 구조에 따라 허용 가능
- **무시 가능**: `clippy::must_use_candidate` — 과도한 `#[must_use]` 강요 시

## Tauri 프로젝트 특화
- `#[allow(clippy::needless_pass_by_value)]`: Tauri command의 `State<T>` 매개변수에 필요
- `#[allow(clippy::used_underscore_binding)]`: command 매개변수 이름 규칙 충돌 시
- `clippy.toml`에 `msrv = "1.70"` 등 최소 Rust 버전 명시 → 버전별 lint 조정

## Common Patterns
- `#[allow(...)]`은 함수/블록 단위로 최소 범위 적용. 파일 전체 `#![allow]` 지양
- `cargo clippy --fix`: 자동 수정 가능한 경고 일괄 처리
- `.cargo/config.toml`에 `[target.'cfg(...)']` 타겟별 lint 설정 가능
