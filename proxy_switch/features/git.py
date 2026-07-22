"""Git proxy configuration via git config --global.

Manages http.proxy, https.proxy, and http.*.noProxy in ~/.gitconfig.
"""

from __future__ import annotations

from typing import Dict, Optional, List

from ..core.models import Result, StatusInfo

NAME = "git"
DESCRIPTION = "Git VCS proxy (git config --global)"
CONFIG_FILES = ["~/.gitconfig"]


def _run_git(args: str, executor=None) -> dict:
    """Run a git config command and return {'success': bool, 'output': str}."""
    cmd = f"git config --global {args}"
    if executor:
        result = executor.run(cmd)
        return {"success": result.returncode == 0, "output": result.stdout.strip()}
    else:
        import subprocess
        try:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return {"success": r.returncode == 0, "output": r.stdout.strip()}
        except Exception as e:
            return {"success": False, "output": str(e)}


def detect(executor=None) -> bool:
    """Check if git is installed."""
    if executor:
        return executor.run("command -v git").returncode == 0
    import shutil
    return shutil.which("git") is not None


def enable(proxy_config: Dict[str, str], executor=None) -> Result:
    """Set git http.proxy, https.proxy, and http.*.noProxy."""
    http = proxy_config.get("http_proxy", "")
    https = proxy_config.get("https_proxy", "")
    no_proxy = proxy_config.get("no_proxy", "")

    errors = []
    if http:
        r = _run_git(f'http.proxy "{http}"', executor)
        if not r["success"]:
            errors.append(f"http.proxy: {r['output']}")
    if https:
        r = _run_git(f'https.proxy "{https}"', executor)
        if not r["success"]:
            errors.append(f"https.proxy: {r['output']}")
    if no_proxy:
        r = _run_git(f'http."*".noProxy "{no_proxy}"', executor)
        if not r["success"]:
            errors.append(f"noProxy: {r['output']}")

    if errors:
        return Result(success=False, message="; ".join(errors))
    return Result(success=True, message="Git proxy configured")


def disable(executor=None) -> Result:
    """Unset git proxy settings."""
    _run_git("--unset http.proxy", executor)
    _run_git("--unset https.proxy", executor)
    _run_git("--unset http.*.noProxy", executor)
    return Result(success=True, message="Git proxy disabled")


def status(executor=None) -> StatusInfo:
    """Check git proxy settings."""
    r1 = _run_git("--get http.proxy", executor)
    r2 = _run_git("--get https.proxy", executor)
    proxy = r1["output"] or r2["output"] or None

    return StatusInfo(
        enabled=bool(r1["output"] or r2["output"]),
        proxy=proxy,
        config_file="~/.gitconfig",
    )


def validate(executor=None) -> List[str]:
    """Check Git configuration for issues."""
    issues = []
    if not detect(executor):
        issues.append("Git is not installed on this system")
    return issues
