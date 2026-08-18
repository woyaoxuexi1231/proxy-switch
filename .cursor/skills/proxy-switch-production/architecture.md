# Architecture

## Stack

| Layer | Tech |
|---|---|
| Shell | Tauri 2 (`src-tauri/tauri.conf.json`) — window ~960×720, NSIS installer |
| UI | React 18 + TypeScript + Vite — `src/` |
| Backend | Rust 2021 — `src-tauri/src/` |
| IPC | Tauri `invoke` ↔ `#[tauri::command]` |
| SSH | `ssh2` (libssh2), one session in `ConnectionPool` |
| Persist | `%APPDATA%\proxy-switch\servers.toml` via `config/store.rs` |

Entry: `src/main.tsx` → `App.tsx`. Rust: `main.rs` → `lib.rs` `run()`.

## UI composition

```text
App
├── Sidebar          servers + connect/disconnect + add/edit/delete
├── main
│   ├── Remote cards   REMOTE_COMPONENTS × ProxyCard (isRemote, connected=SSH)
│   └── Local cards    LOCAL_COMPONENTS × ProxyCard (isRemote=false, connected=true)
├── status-bar
└── ServerDialog       add/edit modal
```

`ProxyCard` uses `useProxyStatus` + `StatusIndicator` + `ManualGuide`.

There is **no router**. Important UI state is local (expanded card, dialog).

## IPC map

All wrappers: `src/utils/invoke.ts`. Registered in `src-tauri/src/lib.rs`.

| Command | Side | Returns |
|---|---|---|
| `get_servers` / `add_server` / `update_server` / `delete_server` | config store | `Server[]` / `OpResult` |
| `ssh_connect` / `ssh_disconnect` / `ssh_state` | connection pool | `OpResult` / `SshState` |
| `remote_detect` / `remote_enable` / `remote_disable` | SSH + `ProxyModule` | `ProxyStatus` / `OpResult` |
| `remote_detect_all` | SSH, all remote ids | `ProxyStatus[]` |
| `local_detect` / `local_enable` / `local_disable` | `spawn_blocking` + local modules | `ProxyStatus` / `OpResult` |
| `local_detect_all` | parallel threads | `ProxyStatus[]` |

Frontend currently detects **per card** via `detectProxy` (refresh button).
`localDetectAll` / `remoteDetectAll` exist but are unused. Prefer them if
refactoring launch/connect auto-detect; do not leave a third detect API.

`ssh_connect` and local commands are `async` + `spawn_blocking` so the UI
thread does not stall. Remote detect/enable/disable are sync commands that
lock the pool — keep them short; do not add long blocking work on the UI
thread without `spawn_blocking`.

## Rust modules

```text
lib.rs                 manage ConfigStore + Arc<ConnectionPool>, register commands
models.rs              Server, ProxyConfig, ProxyStatus, ComponentId, OpResult, …
commands/server.rs     CRUD — thin
commands/ssh_cmd.rs    connect/disconnect/state
commands/remote_proxy.rs  parse ComponentId → Box<dyn ProxyModule>
commands/local_proxy.rs   match string → Git/Docker/Npm/Maven local module
ssh/connection.rs      SshSession + ConnectionPool (Mutex<Option<SshSession>>)
proxy/mod.rs           trait ProxyModule (remote; takes &SshSession)
proxy/remote/*         Ubuntu modules
proxy/local/*          Windows modules (same method names, no trait — no session)
proxy/maven_xml.rs     shared settings.xml patch (fixed proxy/mirror ids)
config/store.rs        TOML servers
```

Remote plugin surface:

```rust
pub trait ProxyModule: Send + Sync {
    fn config_files(&self) -> Vec<String>;
    fn manual_steps(&self) -> Vec<(String, Vec<String>)>;
    fn detect(&self, session: &SshSession) -> bool;
    fn status(&self, session: &SshSession) -> ProxyStatus;
    fn enable(&self, session: &SshSession, config: &ProxyConfig) -> OpResult;
    fn disable(&self, session: &SshSession) -> OpResult;
}
```

Local modules duplicate this shape without `SshSession`. Unifying behind a
trait is a valid refactor **if** it stays simple; do not introduce generics
theater.

## Data contracts

Keep these three in sync:

1. `src-tauri/src/models.rs` — source of serde shape
2. `src/types/index.ts` — TS interfaces + `ComponentId` union + card lists
3. Command parsers (`parse_component` in `remote_proxy.rs`, match in `local_proxy.rs`)

`ComponentId` serde: `rename_all = "snake_case"`  
(`SystemProxy` ↔ `"system_proxy"`, `GitRemote` ↔ `"git_remote"`).

`AuthMode`: `rename_all = "lowercase"` (`key` | `password`).

`ProxyConfig` fields: `http_proxy`, `https_proxy`, `no_proxy`, `mirror`.

`OpResult`: `{ success, message }` — UI must branch on `success`, not string matching.

## Add a proxy component (full checklist)

1. `ComponentId` variant + `label` / `is_remote` / `remote_all` or `local_all` in `models.rs`
2. TS `ComponentId` + `REMOTE_COMPONENTS` or `LOCAL_COMPONENTS` + labels in `types/index.ts`
3. New file under `proxy/remote/` or `proxy/local/`
4. Register in `get_module` / `local_*` match + `parse_component` if remote
5. `ProxyCard` flags only if needed: `GUIDE_ONLY`, `supportsMirror`, `needsSudo`, Maven
6. Manual steps that match real files/commands
7. `cargo check` + `npx tsc --noEmit`

Do not add a card that cannot detect/enable/disable (except explicit guide-only).

## SSH helpers

- `run(cmd)` — exec on remote
- `read_file` / `write_file(path, content, sudo)`
- sudo write: `mkdir -p` parent, base64 decode, `sudo tee`, `chmod 644`
- non-sudo write: SFTP
- `tool_exists` — `command -v` / `which`
- `has_sudo` — `sudo -n true`

Component modules should use these helpers, not invent a second shell encoding.

## Config store

Servers keyed as `server:{name}` in TOML. `id` currently equals `name`.
Renaming identity is a breaking change for connect/delete — do not casually
split `id` vs `name` without migrating the file and the UI keys.
