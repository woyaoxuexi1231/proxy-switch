# Proxy-Switch v1.0 — 重写设计文档

## 一、项目概述

将现有的 Python + tkinter 实现的 proxy-switch 工具，使用 **Rust + TypeScript (Tauri 2.x)** 完全重写。保留核心能力（SSH 远程配置 Ubuntu 代理），新增 Windows 本地代理检测与配置，彻底重构 UI 交互模式。

### 核心变化

| 维度 | 旧版 (v0.2) | 新版 (v1.0) |
|---|---|---|
| 语言 | Python | Rust + TypeScript |
| GUI 框架 | tkinter (customtkinter) | Tauri 2.x + React 18 |
| 交互模式 | 批量 Profile 一键应用 | 每个组件独立卡片，各自配置 |
| 远程目标 | Ubuntu (SSH) | Ubuntu (SSH) |
| 本地目标 | 无 | Windows (Docker, Git, npm, Maven) |
| CLI 模式 | 支持 | **删除** — 仅 Windows GUI |
| 多 Profile | 支持 | **删除** — 按组件自由配置 |
| 代理镜像 | 支持 mirror | 保留（APT / Docker / npm / Maven） |

---

## 二、技术选型

### 2.1 Tauri 2.x

- **Rust 后端**：所有系统级操作（SSH 连接、本地进程检测、文件读写、注册表读取）由 Rust 侧完成
- **TypeScript 前端**：React 18 负责全部 UI 渲染与交互
- **IPC 通信**：Tauri `invoke` / `command` 机制，前端调用 Rust 函数
- **打包体积**：~5-8 MB（相比 Electron 的 100MB+ 和 PyInstaller 的 25MB）

### 2.2 Rust 侧依赖 (Cargo.toml)

```toml
[dependencies]
tauri = { version = "2", features = ["devtools"] }
tauri-plugin-shell = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
toml = "0.8"                          # 配置文件读写
ssh2 = "0.9"                          # SSH 客户端（基于 libssh2）
russh = "0.44"                        # 备选：纯 Rust SSH 实现
keyring = "3"                         # 安全存储密码（Windows Credential Manager）
tokio = { version = "1", features = ["full"] }
thiserror = "2"
dirs = "5"                            # 跨平台目录（%APPDATA% 等）
regex = "1"
quick-xml = "0.37"                    # Maven settings.xml 解析
```

### 2.3 TypeScript 侧依赖 (package.json)

```json
{
  "dependencies": {
    "react": "^18.3",
    "react-dom": "^18.3",
    "@tauri-apps/api": "^2",
    "@tauri-apps/plugin-shell": "^2"
  },
  "devDependencies": {
    "typescript": "^5.6",
    "vite": "^6",
    "@vitejs/plugin-react": "^4",
    "@tauri-apps/cli": "^2"
  }
}
```

**不引入任何 UI 组件库** — 所有组件手写 CSS，避免 AI 味的设计。

---

## 三、项目结构

```
proxy-switch/
├── src-tauri/                       # Rust 后端
│   ├── Cargo.toml
│   ├── tauri.conf.json
│   ├── build.rs
│   ├── icons/                       # 应用图标
│   └── src/
│       ├── main.rs                  # Tauri 入口
│       ├── lib.rs                   # 模块注册 + Tauri command 导出
│       ├── commands/                # 所有 #[tauri::command] 函数
│       │   ├── mod.rs
│       │   ├── server.rs            # 服务器 CRUD
│       │   ├── ssh.rs               # SSH 连接管理
│       │   ├── remote_proxy.rs      # 远程代理检测/配置
│       │   └── local_proxy.rs       # 本地 Windows 代理检测/配置
│       ├── ssh/                     # SSH 子系统
│       │   ├── mod.rs
│       │   ├── connection.rs        # SSH 连接 + 连接池
│       │   └── executor.rs          # 高层远程操作
│       ├── proxy/                   # 代理操作核心逻辑
│       │   ├── mod.rs
│       │   ├── remote/              # 远程 Linux 代理
│       │   │   ├── mod.rs
│       │   │   ├── system_proxy.rs  # /etc/environment
│       │   │   ├── apt.rs           # /etc/apt/apt.conf.d/
│       │   │   ├── git.rs           # git config --global
│       │   │   ├── docker.rs        # systemd docker.service.d
│       │   │   ├── npm.rs           # npm config
│       │   │   └── maven.rs         # ~/.m2/settings.xml
│       │   └── local/               # 本地 Windows 代理
│       │       ├── mod.rs
│       │       ├── git.rs
│       │       ├── docker.rs
│       │       ├── npm.rs
│       │       └── maven.rs
│       ├── config/                  # 本地配置管理
│       │   ├── mod.rs
│       │   └── store.rs             # TOML 读写（服务器列表）
│       └── models.rs                # 共享数据结构
│
├── src/                             # TypeScript 前端
│   ├── main.tsx                     # React 入口
│   ├── App.tsx                      # 根组件 + 布局
│   ├── App.css                      # 全局样式
│   ├── components/
│   │   ├── Sidebar.tsx              # 侧边栏：服务器连接
│   │   ├── Sidebar.css
│   │   ├── ProxyCard.tsx            # 单个代理组件的卡片
│   │   ├── ProxyCard.css
│   │   ├── StatusIndicator.tsx      # ●/○ 状态指示器
│   │   ├── ManualGuide.tsx          # 可折叠的“手动配置说明”
│   │   ├── ManualGuide.css
│   │   ├── ServerDialog.tsx         # 添加/编辑服务器对话框
│   │   └── ServerDialog.css
│   ├── hooks/
│   │   ├── useSshConnection.ts      # SSH 连接状态 hook
│   │   └── useProxyStatus.ts        # 代理状态轮询 hook
│   ├── types/
│   │   └── index.ts                 # TypeScript 类型定义
│   └── utils/
│       └── invoke.ts                # Tauri invoke 封装（类型安全包装）
│
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
└── docs/DESIGN.md                   # 本文档
```

