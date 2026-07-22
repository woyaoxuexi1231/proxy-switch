"""APT package manager proxy and mirror configuration.

Proxy: writes to /etc/apt/apt.conf.d/proxy.conf (dedicated file, safe).
Mirror: replaces the Ubuntu archive URL in /etc/apt/sources.list.
Only the first matching archive.ubuntu.com URL is changed.
"""

from __future__ import annotations

import re
from typing import Dict, List

from ..core.models import Result, StatusInfo

NAME = "apt"
DESCRIPTION = "APT package manager proxy and mirror"
CONFIG_FILES = [
    "/etc/apt/apt.conf.d/proxy.conf",
    "/etc/apt/sources.list",
]

APT_CONF = "/etc/apt/apt.conf.d/proxy.conf"
SUPPORTS_MIRROR = True

# Common Ubuntu archive patterns — replace the first match for mirror support
_ARCHIVE_PATTERNS = [
    r"//archive\.ubuntu\.com/ubuntu/?",
    r"//security\.ubuntu\.com/ubuntu/?",
    r"//ports\.ubuntu\.com/ubuntu-ports/?",
    r"//[a-z]+\.archive\.ubuntu\.com/ubuntu/?",
]


def _read_file(executor, path: str) -> str:
    if executor:
        r = executor.run(f"cat {path} 2>/dev/null || echo ''")
        return r.stdout
    try:
        with open(path) as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def _write_file(executor, path: str, content: str, sudo: bool) -> bool:
    if executor:
        r = executor.write(path, content, sudo=sudo)
        return r.returncode == 0
    import tempfile, subprocess, os
    try:
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
            tf.write(content)
            tf.flush()
        if sudo:
            r = subprocess.run(["sudo", "cp", tf.name, path],
                               capture_output=True, text=True)
        else:
            import shutil
            shutil.copy(tf.name, path)
            r = subprocess.CompletedProcess([], 0)
        os.unlink(tf.name)
        return r.returncode == 0
    except Exception:
        return False


def _proxy_content(proxy_config: Dict[str, str]) -> str:
    http = proxy_config.get("http_proxy", "")
    https = proxy_config.get("https_proxy", "")
    ftp = proxy_config.get("ftp_proxy", "")
    no_proxy = proxy_config.get("no_proxy", "")
    lines = ["// Managed by proxy-switch"]
    if http:
        lines.append(f'Acquire::http::Proxy "{http}";')
    if https:
        lines.append(f'Acquire::https::Proxy "{https}";')
    if ftp:
        lines.append(f'Acquire::ftp::Proxy "{ftp}";')
    if no_proxy:
        lines.append(f'Acquire::http::NoProxy "{no_proxy}";')
    return "\n".join(lines) + "\n"


def _detect_current_mirror(content: str) -> str | None:
    """Extract the current Ubuntu archive mirror URL from sources.list."""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("#") or not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[0] in ("deb", "deb-src"):
            url = parts[1]
            # Check if it matches known Ubuntu archive patterns
            for pat in _ARCHIVE_PATTERNS:
                if re.search(pat, url):
                    return url
            # Also return any http(s) URL as a best guess
            if url.startswith("http"):
                return url
    return None


def _update_mirror_in_content(content: str, new_mirror: str) -> str:
    """Replace the first Ubuntu archive URL with the new mirror."""
    replaced = False
    new_lines = []
    for line in content.split("\n"):
        if not replaced:
            stripped = line.strip()
            if stripped.startswith("#") or not stripped:
                new_lines.append(line)
                continue
            parts = stripped.split()
            if len(parts) >= 2 and parts[0] in ("deb", "deb-src"):
                url = parts[1]
                for pat in _ARCHIVE_PATTERNS:
                    if re.search(pat, url):
                        line = line.replace(url, new_mirror)
                        replaced = True
                        break
        new_lines.append(line)

    if not replaced:
        # No archive URL found; append a default entry
        new_lines.append(f"\ndeb {new_mirror} $(lsb_release -cs 2>/dev/null || echo 'focal') main restricted")

    return "\n".join(new_lines)


def _restore_mirror(content: str, original_mirror: str) -> str:
    """Restore original mirror in sources.list."""
    return _update_mirror_in_content(content, original_mirror)


def detect(executor=None) -> bool:
    if executor:
        r = executor.run("command -v apt-get || command -v apt")
        return r.returncode == 0
    import shutil
    return shutil.which("apt-get") is not None or shutil.which("apt") is not None


def enable(proxy_config: Dict[str, str], executor=None) -> Result:
    """Configure APT proxy and optionally set mirror."""
    # Early sudo check
    if executor and not executor.has_sudo():
        return Result(
            success=False,
            message="Sudo access required. Configure passwordless sudo on the remote server."
        )

    # Proxy: write dedicated config file
    content = _proxy_content(proxy_config)
    ok = _write_file(executor, APT_CONF, content, sudo=True)
    if not ok:
        return Result(success=False, message=f"Failed to write {APT_CONF}")

    # Mirror: update sources.list if a mirror URL is provided
    mirror = proxy_config.get("mirror", "")
    if mirror:
        sources = _read_file(executor, "/etc/apt/sources.list")
        if sources:
            updated = _update_mirror_in_content(sources, mirror)
            _write_file(executor, "/etc/apt/sources.list", updated, sudo=True)

    return Result(success=True, message="APT proxy configured")


def disable(executor=None) -> Result:
    """Remove APT proxy config. Mirror is left as-is (user choice)."""
    # Early sudo check
    if executor and not executor.has_sudo():
        return Result(
            success=False,
            message="Sudo access required. Configure passwordless sudo on the remote server."
        )

    if executor:
        r = executor.run(f"sudo rm -f {APT_CONF}")
        if r.returncode != 0:
            return Result(success=False, message=f"Failed to remove {APT_CONF}")
        return Result(success=True, message="APT proxy disabled")
    import os
    try:
        if os.path.exists(APT_CONF):
            os.remove(APT_CONF)
        return Result(success=True, message="APT proxy disabled")
    except Exception as e:
        return Result(success=False, message=str(e))


def status(executor=None) -> StatusInfo:
    """Check APT proxy and mirror status."""
    content = _read_file(executor, APT_CONF)
    enabled = "Acquire::http::Proxy" in content or "Acquire::https::Proxy" in content
    proxy = None
    for line in content.split("\n"):
        if "Acquire::http::Proxy" in line or "Acquire::https::Proxy" in line:
            m = re.search(r'"(.*?)"', line)
            if m:
                proxy = m.group(1)
                break

    # Detect mirror
    mirror = None
    sources = _read_file(executor, "/etc/apt/sources.list")
    if sources:
        mirror = _detect_current_mirror(sources)

    return StatusInfo(
        enabled=enabled,
        proxy=proxy,
        mirror=mirror,
        config_file=APT_CONF,
    )


def validate(executor=None) -> List[str]:
    issues = []
    if not detect(executor):
        issues.append("APT is not installed on this system")
    return issues
