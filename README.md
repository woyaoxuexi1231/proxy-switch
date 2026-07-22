# Proxy-Switch

**一键配置 Ubuntu 服务器代理的 Windows 桌面工具**

通过 SSH 连接到 Ubuntu 服务器，一次操作配置所有代理（系统环境、APT、Git、Docker、npm、Maven）。

## 截图

```
┌─────────────────────────────────────────────┐
│  Proxy-Switch  v0.2         — □ × │
├─────────────────────────────────────────────┤
│  [▼ 选择服务器]  my-ubuntu (192.168.1.101)  │
│  [▼ 选择 Profile]  home                      │
│                                              │
│  ☑ System Proxy  ☑ APT  ☑ Git  ☑ Docker    │
│  ☑ npm  ☑ Maven                              │
│                                              │
│  [⚡ Apply Proxy]  [✕ Disable]  [⟳ Refresh]  │
│                                              │
│  ┌─ Status / Log ─────────────────────────┐  │
│  │ ✓ system_proxy  ENABLED  http://...     │  │
│  │ ✓ apt           ENABLED                 │  │
│  │ ✗ docker        NOT INSTALLED           │  │
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
| System Proxy | `/etc/environment`, `/etc/profile.d/` | ✅ | HTTP_PROXY / HTTPS_PROXY（覆盖 curl, wget, pip 等） |
| APT | `/etc/apt/apt.conf.d/proxy.conf` | ✅ | apt update/install |
| Git | `~/.gitconfig` | ❌ | git config --global |
| Docker | `/etc/systemd/.../proxy.conf` | ✅ | 自动 reload + restart |
| npm | `~/.npmrc` | ❌ | npm config set |
| Maven | `~/.m2/settings.xml` | ❌ | 自动合并已有配置 |

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

# 直接使用 PyInstaller（Windows / Linux / macOS 通用）
pyinstaller build.spec

# 输出: dist/proxy-switch.exe (~25MB)
```

> Windows 用户请直接执行 `pyinstaller build.spec`，`make build` 仅适用于已安装 Make 的环境。

## 项目结构

```
proxy-switch/
├── app.py                        # GUI 入口
├── build.spec                    # PyInstaller 打包配置
├── proxy_switch/
│   ├── __main__.py               # CLI 入口
│   ├── core/
│   │   ├── models.py             # 数据模型（ProxyConfig, Profile, Server, Result）
│   │   └── config.py             # TOML 配置读写
│   ├── features/                 # 功能模块（每个工具一个模块）
│   │   ├── system_proxy.py       # 系统环境代理
│   │   ├── apt.py                # APT 代理
│   │   ├── docker.py             # Docker 代理
│   │   ├── git.py                # Git 代理
│   │   ├── npm.py                # npm 代理
│   │   └── maven.py              # Maven 代理
│   ├── ssh/
│   │   └── connection.py         # SSH 连接 + 远程执行
│   └── gui/
│       ├── theme.py              # 主题与字体
│       ├── window.py             # 主窗口
│       └── dialogs.py            # 添加/编辑对话框
├── tests/
│   ├── test_features.py          # 功能模块测试
│   └── test_models.py            # 数据模型测试
├── requirements.txt
└── Makefile
```

## License

MIT
