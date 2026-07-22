"""wget proxy backend."""

from typing import Dict, Optional

from .base import Backend


class WgetBackend(Backend):

    WGETRC = "~/.wgetrc"

    @staticmethod
    def name() -> str:
        return "wget"

    @staticmethod
    def description() -> str:
        return "wget download tool proxy"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            return executor.run("command -v wget").returncode == 0
        import shutil
        return shutil.which("wget") is not None

    @staticmethod
    def needs_sudo() -> bool:
        return False

    def _path(self) -> str:
        import os
        return os.path.expanduser(self.WGETRC)

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        http = proxy_config.get("http_proxy", "")
        https = proxy_config.get("https_proxy", "")
        ftp = proxy_config.get("ftp_proxy", "")
        no_proxy = proxy_config.get("no_proxy", "")

        lines = ["# Managed by proxy-switch", "use_proxy = on"]
        if http:
            lines.append(f'http_proxy = {http}')
        if https:
            lines.append(f'https_proxy = {https}')
        if ftp:
            lines.append(f'ftp_proxy = {ftp}')
        if no_proxy:
            lines.append(f'no_proxy = {no_proxy}')
        content = "\n".join(lines) + "\n"

        if executor:
            r = executor.write(self._path(), content)
            return {"success": r.returncode == 0,
                    "message": "wget proxy configured" if r.returncode == 0 else "Write failed",
                    "details": r.stderr or ""}
        else:
            try:
                with open(self._path(), "w") as f:
                    f.write(content)
                return {"success": True, "message": "wget proxy configured", "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def disable(self, executor=None) -> Dict:
        if executor:
            executor.run(f"rm -f {self._path()}")
        else:
            import os
            try:
                if os.path.exists(self._path()):
                    os.remove(self._path())
                return {"success": True, "message": "wget proxy disabled", "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def status(self, executor=None) -> Dict:
        if executor:
            r = executor.run(f"cat {self._path()} 2>/dev/null || echo ''")
            content = r.stdout
        else:
            import os
            try:
                with open(self._path()) as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError):
                content = ""

        enabled = False
        proxy = None
        for line in content.split("\n"):
            line = line.strip()
            if line == "use_proxy = on":
                enabled = True
            if line.startswith("http_proxy ="):
                parts = line.split("=", 1)
                if len(parts) > 1:
                    proxy = parts[1].strip()
        return {
            "enabled": enabled,
            "proxy": proxy,
            "config_file": self._path(),
            "notes": "",
        }