---

## 四、数据结构设计

### 4.1 Rust 侧核心类型

```rust
// src-tauri/src/models.rs

use serde::{Deserialize, Serialize};

/// SSH 服务器信息
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Server {
    pub id: String,              // 唯一标识 (UUID)
    pub name: String,            // 显示名称
    pub host: String,            // IP 或域名
    pub port: u16,               // SSH 端口，默认 22
    pub user: String,            // SSH 用户
    pub auth_mode: AuthMode,     // 认证方式
    pub ssh_key_path: Option<String>,
    pub password: Option<String>, // 加密存储
    pub description: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AuthMode {
    Key,
    Password,
}

/// 代理配置值
#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProxyConfig {
    pub http_proxy: String,
    pub https_proxy: String,
    pub no_proxy: String,
    pub mirror: String,          // 镜像地址（APT/Docker/npm/Maven）
}

/// 单个代理组件的状态
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProxyStatus {
    pub component: ComponentId,
    pub installed: bool,
    pub enabled: bool,
    pub current_http_proxy: Option<String>,
    pub current_https_proxy: Option<String>,
    pub current_no_proxy: Option<String>,
    pub current_mirror: Option<String>,
    pub config_files: Vec<String>,            // 涉及的配置文件路径
    pub manual_setup_commands: Vec<String>,    // 手动配置命令/步骤
}

/// 操作结果
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpResult {
    pub success: bool,
    pub message: String,
}

/// 组件标识
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ComponentId {
    // Remote (Linux via SSH)
    SystemProxy,
    Apt,
    GitRemote,
    DockerRemote,
    NpmRemote,
    MavenRemote,
    // Local (Windows)
    GitLocal,
    DockerLocal,
    NpmLocal,
    MavenLocal,
}
```

### 4.2 TypeScript 侧类型

```typescript
// src/types/index.ts

export interface Server {
  id: string;
  name: string;
  host: string;
  port: number;
  user: string;
  auth_mode: 'key' | 'password';
  ssh_key_path?: string;
  password?: string;
  description: string;
}

export interface ProxyConfig {
  http_proxy: string;
  https_proxy: string;
  no_proxy: string;
  mirror: string;
}

export type ComponentId =
  | 'system_proxy'
  | 'apt'
  | 'git_remote'
  | 'docker_remote'
  | 'npm_remote'
  | 'maven_remote'
  | 'git_local'
  | 'docker_local'
  | 'npm_local'
  | 'maven_local';

export interface ProxyStatus {
  component: ComponentId;
  installed: boolean;
  enabled: boolean;
  current_http_proxy: string | null;
  current_https_proxy: string | null;
  current_no_proxy: string | null;
  current_mirror: string | null;
  config_files: string[];
  manual_setup_commands: string[];
}

export interface OpResult {
  success: boolean;
  message: string;
}

export interface SshState {
  connected: boolean;
  server: Server | null;
  error: string | null;
}
```

---

## 五、UI 设计

### 5.1 整体布局

