"""Git proxy backend."""

from typing import Dict, Optional

from .base import Backend


class GitBackend(Backend):

    @staticmethod
    def name() -> str:
        return "git"

    @staticmethod
    def description() -> str:
        return "Git VCS (git config --global)"

    @staticmethod
    def can_apply(executor=None) -> bool:
        if executor:
            return executor.run("command -v git").returncode == 0
        import shutil
        return shutil.which("git") is not None

    @staticmethod
    def needs_sudo() -> bool:
        return False

    def _run_git(self, args: str, executor=None) -> Dict:
        """Run a git config command and return result."""
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

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        http = proxy_config.get("http_proxy", "")
        https = proxy_config.get("https_proxy", "")
        no_proxy = proxy_config.get("no_proxy", "")

        errors = []
        if http:
            r = self._run_git(f'http.proxy "{http}"', executor)
            if not r["success"]:
                errors.append(f"http.proxy: {r['output']}")
        if https:
            r = self._run_git(f'https.proxy "{https}"', executor)
            if not r["success"]:
                errors.append(f"https.proxy: {r['output']}")
        if no_proxy:
            r = self._run_git(f'http."*".noProxy "{no_proxy}"', executor)
            if not r["success"]:
                errors.append(f"noProxy: {r['output']}")

        if errors:
            return {"success": False, "message": "; ".join(errors), "details": ""}
        return {"success": True, "message": "Git proxy configured", "details": ""}

    def disable(self, executor=None) -> Dict:
        self._run_git("--unset http.proxy", executor)
        self._run_git("--unset https.proxy", executor)
        self._run_git("--unset http.*.noProxy", executor)
        return {"success": True, "message": "Git proxy disabled", "details": ""}

    def status(self, executor=None) -> Dict:
        r1 = self._run_git("--get http.proxy", executor)
        r2 = self._run_git("--get https.proxy", executor)
        proxy = r1["output"] or r2["output"] or None
        return {
            "enabled": bool(r1["output"] or r2["output"]),
            "proxy": proxy,
            "config_file": "~/.gitconfig",
            "notes": "",
        }
