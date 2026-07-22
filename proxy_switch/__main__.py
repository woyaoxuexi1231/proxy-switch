"""CLI entry point for local debugging and direct Ubuntu usage.

Usage:
    python -m proxy_switch status
    python -m proxy_switch on <profile_name>
    python -m proxy_switch off
    python -m proxy_switch list
    python -m proxy_switch init
"""

import argparse
import sys
from typing import Dict, Optional

from . import __version__
from .core.app_config import load_config, load_servers
from .backends import get_all_backends


def cmd_list(args):
    """List available profiles and servers."""
    profiles = load_config()
    servers = load_servers()

    print("=== Profiles ===")
    for name, profile in profiles.items():
        config = profile.config
        status = "ENABLED" if config.is_enabled else "DISABLED"
        proxy = config.primary_proxy
        desc = f" - {profile.description}" if profile.description else ""
        print(f"  {name:15s}  [{status:8s}]  {proxy}{desc}")

    print("\n=== Servers ===")
    if not servers:
        print("  (no servers configured)")
    for name, server in servers.items():
        print(f"  {name:15s}  {server.user}@{server.host}:{server.port}")


def cmd_init(args):
    """Interactive setup wizard."""
    print("proxy-switch init - Interactive Setup")
    print("=" * 40)
    print("\nThis will create the initial configuration.")
    print("Config directory: ~/.proxy-switch/\n")

    from .core import app_config
    config_dir = app_config.get_config_dir()
    config_path = app_config.get_config_path()

    if config_path.exists():
        resp = input("Config already exists. Overwrite? [y/N] ").strip().lower()
        if resp != "y":
            print("Cancelled.")
            return

    print("\n--- Default Proxy Settings ---")
    http = input("HTTP Proxy URL [http://127.0.0.1:7890]: ").strip()
    https = input("HTTPS Proxy URL [http://127.0.0.1:7890]: ").strip()
    socks = input("SOCKS5 Proxy URL [socks5://127.0.0.1:7891]: ").strip()
    no_proxy = input("No Proxy (comma-separated) [localhost,127.0.0.1,::1]: ").strip()

    data = {
        "defaults": {
            "http_proxy": http or "http://127.0.0.1:7890",
            "https_proxy": https or "http://127.0.0.1:7890",
            "socks_proxy": socks or "socks5://127.0.0.1:7891",
            "no_proxy": no_proxy or "localhost,127.0.0.1,::1",
        },
        "profile:direct": {
            "description": "Direct connection (no proxy)",
        },
    }

    app_config._write_toml(config_path, data)
    print(f"\nConfig written to: {config_path}")

    add_server = input("\nAdd a server now? [y/N] ").strip().lower()
    if add_server == "y":
        name = input("Server name: ").strip()
        host = input("Host: ").strip()
        port_str = input("SSH port [22]: ").strip()
        user = input("User [root]: ").strip()
        auth_mode = input("Auth mode (key/password) [key]: ").strip() or "key"
        ssh_key = ""
        if auth_mode == "key":
            ssh_key = input("SSH key path [~/.ssh/id_rsa]: ").strip() or "~/.ssh/id_rsa"
        password = ""
        if auth_mode == "password":
            import getpass
            password = getpass.getpass("Password: ")

        server_data = {
            "host": host,
            "port": int(port_str) if port_str else 22,
            "user": user or "root",
            "auth_mode": auth_mode,
            "ssh_key": ssh_key,
            "password": password,
            "description": name,
        }
        servers_path = app_config.get_servers_path()
        app_config._write_toml(servers_path, {f"server:{name}": server_data})
        print(f"Server '{name}' added.")

    print("\nDone! Use 'python -m proxy_switch list' to see your config.")
    print("Use 'python -m proxy_switch on <profile>' to apply proxy.")


