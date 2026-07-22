"""Docker daemon proxy and registry mirror configuration.

Proxy: systemd drop-in at /etc/systemd/system/docker.service.d/proxy.conf
       (daemon.json cannot set environment variables for dockerd).
Mirror: registry-mirrors in /etc/docker/daemon.json.
"""

from __future__ import annotations

import json
from typing import Dict, List

from ..core.models import Result, StatusInfo

NAME = "docker"
DESCRIPTION = "Docker daemon proxy and registry mirror"
CONFIG_FILES = [
    "/etc/systemd/system/docker.service.d/proxy.conf",
    "/etc/docker/daemon.json",
]

DOCKER_CONF_DIR = "/etc/systemd/system/docker.service.d"
DOCKER_CONF = "/etc/systemd/system/docker.service.d/proxy.conf"
DAEMON_JSON = "/etc/docker/daemon.json"
SUPPORTS_MIRROR = True


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
    no_proxy = proxy_config.get("no_proxy", "")
    lines = ["# Managed by proxy-switch", "[Service]"]
    if http:
        lines.append(f'Environment="HTTP_PROXY={http}"')
        lines.append(f'Environment="http_proxy={http}"')
    if https:
        lines.append(f'Environment="HTTPS_PROXY={https}"')
        lines.append(f'Environment="https_proxy={https}"')
    if no_proxy:
        lines.append(f'Environment="NO_PROXY={no_proxy}"')
        lines.append(f'Environment="no_proxy={no_proxy}"')
    return "\n".join(lines) + "\n"


def _restart_docker(executor) -> List[str]:
    """Restart Docker daemon. Returns list of errors."""
    errs = []
    if executor:
        for cmd in ["sudo systemctl daemon-reload", "sudo systemctl restart docker"]:
            r = executor.run(cmd)
            if r.returncode != 0:
                errs.append(f"{cmd}: {r.stderr}")
    else:
        import subprocess
        for cmd in ["sudo systemctl daemon-reload", "sudo systemctl restart docker"]:
            r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if r.returncode != 0:
                errs.append(f"{cmd}: {r.stderr}")
    return errs


def _update_daemon_json(content: str, mirror: str) -> str:
    """Add or update registry-mirrors in daemon.json content."""
    try:
        cfg = json.loads(content) if content.strip() else {}
    except json.JSONDecodeError:
        cfg = {}
    if mirror:
        cfg["registry-mirrors"] = [mirror]
    elif "registry-mirrors" in cfg:
        del cfg["registry-mirrors"]
    return json.dumps(cfg, indent=2) + "\n" if cfg else ""


def detect(executor=None) -> bool:
    if executor:
        r = executor.run("command -v docker && systemctl show -p Id docker.service 2>/dev/null")
        return r.returncode == 0 and "docker.service" in r.stdout
    import shutil
    if not shutil.which("docker"):
        return False
    import subprocess
    try:
        r = subprocess.run(["systemctl", "show", "-p", "Id", "docker.service"],
                           capture_output=True, text=True, timeout=5)
        return r.returncode == 0 and "docker.service" in r.stdout
    except Exception:
        return False


def enable(proxy_config: Dict[str, str], executor=None) -> Result:
    """Set Docker proxy and optionally registry mirror, then restart."""
    # Early sudo check
    if executor and not executor.has_sudo():
        return Result(
            success=False,
            message="Sudo access required. Configure passwordless sudo on the remote server."
        )

    content = _proxy_content(proxy_config)
    ok = _write_file(executor, DOCKER_CONF, content, sudo=True)
    if not ok:
        return Result(success=False, message=f"Failed to write {DOCKER_CONF}")

    # Registry mirror
    mirror = proxy_config.get("mirror", "")
    if mirror:
        existing = _read_file(executor, DAEMON_JSON)
        updated = _update_daemon_json(existing, mirror)
        if updated:
            _write_file(executor, DAEMON_JSON, updated, sudo=True)

    errs = _restart_docker(executor)
    if errs:
        return Result(success=True, message="Proxy written, restart had issues",
                      details="; ".join(errs))
    return Result(success=True, message="Docker proxy configured and restarted")


def disable(executor=None) -> Result:
    """Remove Docker proxy config and restart daemon."""
    if executor:
        executor.run(f"sudo rm -f {DOCKER_CONF}")
    else:
        import subprocess
        subprocess.run(["sudo", "rm", "-f", DOCKER_CONF], shell=True)

    # Remove registry-mirrors from daemon.json if present
    existing = _read_file(executor, DAEMON_JSON)
    if existing.strip():
        updated = _update_daemon_json(existing, "")
        if updated != existing:
            _write_file(executor, DAEMON_JSON, updated, sudo=True)

    _restart_docker(executor)
    return Result(success=True, message="Docker proxy disabled")


def status(executor=None) -> StatusInfo:
    """Check Docker proxy and registry mirror status."""
    content = _read_file(executor, DOCKER_CONF)
    enabled = "HTTP_PROXY=" in content
    proxy = None
    for line in content.split("\n"):
        if 'HTTP_PROXY=' in line:
            import re
            m = re.search(r'"(.*?)"', line)
            if m:
                proxy = m.group(1)
                break

    mirror = None
    daemon = _read_file(executor, DAEMON_JSON)
    if daemon.strip():
        try:
            cfg = json.loads(daemon)
            mirrors = cfg.get("registry-mirrors", [])
            if mirrors:
                mirror = mirrors[0]
        except json.JSONDecodeError:
            pass

    return StatusInfo(
        enabled=enabled,
        proxy=proxy,
        mirror=mirror,
        config_file=DOCKER_CONF,
        notes="Docker daemon restarted to apply changes",
    )


def validate(executor=None) -> List[str]:
    issues = []
    if not detect(executor):
        issues.append("Docker is not installed or not managed by systemd")
    return issues