```
┌──────────────────────────────────────────────────────────┐
│  Proxy-Switch  v1.0                            —  □  ×  │
├────────────┬─────────────────────────────────────────────┤
│            │                                             │
│  服务器连接 │  ┌─ System Proxy (Remote) ────────────────┐│
│            │  │ ● ENABLED  http://127.0.0.1:7890       ││
│  ┌───────┐ │  │                                        ││
│  │Ubuntu │ │  │ 配置文件: /etc/environment              ││
│  │Server │ │  │           /etc/profile.d/proxy-switch.sh││
│  │  ●    │ │  │                                        ││
│  └───────┘ │  │ ▸ 如何手动配置                         ││
│            │  │                                        ││
│  [+ 添加]  │  │ HTTP Proxy  [http://127.0.0.1:7890   ] ││
│            │  │ HTTPS Proxy [http://127.0.0.1:7890   ] ││
│            │  │ No Proxy    [localhost,127.0.0.1     ] ││
│            │  │                                        ││
│  ────────  │  │ [Apply]  [Disable]  [↻ Refresh]        ││
│            │  └────────────────────────────────────────┘│
│  本地 Windows│                                             │
│            │  ┌─ Git (Local) ───────────────────────────┐│
│  ┌───────┐ │  │ ○ disabled                             ││
│  │ 本机   │ │  │                                        ││
│  │  ●    │ │  │ 配置文件: %USERPROFILE%\\.gitconfig     ││
│  └───────┘ │  │ 命令: git config --global http.proxy   ││
│            │  │                                        ││
│            │  │ ▸ 如何手动配置                         ││
│            │  │                                        ││
│            │  │ HTTP Proxy  [________________]          ││
│            │  │ HTTPS Proxy [________________]          ││
│            │  │                                        ││
│            │  │ [Apply]  [Disable]  [↻ Refresh]         ││
│            │  └────────────────────────────────────────┘│
│            │                                             │
│            │  ┌─ Docker (Local) ────────────────────────┐│
│            │  │ ...                                     ││
│            │  └────────────────────────────────────────┘│
│            │  ... (npm, Maven)                          │
│            │                                             │
├────────────┴─────────────────────────────────────────────┤
│  Ready                            Connected: my-ubuntu   │
└──────────────────────────────────────────────────────────┘
```

### 5.2 组件树

```
App
├── Sidebar
│   ├── ServerCard[]           ← 每台服务器一张卡片
│   │   ├── StatusDot          ← 连接状态指示
│   │   └── ServerActions      ← 连接/断开/编辑/删除
│   └── AddServerButton
│
├── MainContent
│   ├── SectionHeader "Remote (Ubuntu)"
│   ├── ProxyCard[]            ← 远程组件卡片列表
│   │   ├── StatusIndicator    ← ●/○/⏭
│   │   ├── ConfigFileList     ← 涉及的配置文件
│   │   ├── ManualGuide        ← 可折叠手动说明
│   │   ├── ProxyInputFields   ← HTTP/HTTPS/NoProxy/Mirror 输入框
│   │   └── ActionButtons      ← Apply / Disable / Refresh
│   │
│   ├── SectionHeader "Local (Windows)"
│   └── ProxyCard[]            ← 本地组件卡片列表
│
├── StatusBar
└── ServerDialog (Modal)
```

### 5.3 配色方案 — 浅色干净风格

**核心原则：克制、干净、信息层级清晰。不使用渐变。不用蓝色作为主色调。**

```
┌─────────────────────────────────────────────┐
│  色彩变量                | 用途             │
├─────────────────────────────────────────────┤
│  --bg-primary: #FFFFFF    | 主背景（纯白）   │
│  --bg-secondary: #F8F9FA  | 卡片/侧边栏背景  │
│  --bg-tertiary: #F0F1F3   | 输入框背景       │
│  --border: #E2E4E8        | 边框/分割线      │
│  --border-hover: #C4C8CF  | 悬停边框         │
│  --text-primary: #1A1C20  | 主文字（近黑）   │
│  --text-secondary: #6B7280| 次要文字         │
│  --text-muted: #9CA3AF    | 辅助信息文字     │
│  --accent: #2D2D2D        | 强调色（深灰/黑）│
│  --success: #16A34A       | 启用/成功状态     │
│  --success-bg: #F0FDF4    | 成功状态背景     │
│  --danger: #DC2626        | 断开/禁用/错误    │
│  --danger-bg: #FEF2F2     | 错误状态背景     │
│  --warning: #D97706       | 警告             │
│  --warning-bg: #FFFBEB    | 警告背景         │
│  --info: #6B7280          | 一般信息         │
│  --info-bg: #F3F4F6       | 信息背景         │
│  --shadow: rgba(0,0,0,0.04)| 卡片阴影       │
└─────────────────────────────────────────────┘
```

**字体系统：**
- UI 字体：`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif`
- 等宽字体：`"Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace`
- 字号层级：`11px` (caption) / `13px` (body) / `15px` (subtitle) / `18px` (title)

### 5.4 ProxyCard 组件详细设计

每个 ProxyCard 是一个独立的可折叠卡片：

**收起状态：**
```
┌──────────────────────────────────────────────────────────┐
│ ● System Proxy (Remote)    http://127.0.0.1:7890    [▼] │
└──────────────────────────────────────────────────────────┘
```

