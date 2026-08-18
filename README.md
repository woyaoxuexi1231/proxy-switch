# 🔌 Proxy Switch

> **A desktop app to manage proxy settings across local Windows and remote Linux servers — all from one clean interface.**

[Features](#features) · [Installation](#installation) · [Usage](#usage) · [Architecture](#architecture) · [Development](#development) · [License](#license)

---

## Why?

Configuring proxies is **tedious**. Every tool has its own config file, its own syntax, its own quirks. On remote Linux servers, you SSH in, edit `/etc/environment`, tweak APT configs, set Git globals, fiddle with Docker daemon settings… and on Windows, it's a different story altogether.

**Proxy Switch** makes this painless. One app, one click — detect, enable, or disable proxies across 10 components on both Windows (local) and Ubuntu (remote via SSH).

---

## Features

### 🌐 Remote (Ubuntu via SSH)
| Component | Config Mechanism | Requires sudo |
|---|---|---|
| **System Proxy** | `/etc/environment` + `/etc/profile.d/proxy-switch.sh` | Yes |
| **APT** | `/etc/apt/apt.conf.d/proxy.conf` | Yes |
| **Git** | `git config --global` | No |
| **Docker** | systemd drop-in + `daemon.json` (mirrors) | Yes |
| **npm** | `npm config set` | No |
| **Maven** | `~/.m2/settings.xml`（含阿里云镜像） | No |

### 🖥 Local (Windows)
| Component | Config Mechanism |
|---|---|
| **Git** | `git config --global` |
| **Docker** | Docker Desktop → Settings → Resources → Proxies（仅指引，不写配置） |
| **npm** | `npm config set` |
| **Maven** | `%USERPROFILE%\.m2\settings.xml`（含阿里云镜像） |

### Core capabilities
- **Auto-detect** — local components are detected on app launch; remote components are detected automatically when an SSH connection is established
- **Per-component control** — each proxy is an independent card with its own settings; no batch profiles, no forced uniformity
- **Manual setup guide** — every component includes a collapsible "How to configure manually" section showing the exact config files and commands, so you learn what's happening under the hood
- **Mirror support** — APT, Docker, npm, and Maven support registry mirror URLs in addition to proxy addresses
- **Toggle on/off** — enable or disable proxies per component, with instant status feedback
- **Config file visibility** — each card shows exactly which config files it touches

---

## Screenshot

```
 ┌─ Sidebar ─────┐  ┌─ Main Content ──────────────────────┐
 │                │  │                                      │
 │  ● dev-server  │  │  ● System Proxy  ENABLED  [▼]       │
 │    192.168...  │  │  ○ APT           disabled [▶]       │
 │    [断开]      │  │  ○ Git (Remote)  disabled [▶]       │
 │                │  │  ○ Docker        disabled [▶]       │
 │  [+ Add]       │  │  ○ npm           disabled [▶]       │
 │                │  │  ○ Maven         disabled [▶]       │
 │  ── Local ──── │  │                                      │
 │  ● This PC     │  │  ○ Git (Local)   disabled [▶]       │
 │                │  │  ○ Docker(Local) disabled [▶]       │
 │                │  │  ○ npm (Local)   disabled [▶]       │
 │                │  │  ○ Maven(Local)  disabled [▶]       │
 └────────────────┘  └──────────────────────────────────────┘
```

---

## Installation

### Download (Windows)

Download the latest `.msi` or `.exe` installer from the [Releases](https://github.com/woyaoxuexi1231/proxy-switch/releases) page.

### Prerequisites

- **Windows 10+** (64-bit)
- **Remote servers**: Ubuntu with SSH access (key-based or password authentication)
- **sudo**: For System Proxy, APT, and Docker remote components, the remote user needs passwordless sudo (`NOPASSWD` in sudoers)

---

## Usage

### 1. Add a server

Click **+ Add Server** in the sidebar, fill in your Ubuntu server's SSH details:

- **Name** — a friendly label
- **Host** — IP or hostname
- **Port** — SSH port (default 22)
- **User** — SSH user (default root)
- **Auth** — SSH key (default) or password

### 2. Connect

Click **Connect** on a server card. A green dot indicates a successful connection.

### 3. Configure proxies

Click any proxy card header to expand it. Each card shows:

- **Status** — enabled/disabled/not installed/not checked
- **Config files** — which files are affected
- **Manual setup guide** — the underlying commands if you want to do it yourself
- **Input fields** — HTTP proxy, HTTPS proxy, No Proxy, Mirror URL
- **Actions** — Apply, Disable, Refresh

Local components are auto-detected on launch. Remote components are auto-detected when you connect via SSH. No extra clicks needed.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                  Tauri 2.x                      │
│                                                 │
│  ┌──────────────────┐  ┌─────────────────────┐  │
│  │   React 18       │  │   Rust Backend      │  │
│  │   (TypeScript)   │◄─┤   (commands)        │  │
│  │                  │  │                     │  │
│  │  • Sidebar       │  │  • Server CRUD      │  │
│  │  • ProxyCard     │  │  • SSH Connection   │  │
│  │  • ServerDialog  │  │  • Connection Pool  │  │
│  │  • ManualGuide   │  │  • Remote Proxy     │  │
│  │  • StatusInd.    │  │  • Local Proxy      │  │
│  └──────────────────┘  │  • Config Store     │  │
│                         └─────────────────────┘  │
│                                                 │
│  Frontend ←→ invoke() ←→ Tauri Commands         │
│                                                 │
│  Rust Backend:                                   │
│  • ssh2 — SSH client (libssh2)                  │
│  • serde — Serialization                        │
│  • toml — Config persistence                    │
│  • regex — Config file parsing                  │
│  • quick-xml — Maven settings.xml               │
└─────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|---|---|
| **Desktop Shell** | [Tauri 2.x](https://v2.tauri.app/) — ~5 MB bundle |
| **Frontend** | React 18 + TypeScript + Vite |
| **Backend** | Rust — SSH, file I/O, process execution |
| **SSH** | [`ssh2`](https://crates.io/crates/ssh2) (libssh2) |
| **Styling** | Hand-written CSS — zero UI dependencies |
| **Config** | TOML files in `%APPDATA%\proxy-switch\` |

### Project Structure

```
proxy-switch/
├── src/                          # TypeScript frontend
│   ├── App.tsx                   # Root layout (sidebar + main + status bar)
│   ├── App.css                   # CSS variables, reset, layout
│   ├── components/
│   │   ├── Sidebar.tsx           # Server list + connection management
│   │   ├── ProxyCard.tsx         # Per-component proxy card (expandable)
│   │   ├── ServerDialog.tsx      # Add/edit server modal
│   │   ├── StatusIndicator.tsx   # ●/○/⏭ status display
│   │   └── ManualGuide.tsx       # Collapsible manual setup instructions
│   ├── hooks/
│   │   ├── useProxyStatus.ts     # Proxy detection/enable/disable logic
│   │   └── useSshConnection.ts   # SSH connection state management
│   ├── types/index.ts            # Shared TypeScript type definitions
│   └── utils/invoke.ts           # Typed Tauri invoke wrappers
│
├── src-tauri/                    # Rust backend
│   ├── Cargo.toml                # Rust dependencies
│   ├── tauri.conf.json           # Tauri window/config/bundle settings
│   └── src/
│       ├── main.rs               # Entry point
│       ├── lib.rs                # Module registration + command export
│       ├── models.rs             # Shared data types (Server, ProxyConfig, etc.)
│       ├── commands/
│       │   ├── server.rs         # CRUD commands for server config
│       │   ├── ssh_cmd.rs        # SSH connect/disconnect/state
│       │   ├── remote_proxy.rs   # Remote proxy detect/enable/disable
│       │   └── local_proxy.rs    # Local proxy detect/enable/disable
│       ├── ssh/
│       │   └── connection.rs     # SSH session + connection pool
│       ├── proxy/
│       │   ├── mod.rs            # ProxyModule trait definition
│       │   ├── remote/           # Ubuntu proxy modules
│       │   │   ├── system_proxy.rs
│       │   │   ├── apt.rs
│       │   │   ├── git.rs
│       │   │   ├── docker.rs
│       │   │   ├── npm.rs
│       │   │   └── maven.rs
│       │   └── local/            # Windows proxy modules
│       │       ├── git.rs
│       │       ├── docker.rs
│       │       ├── npm.rs
│       │       └── maven.rs
│       └── config/
│           └── store.rs          # TOML-based config persistence
│
├── package.json
├── vite.config.ts
├── tsconfig.json
└── docs/                         # Design, release, and engineering docs
```

### How It Works

1. **Local detection** — On Windows, the Rust backend spawns child processes (`git config --get`, `npm config get`, etc.) or reads config files (`settings.xml`) directly from the filesystem.
2. **Remote detection** — Through an SSH session (managed by a connection pool), the backend executes commands on the remote Ubuntu server (`cat /etc/environment`, `git config --global --get`, `npm config get`, etc.) or reads files via SFTP/base64 piping.
3. **Enabling/disabling** — For each component, the backend applies the appropriate configuration: writing files (SFTP for user-owned, base64 + `sudo tee` for root-owned), running CLI commands, or modifying XML/JSON configs.
4. **Connection pool** — Only one SSH connection is active at a time (simplifies state management). The pool is protected by a `Mutex` for thread safety.

### Plugin Architecture

Every proxy component (local or remote) follows the same interface:

```rust
pub trait ProxyModule {
    fn config_files(&self) -> Vec<String>;
    fn manual_steps(&self) -> Vec<(String, Vec<String>)>;
    fn detect(&self, session: &SshSession) -> bool;
    fn status(&self, session: &SshSession) -> ProxyStatus;
    fn enable(&self, session: &SshSession, config: &ProxyConfig) -> OpResult;
    fn disable(&self, session: &SshSession) -> OpResult;
}
```

To add a new component, you implement this trait and register it in the respective command handler. The frontend automatically picks it up by adding a new entry to `ComponentId`.

---

## Development

### Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [Rust](https://www.rust-lang.org/) 1.70+
- [Tauri CLI](https://v2.tauri.app/start/prerequisites/) (`cargo install tauri-cli`)
- Windows: [Microsoft Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### Setup

```bash
# Clone the repo
git clone https://github.com/woyaoxuexi1231/proxy-switch.git
cd proxy-switch

# Install frontend dependencies
npm install

# Run in development mode
npm run tauri dev

# Build for production
npm run tauri build
```

### Commands

| Command | Description |
|---|---|
| `npm run dev` | Start Vite dev server only |
| `npm run build` | Type-check + build frontend |
| `npm run tauri dev` | Full Tauri dev mode (hot reload) |
| `npm run tauri build` | Production build → `.msi` / `.exe` |

### Config File Location

Server configurations are stored at:

```
%APPDATA%\proxy-switch\servers.toml
```

**⚠️ Note:** Passwords are currently stored in this TOML file. A future version will use Windows Credential Manager via the `keyring` crate for secure credential storage.

---

## FAQ

### Why per-component instead of batch profiles?

Each tool has different proxy needs — npm might use a registry mirror instead of a proxy, Docker needs systemd restarts, APT needs sudo. Treating each as an independent unit gives you full control and clear visibility.

### Does it support macOS / Linux desktop?

Currently Windows-only for the desktop app. The remote target is always Ubuntu (any Linux with the standard tools). macOS/Linux desktop support is planned for a future release.

### What if a tool isn't installed?

The card shows `⏭ NOT INSTALLED` with a gray indicator. The manual setup guide is still available so you know what to do once you install it.

### What SSH authentication methods are supported?

- **SSH key** (default) — specify the path to your private key (supports `~` expansion)
- **Password** — entered in the server dialog

---

## Roadmap

- [ ] Secure credential storage via Windows Credential Manager
- [ ] macOS and Linux desktop support
- [ ] SSH key passphrase support
- [ ] Connection keep-alive with auto-reconnect
- [ ] Dark mode
- [ ] CLI companion for headless automation

---

## License

[MIT](LICENSE)

---

## Acknowledgments

Built with:
- [Tauri](https://v2.tauri.app/) — the lightweight desktop framework
- [ssh2](https://crates.io/crates/ssh2) — SSH for Rust
- [React](https://react.dev/) — UI library

---

<p align="center">
  <sub>Made with ❤️ for developers tired of manually configuring proxies</sub>
</p>
