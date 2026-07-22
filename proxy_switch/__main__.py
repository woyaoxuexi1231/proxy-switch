"""CLI entry point for proxy-switch.

Usage:
    python -m proxy_switch status
    python -m proxy_switch on <profile>
    python -m proxy_switch off
    python -m proxy_switch list
    python -m proxy_switch init
"""

from __future__ import annotations

import argparse
import sys
from typing import Dict, List, Optional

from . import __version__
from .core import config as cfg
from .features import discover, get_all, list_names


# ── Command: list ──────────────────────────────────────────────────────────


def cmd_list(args: argparse.Namespace) -> None:
    """List available profiles and servers."""
    profiles = cfg.load_profiles()
    servers = cfg.load_servers()

    print("=== Profiles ===")
    for name, profile in profiles.items():
        config = profile.config
        status = "ENABLED" if config.is_enabled else "DISABLED"
        proxy = config.primary_proxy
        desc = f" — {profile.description}" if profile.description else ""
        print(f"  {name:15s}  [{status:8s}]  {proxy}{desc}")

    print("\n=== Servers ===")
    if not servers:
        print("  (no servers configured)")
    for name, server in servers.items():
        print(f"  {name:15s}  {server.user}@{server.host}:{server.port}")


# ── Command: init ──────────────────────────────────────────────────────────


def cmd_init(args: argparse.Namespace) -> None:
    """Interactive setup wizard."""
    print("proxy-switch init — Interactive Setup")
    print("=" * 40)

    config_path = cfg.config_path()
    if config_path.exists():
        resp = input("\nConfig already exists. Overwrite? [y/N] ").strip().lower()
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

    cfg._write_toml(config_path, data)
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
        }
        cfg._write_toml(cfg.servers_path(), {f"server:{name}": server_data})
        print(f"Server '{name}' added.")

    print("\nDone! Use 'python -m proxy_switch list' to see your config.")
    print("Use 'python -m proxy_switch on <profile>' to apply proxy.")


# ── Command: on ────────────────────────────────────────────────────────────


def cmd_on(args: argparse.Namespace) -> None:
    """Enable proxy using a named profile on the local system."""
    profiles = cfg.load_profiles()
    profile_name = args.profile or "default"

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

    features = get_all()
    if args.only:
        only_list = [b.strip() for b in args.only.split(",")]
        features = {n: m for n, m in features.items() if n in only_list}

    print(f"Applying profile '{profile_name}'...")
    print(f"  Proxy: {config.primary_proxy}")
    if config.no_proxy:
        print(f"  No-Proxy: {config.no_proxy}")
    print()

    success = fail = skip = 0
    for fname, mod in sorted(features.items()):
        try:
            if not mod.detect():
                print(f"  ⏭  {fname:15s}  skipped (not installed)")
                skip += 1
                continue

            result = mod.enable(proxy_dict)
            if result.success:
                print(f"  ✓  {fname:15s}  enabled")
                success += 1
            else:
                print(f"  ✗  {fname:15s}  failed: {result.message}")
                fail += 1
        except Exception as e:
            print(f"  ✗  {fname:15s}  error: {e}")
            fail += 1

    print(f"\nDone: {success} enabled, {fail} failed, {skip} skipped.")


# ── Command: off ───────────────────────────────────────────────────────────


def cmd_off(args: argparse.Namespace) -> None:
    """Disable all proxies on the local system."""
    features = get_all()
    if args.only:
        only_list = [b.strip() for b in args.only.split(",")]
        features = {n: m for n, m in features.items() if n in only_list}

    print("Disabling proxy for all tools...")

    success = fail = skip = 0
    for fname, mod in sorted(features.items()):
        try:
            if not mod.detect():
                print(f"  ⏭  {fname:15s}  skipped (not installed)")
                skip += 1
                continue

            result = mod.disable()
            if result.success:
                print(f"  ✓  {fname:15s}  disabled")
                success += 1
            else:
                print(f"  ✗  {fname:15s}  failed: {result.message}")
                fail += 1
        except Exception as e:
            print(f"  ✗  {fname:15s}  error: {e}")
            fail += 1

    print(f"\nDone: {success} disabled, {fail} failed, {skip} skipped.")


# ── Command: status ────────────────────────────────────────────────────────


def cmd_status(args: argparse.Namespace) -> None:
    """Show proxy status for all tools on the local system."""
    features = get_all()

    print("Proxy Status")
    print("=" * 60)
    print()

    if args.profile:
        profiles = cfg.load_profiles()
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

    print(f"{'Feature':15s}  {'Status':12s}  Proxy")
    print("-" * 60)
    for fname, mod in sorted(features.items()):
        try:
            if not mod.detect():
                print(f"{fname:15s}  {'NOT INSTALLED':12s}")
                continue
            s = mod.status()
            status_text = "ENABLED" if s.enabled else "disabled"
            proxy_url = s.proxy or ""
            print(f"{fname:15s}  {status_text:12s}  {proxy_url}")
        except Exception as e:
            print(f"{fname:15s}  {'ERROR':12s}  {e}")


# ── Parser ─────────────────────────────────────────────────────────────────


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="proxy-switch",
        description="One-click proxy configuration for Ubuntu servers.",
    )
    parser.add_argument("--version", action="version", version=f"proxy-switch {__version__}")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    subparsers.add_parser("list", help="List available profiles and servers")
    subparsers.add_parser("init", help="Interactive setup wizard")

    on_parser = subparsers.add_parser("on", help="Enable proxy using a profile")
    on_parser.add_argument("profile", nargs="?", default="default", help="Profile name")
    on_parser.add_argument("--only", help="Comma-separated list of features to configure")

    off_parser = subparsers.add_parser("off", help="Disable all proxies")
    off_parser.add_argument("--only", help="Comma-separated list of features to disable")

    status_parser = subparsers.add_parser("status", help="Show proxy status")
    status_parser.add_argument("--profile", help="Show profile details")
    status_parser.add_argument("--json", action="store_true", help="JSON output (NYI)")

    return parser


# ── Main ───────────────────────────────────────────────────────────────────


def main(argv: Optional[List[str]] = None) -> None:
    """CLI entry point."""
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
