use super::*;
use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use std::fs;

pub struct NpmLocalModule;

impl NpmLocalModule {
    pub fn new() -> Self {
        Self
    }

    pub fn config_files(&self) -> Vec<String> {
        vec!["%USERPROFILE%\\.npmrc".into()]
    }

    pub fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Configure npm proxy on Windows".into(),
            vec![
                "npm config set proxy http://your-proxy:port".into(),
                "npm config set https-proxy http://your-proxy:port".into(),
                String::new(),
                "# To remove:".into(),
                "npm config delete proxy".into(),
                "npm config delete https-proxy".into(),
                String::new(),
                "# Config file:".to_string(),
                "%USERPROFILE%\\.npmrc".into(),
            ],
        )]
    }

    pub fn detect(&self) -> bool {
        tool_installed("npm")
    }

    pub fn status(&self) -> ProxyStatus {
        let (proxy, https) = read_npmrc_proxy();
        ProxyStatus {
            component: ComponentId::NpmLocal,
            installed: self.detect(),
            enabled: !proxy.is_empty() || !https.is_empty(),
            current_http_proxy: if proxy.is_empty() { None } else { Some(proxy.clone()) },
            current_https_proxy: if https.is_empty() { None } else { Some(https) },
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

    pub fn enable(&self, config: &ProxyConfig) -> OpResult {
        let mut errors = Vec::new();
        if !config.http_proxy.is_empty() {
            if !npm_config_set("proxy", &config.http_proxy) {
                errors.push("proxy");
            }
        }
        if !config.https_proxy.is_empty() {
            if !npm_config_set("https-proxy", &config.https_proxy) {
                errors.push("https-proxy");
            }
        }
        if errors.is_empty() {
            OpResult::ok("npm proxy configured")
        } else {
            OpResult::err(format!("Failed to set: {}", errors.join(", ")))
        }
    }

    pub fn disable(&self) -> OpResult {
        npm_config_delete("proxy");
        npm_config_delete("https-proxy");
        OpResult::ok("npm proxy disabled")
    }
}

// ── Direct .npmrc parsing (zero process spawn) ─────────────────────────────

fn read_npmrc_proxy() -> (String, String) {
    let path = match dirs::home_dir() {
        Some(h) => h.join(".npmrc"),
        None => return (String::new(), String::new()),
    };
    let content = match fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return (String::new(), String::new()),
    };
    let mut proxy = String::new();
    let mut https_proxy = String::new();
    for line in content.lines() {
        let trimmed = line.trim();
        // Skip comments and empty lines
        if trimmed.is_empty() || trimmed.starts_with('#') || trimmed.starts_with(';') {
            continue;
        }
        if let Some(eq_pos) = trimmed.find('=') {
            let key = trimmed[..eq_pos].trim();
            let val = trimmed[eq_pos + 1..].trim();
            match key {
                "proxy" => proxy = val.to_string(),
                "https-proxy" => https_proxy = val.to_string(),
                _ => {}
            }
        }
    }
    (proxy, https_proxy)
}

// ── Command-line operations (for enable/disable) ───────────────────────────

fn npm_config_set(key: &str, val: &str) -> bool {
    run_cmd("npm", &["config", "set", key, val]).0
}

fn npm_config_delete(key: &str) {
    run_cmd("npm", &["config", "delete", key]);
}
