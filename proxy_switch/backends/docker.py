"""Docker daemon proxy backend.

Configures /etc/systemd/system/docker.service.d/proxy.conf.
"""

from typing import Dict, Optional

from .base import Backend


class DockerBackend(Backend):

    DOCKER_CONF_DIR = "/etc/systemd/system/docker.service.d"
    DOCKER_CONF = "/etc/systemd/system/docker.service.d/proxy.conf"

    @staticmethod
    def name() -> str:
        return "docker"

    @staticmethod
    def description() -> str:
        return "Docker daemon proxy (systemd drop-in)"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            r = executor.run("command -v docker && systemctl show -p Id docker.service 2>/dev/null")
            return r.returncode == 0 and "docker.service" in r.stdout
        import shutil
        if not shutil.which("docker"):
            return False
        import subprocess
        r = subprocess.run(["systemctl", "show", "-p", "Id", "docker.service"],
                           capture_output=True, text=True, timeout=5)
        return r.returncode == 0 and "docker.service" in r.stdout

    @staticmethod
    def needs_sudo() -> bool:
        return True

    def _content(self, proxy_config: Dict[str, str]) -> str:
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

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        content = self._content(proxy_config)
        if executor:
            r = executor.write(self.DOCKER_CONF, content, sudo=True)
            if r.returncode != 0:
                return {"success": False, "message": f"Write failed: {r.stderr}", "details": ""}
            r1 = executor.run("sudo systemctl daemon-reload")
            r2 = executor.run("sudo systemctl restart docker")
            errors = []
            if r1.returncode != 0:
                errors.append(f"daemon-reload: {r1.stderr}")
            if r2.returncode != 0:
                errors.append(f"restart: {r2.stderr}")
            if errors:
                return {"success": True,
                        "message": "Proxy written, but service restart had issues: " + "; ".join(errors),
                        "details": ""}
            return {"success": True, "message": "Docker proxy configured and restarted", "details": ""}
        else:
            import os
            import subprocess
            import tempfile
            try:
                os.makedirs(self.DOCKER_CONF_DIR, exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
                    tf.write(content)
                    tf.flush()
                subprocess.run(["sudo", "cp", tf.name, self.DOCKER_CONF], check=True,
                               capture_output=True, text=True)
                os.unlink(tf.name)
                subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True,
                               capture_output=True, text=True)
                subprocess.run(["sudo", "systemctl", "restart", "docker"], check=True,
                               capture_output=True, text=True)
                return {"success": True, "message": "Docker proxy configured", "details": ""}
            except subprocess.CalledProcessError as e:
                return {"success": False, "message": e.stderr or str(e), "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def disable(self, executor=None) -> Dict:
        cmds = [
            f"sudo rm -f {self.DOCKER_CONF}",
            "sudo systemctl daemon-reload",
            "sudo systemctl restart docker",
        ]
        if executor:
            for cmd in cmds:
                executor.run(cmd)
            return {"success": True, "message": "Docker proxy disabled", "details": ""}
        else:
            import subprocess
            for cmd in cmds:
                subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return {"success": True, "message": "Docker proxy disabled", "details": ""}

    def status(self, executor=None) -> Dict:
        if executor:
            r = executor.run(f"cat {self.DOCKER_CONF} 2>/dev/null || echo ''")
            content = r.stdout
        else:
            try:
                with open(self.DOCKER_CONF) as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError):
                content = ""

        enabled = "HTTP_PROXY=" in content
        proxy = None
        for line in content.split("\n"):
            if 'HTTP_PROXY=' in line:
                import re
                m = re.search(r'"(.*?)"', line)
                if m:
                    proxy = m.group(1)
                    break
        return {
            "enabled": enabled,
            "proxy": proxy,
            "config_file": self.DOCKER_CONF,
            "notes": "Docker daemon was restarted",
        }
