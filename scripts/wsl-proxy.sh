#!/usr/bin/env bash
# =============================================================================
# wsl-proxy.sh — 让 WSL 使用 Windows 宿主机上的代理（FlClash / Clash 等）
#
# 背景：
#   WSL2 默认 NAT 模式，WSL 的默认网关就是 Windows 宿主在虚拟网卡上的地址，
#   而 Windows 上的代理通常只监听 127.0.0.1，所以 WSL 里必须用「网关 IP:端口」。
#   网关 IP 会在 WSL 重启后变化，因此这里每次开 shell 动态探测，而不是写死。
#
# 用法：
#   sudo ./scripts/wsl-proxy.sh install     安装（写入 /etc/profile.d + 接入 ~/.bashrc）
#   sudo ./scripts/wsl-proxy.sh uninstall   卸载
#   ./scripts/wsl-proxy.sh status           查看安装、开关、连通性
#   ./scripts/wsl-proxy.sh show             只打印将要安装的 profile 内容
#   ./scripts/wsl-proxy.sh on               开启（新终端生效）
#   ./scripts/wsl-proxy.sh off              暂停（新终端不再加载）
#
# 安装后在任何交互终端里可直接使用：
#   proxyon       开启代理（立即生效）
#   proxyoff      关闭代理（当前会话立即清除）
#   proxystatus   查看状态
#
# 端口默认 7890，可用环境变量覆盖：PROXY_PORT=7897 sudo -E ./scripts/wsl-proxy.sh install
# =============================================================================

set -euo pipefail

PROFILE_FILE="/etc/profile.d/proxy-switch.sh"
MARKER="# [wsl-proxy] 加载 WSL -> Windows 宿主机代理"
# 用于识别 /etc/profile.d/proxy-switch.sh 是否由本脚本生成
PROFILE_SIG="由 proxy-switch 仓库 scripts/wsl-proxy.sh 生成"

# 取「真正调用脚本的用户」家目录（兼容 sudo 场景）
INVOKING_USER="${SUDO_USER:-$(id -un)}"
INVOKING_HOME="$(getent passwd "$INVOKING_USER" | cut -d: -f6)"
BASHRC="${INVOKING_HOME}/.bashrc"
FLAG_FILE="${INVOKING_HOME}/.wsl-proxy-off"

PORT="${PROXY_PORT:-7890}"
GATEWAY="$(ip route show default 2>/dev/null | awk '/default/ { print $3; exit }')"

usage() {
    cat <<'EOF'
wsl-proxy.sh — 让 WSL 使用 Windows 宿主机代理

用法:
  sudo ./scripts/wsl-proxy.sh install     安装到 /etc/profile.d 并接入 ~/.bashrc
  sudo ./scripts/wsl-proxy.sh install --force
                                          覆盖同名但非本脚本生成的 profile 文件
  sudo ./scripts/wsl-proxy.sh uninstall   卸载并清理 ~/.bashrc 中的加载行
  ./scripts/wsl-proxy.sh status           查看安装状态、开关、网关与连通性
  ./scripts/wsl-proxy.sh show             只打印将要安装的 profile 内容
  ./scripts/wsl-proxy.sh on               开启（新终端生效；当前终端用 proxyon）
  ./scripts/wsl-proxy.sh off              暂停（新终端不再加载；当前终端用 proxyoff）

安装后可用命令:
  proxyon / proxyoff / proxystatus

前提:
  Windows 端代理客户端需开启「允许局域网连接 / Allow LAN」，
  并在 Windows 防火墙放行 WSL 虚拟网卡的代理端口。
EOF
}

