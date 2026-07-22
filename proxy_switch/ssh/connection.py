"""SSH connection management and remote command execution.

Uses Paramiko for SSH connections with key and password authentication,
connection pooling, keepalive, and sudo-aware command execution.
"""

from __future__ import annotations

import base64
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

import paramiko
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import SSHException, AuthenticationException, NoValidConnectionsError

from ..core.models import Server

# ── Constants ──────────────────────────────────────────────────────────────

DEFAULT_TIMEOUT = 15
KEEPALIVE_INTERVAL = 30


# ── Exceptions ─────────────────────────────────────────────────────────────


class SSHConnectionError(Exception):
    """Raised when SSH connection or command execution fails."""
    pass


# ── Command Result ─────────────────────────────────────────────────────────


@dataclass
class CommandResult:
    """Result of a remote command execution."""
    returncode: int
    stdout: str = ""
    stderr: str = ""

    def __bool__(self) -> bool:
        return self.returncode == 0


# ═══════════════════════════════════════════════════════════════════════════
# SSHConnection — low-level SSH transport
# ═══════════════════════════════════════════════════════════════════════════


class SSHConnection:
    """Manages a single SSH connection to a server."""

    def __init__(self, server: Server, timeout: int = DEFAULT_TIMEOUT):
        self.server = server
        self.timeout = timeout
        self._client: Optional[SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._connected = False
        self._lock = threading.Lock()

    # ── Connection Lifecycle ───────────────────────────────────────────

    def connect(self) -> None:
        """Establish SSH connection. Raises SSHConnectionError on failure."""
        with self._lock:
            if self._connected and self._client:
                try:
                    transport = self._client.get_transport()
                    if transport and transport.is_active():
                        return
                except SSHException:
                    pass
                self._cleanup()

            self._client = SSHClient()
            self._client.set_missing_host_key_policy(AutoAddPolicy())

            try:
                connect_kwargs = {
                    "hostname": self.server.host,
                    "port": self.server.port or 22,
                    "username": self.server.user,
                    "timeout": self.timeout,
                    "compress": True,
                }

                if self.server.auth_mode == "key" and self.server.ssh_key:
                    key_path = os.path.expanduser(self.server.ssh_key)
                    if os.path.exists(key_path):
                        connect_kwargs["key_filename"] = key_path
                    else:
                        raise SSHConnectionError(f"SSH key not found: {key_path}")
                elif self.server.password:
                    connect_kwargs["password"] = self.server.password

                self._client.connect(**connect_kwargs)

                transport = self._client.get_transport()
                if transport:
                    transport.set_keepalive(KEEPALIVE_INTERVAL)

                self._connected = True

            except (AuthenticationException,
                    NoValidConnectionsError,
                    socket.timeout,
                    SSHException, OSError) as e:
                self._cleanup()
                raise SSHConnectionError(
                    f"Failed to connect to {self.server.user}@{self.server.host}:"
                    f"{self.server.port} — {e}"
                )

    def disconnect(self) -> None:
        """Close the SSH connection."""
        with self._lock:
            self._cleanup()

    def _cleanup(self) -> None:
        """Internal cleanup (caller must hold the lock)."""
        try:
            if self._sftp:
                self._sftp.close()
        except Exception:
            pass
        try:
            if self._client:
                self._client.close()
        except Exception:
            pass
        self._client = None
        self._sftp = None
        self._connected = False

    def ensure_connected(self) -> None:
        """Ensure connection is active, reconnect if needed."""
        if not self._connected or not self._client:
            self.connect()
            return
        try:
            transport = self._client.get_transport()
            if not transport or not transport.is_active():
                self.connect()
        except SSHException:
            self.connect()

    @property
    def client(self) -> SSHClient:
        """Get the underlying SSHClient, ensuring connection."""
        self.ensure_connected()
        if not self._client:
            raise SSHConnectionError("Not connected")
        return self._client

    @property
    def sftp(self) -> paramiko.SFTPClient:
        """Get an SFTP client for file transfers."""
        with self._lock:
            if not self._sftp or not self._sftp._channel:
                self._sftp = self.client.open_sftp()
            return self._sftp

    # ── Command Execution ──────────────────────────────────────────────

    def run(self, command: str, timeout: int = 30,
            sudo: bool = False, password: str = "") -> CommandResult:
        """Execute a command on the remote server.

        Args:
            command: Shell command to execute.
            timeout: Command timeout in seconds.
            sudo: Whether to prefix with sudo.
            password: Sudo password (uses -S with stdin).

        Returns:
            CommandResult with returncode, stdout, stderr.
        """
        if sudo:
            if password:
                escaped = command.replace("'", "'\\''")
                command = f'echo "{password}" | sudo -S bash -c \'{escaped}\''
            else:
                command = f"sudo {command}"

        self.ensure_connected()
        if not self._client:
            raise SSHConnectionError("Not connected")

        try:
            transport = self._client.get_transport()
            if not transport:
                raise SSHConnectionError("No transport available")

            channel = transport.open_session()
            channel.settimeout(timeout)
            channel.get_pty()
            channel.exec_command(command)

            stdout_data = b""
            stderr_data = b""
            deadline = time.time() + max(timeout, 5)

            while not channel.exit_status_ready():
                if time.time() > deadline:
                    channel.close()
                    msg = f"Command timed out after {timeout}s"
                    return CommandResult(-1, "", msg)

                if channel.recv_ready():
                    try:
                        stdout_data += channel.recv(4096)
                    except socket.timeout:
                        pass
                if channel.recv_stderr_ready():
                    try:
                        stderr_data += channel.recv_stderr(4096)
                    except socket.timeout:
                        pass

                # Detect sudo password prompt — abort fast instead of hanging
                out = stdout_data + stderr_data
                if b"password" in out.lower() and (
                    b"sudo" in out.lower() or b"su" in out.lower()
                ):
                    channel.close()
                    return CommandResult(
                        -1, "",
                        "Sudo requires a password on the remote server. "
                        "Configure passwordless sudo or set up the sudo password."
                    )

                time.sleep(0.05)

            # Drain remaining output
            while channel.recv_ready():
                stdout_data += channel.recv(4096)
            while channel.recv_stderr_ready():
                stderr_data += channel.recv_stderr(4096)

            returncode = channel.recv_exit_status()
            stdout = stdout_data.decode("utf-8", errors="replace").strip()
            stderr = stderr_data.decode("utf-8", errors="replace").strip()

            channel.close()
            return CommandResult(returncode, stdout, stderr)

        except socket.timeout:
            return CommandResult(-1, "", "Command timed out")
        except SSHException as e:
            return CommandResult(-1, "", str(e))

    # ── File Operations ────────────────────────────────────────────────

    def read(self, remote_path: str) -> CommandResult:
        """Read a remote file's contents."""
        return self.run(f"cat {remote_path} 2>/dev/null || echo ''")

    def write(self, remote_path: str, content: str,
              sudo: bool = False) -> CommandResult:
        """Write content to a remote file.

        Uses SFTP for user-writable files, or base64 + sudo tee for system files.
        """
        if sudo:
            encoded = base64.b64encode(content.encode()).decode()
            cmds = [
                f"echo '{encoded}' | base64 -d | sudo tee {remote_path} > /dev/null",
                f"sudo chmod 644 {remote_path}",
            ]
            for cmd in cmds:
                result = self.run(cmd)
                if result.returncode != 0:
                    return result
            return CommandResult(0, "", "")
        else:
            try:
                # Ensure parent directory exists
                dirname = os.path.dirname(remote_path)
                if dirname:
                    self.run(f"mkdir -p {dirname}")

                sftp = self.sftp
                with sftp.open(remote_path, "w") as f:
                    f.write(content)
                return CommandResult(0, "", "")
            except (OSError, SSHException, IOError):
                # Fallback to heredoc
                escaped = content.replace("'", "'\\''")
                return self.run(
                    f"mkdir -p {os.path.dirname(remote_path)} && "
                    f"cat > {remote_path} << 'EOF'\n{content}\nEOF"
                )

    def upload(self, local_path: str, remote_path: str) -> CommandResult:
        """Upload a local file to remote path via SFTP."""
        try:
            sftp = self.sftp
            dirname = os.path.dirname(remote_path)
            if dirname:
                self.run(f"mkdir -p {dirname}")
            sftp.put(local_path, remote_path)
            return CommandResult(0, "", "")
        except (OSError, SSHException, IOError) as e:
            return CommandResult(-1, "", str(e))

    def download(self, remote_path: str, local_path: str) -> CommandResult:
        """Download a remote file to local path via SFTP."""
        try:
            sftp = self.sftp
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            sftp.get(remote_path, local_path)
            return CommandResult(0, "", "")
        except (OSError, SSHException, IOError) as e:
            return CommandResult(-1, "", str(e))

    # ── Lifecycle ──────────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    def __del__(self):
        self._cleanup()


# ═══════════════════════════════════════════════════════════════════════════
# Executor — higher-level operations on a remote server
# ═══════════════════════════════════════════════════════════════════════════


class Executor:
    """High-level executor for remote proxy operations.

    Wraps SSHConnection with sudo handling, tool detection, and
    OS information gathering for use by feature modules.
    """

    def __init__(self, server: Server):
        self.server = server
        self._conn: Optional[SSHConnection] = None
        self._connected = False
        self.sudo_password: str = ""

    # ── Connection ─────────────────────────────────────────────────────

    def connect(self) -> None:
        """Establish SSH connection."""
        self._conn = SSHConnection(self.server)
        self._conn.connect()
        self._connected = True

    def disconnect(self) -> None:
        """Close the connection."""
        if self._conn:
            try:
                self._conn.disconnect()
            except Exception:
                pass
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

    # ── Command Execution ──────────────────────────────────────────────

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

    # ── Utility Methods ────────────────────────────────────────────────

    def tool_exists(self, tool_name: str) -> bool:
        """Check if a tool is installed on the remote server."""
        result = self.run(f"command -v {tool_name} 2>/dev/null || which {tool_name} 2>/dev/null")
        return bool(result.stdout.strip())

    def has_sudo(self) -> bool:
        """Check if current user has passwordless or configured sudo access."""
        r = self.run("sudo -n true 2>&1", sudo=False)
        if r.returncode == 0:
            return True
        if self.sudo_password:
            r = self.run("sudo -S true 2>&1", sudo=True)
            return r.returncode == 0
        return False

    # ── Lifecycle ──────────────────────────────────────────────────────

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()


# ═══════════════════════════════════════════════════════════════════════════
# Connection Pool
# ═══════════════════════════════════════════════════════════════════════════

_connection_pool: Dict[str, SSHConnection] = {}
_pool_lock = threading.Lock()


def _pool_key(server: Server) -> str:
    return f"{server.host}:{server.port}:{server.user}"


def get_connection(server: Server) -> SSHConnection:
    """Get or create a pooled SSH connection."""
    key = _pool_key(server)
    with _pool_lock:
        if key in _connection_pool:
            conn = _connection_pool[key]
            try:
                conn.ensure_connected()
                return conn
            except SSHConnectionError:
                del _connection_pool[key]

        conn = SSHConnection(server)
        conn.connect()
        _connection_pool[key] = conn
        return conn


def close_connection(server: Server) -> None:
    """Close and remove a pooled connection."""
    key = _pool_key(server)
    with _pool_lock:
        if key in _connection_pool:
            _connection_pool[key].disconnect()
            del _connection_pool[key]


def close_all_connections() -> None:
    """Close all SSH connections in the pool."""
    with _pool_lock:
        for key, conn in list(_connection_pool.items()):
            try:
                conn.disconnect()
            except Exception:
                pass
        _connection_pool.clear()
