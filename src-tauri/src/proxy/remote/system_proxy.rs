use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::ProxyModule;
use crate::ssh::connection::SshSession;

const ENV_FILE: &str = "/etc/environment";
const PROFILE_FILE: &str = "/etc/profile.d/proxy-switch.sh";

const PROXY_KEYS_LOWER: &[&str] = &["http_proxy", "https_proxy", "ftp_proxy", "no_proxy"];
const PROXY_KEYS_UPPER: &[&str] = &["HTTP_PROXY", "HTTPS_PROXY", "FTP_PROXY", "NO_PROXY"];

pub struct SystemProxyModule;

impl ProxyModule for SystemProxyModule {
    fn config_files(&self) -> Vec<String> {
        vec![ENV_FILE.into(), PROFILE_FILE.into()]
    }
    fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Edit system proxy config".into(),
            vec![
                format!("# Edit {}", ENV_FILE),
                format!("sudo nano {}", ENV_FILE),
                String::new(),
                "# Add these lines:".to_string(),
                "http_proxy=\"http://your-proxy:port\"".into(),
                "https_proxy=\"http://your-proxy:port\"".into(),
                "HTTP_PROXY=\"http://your-proxy:port\"".into(),
                "HTTPS_PROXY=\"http://your-proxy:port\"".into(),
                "no_proxy=\"localhost,127.0.0.1,::1\"".into(),
                "NO_PROXY=\"localhost,127.0.0.1,::1\"".into(),
                String::new(),
                "# Then apply:".to_string(),
                format!("source {}", PROFILE_FILE),
                "# or re-login".to_string(),
            ],
        )]
    }
    fn detect(&self, _session: &SshSession) -> bool {
        true
    }
    fn status(&self, session: &SshSession) -> ProxyStatus {
        let content = session.read_file(ENV_FILE);
        let enabled = content.contains("http_proxy=") || content.contains("HTTP_PROXY=");
        let mut proxy = None;
        for line in content.lines() {
            let trimmed = line.trim();
            if trimmed.starts_with("http_proxy=") || trimmed.starts_with("HTTP_PROXY=") {
                if let Some(val) = trimmed.splitn(2, '=').nth(1) {
                    proxy = Some(val.trim_matches('"').trim_matches('\'').to_string());
                }
                break;
            }
        }
        ProxyStatus {
            component: ComponentId::SystemProxy,
            installed: true,
            enabled,
            current_http_proxy: proxy.clone(),
            current_https_proxy: proxy,
            current_no_proxy: None,
            current_mirror: None,
            config_files: self.config_files(),
            manual_setup_steps: self
                .manual_steps()
                .into_iter()
                .map(|(t, c)| ManualStep {
                    title: t,
                    commands: c,
                })
                .collect(),
        }
    }
    fn enable(&self, session: &SshSession, config: &ProxyConfig) -> OpResult {
        if !session.has_sudo() {
            return OpResult::err("Sudo access required. Configure passwordless sudo on the remote server.");
        }
        let env_content = update_env_lines(&session.read_file(ENV_FILE), config);
        if let Err(e) = session.write_file(ENV_FILE, &env_content, true) {
            return OpResult::err(format!("Failed to write {}: {}", ENV_FILE, e));
        }
        let profile_content = make_profile_content(config);
        if let Err(e) = session.write_file(PROFILE_FILE, &profile_content, true) {
            return OpResult::err(format!("Failed to write {}: {}", PROFILE_FILE, e));
        }
        OpResult::ok("System proxy configured")
    }
    fn disable(&self, session: &SshSession) -> OpResult {
        if !session.has_sudo() {
            return OpResult::err("Sudo access required.");
        }
        let env_content = update_env_lines(&session.read_file(ENV_FILE), &ProxyConfig::default());
        session.write_file(ENV_FILE, &env_content, true).ok();
        session.run(&format!("sudo rm -f {}", PROFILE_FILE), 10);
        OpResult::ok("System proxy disabled")
    }
}

fn update_env_lines(existing: &str, config: &ProxyConfig) -> String {
    let proxy_prefixes: Vec<&str> = PROXY_KEYS_LOWER
        .iter()
        .map(|k| *k)
        .chain(PROXY_KEYS_UPPER.iter().map(|k| *k))
        .collect();
    let keep: Vec<&str> = existing
        .lines()
        .filter(|line| {
            let trimmed = line.trim();
            if trimmed.starts_with("# Managed by proxy-switch") {
                return false;
            }
            for prefix in &proxy_prefixes {
                if trimmed.starts_with(&format!("{}=", prefix)) {
                    return false;
                }
            }
            true
        })
        .collect();
    let mut new_lines: Vec<String> = keep.iter().map(|s| s.to_string()).collect();
    while new_lines.last().map_or(false, |l| l.is_empty()) {
        new_lines.pop();
    }
    if !new_lines.is_empty() && !new_lines.last().unwrap().is_empty() {
        new_lines.push(String::new());
    }
    new_lines.push("# Managed by proxy-switch".into());
    for key in PROXY_KEYS_LOWER {
        let val = match *key {
            "http_proxy" => &config.http_proxy,
            "https_proxy" => &config.https_proxy,
            "ftp_proxy" => "",
            "no_proxy" => &config.no_proxy,
            _ => "",
        };
        if !val.is_empty() {
            new_lines.push(format!("{}=\"{}\"", key, val));
        }
    }
    for key in PROXY_KEYS_UPPER {
        let val = match *key {
            "HTTP_PROXY" => &config.http_proxy,
            "HTTPS_PROXY" => &config.https_proxy,
            "FTP_PROXY" => "",
            "NO_PROXY" => &config.no_proxy,
            _ => "",
        };
        if !val.is_empty() {
            new_lines.push(format!("{}=\"{}\"", key, val));
        }
    }
    new_lines.push(String::new());
    new_lines.join("\n")
}

fn make_profile_content(config: &ProxyConfig) -> String {
    let mut lines = vec!["# Managed by proxy-switch".to_string(), String::new()];
    let keys = [
        ("http_proxy", &config.http_proxy),
        ("https_proxy", &config.https_proxy),
        ("no_proxy", &config.no_proxy),
    ];
    for (key, val) in &keys {
        if !val.is_empty() {
            lines.push(format!("export {}=\"{}\"", key, val));
        }
    }
    lines.push(String::new());
    lines.join("\n")
}
