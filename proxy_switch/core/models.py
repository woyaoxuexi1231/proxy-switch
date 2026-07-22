"""Data models for profiles and server configurations."""

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
        """Return True if at least http_proxy or https_proxy is set."""
        return bool(self.http_proxy or self.https_proxy)

    @property
    def primary_proxy(self) -> str:
        """Return the best proxy URL for display."""
        return self.https_proxy or self.http_proxy or self.socks_proxy or ""

    def to_dict(self) -> dict:
        return {
            "http_proxy": self.http_proxy,
            "https_proxy": self.https_proxy,
            "socks_proxy": self.socks_proxy,
            "ftp_proxy": self.ftp_proxy,
            "no_proxy": self.no_proxy,
        }

    def merged_with(self, defaults: "ProxyConfig") -> "ProxyConfig":
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
    """SSH server connection info."""
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
