"""Configuration file management.

Handles reading/writing TOML config files for profiles and servers.
Config files are stored in ~/.proxy-switch/ on the Windows host.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

from .models import Profile, ProxyConfig, ProxyAuth, Server

# Try to import tomllib (Python 3.11+) or tomli
try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None  # type: ignore

try:
    import tomli_w
except ImportError:
    tomli_w = None  # type: ignore


def get_config_dir() -> Path:
    """Return the config directory path, creating it if needed."""
    config_dir = Path.home() / ".proxy-switch"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_config_path() -> Path:
    return get_config_dir() / "config.toml"


def get_servers_path() -> Path:
    return get_config_dir() / "servers.toml"


# ── Config ──────────────────────────────────────────────────────────────


def load_config() -> Dict[str, Profile]:
    """Load all profiles from config.toml.

    Returns:
        Dict of {profile_name: Profile}, including a synthetic 'direct' profile.
    """
    config_path = get_config_path()
    data = _read_toml(config_path) or {}

    defaults = _parse_proxy_config(data.get("defaults", {}))

    profiles: Dict[str, Profile] = {}
    for key, value in data.items():
        if key.startswith("profile:"):
            name = key[len("profile:"):]
            profile_config = _parse_proxy_config(value, defaults)
            desc = value.get("description", "")
            profiles[name] = Profile(name=name, config=profile_config, description=desc)

    # Always include a "direct" profile
    if "direct" not in profiles:
        profiles["direct"] = Profile(
            name="direct",
            config=ProxyConfig(),
            description="Direct connection (no proxy)",
        )

    return profiles


def save_profile(profile: Profile, defaults: Optional[ProxyConfig] = None) -> None:
    """Save or update a profile."""
    config_path = get_config_path()
    data = _read_toml(config_path) or {}

    section_key = f"profile:{profile.name}"
    section = data.get(section_key, {})

    config = profile.config
    if config.http_proxy:
        section["http_proxy"] = config.http_proxy
    if config.https_proxy:
        section["https_proxy"] = config.https_proxy
    if config.socks_proxy:
        section["socks_proxy"] = config.socks_proxy
    if config.ftp_proxy:
        section["ftp_proxy"] = config.ftp_proxy
    if config.no_proxy:
        section["no_proxy"] = config.no_proxy
    if config.auth.username:
        section.setdefault("auth", {})["username"] = config.auth.username
    if config.auth.password:
        section.setdefault("auth", {})["password"] = config.auth.password
    if profile.description:
        section["description"] = profile.description

    data[section_key] = section
    _write_toml(config_path, data)


def delete_profile(name: str) -> bool:
    """Delete a profile by name. Returns True if deleted."""
    config_path = get_config_path()
    data = _read_toml(config_path) or {}
    section_key = f"profile:{name}"
    if section_key in data:
        del data[section_key]
        _write_toml(config_path, data)
        return True
    return False


# ── Servers ─────────────────────────────────────────────────────────────


def load_servers() -> Dict[str, Server]:
    """Load all servers from servers.toml."""
    servers_path = get_servers_path()
    data = _read_toml(servers_path) or {}

    servers: Dict[str, Server] = {}
    for key, value in data.items():
        if key.startswith("server:"):
            name = key[len("server:"):]
            servers[name] = Server(
                name=name,
                host=value.get("host", ""),
                port=value.get("port", 22),
                user=value.get("user", "root"),
                auth_mode=value.get("auth_mode", "key"),
                ssh_key=value.get("ssh_key", ""),
                password=value.get("password", ""),
                description=value.get("description", ""),
            )
    return servers


def save_server(server: Server) -> None:
    """Save or update a server."""
    servers_path = get_servers_path()
    data = _read_toml(servers_path) or {}

    section_key = f"server:{server.name}"
    data[section_key] = {
        "host": server.host,
        "port": server.port,
        "user": server.user,
        "auth_mode": server.auth_mode,
        "ssh_key": server.ssh_key,
        "password": server.password,
        "description": server.description,
    }
    _write_toml(servers_path, data)


def delete_server(name: str) -> bool:
    """Delete a server by name. Returns True if deleted."""
    servers_path = get_servers_path()
    data = _read_toml(servers_path) or {}
    section_key = f"server:{name}"
    if section_key in data:
        del data[section_key]
        _write_toml(servers_path, data)
        return True
    return False


# ── Internal helpers ────────────────────────────────────────────────────


def _parse_proxy_config(data: dict, defaults: Optional[ProxyConfig] = None) -> ProxyConfig:
    """Parse a dict into ProxyConfig, merging with defaults."""
    config = ProxyConfig(
        http_proxy=data.get("http_proxy", ""),
        https_proxy=data.get("https_proxy", ""),
        socks_proxy=data.get("socks_proxy", ""),
        ftp_proxy=data.get("ftp_proxy", ""),
        no_proxy=data.get("no_proxy", ""),
    )
    auth_data = data.get("auth", {})
    if auth_data:
        config.auth = ProxyAuth(
            username=auth_data.get("username", ""),
            password=auth_data.get("password", ""),
        )
    if defaults:
        config = config.merged_with(defaults)
    return config


def _read_toml(path: Path) -> Optional[dict]:
    """Read a TOML file, returning None if file doesn't exist."""
    if tomllib is None:
        print("Warning: No TOML library available. Install tomli or use Python 3.11+.",
              file=sys.stderr)
        return {}
    if not path.exists():
        return {}
    try:
        with open(path, "rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"Warning: Failed to read {path}: {e}", file=sys.stderr)
        return {}


def _write_toml(path: Path, data: dict) -> None:
    """Write a dict to a TOML file."""
    if tomli_w is None:
        print("Warning: tomli_w not available, can't write config.",
              file=sys.stderr)
        return
    with open(path, "wb") as f:
        tomli_w.dump(data, f)
