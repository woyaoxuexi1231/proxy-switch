"""System environment proxy backend.

Configures /etc/environment and /etc/profile.d/proxy.sh.
"""

from typing import Dict, Optional

from .base import Backend


class SystemEnvBackend(Backend):

    ENV_FILE = "/etc/environment"
    PROFILE_FILE = "/etc/profile.d/proxy-switch.sh"

    @staticmethod
    def name() -> str:
        return "system_env"

    @staticmethod
    def description() -> str:
        return "System environment variables (/etc/environment, /etc/profile.d)"

    @staticmethod
    def can_apply(executor=None) -> bool:
        return True  # Every Linux system has /etc/environment

    @staticmethod
    def needs_sudo() -> bool:
        return True

    def _env_content(self, proxy_config: Dict[str, str]) -> str:
        """Generate /etc/environment format (KEY=VALUE, no export)."""
        lines = ["# Managed by proxy-switch"]
        for key in ("http_proxy", "https_proxy", "ftp_proxy", "no_proxy"):
            val = proxy_config.get(key, "")
            if val:
                lines.append(f'{key}="{val}"')
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "FTP_PROXY", "NO_PROXY"):
            lower_key = key.lower()
            val = proxy_config.get(lower_key, "")
            if not val:
                val = proxy_config.get(key.lower(), "")
            if val:
                lines.append(f'{key}="{val}"')
        return "\n".join(lines) + "\n"

    def _profile_content(self, proxy_config: Dict[str, str]) -> str:
        """Generate shell profile format (export KEY=value)."""
        lines = ["# Managed by proxy-switch", ""]
        for key in ("http_proxy", "https_proxy", "ftp_proxy", "no_proxy"):
            val = proxy_config.get(key, "")
            if val:
                lines.append(f'export {key}="{val}"')
        for key in ("HTTP_PROXY", "HTTPS_PROXY", "FTP_PROXY", "NO_PROXY"):
            lower_key = key.lower()
            val = proxy_config.get(lower_key, "")
            if not val:
                val = proxy_config.get(key.lower(), "")
            if val:
                lines.append(f'export {key}="{val}"')
        lines.append("")
        return "\n".join(lines)

    def enable(self, proxy_config: Dict[str, str], executor=None) -> Dict:
        env_content = self._env_content(proxy_config)
        profile_content = self._profile_content(proxy_config)

        if executor:
            r1 = executor.write(self.ENV_FILE, env_content, sudo=True)
            r2 = executor.write(self.PROFILE_FILE, profile_content, sudo=True)
            errors = []
            if r1.returncode != 0:
                errors.append(f"env: {r1.stderr}")
            if r2.returncode != 0:
                errors.append(f"profile: {r2.stderr}")
            if errors:
                return {"success": False, "message": "; ".join(errors), "details": ""}
            return {"success": True, "message": "System proxy configured", "details": ""}
        else:
            import os
            import tempfile
            import subprocess
            errors = []
            for path, content in [(self.ENV_FILE, env_content),
                                  (self.PROFILE_FILE, profile_content)]:
                try:
                    with tempfile.NamedTemporaryFile(mode="w", delete=False) as tf:
                        tf.write(content)
                        tf.flush()
                    r = subprocess.run(["sudo", "cp", tf.name, path],
                                       capture_output=True, text=True)
                    os.unlink(tf.name)
                    if r.returncode != 0:
                        errors.append(f"{path}: {r.stderr}")
                except Exception as e:
                    errors.append(f"{path}: {e}")
            if errors:
                return {"success": False, "message": "; ".join(errors), "details": ""}
            return {"success": True, "message": "System proxy configured", "details": ""}

    def disable(self, executor=None) -> Dict:
        if executor:
            executor.run(f"sudo rm -f {self.PROFILE_FILE}")
            # Clear proxy lines from /etc/environment
            executor.run(f"sudo sed -i '/proxy-switch/,+2d' {self.ENV_FILE}")
            executor.run(f"sudo sed -i '/_proxy=/Id' {self.ENV_FILE}")
            executor.run(f"sudo sed -i '/_PROXY=/Id' {self.ENV_FILE}")
            return {"success": True, "message": "System proxy disabled", "details": ""}
        else:
            import subprocess
            subprocess.run(["sudo", "rm", "-f", self.PROFILE_FILE])
            subprocess.run(["sudo", "sed", "-i", "/_proxy=/Id", self.ENV_FILE])
            subprocess.run(["sudo", "sed", "-i", "/_PROXY=/Id", self.ENV_FILE])
            return {"success": True, "message": "System proxy disabled", "details": ""}

    def status(self, executor=None) -> Dict:
        if executor:
            r = executor.run(f"cat {self.ENV_FILE} 2>/dev/null || echo ''")
            content = r.stdout
        else:
            try:
                with open(self.ENV_FILE) as f:
                    content = f.read()
            except (FileNotFoundError, PermissionError):
                content = ""

        enabled = "http_proxy" in content or "HTTP_PROXY" in content
        proxy = None
        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("http_proxy=") or line.startswith("HTTP_PROXY="):
                proxy = line.split("=", 1)[1].strip('"').strip("'")
                break
        return {
            "enabled": enabled,
            "proxy": proxy,
            "config_file": f"{self.ENV_FILE}, {self.PROFILE_FILE}",
            "notes": "Run 'source /etc/profile.d/proxy-switch.sh' or re-login to apply",
        }
