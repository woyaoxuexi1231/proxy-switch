"""npm proxy backend."""

from typing import Dict, Optional

from .base import Backend


class NpmBackend(Backend):

    @staticmethod
    def name() -> str:
        return "npm"

    @staticmethod
    def description() -> str:
        return "npm package manager proxy"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            return executor.run("command -v npm").returncode == 0
        import shutil
        return shutil.which("npm") is not None

    @staticmethod
    def needs_sudo() -> bool:
        return False

    def _run_npm(self, args: str, executor=None) -> Dict:
        cmd = f"npm {args}"
        if executor:
            r = executor.run(cmd)
            return {"success": r.returncode == 0, "output": r.stdout.strip()}
        else:
            import subprocess
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return {"success": r.returncode == 0, "output": r.stdout.strip()}
            except Exception as e:
                return {"success": False, "output": str(e)}

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        http = proxy_config.get("http_proxy", "")
        https = proxy_config.get("https_proxy", "")

        errors = []
        if http:
            r = self._run_npm(f'config set proxy "{http}"', executor)
            if not r["success"]:
                errors.append(f"proxy: {r['output']}")
        if https:
            r = self._run_npm(f'config set https-proxy "{https}"', executor)
            if not r["success"]:
                errors.append(f"https-proxy: {r['output']}")

        # Also handle no_proxy for npm
        no_proxy = proxy_config.get("no_proxy", "")
        if no_proxy:
            self._run_npm(f'config set no-proxy "{no_proxy}"', executor)

        if errors:
            return {"success": False, "message": "; ".join(errors), "details": ""}
        return {"success": True, "message": "npm proxy configured", "details": ""}

    def disable(self, executor=None) -> Dict:
        self._run_npm("config delete proxy", executor)
        self._run_npm("config delete https-proxy", executor)
        self._run_npm("config delete no-proxy", executor)
        return {"success": True, "message": "npm proxy disabled", "details": ""}

    def status(self, executor=None) -> Dict:
        r1 = self._run_npm("config get proxy 2>/dev/null || echo '(not set)'", executor)
        r2 = self._run_npm("config get https-proxy 2>/dev/null || echo '(not set)'", executor)
        proxy = None
        for r in [r1, r2]:
            if r["output"] and r["output"] != "(not set)":
                proxy = r["output"]
                break
        return {
            "enabled": bool(r1["output"] and r1["output"] != "(not set)"),
            "proxy": proxy,
            "config_file": "~/.npmrc",
            "notes": "",
        }
