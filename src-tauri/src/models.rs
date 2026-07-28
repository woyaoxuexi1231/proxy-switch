use serde::{Deserialize, Serialize};

// ── Server ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Server {
    pub id: String,
    pub name: String,
    pub host: String,
    pub port: u16,
    pub user: String,
    pub auth_mode: AuthMode,
    pub ssh_key_path: Option<String>,
    pub password: Option<String>,
    pub description: String,
}

impl Server {
    pub fn label(&self) -> String {
        format!("{} ({}:{})", self.name, self.host, self.port)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "lowercase")]
pub enum AuthMode {
    Key,
    Password,
}

// ── Proxy Config ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct ProxyConfig {
    pub http_proxy: String,
    pub https_proxy: String,
    pub no_proxy: String,
    pub mirror: String,
}

impl ProxyConfig {
    pub fn is_empty(&self) -> bool {
        self.http_proxy.is_empty()
            && self.https_proxy.is_empty()
            && self.no_proxy.is_empty()
            && self.mirror.is_empty()
    }

    pub fn primary_proxy(&self) -> Option<String> {
        if !self.https_proxy.is_empty() {
            Some(self.https_proxy.clone())
        } else if !self.http_proxy.is_empty() {
            Some(self.http_proxy.clone())
        } else {
            None
        }
    }
}

// ── Proxy Status ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ProxyStatus {
    pub component: ComponentId,
    pub installed: bool,
    pub enabled: bool,
    pub current_http_proxy: Option<String>,
    pub current_https_proxy: Option<String>,
    pub current_no_proxy: Option<String>,
    pub current_mirror: Option<String>,
    pub config_files: Vec<String>,
    pub manual_setup_steps: Vec<ManualStep>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ManualStep {
    pub title: String,
    pub commands: Vec<String>,
}

// ── Op Result ───────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct OpResult {
    pub success: bool,
    pub message: String,
}

impl OpResult {
    pub fn ok(msg: impl Into<String>) -> Self {
        Self {
            success: true,
            message: msg.into(),
        }
    }

    pub fn err(msg: impl Into<String>) -> Self {
        Self {
            success: false,
            message: msg.into(),
        }
    }
}

// ── Component ID ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum ComponentId {
    SystemProxy,
    Apt,
    GitRemote,
    DockerRemote,
    NpmRemote,
    MavenRemote,
    GitLocal,
    DockerLocal,
    NpmLocal,
    MavenLocal,
}

impl ComponentId {
    pub fn label(&self) -> &'static str {
        match self {
            Self::SystemProxy => "System Proxy (Remote)",
            Self::Apt => "APT (Remote)",
            Self::GitRemote => "Git (Remote)",
            Self::DockerRemote => "Docker (Remote)",
            Self::NpmRemote => "npm (Remote)",
            Self::MavenRemote => "Maven (Remote)",
            Self::GitLocal => "Git (Local)",
            Self::DockerLocal => "Docker (Local)",
            Self::NpmLocal => "npm (Local)",
            Self::MavenLocal => "Maven (Local)",
        }
    }

    pub fn is_remote(&self) -> bool {
        matches!(
            self,
            Self::SystemProxy
                | Self::Apt
                | Self::GitRemote
                | Self::DockerRemote
                | Self::NpmRemote
                | Self::MavenRemote
        )
    }

    pub fn remote_all() -> Vec<ComponentId> {
        vec![
            Self::SystemProxy,
            Self::Apt,
            Self::GitRemote,
            Self::DockerRemote,
            Self::NpmRemote,
            Self::MavenRemote,
        ]
    }

    pub fn local_all() -> Vec<ComponentId> {
        vec![
            Self::GitLocal,
            Self::DockerLocal,
            Self::NpmLocal,
            Self::MavenLocal,
        ]
    }
}

// ── Ssh State (for frontend) ────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SshState {
    pub connected: bool,
    pub server_name: Option<String>,
    pub server_host: Option<String>,
    pub error: Option<String>,
}

// ── Server Input (for add/edit dialogs) ─────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ServerInput {
    pub name: String,
    pub host: String,
    pub port: u16,
    pub user: String,
    pub auth_mode: AuthMode,
    pub ssh_key_path: Option<String>,
    pub password: Option<String>,
    pub description: String,
}
