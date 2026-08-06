use super::*;
use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use std::fs;

pub struct GitLocalModule;

impl GitLocalModule {
    pub fn new() -> Self {
        Self
    }

    pub fn config_files(&self) -> Vec<String> {
        vec!["%USERPROFILE%\\.gitconfig".into()]
    }

    pub fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Configure Git proxy on Windows".into(),
            vec![
                "git config --global http.proxy http://your-proxy:port".into(),
                "git config --global https.proxy http://your-proxy:port".into(),
                String::new(),
                "# To remove:".into(),
                "git config --global --unset http.proxy".into(),
                "git config --global --unset https.proxy".into(),
                String::new(),
                "# Config file:".to_string(),
                "%USERPROFILE%\\.gitconfig".into(),
            ],
        )]
    }

    pub fn detect(&self) -> bool {
        tool_installed("git")
    }

    pub fn status(&self) -> ProxyStatus {
        let (http, https) = read_gitconfig_proxy();
        ProxyStatus {
            component: ComponentId::GitLocal,
            installed: self.detect(),
            enabled: !http.is_empty() || !https.is_empty(),
            current_http_proxy: if http.is_empty() { None } else { Some(http) },
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
            if !git_config_set("http.proxy", &config.http_proxy) {
                errors.push("http.proxy");
            }
        }
        if !config.https_proxy.is_empty() {
            if !git_config_set("https.proxy", &config.https_proxy) {
                errors.push("https.proxy");
            }
        }
        if errors.is_empty() {
            OpResult::ok("Git proxy configured")
        } else {
            OpResult::err(format!("Failed to set: {}", errors.join(", ")))
        }
    }

    pub fn disable(&self) -> OpResult {
        git_config_unset("http.proxy");
        git_config_unset("https.proxy");
        OpResult::ok("Git proxy disabled")
    }
}

// ── Direct .gitconfig parsing (zero process spawn) ─────────────────────────

fn read_gitconfig_proxy() -> (String, String) {
    let path = match dirs::home_dir() {
        Some(h) => h.join(".gitconfig"),
        None => return (String::new(), String::new()),
    };
    let content = match fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return (String::new(), String::new()),
    };
    let mut http = String::new();
    let mut https = String::new();
    let mut current_section = "";
    for line in content.lines() {
        let trimmed = line.trim();
        // Track INI section
        if trimmed.starts_with('[') && trimmed.ends_with(']') {
            current_section = &trimmed[1..trimmed.len() - 1];
            // Handle "http" and 'http' quoting variants
            let section = current_section.trim_matches('"').trim_matches('\'');
            if section.eq_ignore_ascii_case("http") {
                current_section = "http";
            } else if section.eq_ignore_ascii_case("https") {
                current_section = "https";
            }
            continue;
        }
        // Parse key = value
        if let Some(eq_pos) = trimmed.find('=') {
            let key = trimmed[..eq_pos].trim();
            let val = trimmed[eq_pos + 1..].trim();
            match current_section {
                "http" if key.eq_ignore_ascii_case("proxy") => http = val.to_string(),
                "https" if key.eq_ignore_ascii_case("proxy") => https = val.to_string(),
                _ => {}
            }
        }
    }
    (http, https)
}

// ── Command-line operations (for enable/disable, where process spawn is acceptable) ──

fn git_config_set(key: &str, val: &str) -> bool {
    run_cmd("git", &["config", "--global", key, val]).0
}

fn git_config_unset(key: &str) {
    run_cmd("git", &["config", "--global", "--unset", key]);
}