profile_template() {
    cat <<'EOF'
# =============================================================================
# WSL -> Windows 宿主机代理（由 proxy-switch 仓库 scripts/wsl-proxy.sh 生成）
# 建议修改源脚本后重新执行 install，而不是直接改本文件。
#
#   proxyon       开启代理（清除暂停标记并立即生效）
#   proxyoff      关闭代理（当前会话立即清除，新终端不再加载）
#   proxystatus   查看状态
#
# 端口可用环境变量 PROXY_PORT 覆盖，默认 7890。
# =============================================================================

_proxy_port="${PROXY_PORT:-7890}"
_proxy_off_flag="$HOME/.wsl-proxy-off"

_proxy_gateway() {
    ip route show default 2>/dev/null | awk '/default/ { print $3; exit }'
}

_proxy_port_open() {
    timeout 1 bash -c "</dev/tcp/$1/$2" 2>/dev/null
}

_proxy_clear() {
    unset http_proxy https_proxy ftp_proxy all_proxy \
          HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY no_proxy
}

_proxy_apply() {
    _proxy_host=""
    _proxy_gw="$(_proxy_gateway)"

    # NAT 模式用默认网关；mirrored 模式回退到回环地址
    for _h in "$_proxy_gw" "127.0.0.1"; do
        [ -z "$_h" ] && continue
        if _proxy_port_open "$_h" "$_proxy_port"; then
            _proxy_host="$_h"
            break
        fi
    done

    if [ -z "$_proxy_host" ]; then
        _proxy_clear
        unset _proxy_host _proxy_gw _h
        return 1
    fi

    export http_proxy="http://${_proxy_host}:${_proxy_port}"
    export https_proxy="$http_proxy"
    export ftp_proxy="$http_proxy"
    export all_proxy="socks5://${_proxy_host}:${_proxy_port}"
    export no_proxy="localhost,127.0.0.1,::1,192.168.0.0/16,10.0.0.0/8,172.16.0.0/12,.local,.lan"
    export HTTP_PROXY="$http_proxy"
    export HTTPS_PROXY="$https_proxy"
    export ALL_PROXY="$all_proxy"
    export NO_PROXY="$no_proxy"

    unset _proxy_host _proxy_gw _h
    return 0
}

proxyon() {
    rm -f "$_proxy_off_flag"
    if _proxy_apply; then
        echo "代理已开启：$http_proxy"
    else
        echo "未检测到可用代理：请确认 FlClash 在运行、已开启 Allow LAN，" \
             "且 ${_proxy_port} 端口可从 WSL 访问" >&2
        return 1
    fi
}

proxyoff() {
    : > "$_proxy_off_flag"
    _proxy_clear
    echo "代理已关闭：本次会话已清除，新终端不再加载"
}

proxystatus() {
    _proxy_gw="$(_proxy_gateway)"
    if [ -f "$_proxy_off_flag" ]; then
        echo "开关    : 已暂停"
    else
        echo "开关    : 已启用"
    fi
    echo "端口    : $_proxy_port"
    echo "宿主网关: ${_proxy_gw:-未检测到}"
    if [ -n "$_proxy_gw" ] && _proxy_port_open "$_proxy_gw" "$_proxy_port"; then
        echo "连通性  : 可达 (${_proxy_gw}:${_proxy_port})"
    else
        echo "连通性  : 不可达"
    fi
    echo "当前代理: ${http_proxy:-<未设置>}"
    unset _proxy_gw
}

# 初始化：存在暂停标记则不加载
if [ -f "$_proxy_off_flag" ]; then
    _proxy_clear
else
    _proxy_apply >/dev/null 2>&1 || true
fi
EOF
}

require_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo "需要 root 权限，请这样执行：sudo $0 $1" >&2
        exit 1
    fi
}

ensure_bashrc() {
    [ -f "$BASHRC" ] || : > "$BASHRC"
    if grep -qF "$MARKER" "$BASHRC"; then
        echo "~/.bashrc 已包含加载行，跳过"
        return 0
    fi
    cp -a "$BASHRC" "${BASHRC}.bak.$(date +%Y%m%d%H%M%S)"
    {
        echo ""
        echo "$MARKER"
        echo "[ -f $PROFILE_FILE ] && . $PROFILE_FILE"
    } >> "$BASHRC"
    echo "已向 $BASHRC 追加加载行"
}

