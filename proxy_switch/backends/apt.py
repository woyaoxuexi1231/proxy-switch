"""APT package manager proxy backend."""

from typing import Dict, Optional

from .base import Backend


class AptBackend(Backend):

    APT_CONF = "/etc/apt/apt.conf.d/proxy.conf"

    @staticmethod
    def name() -> str:
        return "apt"

    @staticmethod
    def description() -> str:
        return "APT package manager proxy"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            r = executor.run("command -v apt-get || command -v apt")
            return r.returncode == 0
        import shutil
        return shutil.which("apt-get") is not None or shutil.which("apt") is not None

    @staticmethod
    def needs_sudo() -> bool:
        return True

    def _content(self, proxy_config: Dict[str, str]) -> str:
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

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        content = self._content(proxy_config)
        return self._write_conf(content, executor)

    def disable(self, executor=None) -> Dict:
        if executor:
            r = executor.run(f"sudo rm -f {self.APT_CONF}")
            return {"success": r.returncode == 0,
                    "message": "APT proxy removed" if r.returncode == 0 else "Failed to remove",
                    "details": r.stderr or ""}
        else:
            import os
            try:
                if os.path.exists(self.APT_CONF):
                    os.remove(self.APT_CONF)
                return {"success": True, "message": "APT proxy removed", "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def status(self, executor=None) -> Dict:
        if executor:
            r = executor.run(f"cat {self.APT_CONF} 2>/dev/null || echo ''")
            content = r.stdout
        else:
            try:
                with open(self.APT_CONF) as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError):
                content = ""

        enabled = "Acquire::http::Proxy" in content or "Acquire::https::Proxy" in content
        proxy = None
        for line in content.split("\n"):
            if "Acquire::http::Proxy" in line or "Acquire::https::Proxy" in line:
                import re
                m = re.search(r'"(.*?)"', line)
                if m:
                    proxy = m.group(1)
                    break
        return {
            "enabled": enabled,
            "proxy": proxy,
            "config_file": self.APT_CONF,
            "notes": "",
        }

    def _write_conf(self, content: str, executor=None) -> Dict:
        if executor:
            r = executor.write(self.APT_CONF, content, sudo=True)
            return {"success": r.returncode == 0,
                    "message": "APT proxy configured" if r.returncode == 0 else "Write failed",
                    "details": r.stderr or ""}
        else:
            import os
            import tempfile
            try:
                os.makedirs(os.path.dirname(self.APT_CONF), exist_ok=True)
                with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
                    tf.write(content)
                    tf.flush()
                import subprocess
                r = subprocess.run(["sudo", "cp", tf.name, self.APT_CONF],
                                   capture_output=True, text=True)
                os.unlink(tf.name)
                return {"success": r.returncode == 0,
                        "message": "APT proxy configured" if r.returncode == 0 else r.stderr,
                        "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}
