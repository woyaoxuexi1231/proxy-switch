"""Pip proxy backend."""

from typing import Dict, Optional

from .base import Backend


class PipBackend(Backend):

    PIP_CONF = "~/.config/pip/pip.conf"

    @staticmethod
    def name() -> str:
        return "pip"

    @staticmethod
    def description() -> str:
        return "Python pip package manager proxy"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            return executor.run("command -v pip3 || command -v pip").returncode == 0
        import shutil
        return shutil.which("pip3") is not None or shutil.which("pip") is not None

    @staticmethod
    def needs_sudo() -> bool:
        return False

    def _conf_path(self) -> str:
        import os
        return os.path.expanduser(self.PIP_CONF)

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        http = proxy_config.get("http_proxy", "")
        https = proxy_config.get("https_proxy", "")

        # Use https proxy if available, fallback to http
        proxy = https or http
        if not proxy:
            return {"success": False, "message": "No proxy URL provided", "details": ""}

        content = "[global]\n"
        content += f'proxy = {proxy}\n'

        if executor:
            r = executor.write(self._conf_path(), content)
            return {"success": r.returncode == 0,
                    "message": "pip proxy configured" if r.returncode == 0 else "Write failed",
                    "details": r.stderr or ""}
        else:
            import os
            try:
                conf_path = self._conf_path()
                os.makedirs(os.path.dirname(conf_path), exist_ok=True)
                with open(conf_path, "w") as f:
                    f.write(content)
                return {"success": True, "message": "pip proxy configured", "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def disable(self, executor=None) -> Dict:
        if executor:
            executor.run(f"rm -f {self._conf_path()}")
        else:
            import os
            try:
                conf_path = self._conf_path()
                if os.path.exists(conf_path):
                    # Try to only remove the proxy line, keep file
                    with open(conf_path, "r") as f:
                        lines = f.readlines()
                    new_lines = [l for l in lines if not l.strip().startswith("proxy")]
                    if not new_lines:
                        os.remove(conf_path)
                    else:
                        with open(conf_path, "w") as f:
                            f.writelines(new_lines)
                return {"success": True, "message": "pip proxy disabled", "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def status(self, executor=None) -> Dict:
        if executor:
            r = executor.run(f"cat {self._conf_path()} 2>/dev/null || echo ''")
            content = r.stdout
        else:
            import os
            try:
                with open(self._conf_path()) as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError):
                content = ""

        enabled = "proxy" in content.lower()
        proxy = None
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("proxy") or line.startswith("proxy "):
                parts = line.split("=", 1)
                if len(parts) > 1:
                    proxy = parts[1].strip()
                    break
        return {
            "enabled": enabled,
            "proxy": proxy,
            "config_file": self._conf_path(),
            "notes": "",
        }