**展开状态：**
```
┌──────────────────────────────────────────────────────────┐
│ ● System Proxy (Remote)    http://127.0.0.1:7890    [▲] │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  配置文件                                                │
│  /etc/environment                                        │
│  /etc/profile.d/proxy-switch.sh                          │
│                                                          │
│  ▸ 如何手动配置                                    [展开]│
│  ┌────────────────────────────────────────────────────┐  │
│  │ # 编辑 /etc/environment，添加：                     │  │
│  │ http_proxy="http://127.0.0.1:7890"                 │  │
│  │ https_proxy="http://127.0.0.1:7890"                │  │
│  │                                                    │  │
│  │ # 或创建 /etc/profile.d/proxy-switch.sh：           │  │
│  │ export http_proxy="http://127.0.0.1:7890"          │  │
│  │ export https_proxy="http://127.0.0.1:7890"         │  │
│  │                                                    │  │
│  │ # 使配置生效：                                      │  │
│  │ source /etc/profile.d/proxy-switch.sh              │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  ┌─ 代理设置 ─────────────────────────────────────────┐  │
│  │                                                    │  │
│  │ HTTP Proxy                                          │  │
│  │ ┌──────────────────────────────────────────────────┐│  │
│  │ │ http://127.0.0.1:7890                            ││  │
│  │ └──────────────────────────────────────────────────┘│  │
│  │                                                    │  │
│  │ HTTPS Proxy                                         │  │
│  │ ┌──────────────────────────────────────────────────┐│  │
│  │ │ http://127.0.0.1:7890                            ││  │
│  │ └──────────────────────────────────────────────────┘│  │
│  │                                                    │  │
│  │ No Proxy (不代理的地址)                              │  │
│  │ ┌──────────────────────────────────────────────────┐│  │
│  │ │ localhost,127.0.0.1,::1                          ││  │
│  │ └──────────────────────────────────────────────────┘│  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  [Apply]   [Disable]   [↻ Refresh]                       │
│                                                          │
└──────────────────────────────────────────────────────────┘
```

**状态变体：**

| 状态 | 指示器 | 颜色 | 按钮 |
|---|---|---|---|
| 已连接 + 已启用 | ● ENABLED | 绿色 | Disable, Refresh |
| 已连接 + 未启用 | ○ disabled | 灰色 | Apply, Refresh |
| 已连接 + 未安装 | ⏭ NOT INSTALLED | 浅灰 | 全部禁用 |
| 未连接 | — (无连接) | 灰色 | 全部禁用 |

### 5.5 Sidebar 设计

```
┌──────────────────────┐
│                      │
│  Proxy-Switch        │
│                      │
│  ── Servers ──────── │
│                      │
│  ┌──────────────────┐│
│  │ ● my-ubuntu      ││  ← 已连接（绿点）
│  │   192.168.1.101  ││
│  │   root@22        ││
│  │         [断开]   ││
│  └──────────────────┘│
│                      │
│  ┌──────────────────┐│
│  │ ○ dev-server     ││  ← 未连接（灰点）
│  │   10.0.0.5       ││
│  │   admin@2222     ││
│  │         [连接]   ││
│  └──────────────────┘│
│                      │
│  [+ Add Server]      │
│                      │
│  ── Local ────────── │
│                      │
│  ┌──────────────────┐│
│  │ 🖥  This PC      ││  ← 始终可用
│  │   Windows 11     ││
│  │   ● Ready        ││
│  └──────────────────┘│
│                      │
└──────────────────────┘
```

### 5.6 对话框

**添加/编辑服务器对话框：**
```
┌──────────────────────────────────────┐
│  Add Server                     [×]  │
├──────────────────────────────────────┤
│                                      │
│  Name        [my-ubuntu__________]   │
│  Host        [192.168.1.101______]   │
│  Port        [22_________________]   │
│  User        [root_______________]   │
│                                      │
│  Auth Method  ○ SSH Key  ● Password  │
│                                      │
│  SSH Key     [______________] [选择] │
│  Password    [______________]        │
│                                      │
│  Description [Home server_______]    │
│                                      │
│  [Cancel]              [Save]        │
└──────────────────────────────────────┘
```

---

## 六、IPC 接口设计 (Tauri Commands)

### 6.1 服务器管理

```rust
// 获取所有服务器
#[tauri::command]
async fn get_servers() -> Vec<Server>;

// 添加服务器
#[tauri::command]
async fn add_server(server: Server) -> OpResult;

// 更新服务器
#[tauri::command]
async fn update_server(id: String, server: Server) -> OpResult;

// 删除服务器
#[tauri::command]
async fn delete_server(id: String) -> OpResult;
```

### 6.2 SSH 连接

```rust
// 连接到服务器（返回连接 ID）
#[tauri::command]
async fn ssh_connect(server_id: String) -> Result<String, String>;
// 成功返回 connection_id (UUID)

// 断开连接
#[tauri::command]
async fn ssh_disconnect(connection_id: String) -> OpResult;

// 获取连接状态
#[tauri::command]
async fn ssh_status(connection_id: String) -> SshState;
```

### 6.3 远程代理操作 (通过 SSH)

```rust
// 检测远程组件状态
#[tauri::command]
async fn remote_detect(connection_id: String, component: ComponentId) -> ProxyStatus;

// 设置远程代理
#[tauri::command]
async fn remote_enable(
    connection_id: String,
    component: ComponentId,
    config: ProxyConfig,
) -> OpResult;

// 禁用远程代理
#[tauri::command]
async fn remote_disable(
    connection_id: String,
    component: ComponentId,
) -> OpResult;
```

### 6.4 本地代理操作 (Windows)

```rust
// 检测本地组件状态
#[tauri::command]
async fn local_detect(component: ComponentId) -> ProxyStatus;

// 设置本地代理
#[tauri::command]
async fn local_enable(
    component: ComponentId,
    config: ProxyConfig,
) -> OpResult;

// 禁用本地代理
#[tauri::command]
async fn local_disable(component: ComponentId) -> OpResult;
```

