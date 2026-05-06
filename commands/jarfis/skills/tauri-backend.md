# Tauri Backend Expertise

<!-- jarfis:context7
library_id: /websites/rs_tauri_2_9_5
query_topics: [commands, IPC, plugins, state management, capabilities]
-->

## Core Patterns

### Command System
- `#[tauri::command]`: Exposes Rust functions to be callable from the WebView
- Return values must implement `serde::Serialize`. Errors use `Result<T, String>` or a custom error type
- `async` commands: Required for blocking operations like file I/O and network. Uses the `tokio` runtime
- State access: Inject app state via `tauri::State<'_, T>` parameter (DI pattern)

### IPC Decision Criteria
- **Data under 1MB**: `invoke()` — Return directly from command
- **Data over 1MB**: Save to file and pass the path, or use streaming events
- **Real-time updates**: Use `app.emit()` event system (unidirectional push)
- **Bidirectional communication**: Combine commands (requests) + events (responses)

### Plugin System
- `tauri-plugin-*`: Official plugins (fs, http, shell, dialog, notification, etc.)
- Tauri v2: Plugins are registered in `Cargo.toml` dependencies + `tauri.conf.json` plugins
- Custom plugins: Create with `tauri::plugin::Builder`. Includes own commands + state + lifecycle

### App Lifecycle
- `setup()`: App initialization — DB connections, config loading, system tray setup
- `on_window_event()`: Handle window close, focus, and other events
- System tray: `SystemTray::new()` + `SystemTrayEvent` handler

## Common Pitfalls
- Using `std::fs` directly in commands — Path security issues. Use relative paths based on app directory via `tauri::api::path`
- Holding `State<Mutex<T>>` lock too long in async commands — UI freeze. Minimize lock scope
- `serde` serialization failure — Runtime error. Convert complex types to DTOs
- Tauri v1 to v2 migration: Most `tauri::api::*` moved to plugins. `@tauri-apps/api` import paths changed
