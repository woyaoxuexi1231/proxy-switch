use crate::models::{AuthMode, Server};
use ssh2::{MethodType, Session};
use std::io::Read;
use std::net::TcpStream;
use std::sync::Mutex;
use std::time::Duration;

/// 握手阶段的超时（毫秒）。握手完成后会恢复为 0（无限等待），
/// 以免影响 apt / git clone 这类长耗时命令。
const HANDSHAKE_TIMEOUT_MS: u32 = 15_000;

/// 密钥交换算法，按优先级从高到低排列。
/// 现代 OpenSSH(7.4+) 默认只提供 curve25519 / sntrup761x25519 / group16-sha512，
/// 客户端若一条都提供不出来，握手会直接以 KEX_FAILURE(-5) 失败。
const KEX_ALGORITHMS: &str = concat!(
    "curve25519-sha256,curve25519-sha256@libssh.org,",
    "ecdh-sha2-nistp256,ecdh-sha2-nistp384,ecdh-sha2-nistp521,",
    "diffie-hellman-group-exchange-sha256,diffie-hellman-group14-sha256,",
    "diffie-hellman-group16-sha512,diffie-hellman-group18-sha512,",
    "diffie-hellman-group-exchange-sha1,diffie-hellman-group14-sha1"
);

/// 主机密钥算法，按优先级从高到低排列。
/// Ubuntu 22.04+ 默认只生成 ssh-ed25519 / rsa-sha2 主机密钥，
/// 不支持这些类型的客户端同样会在 KEX 阶段被拒。
const HOSTKEY_ALGORITHMS: &str = concat!(
    "ssh-ed25519,rsa-sha2-512,rsa-sha2-256,",
    "ecdsa-sha2-nistp256,ecdsa-sha2-nistp384,ecdsa-sha2-nistp521,",
    "ssh-rsa,ssh-dss"
);

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

        let mut session = Session::new().map_err(|e| format!("Failed to create SSH session: {}", e))?;
        session.set_tcp_stream(tcp);
        session.set_timeout(HANDSHAKE_TIMEOUT_MS);

        // 显式声明算法优先级：列表里当前加密后端不支持的算法会被 libssh2 忽略，
        // 全部不支持时自动回退到默认算法集，因此这里无副作用。
        let _ = session.method_pref(MethodType::Kex, KEX_ALGORITHMS);
        let _ = session.method_pref(MethodType::HostKey, HOSTKEY_ALGORITHMS);

        session.handshake().map_err(|e| {
            // -5 = LIBSSH2_ERROR_KEX_FAILURE，客户端与服务器没有共同可用的算法。
            if let ssh2::ErrorCode::Session(-5) = e.code() {
                format!(
                    "SSH handshake failed: {} — no common KEX/HostKey algorithm with the server. \
                     Verify the port is really SSH and the server offers curve25519-sha256, \
                     ecdh-sha2-nistp256, rsa-sha2-256 or ssh-rsa",
                    e
                )
            } else {
                format!("SSH handshake failed: {}", e)
            }
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
