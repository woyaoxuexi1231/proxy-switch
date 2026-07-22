"""Configuration file management.

Reads and writes TOML config files for profiles and servers.
Config files are stored in ~/.proxy-switch/ on the host machine.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

from .models import Profile, ProxyConfig, ProxyAuth, Server

# ── TOML Library Selection ─────────────────────────────────────────────────

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None

try:
    import tomli_w
except ImportError:
    tomli_w = None


# ── Paths ──────────────────────────────────────────────────────────────────


def config_dir() -> Path:
    """Return the config directory, creating it if needed."""
    path = Path.home() / ".proxy-switch"
    path.mkdir(parents=True, exist_ok=True)
    return path


def config_path() -> Path:
    return config_dir() / "config.toml"


def servers_path() -> Path:
    return config_dir() / "servers.toml"


# ── TOML Helpers ───────────────────────────────────────────────────────────


def _read_toml(path: Path) -> Optional[dict]:
    """Read a TOML file, returning None if unavailable."""
    if tomllib is None:
        print("Warning: No TOML library available. Install tomli or use Python 3.11+.",
              file=sys.stderr)
        return None
    if not path.exists():
        return None
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except Exception as e:
        print(f"Warning: Failed to read {path}: {e}", file=sys.stderr)
        return None


def _write_toml(path: Path, data: dict) -> None:
    """Write a dict to a TOML file."""
    if tomli_w is None:
        print("Warning: tomli_w not available, cannot write config.",
              file=sys.stderr)
        return
    with path.open("wb") as f:
        tomli_w.dump(data, f)


# ── Config Parsing ─────────────────────────────────────────────────────────


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


# ── Profiles ───────────────────────────────────────────────────────────────


def load_profiles() -> Dict[str, Profile]:
    """Load all profiles from config.toml.

    Returns a dict of {profile_name: Profile}, always including a 'direct' profile.
    """
    raw = _read_toml(config_path())
    if raw is None:
        raw = {}

    defaults = _parse_proxy_config(raw.get("defaults", {}))

    profiles: Dict[str, Profile] = {}
    for key, value in raw.items():
        if key.startswith("profile:"):
            name = key[len("profile:"):]
            profile_config = _parse_proxy_config(value, defaults)
            desc = value.get("description", "")
            profiles[name] = Profile(name=name, config=profile_config, description=desc)

    # Always include a "direct" (no-proxy) profile
    if "direct" not in profiles:
        profiles["direct"] = Profile(
            name="direct",
            config=ProxyConfig(),
            description="Direct connection (no proxy)",
        )

    return profiles


def save_profile(profile: Profile, defaults: Optional[ProxyConfig] = None) -> None:
    """Save or update a profile."""
    path = config_path()
    raw = _read_toml(path) or {}

    section_key = f"profile:{profile.name}"
    section = raw.get(section_key, {})

    cfg = profile.config
    if cfg.http_proxy:
        section["http_proxy"] = cfg.http_proxy
    if cfg.https_proxy:
        section["https_proxy"] = cfg.https_proxy
    if cfg.socks_proxy:
        section["socks_proxy"] = cfg.socks_proxy
    if cfg.ftp_proxy:
        section["ftp_proxy"] = cfg.ftp_proxy
    if cfg.no_proxy:
        section["no_proxy"] = cfg.no_proxy
    if cfg.auth.username:
        section.setdefault("auth", {})["username"] = cfg.auth.username
    if cfg.auth.password:
        section.setdefault("auth", {})["password"] = cfg.auth.password
    if profile.description:
        section["description"] = profile.description

    raw[section_key] = section
    _write_toml(path, raw)


def delete_profile(name: str) -> bool:
    """Delete a profile by name. Returns True if deleted."""
    path = config_path()
    raw = _read_toml(path) or {}
    section_key = f"profile:{name}"
    if section_key in raw:
        del raw[section_key]
        _write_toml(path, raw)
        return True
    return False


# ── Servers ────────────────────────────────────────────────────────────────


def load_servers() -> Dict[str, Server]:
    """Load all servers from servers.toml."""
    raw = _read_toml(servers_path())
    if raw is None:
        raw = {}

    servers: Dict[str, Server] = {}
    for key, value in raw.items():
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
    path = servers_path()
    raw = _read_toml(path) or {}

    section_key = f"server:{server.name}"
    raw[section_key] = {
        "host": server.host,
        "port": server.port,
        "user": server.user,
        "auth_mode": server.auth_mode,
        "ssh_key": server.ssh_key,
        "password": server.password,
        "description": server.description,
    }
    _write_toml(path, raw)


def delete_server(name: str) -> bool:
    """Delete a server by name. Returns True if deleted."""
    path = servers_path()
    raw = _read_toml(path) or {}
    section_key = f"server:{name}"
    if section_key in raw:
        del raw[section_key]
        _write_toml(path, raw)
        return True
    return False
