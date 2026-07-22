"""Snap package manager proxy backend."""

from typing import Dict, Optional

from .base import Backend


class SnapBackend(Backend):

    @staticmethod
    def name() -> str:
        return "snap"

    @staticmethod
    def description() -> str:
        return "Snap package manager proxy"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            r = executor.run("command -v snap")
            return r.returncode == 0
        import shutil
        return shutil.which("snap") is not None

    @staticmethod
    def needs_sudo() -> bool:
        return True

    def _run_snap(self, args: str, executor=None) -> Dict:
        cmd = f"sudo snap {args}"
        if executor:
            r = executor.run(cmd)
            return {"success": r.returncode == 0, "output": r.stdout.strip(),
                    "error": r.stderr}
        else:
            import subprocess
            try:
                r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                return {"success": r.returncode == 0, "output": r.stdout.strip(),
                        "error": r.stderr}
            except Exception as e:
                return {"success": False, "output": "", "error": str(e)}

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        http = proxy_config.get("http_proxy", "")
        https = proxy_config.get("https_proxy", "")

        errors = []
        if http:
            r = self._run_snap(f'set system proxy.http="{http}"', executor)
            if not r["success"] and "error" in r:
                errors.append(f"http: {r['error']}")
        if https:
            r = self._run_snap(f'set system proxy.https="{https}"', executor)
            if not r["success"] and "error" in r:
                errors.append(f"https: {r['error']}")

        if errors:
            return {"success": False, "message": "; ".join(errors), "details": ""}
        return {"success": True, "message": "Snap proxy configured", "details": ""}

    def disable(self, executor=None) -> Dict:
        self._run_snap('set system proxy.http=""', executor)
        self._run_snap('set system proxy.https=""', executor)
        return {"success": True, "message": "Snap proxy disabled", "details": ""}

    def status(self, executor=None) -> Dict:
        r1 = self._run_snap("get system proxy.http 2>/dev/null || echo ''", executor)
        r2 = self._run_snap("get system proxy.https 2>/dev/null || echo ''", executor)
        proxy = r1["output"] or r2["output"] or None
        return {
            "enabled": bool(r1["output"] or r2["output"]),
            "proxy": proxy,
            "config_file": "(snap store)",
            "notes": "May require snapd restart on some systems",
        }
