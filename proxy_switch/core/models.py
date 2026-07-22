"""Data models for proxy configurations and SSH servers."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ProxyAuth:
    """Proxy authentication credentials."""
    username: str = ""
    password: str = ""


@dataclass
class ProxyConfig:
    """Proxy configuration values."""
    http_proxy: str = ""
    https_proxy: str = ""
    socks_proxy: str = ""
    ftp_proxy: str = ""
    no_proxy: str = "localhost,127.0.0.1,::1"
    auth: ProxyAuth = field(default_factory=ProxyAuth)

    @property
    def is_enabled(self) -> bool:
        """Return True if at least one proxy is configured."""
        return bool(self.http_proxy or self.https_proxy)

    @property
    def primary_proxy(self) -> str:
        """Best proxy URL for display purposes."""
        return self.https_proxy or self.http_proxy or self.socks_proxy or ""

    def to_dict(self) -> dict:
        return {
            "http_proxy": self.http_proxy,
            "https_proxy": self.https_proxy,
            "socks_proxy": self.socks_proxy,
            "ftp_proxy": self.ftp_proxy,
            "no_proxy": self.no_proxy,
        }

    def merged_with(self, defaults: ProxyConfig) -> ProxyConfig:
        """Merge with defaults: use self value if set, otherwise fallback to defaults."""
        merged = ProxyConfig()
        for field_name in ("http_proxy", "https_proxy", "socks_proxy",
                           "ftp_proxy", "no_proxy"):
            my_val = getattr(self, field_name)
            default_val = getattr(defaults, field_name)
            setattr(merged, field_name, my_val if my_val else default_val)
        merged.auth = self.auth if self.auth.username else defaults.auth
        return merged


@dataclass
class Profile:
    """A named proxy profile."""
    name: str
    config: ProxyConfig = field(default_factory=ProxyConfig)
    description: str = ""


@dataclass
class Server:
    """SSH server connection information."""
    name: str
    host: str
    port: int = 22
    user: str = "root"
    auth_mode: str = "key"  # "key" or "password"
    ssh_key: str = ""
    password: str = ""
    description: str = ""

    @property
    def label(self) -> str:
        return f"{self.name} ({self.host}:{self.port})"


# ── Feature Module Return Types ────────────────────────────────────────────


@dataclass
class Result:
    """Standard return type for enable/disable operations."""
    success: bool
    message: str = ""
    details: str = ""


@dataclass
class StatusInfo:
    """Return type for status checks."""
    enabled: bool = False
    proxy: Optional[str] = None
    mirror: Optional[str] = None
    config_file: Optional[str] = None
    notes: str = ""
