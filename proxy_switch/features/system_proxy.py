"""System-wide proxy environment variables.

Writes proxy settings to /etc/environment and /etc/profile.d/proxy-switch.sh.
Only modifies proxy-related lines — never touches other config in these files.
"""

from __future__ import annotations

from typing import Dict, List

from ..core.models import Result, StatusInfo

NAME = "system_proxy"
DESCRIPTION = "System environment proxy variables (/etc/environment)"
CONFIG_FILES = ["/etc/environment", "/etc/profile.d/proxy-switch.sh"]

ENV_FILE = "/etc/environment"
PROFILE_FILE = "/etc/profile.d/proxy-switch.sh"

_PROXY_KEYS_LOWER = ("http_proxy", "https_proxy", "ftp_proxy", "no_proxy")
_PROXY_KEYS_UPPER = ("HTTP_PROXY", "HTTPS_PROXY", "FTP_PROXY", "NO_PROXY")


def detect(executor=None) -> bool:
    """System proxy can always be applied — every Linux has /etc."""
    return True


def _read_file(executor, path: str) -> str:
    """Read a remote or local file, returning empty string on failure."""
    if executor:
        r = executor.run(f"cat {path} 2>/dev/null || echo ''")
        return r.stdout
    try:
        with open(path) as f:
            return f.read()
    except (FileNotFoundError, PermissionError):
        return ""


def _write_file(executor, path: str, content: str, sudo: bool = False) -> bool:
    """Write content to a remote or local file. Returns True on success."""
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


def _update_env_lines(content: str, proxy_config: Dict[str, str]) -> str:
    """Update only proxy-related lines in /etc/environment content.

    Preserves all non-proxy lines. Adds/replaces proxy lines.
    """
    proxy_prefixes = tuple(
        [k + "=" for k in _PROXY_KEYS_LOWER] +
        [k + "=" for k in _PROXY_KEYS_UPPER] +
        ["# Managed by proxy-switch"]
    )

    # Keep lines that are NOT proxy-related
    keep = [l for l in content.split("\n")
            if not l.strip().startswith(proxy_prefixes)]

    # Build new proxy block
    new_lines = ["# Managed by proxy-switch"]
    for key in _PROXY_KEYS_LOWER:
        val = proxy_config.get(key, "")
        if val:
            new_lines.append(f'{key}="{val}"')
    for key in _PROXY_KEYS_UPPER:
        lower_val = proxy_config.get(key.lower(), "")
        if lower_val:
            new_lines.append(f'{key}="{lower_val}"')

    # Remove trailing blank lines from keep
    while keep and keep[-1] == "":
        keep.pop()

    if keep:
        return "\n".join(keep) + "\n\n" + "\n".join(new_lines) + "\n"
    else:
        return "\n".join(new_lines) + "\n"


def _make_profile_content(proxy_config: Dict[str, str]) -> str:
    """Generate shell profile format — export KEY="value"."""
    lines = ["# Managed by proxy-switch", ""]
    for key in _PROXY_KEYS_LOWER:
        val = proxy_config.get(key, "")
        if val:
            lines.append(f'export {key}="{val}"')
    for key in _PROXY_KEYS_UPPER:
        lower_val = proxy_config.get(key.lower(), "")
        if lower_val:
            lines.append(f'export {key}="{lower_val}"')
    lines.append("")
    return "\n".join(lines)


def enable(proxy_config: Dict[str, str], executor=None) -> Result:
    """Set proxy env vars. Only modifies proxy lines — safe for existing config."""
    # Early sudo check — fail fast instead of hanging on password prompt
    if executor and not executor.has_sudo():
        return Result(
            success=False,
            message="Sudo access required. Configure passwordless sudo on the remote server, "
                    "or use a root user."
        )

    # /etc/environment: read-modify-write
    existing = _read_file(executor, ENV_FILE)
    new_env = _update_env_lines(existing, proxy_config)
    ok1 = _write_file(executor, ENV_FILE, new_env, sudo=True)

    # /etc/profile.d/proxy-switch.sh: dedicated file, safe to overwrite
    profile_content = _make_profile_content(proxy_config)
    ok2 = _write_file(executor, PROFILE_FILE, profile_content, sudo=True)

    if not ok1 or not ok2:
        errs = []
        if not ok1:
            errs.append(f"Failed to write {ENV_FILE}")
        if not ok2:
            errs.append(f"Failed to write {PROFILE_FILE}")
        return Result(success=False, message="; ".join(errs))
    return Result(success=True, message="System proxy configured")


def disable(executor=None) -> Result:
    """Remove proxy lines from /etc/environment and delete profile script."""
    # Early sudo check
    if executor and not executor.has_sudo():
        return Result(
            success=False,
            message="Sudo access required. Configure passwordless sudo on the remote server, "
                    "or use a root user."
        )

    # Remove proxy lines from /etc/environment
    existing = _read_file(executor, ENV_FILE)
    new_env = _update_env_lines(existing, {})  # empty config → no proxy lines
    _write_file(executor, ENV_FILE, new_env, sudo=True)

    # Delete the profile script
    if executor:
        executor.run(f"sudo rm -f {PROFILE_FILE}")
    else:
        import subprocess
        subprocess.run(["sudo", "rm", "-f", PROFILE_FILE])

    return Result(success=True, message="System proxy disabled")


def status(executor=None) -> StatusInfo:
    """Check proxy state from /etc/environment."""
    content = _read_file(executor, ENV_FILE)

    enabled = "http_proxy=" in content or "HTTP_PROXY=" in content
    proxy = None
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("http_proxy=") or line.startswith("HTTP_PROXY="):
            proxy = line.split("=", 1)[1].strip('"').strip("'")
            break

    return StatusInfo(
        enabled=enabled,
        proxy=proxy,
        config_file=f"{ENV_FILE}, {PROFILE_FILE}",
        notes="Run 'source /etc/profile.d/proxy-switch.sh' or re-login to apply",
    )


def validate(executor=None) -> List[str]:
    """Check that system proxy is applicable."""
    issues = []
    if not detect(executor):
        issues.append("System proxy is not available on this system")
    return issues
