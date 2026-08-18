# Proxy Switch

> **A desktop app to manage proxy settings across local Windows and remote Ubuntu servers — from one clean interface.**

[Features](#features) · [Installation](#installation) · [Usage](#usage) · [Architecture](#architecture) · [Development](#development) · [License](#license)

**Current release:** [v1.5.0](https://github.com/woyaoxuexi1231/proxy-switch/releases/tag/v1.5.0)

---

## Why?

Configuring proxies is tedious. Every tool has its own config file, syntax, and quirks. On remote Linux you SSH in, edit `/etc/environment`, tweak APT, set Git globals, fiddle with Docker… and on Windows it is a different story.

**Proxy Switch** makes this straightforward. Detect, enable, or disable proxies across **10 components** on Windows (local) and Ubuntu (remote via SSH).

---

## Features

### Remote (Ubuntu via SSH)

| Component | Config Mechanism | Requires sudo |
|---|---|---|
| **System Proxy** | `/etc/environment` + `/etc/profile.d/proxy-switch.sh` | Yes |
| **APT** | `/etc/apt/apt.conf.d/proxy.conf` | Yes |
| **Git** | `git config --global` | No |
| **Docker** | systemd drop-in + `daemon.json` (mirrors) | Yes |
| **npm** | `npm config set` | No |
| **Maven** | `~/.m2/settings.xml` (Aliyun mirror supported) | No |

### Local (Windows)

| Component | Config Mechanism |
|---|---|
| **Git** | `git config --global` |
| **Docker** | Docker Desktop → Settings → Resources → Proxies (**guide only**, never writes files) |
| **npm** | `npm config set` |
| **Maven** | `%USERPROFILE%\.m2\settings.xml` (Aliyun mirror supported) |

### Core capabilities

- **Auto-detect** — local components on launch; remote components when SSH connects
- **Per-component control** — compact tiles in a grid; click opens a settings dialog
- **Islands UI** — sidebar, workspace status, Remote, and Local each sit on their own rounded panel
- **Manual setup guide** — every component shows the real files and commands
- **Mirror support** — APT, Docker, npm, Maven
- **Honest status** — `ON` / `OFF` / `N/A` (not installed) on each tile; full detail in the dialog

---

## Screenshot

```
 ┌─ Servers ──────┐  ┌─ Workspace ─────────────────────────────┐
 │ Proxy Switch   │  │ Connected: dev-server                     │
 │                │  ├─ Remote (Ubuntu via SSH) ───────────────┤
 │ ● dev-server   │  │  ┌ System ┐ ┌ APT ┐ ┌ Git ┐ ┌ Docker ┐ │
 │   192.168...   │  │  │  ON    │ │ OFF │ │ OFF │ │  OFF   │ │
 │   [Disconnect] │  │  └────────┘ └─────┘ └─────┘ └────────┘ │
 │                │  │  ┌ npm ┐ ┌ Maven ┐                      │
 │ [+ Add Server] │  │  │ OFF │ │  OFF  │   ← click → dialog  │
 │                │  │  └─────┘ └───────┘                      │
 │ ── Local ───── │  ├─ Local (Windows) ───────────────────────┤
 │ ● This PC      │  │  ┌ Git ┐ ┌ Docker ┐ ┌ npm ┐ ┌ Maven ┐  │
 │   Windows      │  │  │ OFF │ │  N/A   │ │ OFF │ │  OFF  │  │
 └────────────────┘  └─────────────────────────────────────────┘
```

---

## Installation

### Download (Windows)

Download the latest **NSIS** installer (`Proxy Switch_x.x.x_x64-setup.exe`) from the [Releases](https://github.com/woyaoxuexi1231/proxy-switch/releases) page.

### Prerequisites

- **Windows 10+** (64-bit) with WebView2 (included on recent Windows)
- **Remote servers**: Ubuntu with SSH (key or password)
- **sudo**: System Proxy, APT, and Docker remote need passwordless sudo (`NOPASSWD`) when those modules write root-owned files

---

## Usage

### 1. Add a server

Click **+ Add Server**, then fill in SSH details (name, host, port, user, key or password).

### 2. Connect

Click **Connect** on a server card. A green status dot means the session is live.

### 3. Configure proxies

- **Local** tiles are ready on launch.
- **Remote** tiles unlock after SSH connect; statuses load automatically.
- Click a tile to open its **dialog**: status, config files, manual guide, proxy/mirror fields, Apply / Disable / Refresh.
- Guide-only **Docker (Local)** never writes Docker Desktop files; the dialog shows the GUI steps instead.

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
│  │  • ProxyDialog   │  │  • Connection Pool  │  │
│  │  • ServerDialog  │  │  • Remote Proxy     │  │
│  │  • Island layout │  │  • Local Proxy      │  │
│  └──────────────────┘  │  • Config Store     │  │
│                         └─────────────────────┘  │
│                                                 │
│  Frontend ←→ invoke.ts ←→ Tauri Commands        │
└─────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|---|---|
| **Desktop Shell** | [Tauri 2.x](https://v2.tauri.app/) |
| **Frontend** | React 18 + TypeScript + Vite |
| **Styling** | Tailwind CSS v4 + Outfit / Noto Sans SC / Fira Code |
| **Icons** | lucide-react |
| **Backend** | Rust — SSH, file I/O, process execution |
| **SSH** | [`ssh2`](https://crates.io/crates/ssh2) (libssh2) |
| **Config** | TOML under `%APPDATA%\proxy-switch\` |

### Project Structure

```
proxy-switch/
├── src/                          # TypeScript frontend
│   ├── App.tsx                   # Islands shell (sidebar + Remote + Local)
│   ├── index.css                 # Tailwind + fonts
│   ├── components/
│   │   ├── Sidebar.tsx           # Servers + connect / disconnect
│   │   ├── ProxyCard.tsx         # Compact tile (opens dialog)
│   │   ├── ProxyDialog.tsx       # Per-component settings modal
│   │   ├── ServerDialog.tsx      # Add / edit server modal
│   │   ├── Island.tsx            # Rounded panel wrapper
│   │   ├── StatusIndicator.tsx   # Detailed status text
│   │   └── ManualGuide.tsx       # Manual setup steps
│   ├── hooks/
│   │   ├── useProxyStatus.ts     # Detect / enable / disable
│   │   ├── useSshConnection.ts   # SSH + bulk detect
│   │   └── useServers.ts         # Server list CRUD
│   ├── types/index.ts            # Shared types + component lists
│   └── utils/invoke.ts           # Typed Tauri IPC
│
├── src-tauri/                    # Rust backend
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   └── src/
│       ├── commands/             # Thin IPC handlers
│       ├── ssh/                  # Session + connection pool
│       ├── proxy/remote/         # Ubuntu modules
│       ├── proxy/local/          # Windows modules
│       └── config/store.rs       # servers.toml
│
├── docs/                         # Design + release notes
├── package.json
└── vite.config.ts
```

### How It Works

1. **Local detection** — Rust runs tools (`git`, `npm`, …) or reads files (`settings.xml`, Docker Desktop settings) on Windows without flashing console windows.
2. **Remote detection** — One SSH session in a connection pool; modules detect/status/enable/disable over that session. Heavy work uses `spawn_blocking` so the UI stays responsive.
3. **Enabling / disabling** — Write user files via SFTP, or root files via base64 + `sudo tee` (parent dirs created when needed).
4. **Single session** — Connecting replaces any previous SSH session.

### Plugin Architecture

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

Add a component by implementing the module, registering it in the command layer, and extending `ComponentId` / the frontend component lists together.

---

## Development

### Prerequisites

- [Node.js](https://nodejs.org/) 18+
- [Rust](https://www.rust-lang.org/) 1.70+
- [Tauri CLI](https://v2.tauri.app/start/prerequisites/)
- Windows: [Microsoft Visual Studio C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/)

### Setup

```bash
git clone https://github.com/woyaoxuexi1231/proxy-switch.git
cd proxy-switch
npm install
npm run tauri dev
```

### Commands

| Command | Description |
|---|---|
| `npm run dev` | Vite only |
| `npm run build` | Type-check + frontend build |
| `npm run tauri dev` | Full app with hot reload |
| `npm run tauri build` | Release → NSIS installer under `src-tauri/target/release/bundle/nsis/` |

### Config File Location

```
%APPDATA%\proxy-switch\servers.toml
```

**Note:** Passwords are currently stored in this TOML file. A future version may use Windows Credential Manager.

### Releasing

See [docs/发布文档.md](docs/发布文档.md). Pushing a `v*` tag (for example `v1.5.0`) triggers GitHub Actions to build and attach the Windows installer.

---

## FAQ

### Why per-component instead of batch profiles?

Each tool has different needs — npm may use a mirror, Docker needs restarts, APT needs sudo. Independent tiles keep status and ownership clear.

### Does it support macOS / Linux desktop?

The app is **Windows-only** today. Remote targets are Ubuntu (or similar). Desktop support for other OSes is not shipped yet.

### What if a tool isn't installed?

The tile shows **N/A**. The dialog still includes the manual guide for when you install the tool later.

### What SSH auth methods are supported?

- **SSH key** (default) — path with `~` expansion
- **Password** — set in the server dialog

---

## Roadmap

- [ ] Secure credential storage via Windows Credential Manager
- [ ] macOS and Linux desktop support
- [ ] SSH key passphrase support
- [ ] Connection keep-alive with auto-reconnect
- [ ] Dark mode

---

## License

[MIT](LICENSE)

---

## Acknowledgments

Built with [Tauri](https://v2.tauri.app/), [ssh2](https://crates.io/crates/ssh2), and [React](https://react.dev/).
