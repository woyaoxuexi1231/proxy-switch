use crate::models::{AuthMode, Server};
use ssh2::Session;
use std::io::Read;
use std::net::TcpStream;
use std::sync::Mutex;
use std::time::Duration;

/// 握手阶段的超时（毫秒）。握手完成后会恢复为 0（无限等待），
/// 以免影响 apt / git clone 这类长耗时命令。
const HANDSHAKE_TIMEOUT_MS: u32 = 15_000;

/// 等待对端 banner 的时间。OpenSSH 在 accept 后会立即发送 banner，
/// 正常情况下瞬间就能读到；超时说明对端大概率不是 SSH 服务。
const BANNER_PEEK_TIMEOUT: Duration = Duration::from_secs(3);

pub struct SshSession {
    pub session: Session,
    pub server_name: String,
    #[allow(dead_code)]
    connected_at: std::time::Instant,
}

pub struct CommandResult {
    pub exit_code: i32,
    pub stdout: String,
    pub stderr: String,
}

impl CommandResult {
}

impl SshSession {
    pub fn connect(server: &Server, timeout_secs: u64) -> Result<Self, String> {
        let addr = format!("{}:{}", server.host, server.port);
        let tcp = TcpStream::connect_timeout(
            &addr
                .parse()
                .map_err(|e| format!("Invalid address: {}", e))?,
            Duration::from_secs(timeout_secs),
        )
        .map_err(|e| format!("TCP connection failed: {}", e))?;
        tcp.set_read_timeout(Some(Duration::from_secs(30)))
            .map_err(|e| format!("Failed to set timeout: {}", e))?;

        // 先偷看一眼对端 banner（peek 不消费数据，libssh2 稍后照常读取），
        // 握手失败时能据此判断对端到底是不是 SSH 服务、是什么版本。
        let server_banner = peek_server_banner(&tcp);

        let mut session = Session::new().map_err(|e| format!("Failed to create SSH session: {}", e))?;
        session.set_tcp_stream(tcp);
        session.set_timeout(HANDSHAKE_TIMEOUT_MS);

        // 算法清单交给 libssh2 默认值（OpenSSL 后端下包含 curve25519 / ed25519 / ecdsa /
        // rsa-sha2 全套现代算法），不做人为收窄，以保证与服务端的最大交集。
        session.handshake().map_err(|e| {
            let hint = if server_banner.is_empty() {
                "the remote sent no banner within 3s — this port is probably not an SSH service, \
                 double-check the host and port"
                    .to_string()
            } else {
                format!("remote banner: \"{}\"", server_banner)
            };
            format!("SSH handshake failed: {} ({})", e, hint)
        })?;
        // 握手已完成，后续命令不设上限，避免长耗时操作被误判超时。
        session.set_timeout(0);

        match &server.auth_mode {
            AuthMode::Key => {
                let key_path = server
                    .ssh_key_path
                    .as_deref()
                    .unwrap_or("~/.ssh/id_rsa");
                let expanded = shellexpand::tilde(key_path).to_string();
                session
                    .userauth_pubkey_file(&server.user, None, std::path::Path::new(&expanded), None)
                    .map_err(|e| format!("Key auth failed ({}): {}", expanded, e))?;
            }
            AuthMode::Password => {
                let pw = server.password.as_deref().unwrap_or("");
                session
                    .userauth_password(&server.user, pw)
                    .map_err(|e| format!("Password auth failed: {}", e))?;
            }
        }

        if !session.authenticated() {
            return Err("Authentication failed".into());
        }

        Ok(Self {
            session,
            server_name: server.name.clone(),
            connected_at: std::time::Instant::now(),
        })
    }

    pub fn run(&self, cmd: &str, _timeout_secs: u64) -> CommandResult {
        let mut channel = match self.session.channel_session() {
            Ok(c) => c,
            Err(e) => {
                return CommandResult {
                    exit_code: -1,
                    stdout: String::new(),
                    stderr: format!("Failed to open channel: {}", e),
                }
            }
        };
        if let Err(e) = channel.exec(cmd) {
            return CommandResult {
                exit_code: -1,
                stdout: String::new(),
                stderr: format!("Exec failed: {}", e),
            };
        }

        let mut stdout = String::new();
        let mut stderr = String::new();
        channel.read_to_string(&mut stdout).ok();
        channel.stderr().read_to_string(&mut stderr).ok();
        channel.wait_close().ok();

        let exit_code = channel.exit_status().unwrap_or(-1);

        CommandResult {
            exit_code,
            stdout: stdout.trim().to_string(),
            stderr: stderr.trim().to_string(),
        }
    }

