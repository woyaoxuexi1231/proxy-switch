use crate::models::{AuthMode, Server};
use ssh2::Session;
use std::io::Read;
use std::net::TcpStream;
use std::sync::Mutex;
use std::time::Duration;

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
        session
            .handshake()
            .map_err(|e| format!("SSH handshake failed: {}", e))?;

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
