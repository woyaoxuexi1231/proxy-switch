use super::*;
use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};

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
        tool_exists("git")
    }

    pub fn status(&self) -> ProxyStatus {
        let http = git_config_get("http.proxy");
        let https = git_config_get("https.proxy");
        let _proxy = if !https.is_empty() {
            Some(https.clone())
        } else if !http.is_empty() {
            Some(http.clone())
        } else {
            None
        };
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

fn git_config_get(key: &str) -> String {
    let (_, out) = run_cmd("git", &["config", "--global", "--get", key]);
    out
}

fn git_config_set(key: &str, val: &str) -> bool {
    run_cmd("git", &["config", "--global", key, val]).0
}

fn git_config_unset(key: &str) {
    run_cmd("git", &["config", "--global", "--unset", key]);
}
