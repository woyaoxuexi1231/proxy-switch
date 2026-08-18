use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::ProxyModule;
use crate::ssh::connection::SshSession;

const APT_CONF: &str = "/etc/apt/apt.conf.d/proxy.conf";

pub struct AptModule;

impl ProxyModule for AptModule {
    fn config_files(&self) -> Vec<String> {
        vec![APT_CONF.into()]
    }
    fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Configure APT proxy".into(),
            vec![
                format!("sudo nano {}", APT_CONF),
                String::new(),
                "# Add these lines:".to_string(),
                "Acquire::http::Proxy \"http://your-proxy:port\";".into(),
                "Acquire::https::Proxy \"http://your-proxy:port\";".into(),
                "Acquire::ftp::Proxy \"http://your-proxy:port\";".into(),
            ],
        )]
    }
    fn detect(&self, session: &SshSession) -> bool {
        session.tool_exists("apt-get") || session.tool_exists("apt")
    }
    fn status(&self, session: &SshSession) -> ProxyStatus {
        let content = session.read_file(APT_CONF);
        let http = apt_proxy_value(&content, "Acquire::http::Proxy");
        let https = apt_proxy_value(&content, "Acquire::https::Proxy");
        let no_proxy = apt_proxy_value(&content, "Acquire::http::NoProxy");
        let enabled = http.is_some() || https.is_some();
        ProxyStatus {
            component: ComponentId::Apt,
            installed: self.detect(session),
            enabled,
            current_http_proxy: http,
            current_https_proxy: https,
            current_no_proxy: no_proxy,
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
            return OpResult::err("Sudo access required.");
        }
        let content = proxy_content(config);
        match session.write_file(APT_CONF, &content, true) {
            Ok(_) => OpResult::ok("APT proxy configured"),
            Err(e) => OpResult::err(format!("Failed to write {}: {}", APT_CONF, e)),
        }
    }
    fn disable(&self, session: &SshSession) -> OpResult {
        if !session.has_sudo() {
            return OpResult::err("Sudo access required.");
        }
        session.run(&format!("sudo rm -f {}", APT_CONF), 10);
        OpResult::ok("APT proxy disabled")
    }
}

fn proxy_content(config: &ProxyConfig) -> String {
    let mut lines = vec!["// Managed by proxy-switch".to_string()];
    if !config.http_proxy.is_empty() {
        lines.push(format!("Acquire::http::Proxy \"{}\";", config.http_proxy));
    }
    if !config.https_proxy.is_empty() {
        lines.push(format!("Acquire::https::Proxy \"{}\";", config.https_proxy));
    }
    if !config.no_proxy.is_empty() {
        lines.push(format!(
            "Acquire::http::NoProxy \"{}\";",
            config.no_proxy
        ));
    }
    lines.push(String::new());
    lines.join("\n")
}

fn apt_proxy_value(content: &str, key: &str) -> Option<String> {
    for line in content.lines() {
        let trimmed = line.trim();
        if trimmed.starts_with("//") || !trimmed.contains(key) {
            continue;
        }
        let re = regex::Regex::new(r#""(.*?)""#).unwrap();
        if let Some(cap) = re.captures(trimmed) {
            let val = cap[1].trim();
            if !val.is_empty() {
                return Some(val.to_string());
            }
        }
    }
    None
}
