use super::*;
use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use std::fs;

pub struct DockerLocalModule;

impl DockerLocalModule {
    pub fn new() -> Self {
        Self
    }



    pub fn config_files(&self) -> Vec<String> {
        vec!["%USERPROFILE%\\.docker\\daemon.json".into()]
    }

    pub fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Configure Docker proxy on Windows".into(),
            vec![
                "Method 1 — Docker Desktop GUI:".into(),
                "Settings → Resources → Proxies".into(),
                "Fill in HTTP/HTTPS proxy → Apply & Restart".into(),
                String::new(),
                "Method 2 — Edit daemon.json:".into(),
                "%USERPROFILE%\\.docker\\daemon.json".into(),
                "{".into(),
                "  \"proxies\": {".into(),
                "    \"default\": {".into(),
                "      \"httpProxy\": \"http://your-proxy:port\",".into(),
                "      \"httpsProxy\": \"http://your-proxy:port\",".into(),
                "      \"noProxy\": \"localhost,127.0.0.1\"".into(),
                "    }".into(),
                "  }".into(),
                "}".into(),
            ],
        )]
    }

    pub fn detect(&self) -> bool {
        tool_exists("docker")
    }

    fn daemon_path() -> Option<std::path::PathBuf> {
        dirs::home_dir().map(|h| h.join(".docker").join("daemon.json"))
    }

    pub fn status(&self) -> ProxyStatus {
        let (enabled, http, https, no_proxy) = read_daemon_proxies();
        let _proxy = if let Some(ref h) = https {
            Some(h.clone())
        } else if let Some(ref h) = http {
            Some(h.clone())
        } else {
            None
        };
        ProxyStatus {
            component: ComponentId::DockerLocal,
            installed: self.detect(),
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

    pub fn enable(&self, config: &ProxyConfig) -> OpResult {
        let path = match Self::daemon_path() {
            Some(p) => p,
            None => return OpResult::err("Cannot find home directory"),
        };
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).ok();
        }
        let mut daemon: serde_json::Value = if path.exists() {
            let content = fs::read_to_string(&path).unwrap_or_default();
            serde_json::from_str(&content).unwrap_or(serde_json::Value::Object(
                serde_json::Map::new(),
            ))
        } else {
            serde_json::Value::Object(serde_json::Map::new())
        };
        let mut proxies = serde_json::Map::new();
        let mut default_proxy = serde_json::Map::new();
        if !config.http_proxy.is_empty() {
            default_proxy.insert(
                "httpProxy".into(),
                serde_json::Value::String(config.http_proxy.clone()),
            );
        }
        if !config.https_proxy.is_empty() {
            default_proxy.insert(
                "httpsProxy".into(),
                serde_json::Value::String(config.https_proxy.clone()),
            );
        }
        if !config.no_proxy.is_empty() {
            default_proxy.insert(
                "noProxy".into(),
                serde_json::Value::String(config.no_proxy.clone()),
            );
        }
        proxies.insert(
            "default".into(),
            serde_json::Value::Object(default_proxy),
        );
        if let Some(obj) = daemon.as_object_mut() {
            obj.insert(
                "proxies".into(),
                serde_json::Value::Object(proxies),
            );
        }
        let content = serde_json::to_string_pretty(&daemon).unwrap_or_default();
        match fs::write(&path, &content) {
            Ok(_) => OpResult::ok("Docker proxy configured. Restart Docker Desktop to apply."),
            Err(e) => OpResult::err(format!("Failed to write daemon.json: {}", e)),
        }
    }

    pub fn disable(&self) -> OpResult {
        let path = match Self::daemon_path() {
            Some(p) => p,
            None => return OpResult::err("Cannot find home directory"),
        };
        if !path.exists() {
            return OpResult::ok("No Docker config to disable");
        }
        let content = fs::read_to_string(&path).unwrap_or_default();
        let mut daemon: serde_json::Value = serde_json::from_str(&content)
            .unwrap_or(serde_json::Value::Object(serde_json::Map::new()));
        if let Some(obj) = daemon.as_object_mut() {
            obj.remove("proxies");
        }
        let content = serde_json::to_string_pretty(&daemon).unwrap_or_default();
        match fs::write(&path, &content) {
            Ok(_) => OpResult::ok("Docker proxy removed. Restart Docker Desktop to apply."),
            Err(e) => OpResult::err(format!("Failed to write daemon.json: {}", e)),
        }
    }
}

fn read_daemon_proxies() -> (
    bool,
    Option<String>,
    Option<String>,
    Option<String>,
) {
    let path = match dirs::home_dir() {
        Some(h) => h.join(".docker").join("daemon.json"),
        None => return (false, None, None, None),
    };
    if !path.exists() {
        return (false, None, None, None);
    }
    let content = match fs::read_to_string(&path) {
        Ok(c) => c,
        Err(_) => return (false, None, None, None),
    };
    let cfg: serde_json::Value = match serde_json::from_str(&content) {
        Ok(v) => v,
        Err(_) => return (false, None, None, None),
    };
    let default = cfg
        .get("proxies")
        .and_then(|p| p.get("default"));
    let enabled = default.is_some();
    let http = default
        .and_then(|d| d.get("httpProxy"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let https = default
        .and_then(|d| d.get("httpsProxy"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    let no_proxy = default
        .and_then(|d| d.get("noProxy"))
        .and_then(|v| v.as_str())
        .map(|s| s.to_string());
    (enabled, http, https, no_proxy)
}