cmd_install() {
    require_root install
    local force="${2:-}"

    if [ -f "$PROFILE_FILE" ]; then
        if ! grep -qF "$PROFILE_SIG" "$PROFILE_FILE" && [ "$force" != "--force" ]; then
            echo "检测到已有的 $PROFILE_FILE，但它不是本脚本生成的。" >&2
            echo "为避免覆盖你自己的配置，已中止。" >&2
            echo "请先备份并移走该文件，或执行：sudo $0 install --force" >&2
            exit 1
        fi
        cp -a "$PROFILE_FILE" "${PROFILE_FILE}.bak.$(date +%Y%m%d%H%M%S)"
        echo "已备份旧配置到 ${PROFILE_FILE}.bak.*"
    fi

    profile_template > "$PROFILE_FILE"
    chmod 644 "$PROFILE_FILE"
    ensure_bashrc
    echo ""
    echo "安装完成：$PROFILE_FILE"
    echo "当前终端执行：. $PROFILE_FILE   （或新开终端自动生效）"
    echo "之后可用：proxyon / proxyoff / proxystatus"
}

cmd_uninstall() {
    require_root uninstall

    if [ -f "$PROFILE_FILE" ]; then
        if grep -qF "$PROFILE_SIG" "$PROFILE_FILE"; then
            rm -f "$PROFILE_FILE"
        else
            echo "跳过删除：$PROFILE_FILE 不是本脚本生成的，保持原样" >&2
        fi
    fi

    if [ -f "$BASHRC" ] && grep -qF "$MARKER" "$BASHRC"; then
        cp -a "$BASHRC" "${BASHRC}.bak.$(date +%Y%m%d%H%M%S)"
        tmp="$(mktemp)"
        # 只删除本脚本写入的两行（精确整行匹配），其余内容原样保留
        grep -vF -e "$MARKER" -e "[ -f $PROFILE_FILE ] && . $PROFILE_FILE" "$BASHRC" > "$tmp" || true
        # 用 cat 写回而不是 mv，保持原文件的属主与权限
        cat "$tmp" > "$BASHRC"
        rm -f "$tmp"
        echo "已清理 $BASHRC 中的加载行"
    fi
    rm -f "$FLAG_FILE"
    echo "已卸载。当前终端里若还有代理变量，可执行："
    echo "  unset http_proxy https_proxy ftp_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY no_proxy"
}

cmd_status() {
    echo "配置文件: $PROFILE_FILE ($([ -f "$PROFILE_FILE" ] && echo 已安装 || echo 未安装))"
    echo "开关文件: $FLAG_FILE ($([ -f "$FLAG_FILE" ] && echo 已暂停 || echo 未暂停))"
    echo "代理端口: $PORT"
    echo "宿主网关: ${GATEWAY:-未检测到}"
    if [ -n "$GATEWAY" ] && port_open "$GATEWAY" "$PORT"; then
        echo "连通性  : 可达 (${GATEWAY}:${PORT})"
    else
        echo "连通性  : 不可达（检查 FlClash Allow LAN 与 Windows 防火墙）"
    fi
    echo "当前环境: ${http_proxy:-<未设置>}"
    echo ""
    echo "提示: 已安装后，交互终端里可用 proxyon / proxyoff / proxystatus"
}

port_open() {
    timeout 1 bash -c "</dev/tcp/$1/$2" 2>/dev/null
}

cmd_on() {
    [ -f "$PROFILE_FILE" ] || { echo "尚未安装，请先执行：sudo $0 install" >&2; exit 1; }
    rm -f "$FLAG_FILE"
    echo "已开启（新终端生效）。当前终端请执行：proxyon"
}

cmd_off() {
    : > "$FLAG_FILE"
    echo "已暂停（新终端不再加载）。当前终端请执行：proxyoff"
}

case "${1:-status}" in
    install)   cmd_install "$@" ;;
    uninstall) cmd_uninstall ;;
    status)    cmd_status ;;
    show)      profile_template ;;
    on|enable) cmd_on ;;
    off|disable) cmd_off ;;
    help|-h|--help) usage ;;
    *)
        usage
        exit 2
        ;;
esac
