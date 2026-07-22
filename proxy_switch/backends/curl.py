"""curl proxy backend."""

from typing import Dict, Optional

from .base import Backend


class CurlBackend(Backend):

    CURLRC = "~/.curlrc"

    @staticmethod
    def name() -> str:
        return "curl"

    @staticmethod
    def description() -> str:
        return "curl HTTP client proxy"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            return executor.run("command -v curl").returncode == 0
        import shutil
        return shutil.which("curl") is not None

    @staticmethod
    def needs_sudo() -> bool:
        return False

    def _path(self) -> str:
        import os
        return os.path.expanduser(self.CURLRC)

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        http = proxy_config.get("http_proxy", "")
        https = proxy_config.get("https_proxy", "")
        no_proxy = proxy_config.get("no_proxy", "")

        lines = ["# Managed by proxy-switch"]
        if http:
            lines.append(f'proxy = "{http}"')
        if https:
            lines.append(f'https-proxy = "{https}"')
        if no_proxy:
            lines.append(f'noproxy = "{no_proxy}"')
        if not lines[1:]:
            return {"success": False, "message": "No proxy URL provided", "details": ""}
        content = "\n".join(lines) + "\n"

        if executor:
            r = executor.write(self._path(), content)
            return {"success": r.returncode == 0,
                    "message": "curl proxy configured" if r.returncode == 0 else "Write failed",
                    "details": r.stderr or ""}
        else:
            try:
                with open(self._path(), "w") as f:
                    f.write(content)
                return {"success": True, "message": "curl proxy configured", "details": ""}
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
                return {"success": True, "message": "curl proxy disabled", "details": ""}
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
            if line.startswith("proxy ="):
                enabled = True
                parts = line.split("=", 1)
                if len(parts) > 1:
                    proxy = parts[1].strip().strip('"')
        return {
            "enabled": enabled,
            "proxy": proxy,
            "config_file": self._path(),
            "notes": "",
        }
