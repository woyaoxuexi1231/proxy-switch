"""SSH connection management using Paramiko.

Handles authentication (key and password), connection pooling,
keepalive, and reconnection logic.
"""

import os
import socket
import threading
import time
from typing import Optional, Dict, Any

import paramiko
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import (
    SSHException,
    AuthenticationException,
    NoValidConnectionsError,
)

from ..core.models import Server


# Global connection pool: {(host, port, user): SSHConnection}
_connection_pool: Dict[str, "SSHConnection"] = {}
_pool_lock = threading.Lock()

DEFAULT_TIMEOUT = 15
KEEPALIVE_INTERVAL = 30


class SSHConnectionError(Exception):
    """Raised when SSH connection fails."""
    pass


class SSHConnection:
    """Manages a single SSH connection to a server."""

    def __init__(self, server: Server, timeout: int = DEFAULT_TIMEOUT):
        self.server = server
        self.timeout = timeout
        self._client: Optional[SSHClient] = None
        self._sftp: Optional[paramiko.SFTPClient] = None
        self._connected = False
        self._lock = threading.Lock()

    # ── Connection / Disconnection ──────────────────────────────────────

    def connect(self) -> bool:
        """Establish SSH connection. Returns True on success."""
        with self._lock:
            if self._connected and self._client:
                try:
                    transport = self._client.get_transport()
                    if transport and transport.is_active():
                        return True
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

                # Set up keepalive
                transport = self._client.get_transport()
                if transport:
                    transport.set_keepalive(KEEPALIVE_INTERVAL)

                self._connected = True
                return True

            except (AuthenticationException,
                    NoValidConnectionsError,
                    socket.timeout,
                    SSHException, OSError) as e:
                self._cleanup()
                raise SSHConnectionError(f"Failed to connect to "
                    f"{self.server.user}@{self.server.host}:{self.server.port} - {e}")

    def disconnect(self) -> None:
        """Close the SSH connection."""
        with self._lock:
            self._cleanup()

    def _cleanup(self) -> None:
        """Internal cleanup without lock."""
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

    # ── Command Execution ────────────────────────────────────────────────

    class CommandResult:
        """Result of a remote command execution."""
        def __init__(self, returncode: int, stdout: str, stderr: str):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

        def __bool__(self):
            return self.returncode == 0

    def run(self, command: str, timeout: int = 30,
            sudo: bool = False, password: str = "") -> "CommandResult":
        """Execute a command on the remote server.

        Args:
            command: Shell command to execute.
            timeout: Command timeout in seconds.
            sudo: Whether to run with sudo.
            password: Password for sudo if needed (use -S flag).

        Returns:
            CommandResult with returncode, stdout, stderr.
        """
        if sudo:
            if password:
                # Use sudo with password via stdin
                command = f'echo "{password}" | sudo -S bash -c {self._quote(command)}'
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
            channel.get_pty()  # Get a pseudo-terminal for sudo
            channel.exec_command(command)

            stdout_data = b""
            stderr_data = b""

            # Read output
            while not channel.exit_status_ready():
                if channel.recv_ready():
                    stdout_data += channel.recv(4096)
                if channel.recv_stderr_ready():
                    stderr_data += channel.recv_stderr(4096)
                time.sleep(0.05)

            # Read remaining
            while channel.recv_ready():
                stdout_data += channel.recv(4096)
            while channel.recv_stderr_ready():
                stderr_data += channel.recv_stderr(4096)

            returncode = channel.recv_exit_status()
            stdout = stdout_data.decode("utf-8", errors="replace").strip()
            stderr = stderr_data.decode("utf-8", errors="replace").strip()

            channel.close()
            return self.CommandResult(returncode, stdout, stderr)

        except socket.timeout:
            return self.CommandResult(-1, "", "Command timed out")
        except SSHException as e:
            return self.CommandResult(-1, "", str(e))

    # ── File Operations ──────────────────────────────────────────────────

    def read(self, remote_path: str) -> "CommandResult":
        """Read a remote file's contents."""
        return self.run(f"cat {remote_path} 2>/dev/null || echo ''")

    def write(self, remote_path: str, content: str,
              sudo: bool = False) -> "CommandResult":
        """Write content to a remote file.

        Uses SFTP for user files, or sudo tee for system files.
        """
        if sudo:
            # Use a temp file approach for sudo writes
            import base64
            encoded = base64.b64encode(content.encode()).decode()
            cmds = [
                f"echo '{encoded}' | base64 -d | sudo tee {remote_path} > /dev/null",
                f"sudo chmod 644 {remote_path}",
            ]
            for cmd in cmds:
                result = self.run(cmd)
                if result.returncode != 0:
                    return result
            return self.CommandResult(0, "", "")
        else:
            try:
                # Ensure parent directory exists
                dirname = os.path.dirname(remote_path)
                if dirname:
                    self.run(f"mkdir -p {dirname}")

                # Write via SFTP
                sftp = self.sftp
                with sftp.open(remote_path, "w") as f:
                    f.write(content)
                return self.CommandResult(0, "", "")
            except (OSError, SSHException, IOError) as e:
                # Fallback to echo method
                escaped = content.replace("'", "'\\''")
                return self.run(
                    f"mkdir -p {os.path.dirname(remote_path)} && "
                    f"cat > {remote_path} << 'EOF'\n{content}\nEOF"
                )

    def upload(self, local_path: str, remote_path: str) -> "CommandResult":
        """Upload a local file to remote path."""
        try:
            sftp = self.sftp
            dirname = os.path.dirname(remote_path)
            if dirname:
                self.run(f"mkdir -p {dirname}")
            sftp.put(local_path, remote_path)
            return self.CommandResult(0, "", "")
        except (OSError, SSHException, IOError) as e:
            return self.CommandResult(-1, "", str(e))

    def download(self, remote_path: str, local_path: str) -> "CommandResult":
        """Download a remote file to local path."""
        try:
            sftp = self.sftp
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            sftp.get(remote_path, local_path)
            return self.CommandResult(0, "", "")
        except (OSError, SSHException, IOError) as e:
            return self.CommandResult(-1, "", str(e))

    # ── Utilities ────────────────────────────────────────────────────────

    def _quote(self, s: str) -> str:
        """Shell-quote a string for embedding in a command."""
        escaped = s.replace("'", "'\\''")
        return f"'{escaped}'"

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()

    def __del__(self):
        self._cleanup()


# ── Connection Pool ─────────────────────────────────────────────────────

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
