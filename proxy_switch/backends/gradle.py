"""Gradle proxy backend."""

from typing import Dict, Optional
import os
import re

from .base import Backend


class GradleBackend(Backend):

    GRADLE_PROPS = "~/.gradle/gradle.properties"

    @staticmethod
    def name() -> str:
        return "gradle"

    @staticmethod
    def description() -> str:
        return "Gradle build tool proxy"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            return executor.run("command -v gradle").returncode == 0
        import shutil
        return shutil.which("gradle") is not None

    @staticmethod
    def needs_sudo() -> bool:
        return False

    def _path(self) -> str:
        return os.path.expanduser(self.GRADLE_PROPS)

    def _parse_host_port(self, url: str) -> tuple:
        """Extract host and port from a proxy URL."""
        if not url:
            return ("", "")
        m = re.match(r'(https?|socks5?)://(.+)', url)
        if m:
            url = m.group(2)
        if ":" in url:
            host, port = url.split(":", 1)
            return (host, port.split("/")[0])
        return (url, "80")

    def _content(self, proxy_config: Dict[str, str]) -> str:
        http = proxy_config.get("http_proxy", "")
        https = proxy_config.get("https_proxy", "")
        no_proxy = proxy_config.get("no_proxy", "")

        lines = ["# Managed by proxy-switch"]
        if http:
            h, p = self._parse_host_port(http)
            lines.append(f"systemProp.http.proxyHost={h}")
            lines.append(f"systemProp.http.proxyPort={p}")
        if https:
            h, p = self._parse_host_port(https)
            lines.append(f"systemProp.https.proxyHost={h}")
            lines.append(f"systemProp.https.proxyPort={p}")
        if no_proxy:
            gradle_non_proxy = no_proxy.replace(",", "|")
            lines.append(f"systemProp.http.nonProxyHosts={gradle_non_proxy}")
        lines.append("")
        return "\n".join(lines)

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        content = self._content(proxy_config)
        if not any("proxyHost" in l for l in content.split("\n")):
            return {"success": False, "message": "No proxy URL provided", "details": ""}

        if executor:
            r = executor.write(self._path(), content)
            return {"success": r.returncode == 0,
                    "message": "Gradle proxy configured" if r.returncode == 0 else "Write failed",
                    "details": r.stderr or ""}
        else:
            try:
                os.makedirs(os.path.dirname(self._path()), exist_ok=True)
                with open(self._path(), "w") as f:
                    f.write(content)
                return {"success": True, "message": "Gradle proxy configured", "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def disable(self, executor=None) -> Dict:
        if executor:
            r = executor.read(self._path())
            if r.returncode == 0:
                new_content = self._remove_proxy_lines(r.stdout)
                executor.write(self._path(), new_content)
            return {"success": True, "message": "Gradle proxy disabled", "details": ""}
        else:
            try:
                path = self._path()
                if os.path.exists(path):
                    with open(path) as f:
                        content = f.read()
                    new_content = self._remove_proxy_lines(content)
                    with open(path, "w") as f:
                        f.write(new_content)
                return {"success": True, "message": "Gradle proxy disabled", "details": ""}
            except Exception as e:
                return {"success": False, "message": str(e), "details": ""}

    def status(self, executor=None) -> Dict:
        if executor:
            r = executor.read(self._path())
            if r.returncode != 0:
                return {"enabled": False, "proxy": None,
                        "config_file": self._path(), "notes": ""}
            content = r.stdout
        else:
            try:
                with open(self._path()) as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError):
                content = ""

        enabled = "systemProp.http.proxyHost" in content
        proxy = None
        for line in content.split("\n"):
            if "systemProp.http.proxyHost" in line:
                host = line.split("=", 1)[1].strip()
                proxy = f"http://{host}"
                break
        return {
            "enabled": enabled,
            "proxy": proxy,
            "config_file": self._path(),
            "notes": "",
        }

    def _remove_proxy_lines(self, content: str) -> str:
        """Remove all systemProp proxy lines from content."""
        lines = content.split("\n")
        keep = []
        for line in lines:
            stripped = line.strip()
            if (stripped.startswith("systemProp.http.proxy") or
                stripped.startswith("systemProp.https.proxy") or
                stripped.startswith("systemProp.http.nonProxyHosts")):
                continue
            keep.append(line)
        return "\n".join(keep)