    pub fn read_file(&self, path: &str) -> String {
        let cmd = format!("cat '{}' 2>/dev/null || echo ''", path);
        self.run(&cmd, 10).stdout
    }

    pub fn write_file(&self, path: &str, content: &str, sudo: bool) -> Result<(), String> {
        if sudo {
            use base64::Engine;
            let encoded = base64::engine::general_purpose::STANDARD.encode(content);
            // Ensure the parent directory exists first — sudo tee won't create it.
            // e.g. /etc/systemd/system/docker.service.d doesn't exist on a fresh
            // Docker install, so writes would fail without this mkdir.
            let mkdir = std::path::Path::new(path)
                .parent()
                .map(|p| p.to_string_lossy().to_string())
                .filter(|d| !d.is_empty() && d != "/")
                .map(|d| format!("sudo mkdir -p '{}' && ", d))
                .unwrap_or_default();
            let cmd = format!(
                "{}echo '{}' | base64 -d | sudo tee '{}' > /dev/null && sudo chmod 644 '{}'",
                mkdir, encoded, path, path
            );
            let result = self.run(&cmd, 15);
            if result.exit_code != 0 {
                return Err(format!("Failed to write {}: {}", path, result.stderr));
            }
        } else {
            self.ensure_dir(path)?;
            let sftp = self
                .session
                .sftp()
                .map_err(|e| format!("SFTP error: {}", e))?;
            let file = sftp
                .create(std::path::Path::new(path))
                .map_err(|e| format!("Failed to create {}: {}", path, e))?;
            use std::io::Write;
            let mut file = file;
            file.write_all(content.as_bytes())
                .map_err(|e| format!("Failed to write {}: {}", path, e))?;
        }
        Ok(())
    }

    fn ensure_dir(&self, path: &str) -> Result<(), String> {
        if let Some(parent) = std::path::Path::new(path).parent() {
            let dir = parent.to_string_lossy();
            if !dir.is_empty() && dir != "/" {
                self.run(&format!("mkdir -p '{}'", dir), 10);
            }
        }
        Ok(())
    }

    pub fn tool_exists(&self, tool: &str) -> bool {
        let cmd = format!(
            "command -v {} 2>/dev/null || which {} 2>/dev/null",
            tool, tool
        );
        let result = self.run(&cmd, 5);
        !result.stdout.is_empty()
    }

    pub fn has_sudo(&self) -> bool {
        let result = self.run("sudo -n true 2>&1", 5);
        result.exit_code == 0
    }

    pub fn ensure_connected(&self) -> bool {
        self.session.authenticated()
    }
}

// ── Banner probe ────────────────────────────────────────────────────────────

/// 在不消费数据的前提下读取对端返回的第一行 banner。
/// 失败或超时返回空串，不影响后续握手。
fn peek_server_banner(tcp: &TcpStream) -> String {
    let prev_timeout = tcp.read_timeout().ok().flatten();
    let _ = tcp.set_read_timeout(Some(BANNER_PEEK_TIMEOUT));
    let mut buf = [0u8; 256];
    let result = tcp.peek(&mut buf);
    let _ = tcp.set_read_timeout(prev_timeout);

    match result {
        Ok(n) if n > 0 => {
            let text = String::from_utf8_lossy(&buf[..n]).into_owned();
            text.lines().next().unwrap_or("").trim_end().to_string()
        }
        _ => String::new(),
    }
}

// ── Connection Pool ─────────────────────────────────────────────────────────

pub struct ConnectionPool {
    pub current: Mutex<Option<SshSession>>,
}

impl ConnectionPool {
    pub fn new() -> Self {
        Self {
            current: Mutex::new(None),
        }
    }

    pub fn with_session<F, R>(&self, f: F) -> Result<R, String>
    where
        F: FnOnce(&SshSession) -> Result<R, String>,
    {
        let guard = self
            .current
            .lock()
            .map_err(|e| format!("Lock error: {}", e))?;
        match guard.as_ref() {
            Some(session) => {
                if session.ensure_connected() {
                    f(session)
                } else {
                    Err("SSH connection lost. Please reconnect.".into())
                }
            }
            None => Err("Not connected to any server. Connect first.".into()),
        }
    }

    pub fn disconnect(&self) {
        if let Ok(mut guard) = self.current.lock() {
            *guard = None;
        }
    }

    pub fn state(&self) -> (bool, Option<String>, Option<String>) {
        match self.current.lock() {
            Ok(guard) => match guard.as_ref() {
                Some(s) if s.ensure_connected() => {
                    (true, Some(s.server_name.clone()), None)
                }
                Some(_) => (false, None, Some("Connection lost".into())),
                None => (false, None, None),
            },
            Err(_) => (false, None, Some("Internal lock error".into())),
        }
    }
}
