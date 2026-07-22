"""npm proxy and registry mirror configuration.

Uses npm config to set proxy, https-proxy, registry, and no-proxy.
All operations are user-scoped — never touches system npm config.
"""

from __future__ import annotations

from typing import Dict, List

from ..core.models import Result, StatusInfo

NAME = "npm"
DESCRIPTION = "npm package manager proxy and registry"
CONFIG_FILES = ["~/.npmrc"]
SUPPORTS_MIRROR = True

# Default npm registry used to detect if a custom registry is set
_DEFAULT_REGISTRY = "https://registry.npmjs.org/"


def _run_npm(args: str, executor=None) -> dict:
    """Run npm config command. Returns {'success': bool, 'output': str}."""
    cmd = f"npm {args}"
    if executor:
        r = executor.run(cmd)
        return {"success": r.returncode == 0, "output": r.stdout.strip()}
    import subprocess
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return {"success": r.returncode == 0, "output": r.stdout.strip()}
    except Exception as e:
        return {"success": False, "output": str(e)}


def detect(executor=None) -> bool:
    if executor:
        return executor.run("command -v npm").returncode == 0
    import shutil
    return shutil.which("npm") is not None


def enable(proxy_config: Dict[str, str], executor=None) -> Result:
    """Set npm proxy, https-proxy, registry mirror, and no-proxy."""
    errors = []

    http = proxy_config.get("http_proxy", "")
    if http:
        r = _run_npm(f'config set proxy "{http}"', executor)
        if not r["success"]:
            errors.append(f"proxy: {r['output']}")

    https = proxy_config.get("https_proxy", "")
    if https:
        r = _run_npm(f'config set https-proxy "{https}"', executor)
        if not r["success"]:
            errors.append(f"https-proxy: {r['output']}")

    no_proxy = proxy_config.get("no_proxy", "")
    if no_proxy:
        _run_npm(f'config set no-proxy "{no_proxy}"', executor)

    mirror = proxy_config.get("mirror", "")
    if mirror:
        r = _run_npm(f'config set registry "{mirror}"', executor)
        if not r["success"]:
            errors.append(f"registry: {r['output']}")

    if errors:
        return Result(success=False, message="; ".join(errors))
    return Result(success=True, message="npm proxy configured")


def disable(executor=None) -> Result:
    """Delete npm proxy and registry settings."""
    _run_npm("config delete proxy", executor)
    _run_npm("config delete https-proxy", executor)
    _run_npm("config delete no-proxy", executor)
    _run_npm("config delete registry", executor)
    return Result(success=True, message="npm proxy disabled")


def status(executor=None) -> StatusInfo:
    """Check npm proxy and registry settings."""
    r1 = _run_npm("config get proxy 2>/dev/null || echo '(not set)'", executor)
    r2 = _run_npm("config get https-proxy 2>/dev/null || echo '(not set)'", executor)

    proxy = None
    for r in [r1, r2]:
        if r["output"] and r["output"] != "(not set)":
            proxy = r["output"]
            break

    enabled = bool(r1["output"] and r1["output"] != "(not set)")

    # Detect custom registry
    mirror = None
    r3 = _run_npm("config get registry 2>/dev/null || echo ''", executor)
    if r3["output"] and r3["output"] != _DEFAULT_REGISTRY:
        mirror = r3["output"]

    return StatusInfo(
        enabled=enabled,
        proxy=proxy,
        mirror=mirror,
        config_file="~/.npmrc",
    )


def validate(executor=None) -> List[str]:
    issues = []
    if not detect(executor):
        issues.append("npm is not installed on this system")
    return issues