---

## 七、Rust 后端实现细节

### 7.1 SSH 连接管理 (`src-tauri/src/ssh/`)

使用 `ssh2` crate（基于 libssh2），采用连接池模式：

```rust
// 连接池 — 全局 HashMap<String, SshConnection>
// key: connection_id (UUID)
// value: 活跃的 SSH 会话

use std::collections::HashMap;
use std::sync::Mutex;
use ssh2::Session;

pub struct ConnectionPool {
    connections: Mutex<HashMap<String, SshSession>>,
}

pub struct SshSession {
    pub session: Session,
    pub server_id: String,
    pub connected_at: std::time::Instant,
}
```

**连接流程：**
1. 前端调用 `ssh_connect(server_id)`
2. Rust 从配置加载 Server 信息
3. 根据 `auth_mode` 选择 key 或 password 认证
4. 建立 TCP → 创建 Session → 认证 → 返回 connection_id
5. 连接加入全局连接池

**保活机制：**
- 每 30 秒发送 keepalive
- 命令执行前检查连接状态，断线则自动重连

### 7.2 远程命令执行 (`src-tauri/src/ssh/executor.rs`)

```rust
impl SshSession {
    /// 执行远程命令
    pub fn run(&self, cmd: &str, sudo: bool, timeout_secs: u64) -> Result<CommandResult> {
        let mut channel = self.session.channel_session()?;
        let full_cmd = if sudo {
            format!("sudo bash -c '{}'", cmd.replace('\'', "'\\''"))
        } else {
            cmd.to_string()
        };
        channel.exec(&full_cmd)?;
        // 读取 stdout/stderr，等待退出码
        // ...
    }

    /// 读取远程文件
    pub fn read_file(&self, path: &str) -> Result<String> {
        self.run(&format!("cat '{}' 2>/dev/null || echo ''", path), false, 10)
    }

    /// 写入远程文件（通过 base64 + sudo tee，或 SFTP）
    pub fn write_file(&self, path: &str, content: &str, sudo: bool) -> Result<()> {
        if sudo {
            let encoded = base64_encode(content);
            self.run(&format!(
                "echo '{}' | base64 -d | sudo tee '{}' > /dev/null && sudo chmod 644 '{}'",
                encoded, path, path
            ), false, 10)?;
        } else {
            // 使用 SFTP
            let sftp = self.session.sftp()?;
            // 确保父目录存在
            // ...
            let mut file = sftp.create(path)?;
            file.write_all(content.as_bytes())?;
        }
        Ok(())
    }

    /// 检测工具是否安装
    pub fn tool_exists(&self, tool: &str) -> bool {
        let cmd = format!("command -v {} 2>/dev/null || which {} 2>/dev/null", tool, tool);
        self.run(&cmd, false, 5).map(|r| !r.stdout.trim().is_empty()).unwrap_or(false)
    }

    /// 检查是否有 sudo 权限
    pub fn has_sudo(&self) -> bool {
        self.run("sudo -n true 2>&1", false, 5)
            .map(|r| r.exit_code == 0)
            .unwrap_or(false)
    }
}
```

### 7.3 远程代理模块 (`src-tauri/src/proxy/remote/`)

每个模块实现统一的 trait：

```rust
pub trait ProxyModule {
    fn name(&self) -> &'static str;
    fn description(&self) -> &'static str;
    fn config_files(&self) -> &'static [&'static str];
    fn manual_setup_commands(&self) -> Vec<String>;

    /// 检测是否已安装
    fn detect(&self, session: &SshSession) -> Result<bool>;

    /// 获取当前状态
    fn status(&self, session: &SshSession) -> Result<ProxyStatus>;

    /// 启用代理
    fn enable(&self, session: &SshSession, config: &ProxyConfig) -> Result<OpResult>;

    /// 禁用代理
    fn disable(&self, session: &SshSession) -> Result<OpResult>;
}
```

**各模块实现要点：**

#### system_proxy
- 检测：始终可用（Linux 必有 /etc）
- 启用：修改 `/etc/environment`（只改 proxy 相关行，保留其余内容）+ 写入 `/etc/profile.d/proxy-switch.sh`
- 禁用：移除 `/etc/environment` 中的 proxy 行 + 删除 `/etc/profile.d/proxy-switch.sh`
- 需要 sudo：是
- 手动配置说明：列出两个文件路径和需要添加的环境变量

#### apt
- 检测：`command -v apt-get`
- 启用：写入 `/etc/apt/apt.conf.d/proxy.conf`（专用文件，覆盖写入）
- 禁用：删除 `/etc/apt/apt.conf.d/proxy.conf`
- 需要 sudo：是
- Mirror 支持：修改 `/etc/apt/sources.list` 中的 Ubuntu archive URL
- 手动配置说明：列出 proxy.conf 的 Acquire 指令格式