def cmd_on(args):
    """Enable proxy using a named profile."""
    profiles = load_config()
    profile_name = args.profile or "default"

    # Fallback: use first non-direct profile if "default" not found
    if profile_name == "default" and "default" not in profiles:
        available = [n for n in profiles if n != "direct"]
        if available:
            profile_name = available[0]
        else:
            print("Error: No profiles found. Run 'proxy-switch init' first.")
            sys.exit(1)

    if profile_name not in profiles:
        print(f"Error: Profile '{profile_name}' not found.")
        print(f"Available profiles: {', '.join(profiles.keys())}")
        sys.exit(1)

    profile = profiles[profile_name]
    config = profile.config
    proxy_dict = config.to_dict()

    if not config.is_enabled:
        print(f"Profile '{profile_name}' has no proxy configured. Use 'proxy-switch off' instead.")
        sys.exit(1)

    backends = get_all_backends()
    if args.only:
        filter_list = [b.strip() for b in args.only.split(",")]
        backends = {n: b for n, b in backends.items() if n in filter_list}

    print(f"Applying profile '{profile_name}'...")
    print(f"  Proxy: {config.primary_proxy}")
    if config.no_proxy:
        print(f"  No-Proxy: {config.no_proxy}")
    print()

    success_count = 0
    fail_count = 0
    skip_count = 0

    for bname, bcls in backends.items():
        try:
            backend = bcls()
            if not backend.can_apply():
                print(f"  ⏭  {bname:15s}  skipped (not installed)")
                skip_count += 1
                continue

            result = backend.enable(proxy_dict)
            if result.get("success"):
                print(f"  ✓  {bname:15s}  enabled")
                success_count += 1
            else:
                print(f"  ✗  {bname:15s}  failed: {result.get('message', '')}")
                fail_count += 1
        except Exception as e:
            print(f"  ✗  {bname:15s}  error: {e}")
            fail_count += 1

    print(f"\nDone: {success_count} enabled, {fail_count} failed, {skip_count} skipped.")


def cmd_off(args):
    """Disable all proxies."""
    backends = get_all_backends()
    if args.only:
        filter_list = [b.strip() for b in args.only.split(",")]
        backends = {n: b for n, b in backends.items() if n in filter_list}

    print("Disabling proxy for all tools...")

    success_count = 0
    fail_count = 0
    skip_count = 0

    for bname, bcls in backends.items():
        try:
            backend = bcls()
            if not backend.can_apply():
                print(f"  ⏭  {bname:15s}  skipped (not installed)")
                skip_count += 1
                continue

            result = backend.disable()
            if result.get("success"):
                print(f"  ✓  {bname:15s}  disabled")
                success_count += 1
            else:
                print(f"  ✗  {bname:15s}  failed: {result.get('message', '')}")
                fail_count += 1
        except Exception as e:
            print(f"  ✗  {bname:15s}  error: {e}")
            fail_count += 1

    print(f"\nDone: {success_count} disabled, {fail_count} failed, {skip_count} skipped.")


def cmd_status(args):
    """Show proxy status for all tools."""
    backends = get_all_backends()

    print("Proxy Status")
    print("=" * 60)
    print()

    if args.profile:
        profiles = load_config()
        if args.profile in profiles:
            config = profiles[args.profile].config
            print(f"Profile: {args.profile}")
            print(f"  HTTP Proxy:    {config.http_proxy or '(not set)'}")
            print(f"  HTTPS Proxy:   {config.https_proxy or '(not set)'}")
            print(f"  SOCKS5 Proxy:  {config.socks_proxy or '(not set)'}")
            print(f"  No Proxy:      {config.no_proxy or '(not set)'}")
            print()
        else:
            print(f"Profile '{args.profile}' not found.\n")

    print(f"{'Tool':15s}  {'Status':10s}  {'Proxy'}")
    print("-" * 60)
    for bname, bcls in backends.items():
        try:
            backend = bcls()
            if not backend.can_apply():
                print(f"{bname:15s}  {'NOT INSTALLED':10s}")
                continue
            s = backend.status()
            status_text = "ENABLED" if s.get("enabled") else "DISABLED"
            proxy_url = s.get("proxy") or ""
            print(f"{bname:15s}  {status_text:10s}  {proxy_url}")
        except Exception as e:
            print(f"{bname:15s}  {'ERROR':10s}  {e}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proxy-switch",
        description="One-click proxy configuration for Ubuntu servers.",
    )
    parser.add_argument("--version", action="version", version=f"proxy-switch {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # list
    subparsers.add_parser("list", help="List available profiles and servers")

    # init
    subparsers.add_parser("init", help="Interactive setup wizard")

    # on
    on_parser = subparsers.add_parser("on", help="Enable proxy using a profile")
    on_parser.add_argument("profile", nargs="?", default="default", help="Profile name")
    on_parser.add_argument("--only", help="Comma-separated list of tools to configure")

    # off
    off_parser = subparsers.add_parser("off", help="Disable all proxies")
    off_parser.add_argument("--only", help="Comma-separated list of tools to disable")

    # status
    status_parser = subparsers.add_parser("status", help="Show proxy status")
    status_parser.add_argument("--profile", help="Show profile details")
    status_parser.add_argument("--json", action="store_true", help="JSON output")

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)

    commands = {
        "list": cmd_list,
        "init": cmd_init,
        "on": cmd_on,
        "off": cmd_off,
        "status": cmd_status,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
