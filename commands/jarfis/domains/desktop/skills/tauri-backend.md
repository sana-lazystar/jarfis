# Tauri Backend Expertise

## Core Patterns

### Command System
- `#[tauri::command]`: Rust 함수를 WebView에서 호출 가능하게 노출
- 반환값은 `serde::Serialize` 필수. 에러는 `Result<T, String>` 또는 커스텀 에러 타입
- `async` command: 파일 I/O, 네트워크 등 블로킹 작업 시 필수. `tokio` 런타임 사용
- State 접근: `tauri::State<'_, T>` 매개변수로 앱 상태 주입 (DI 패턴)

### IPC 판단 기준
- **1MB 미만 데이터**: `invoke()` → command 반환값으로 직접 전달
- **1MB 이상 데이터**: 파일로 저장 후 경로만 전달, 또는 스트리밍 이벤트
- **실시간 업데이트**: `app.emit()` 이벤트 시스템 사용 (단방향 push)
- **양방향 통신**: command(요청) + event(응답) 조합

### Plugin System
- `tauri-plugin-*`: 공식 플러그인 (fs, http, shell, dialog, notification 등)
- Tauri v2: 플러그인은 `Cargo.toml` dependencies + `tauri.conf.json` plugins에 등록
- 커스텀 플러그인: `tauri::plugin::Builder`로 생성. 자체 command + state + 라이프사이클

### App Lifecycle
- `setup()`: 앱 초기화 — DB 연결, 설정 로드, 시스템 트레이 설정
- `on_window_event()`: 창 닫기, 포커스 등 이벤트 처리
- 시스템 트레이: `SystemTray::new()` + `SystemTrayEvent` 핸들러

## Common Pitfalls
- Command에서 `std::fs` 직접 사용 → 경로 보안 문제. `tauri::api::path`로 앱 디렉토리 기준 상대 경로 사용
- `State<Mutex<T>>`를 async command에서 오래 잠금 → UI 프리즈. 잠금 범위 최소화
- `serde` 직렬화 실패 → 런타임 에러. 복잡한 타입은 DTO로 변환
- Tauri v1 → v2 마이그레이션: `tauri::api::*` 대부분 플러그인으로 이동. `@tauri-apps/api` 임포트 경로 변경
