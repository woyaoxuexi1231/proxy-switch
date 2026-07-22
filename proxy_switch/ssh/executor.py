"""Remote command executor.

Provides a higher-level interface for running commands and managing
configurations on remote servers. Wraps SSHConnection with convenience
methods used by backends.
"""

from typing import List, Optional, Dict, Any, Callable

from .connection import SSHConnection, SSHConnectionError, CommandResult
from ..core.models import Server


class Executor:
    """High-level executor for remote proxy operations.

    This is the main interface backends use when operating remotely.
    It handles connection lifecycle, sudo, and file operations.
    """

    def __init__(self, server: Server):
        self.server = server
        self._conn: Optional[SSHConnection] = None
        self._connected = False
        self.sudo_password: str = ""

    # ── Connection ──────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Establish SSH connection."""
        self._conn = SSHConnection(self.server)
        try:
            self._conn.connect()
            self._connected = True
            return True
        except SSHConnectionError as e:
            raise SSHConnectionError(str(e))

    def disconnect(self) -> None:
        """Close the connection."""
        if self._conn:
            self._conn.disconnect()
            self._conn = None
        self._connected = False

    def ensure_connected(self) -> None:
        """Ensure connection is active."""
        if not self._connected or not self._conn:
            self.connect()
        else:
            self._conn.ensure_connected()

    @property
    def conn(self) -> SSHConnection:
        """Get the underlying SSH connection."""
        self.ensure_connected()
        if not self._conn:
            raise SSHConnectionError("Not connected")
        return self._conn

    # ── Command Execution ───────────────────────────────────────────────

    def run(self, command: str, sudo: bool = False) -> CommandResult:
        """Execute a command on the remote server."""
        return self.conn.run(command, sudo=sudo, password=self.sudo_password)

    def read(self, remote_path: str) -> CommandResult:
        """Read contents of a remote file."""
        return self.conn.read(remote_path)

    def write(self, remote_path: str, content: str, sudo: bool = False) -> CommandResult:
        """Write content to a remote file."""
        return self.conn.write(remote_path, content, sudo=sudo)

    def upload(self, local_path: str, remote_path: str) -> CommandResult:
        """Upload a local file to remote path."""
        return self.conn.upload(local_path, remote_path)

    def download(self, remote_path: str, local_path: str) -> CommandResult:
        """Download a remote file to local path."""
        return self.conn.download(remote_path, local_path)

    # ── Utility Methods ─────────────────────────────────────────────────

    def tool_exists(self, tool_name: str) -> bool:
        """Check if a tool is installed on the remote server."""
        result = self.run(f"command -v {tool_name} 2>/dev/null || which {tool_name} 2>/dev/null")
        return bool(result.stdout.strip())

    def detect_installed_tools(self) -> Dict[str, bool]:
        """Detect which proxy-relevant tools are installed."""
        tools = [
            "apt-get", "git", "docker", "mvn", "gradle",
            "npm", "pip3", "pip", "curl", "wget", "snap",
        ]
        result = {}
        for tool in tools:
            result[tool] = self.tool_exists(tool)
        return result

    def get_os_info(self) -> Dict[str, str]:
        """Get OS information from the remote server."""
        info = {}
        r = self.run("cat /etc/os-release 2>/dev/null | head -5")
        for line in r.stdout.split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                info[k.strip()] = v.strip().strip('"')
        if not info:
            r = self.run("lsb_release -d 2>/dev/null || uname -a")
            info["PRETTY_NAME"] = r.stdout.split("\n")[0]
        return info

    def has_sudo(self) -> bool:
        """Check if current user has sudo access (passwordless or with password)."""
        r = self.run("sudo -n true 2>&1", sudo=False)
        if r.returncode == 0:
            return True
        # Check if we have a password configured
        if self.sudo_password:
            r = self.run("sudo -S true 2>&1", sudo=True)
            return r.returncode == 0
        return False

    # ── Lifecycle ───────────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
