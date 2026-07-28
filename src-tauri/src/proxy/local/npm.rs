use super::*;
use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};

pub struct NpmLocalModule;

impl NpmLocalModule {
    pub fn new() -> Self {
        Self
    }

    pub fn name(&self) -> &'static str {
        "npm_local"
    }

    pub fn description(&self) -> &'static str {
        "npm package manager proxy (Windows)"
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
        tool_exists("npm")
    }

    pub fn status(&self) -> ProxyStatus {
        let proxy = npm_config_get("proxy");
        let https = npm_config_get("https-proxy");
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

fn npm_config_get(key: &str) -> String {
    let (_, out) = run_cmd("npm", &["config", "get", key]);
    out
}

fn npm_config_set(key: &str, val: &str) -> bool {
    run_cmd("npm", &["config", "set", key, val]).0
}

fn npm_config_delete(key: &str) {
    run_cmd("npm", &["config", "delete", key]);
}