#### git (remote)
- 检测：`command -v git`
- 启用：`git config --global http.proxy ...`
- 禁用：`git config --global --unset http.proxy ...`
- 需要 sudo：否
- 手动配置说明：`git config --global http.proxy <url>` 命令

#### docker (remote)
- 检测：`command -v docker && systemctl show docker.service`
- 启用：写入 systemd drop-in `/etc/systemd/system/docker.service.d/proxy.conf` + `systemctl daemon-reload && systemctl restart docker`
- 禁用：删除 drop-in + 重启
- 需要 sudo：是
- Mirror 支持：修改 `/etc/docker/daemon.json` 中的 `registry-mirrors`
- 手动配置说明：列出 systemd drop-in 的 Environment 配置格式

#### npm (remote)
- 检测：`command -v npm`
- 启用：`npm config set proxy ...`
- 禁用：`npm config delete proxy ...`
- 需要 sudo：否
- Mirror 支持：`npm config set registry <url>`
- 手动配置说明：`npm config set proxy <url>` 或直接编辑 `~/.npmrc`

#### maven (remote)
- 检测：`command -v mvn`
- 启用：XML 解析 `~/.m2/settings.xml`，添加 `<proxy>` 元素（保留已有内容）
- 禁用：从 XML 中移除 proxy-switch 管理的 `<proxy>` 和 `<mirror>`
- 需要 sudo：否
- Mirror 支持：添加 `<mirror>` 元素
- 手动配置说明：列出 settings.xml 的 proxy 元素 XML 示例

### 7.4 本地代理模块 (`src-tauri/src/proxy/local/`)

#### git (local - Windows)
- 检测：`where git` → 检查 git.exe 是否存在
- 状态：`git config --global --get http.proxy` 等
- 启用：`git config --global http.proxy <url>`
- 禁用：`git config --global --unset http.proxy`
- 配置文件：`%USERPROFILE%\.gitconfig`
- 手动配置说明：提供 git config 命令 + `.gitconfig` 文件路径

#### docker (local - Windows)
- 检测：`where docker` → 检查 docker.exe
- 状态：读取 `%USERPROFILE%\.docker\daemon.json` 中的 `proxies` 字段
- 启用：修改 `daemon.json` 的 `proxies` 字段
- 禁用：移除 `daemon.json` 中的 `proxies` 字段
- 配置文件：`%USERPROFILE%\.docker\daemon.json`
- 手动配置说明：展示 Docker Desktop Settings → Resources → Proxies 的 GUI 操作路径 + 手动编辑 daemon.json 的 JSON 示例

```json
// daemon.json proxy 配置示例
{
  "proxies": {
    "default": {
      "httpProxy": "http://127.0.0.1:7890",
      "httpsProxy": "http://127.0.0.1:7890",
      "noProxy": "localhost,127.0.0.1"
    }
  }
}
```

#### npm (local - Windows)
- 检测：`where npm`
- 状态：`npm config get proxy`
- 启用：`npm config set proxy <url>`
- 禁用：`npm config delete proxy`
- 配置文件：`%USERPROFILE%\.npmrc`
- 手动配置说明：提供 npm config 命令

#### maven (local - Windows)
- 检测：`where mvn`
- 状态：解析 `%USERPROFILE%\.m2\settings.xml`
- 启用：XML 处理（同远程 Maven 逻辑）
- 禁用：XML 处理
- 配置文件：`%USERPROFILE%\.m2\settings.xml`
- 手动配置说明：提供 settings.xml 示例

### 7.5 配置持久化 (`src-tauri/src/config/`)

```rust
// 存储路径：%APPDATA%\proxy-switch\servers.toml
// 不存密码明文 — 使用 Windows Credential Manager (keyring crate)

pub struct ConfigStore {
    config_dir: PathBuf,
}

impl ConfigStore {
    pub fn new() -> Self {
        let dir = dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("proxy-switch");
        std::fs::create_dir_all(&dir).ok();
        Self { config_dir: dir }
    }

    pub fn load_servers(&self) -> Vec<Server> { /* ... */ }
    pub fn save_server(&self, server: &Server) -> Result<()> { /* ... */ }
    pub fn delete_server(&self, id: &str) -> Result<()> { /* ... */ }
}
```

---

## 八、实现计划

### Phase 1 — 项目脚手架 (2-3 天)
- [ ] 初始化 Tauri 2.x 项目
- [ ] 配置 Vite + React + TypeScript
- [ ] 搭建基本目录结构
- [ ] 配置 ESLint + Prettier
- [ ] 定义 Rust models.rs
- [ ] 定义 TypeScript types/index.ts
- [ ] 实现基础 UI 框架（Sidebar + MainContent + StatusBar 布局）
- [ ] 配置应用图标

### Phase 2 — SSH 与服务器管理 (2-3 天)
- [ ] Rust: 实现 ConfigStore（TOML 读写）
- [ ] Rust: 实现 Server CRUD commands
- [ ] Rust: 实现 ssh2 连接 + 连接池
- [ ] Rust: 实现远程命令执行（run / read_file / write_file / tool_exists / has_sudo）
- [ ] TS: 实现 ServerDialog 组件（添加/编辑服务器）
- [ ] TS: 实现 Sidebar 服务器列表
- [ ] TS: 实现 SSH 连接/断开交互
- [ ] 测试：连接真实 Ubuntu 服务器

