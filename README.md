# Proxy-Switch

**一键配置 Ubuntu 服务器代理的 Windows 桌面工具**

通过 SSH 连接到 Ubuntu 服务器，一次操作配置所有工具的代理（系统环境、APT、Git、Docker、Maven、npm、pip、curl、wget、Gradle、Snap）。

## 截图

```
┌─────────────────────────────────────────────┐
│  Proxy-Switch  v0.1         — □ × │
├─────────────────────────────────────────────┤
│  [▼ 选择服务器]  my-ubuntu (192.168.1.101)  │
│  [▼ 选择 Profile]  home                      │
│                                              │
│  ☑ 系统环境 ☑ APT ☑ Git ☑ Docker ☑ Maven   │
│  ☑ Gradle   ☑ npm ☑ pip ☑ curl ☑ wget ☑ Snap│
│                                              │
│  [⚡ Apply Proxy]  [✕ Disable]  [⟳ Refresh]  │
│                                              │
│  ┌─ Status / Log ─────────────────────────┐  │
│  │ ✓ 系统环境: ENABLED  http://...         │  │
│  │ ✓ APT:      ENABLED                     │  │
│  │ ✗ Docker:   NOT INSTALLED              │  │
│  └────────────────────────────────────────┘  │
├─────────────────────────────────────────────┤
│  Connected: my-ubuntu | Profile: home        │
└─────────────────────────────────────────────┘
```

## 快速开始

### 前提条件

- Windows 7+
- 能通过 SSH 访问的 Ubuntu 服务器（16.04+）

### 方法 1：下载打包好的 EXE（推荐）

从 [Releases](https://github.com/user/proxy-switch/releases) 下载 `proxy-switch.exe`，双击运行。

### 方法 2：源码运行

```bash
# 1. 克隆仓库
git clone https://github.com/user/proxy-switch.git
cd proxy-switch

# 2. 安装依赖
pip install -r requirements.txt

# 3. 运行
python app.py
```

### 首次使用

1. **添加服务器**：点击 `File → Add Server`，填写服务器信息
2. **添加 Profile**：点击 `File → Add Profile`，配置代理地址
3. **连接**：选择服务器，点击 `Connect`
4. **应用**：选择 Profile，勾选要配置的工具，点击 `Apply Proxy` ✅

## 支持的 Profile

在 `~/.proxy-switch/config.toml` 中管理：

```toml
[defaults]
http_proxy = "http://127.0.0.1:7890"
https_proxy = "http://127.0.0.1:7890"
socks_proxy = "socks5://127.0.0.1:7891"
no_proxy = "localhost,127.0.0.1,::1,10.0.0.0/8"

[profile.home]
http_proxy = "http://192.168.1.100:7890"

[profile.company]
http_proxy = "http://proxy.company.com:8080"
auth.username = "jdoe"

[profile.direct]
# 直连（关闭代理）
```

## 支持的组件

| 组件 | 配置文件 | 需要 sudo | 说明 |
|---|---|---|---|
| 系统环境 | `/etc/environment`, `/etc/profile.d/` | ✅ | HTTP_PROXY / HTTPS_PROXY |
| APT | `/etc/apt/apt.conf.d/proxy.conf` | ✅ | apt update/install |
| Git | `~/.gitconfig` | ❌ | git config --global |
| Docker | `/etc/systemd/.../proxy.conf` | ✅ | 自动 reload + restart |
| Maven | `~/.m2/settings.xml` | ❌ | 自动合并已有配置 |
| Gradle | `~/.gradle/gradle.properties` | ❌ | |
| npm | `~/.npmrc` | ❌ | npm config set |
| pip | `~/.config/pip/pip.conf` | ❌ | |
| curl | `~/.curlrc` | ❌ | |
| wget | `~/.wgetrc` | ❌ | |
| Snap | snap set system proxy | ✅ | |

## CLI 模式

工具也可以在 Ubuntu 上直接通过 CLI 使用：

```bash
# 初始化配置
python -m proxy_switch init

# 查看状态
python -m proxy_switch status

# 启用代理
python -m proxy_switch on home

# 仅配置个别组件
python -m proxy_switch on home --only apt,git

# 关闭代理
python -m proxy_switch off

# 查看配置
python -m proxy_switch list
```

## 打包成 EXE

```bash
pip install pyinstaller
make build
# 输出: dist/proxy-switch.exe (~25MB)
```

## 项目结构

```
proxy-switch/
├── app.py                    # GUI 入口
├── proxy_switch/
│   ├── core/                 # 配置和模型
│   ├── backends/             # 11 个代理后端
│   ├── ssh/                  # SSH 连接管理
│   └── gui/                  # CustomTkinter 界面
├── requirements.txt
├── build.spec                # PyInstaller 配置
└── Makefile
```

## License

MIT