### Phase 3 — 远程代理模块 (3-4 天)
- [ ] Rust: 实现 ProxyModule trait
- [ ] Rust: 实现 system_proxy 模块
- [ ] Rust: 实现 apt 模块
- [ ] Rust: 实现 git_remote 模块
- [ ] Rust: 实现 docker_remote 模块
- [ ] Rust: 实现 npm_remote 模块
- [ ] Rust: 实现 maven_remote 模块
- [ ] Rust: 实现 remote_* Tauri commands
- [ ] TS: 实现 ProxyCard 组件
- [ ] TS: 实现 StatusIndicator 组件
- [ ] TS: 实现 ManualGuide 可折叠组件
- [ ] TS: 实现远程代理卡片列表 + 交互
- [ ] 测试：逐个组件在真实 Ubuntu 上测试

### Phase 4 — 本地 Windows 代理模块 (2-3 天)
- [ ] Rust: 实现 git_local 模块（调用本地 git）
- [ ] Rust: 实现 docker_local 模块（读写 daemon.json）
- [ ] Rust: 实现 npm_local 模块（调用本地 npm）
- [ ] Rust: 实现 maven_local 模块（读写 settings.xml）
- [ ] Rust: 实现 local_* Tauri commands
- [ ] TS: 实现本地代理区域 UI
- [ ] 测试：在 Windows 上逐个组件测试

### Phase 5 — 打磨与打包 (2 天)
- [ ] 全局样式微调（间距、字体、动画）
- [ ] 错误处理完善（网络断线、权限不足、超时等）
- [ ] 密码安全存储（Windows Credential Manager）
- [ ] Tauri 打包配置（Windows MSI/NSIS installer）
- [ ] 测试打包后的 exe

---

## 九、关键设计决策

### 9.1 为什么每个组件独立操作而不是批量？

用户的原话：*"不用批量设置了，就单独设置每一个就行了"*。这样设计的好处：
- 灵活：只想改 Docker 代理不动别的，直接操作 Docker 卡片即可
- 信息清晰：每个卡片的当前状态一目了然
- 安全性：操作失败不会影响其他组件

### 9.2 为什么不用全局 Profile？

每个组件的代理地址可能不同（比如 npm 可能用淘宝镜像而非代理），统一 Profile 反而限制灵活性。用户想怎么配就怎么配。

### 9.3 为什么展示"手动配置说明"？

这来源于用户需求：*"展示如果自己去设置，去改什么文件什么的"*。把 GUI 操作和手动操作打通 — 用户通过 GUI 设置了，也同时学到了底层原理。

### 9.4 SSH 连接管理

- 同一时间只保持一个活跃的 SSH 连接（简化 UI 和状态管理）
- 连接是惰性的 — 用户点击服务器才连接
- 密码通过 Windows Credential Manager 存储，不落盘明文

### 9.5 sudo 处理

- 优先假设服务器已配置 passwordless sudo
- 如果 sudo 需要密码，提示用户配置 NOPASSWD 或在密码输入框提供 sudo 密码

---

## 十、每个组件的"手动配置说明"文案

### System Proxy (Remote)
```
编辑 /etc/environment，添加以下行：
  http_proxy="http://your-proxy:port"
  https_proxy="http://your-proxy:port"
  HTTP_PROXY="http://your-proxy:port"
  HTTPS_PROXY="http://your-proxy:port"
  no_proxy="localhost,127.0.0.1,::1"
  NO_PROXY="localhost,127.0.0.1,::1"

或创建 /etc/profile.d/proxy-switch.sh，添加：
  export http_proxy="http://your-proxy:port"
  export https_proxy="http://your-proxy:port"
  export no_proxy="localhost,127.0.0.1,::1"

生效方式：
  source /etc/profile.d/proxy-switch.sh
  # 或重新登录
```

### APT (Remote)
```
创建 /etc/apt/apt.conf.d/proxy.conf，写入：
  Acquire::http::Proxy "http://your-proxy:port";
  Acquire::https::Proxy "http://your-proxy:port";
  Acquire::ftp::Proxy "http://your-proxy:port";
```

### Git (Remote)
```
git config --global http.proxy http://your-proxy:port
git config --global https.proxy http://your-proxy:port

# 取消：
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### Docker (Remote)
```
创建 /etc/systemd/system/docker.service.d/proxy.conf：
  [Service]
  Environment="HTTP_PROXY=http://your-proxy:port"
  Environment="HTTPS_PROXY=http://your-proxy:port"
  Environment="NO_PROXY=localhost,127.0.0.1"

然后执行：
  sudo systemctl daemon-reload
  sudo systemctl restart docker
```

### npm (Remote)
```
npm config set proxy http://your-proxy:port
npm config set https-proxy http://your-proxy:port

# 取消：
npm config delete proxy
npm config delete https-proxy
```

### Maven (Remote)
```
编辑 ~/.m2/settings.xml，在 <proxies> 中添加：
  <proxy>
    <id>my-proxy</id>
    <active>true</active>
    <protocol>http</protocol>
    <host>your-proxy-host</host>
    <port>7890</port>
    <nonProxyHosts>localhost|127.0.0.1</nonProxyHosts>
  </proxy>
```

### Git (Local - Windows)
```
git config --global http.proxy http://your-proxy:port
git config --global https.proxy http://your-proxy:port

配置文件位置：
  %USERPROFILE%\.gitconfig

# 取消：
git config --global --unset http.proxy
git config --global --unset https.proxy
```

### Docker (Local - Windows)
```
编辑 %USERPROFILE%\.docker\daemon.json：
  {
    "proxies": {
      "default": {
        "httpProxy": "http://your-proxy:port",
        "httpsProxy": "http://your-proxy:port",
        "noProxy": "localhost,127.0.0.1"
      }
    }
  }

或在 Docker Desktop 中：
  Settings → Resources → Proxies → 填写代理地址 → Apply & Restart
```

### npm (Local - Windows)
```
npm config set proxy http://your-proxy:port
npm config set https-proxy http://your-proxy:port

配置文件位置：
  %USERPROFILE%\.npmrc

# 取消：
npm config delete proxy
npm config delete https-proxy
```

### Maven (Local - Windows)
```
编辑 %USERPROFILE%\.m2\settings.xml：
  <proxies>
    <proxy>
      <id>my-proxy</id>
      <active>true</active>
      <protocol>http</protocol>
      <host>your-proxy-host</host>
      <port>7890</port>
    </proxy>
  </proxies>
```

---

## 十一、样式系统

### CSS 变量定义 (`:root`)

```css
:root {
  /* Background */
  --bg-primary: #FFFFFF;
  --bg-secondary: #F8F9FA;
  --bg-tertiary: #F0F1F3;
  --bg-hover: #F3F4F6;

  /* Border */
  --border: #E2E4E8;
  --border-hover: #C4C8CF;
  --border-focus: #6B7280;

  /* Text */
  --text-primary: #1A1C20;
  --text-secondary: #6B7280;
  --text-muted: #9CA3AF;
  --text-inverse: #FFFFFF;

  /* Semantic */
  --success: #16A34A;
  --success-bg: #F0FDF4;
  --danger: #DC2626;
  --danger-bg: #FEF2F2;
  --warning: #D97706;
  --warning-bg: #FFFBEB;
  --info: #6B7280;
  --info-bg: #F3F4F6;

  /* Component */
  --accent: #2D2D2D;
  --accent-hover: #404040;
  --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 2px 8px rgba(0, 0, 0, 0.06);
  --radius-sm: 4px;
  --radius-md: 6px;
  --radius-lg: 8px;

  /* Font */
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-mono: "Cascadia Code", "Fira Code", "JetBrains Mono", "Consolas", monospace;
  --text-xs: 11px;
  --text-sm: 12px;
  --text-base: 13px;
  --text-lg: 15px;
  --text-xl: 18px;
  --text-2xl: 22px;
}
```

### 按钮样式

```css
.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 5px 14px;
  font-size: var(--text-base);
  font-family: var(--font-sans);
  border-radius: var(--radius-sm);
  border: 1px solid var(--border);
  background: var(--bg-primary);
  color: var(--text-primary);
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  user-select: none;
  gap: 4px;
}

.btn:hover {
  background: var(--bg-hover);
  border-color: var(--border-hover);
}

.btn:active {
  background: var(--bg-tertiary);
}

.btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.btn-accent {
  background: var(--accent);
  color: var(--text-inverse);
  border-color: var(--accent);
}

.btn-accent:hover {
  background: var(--accent-hover);
}

.btn-danger {
  color: var(--danger);
  border-color: var(--danger);
}

.btn-danger:hover {
  background: var(--danger-bg);
}
```

### 输入框样式

```css
.input {
  width: 100%;
  padding: 6px 10px;
  font-size: var(--text-base);
  font-family: var(--font-mono);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg-tertiary);
  color: var(--text-primary);
  outline: none;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.input:focus {
  border-color: var(--border-focus);
  box-shadow: 0 0 0 2px rgba(107, 114, 128, 0.1);
}

.input::placeholder {
  color: var(--text-muted);
}
```

---

## 十二、注意事项

1. **密码安全**：服务器密码存入 Windows Credential Manager，不写 TOML
2. **XML 处理**：Maven settings.xml 解析使用 `quick-xml`，保留已有的非代理元素
3. **原子性**：远程文件写入失败时，不残留半成品文件
4. **超时处理**：SSH 操作设置合理超时，网络断线给出明确提示
5. **并发安全**：Rust 侧连接池使用 `Mutex` 保护，前端同一时间只允许一个 SSH 操作
6. **错误信息**：所有错误都返回人类可读的中文/英文描述，不暴露底层调用栈
7. **幂等性**：Enable/Disable 操作支持重复调用，多次 Enable 不会重复添加配置
