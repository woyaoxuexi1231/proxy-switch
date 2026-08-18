use super::*;
use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use serde_json::{Map, Value};
use std::fs;
use std::path::{Path, PathBuf};

/// Docker Desktop proxy is only applied from its own Settings UI.
/// This module never writes Docker files; it only reads status and shows steps.
const MODE_KEYS: &[&str] = &["ProxyHTTPMode", "proxyHttpMode", "ProxyHttpMode"];
const HTTP_KEYS: &[&str] = &[
    "OverrideProxyHTTP",
    "overrideProxyHttp",
    "OverrideProxyHttp",
];
const HTTPS_KEYS: &[&str] = &[
    "OverrideProxyHTTPS",
    "overrideProxyHttps",
    "OverrideProxyHttps",
];
const EXCLUDE_KEYS: &[&str] = &["OverrideProxyExclude", "overrideProxyExclude"];

const GUIDE_MESSAGE: &str = "\
Docker Desktop proxy is not changed by this app. \
Open Docker Desktop → Settings → Resources → Proxies → Manual proxy configuration, \
enter your HTTP/HTTPS URL, then Apply & Restart. \
docker info will still show http.docker.internal:3128 — that is Desktop's internal proxy.";

pub struct DockerLocalModule;

impl DockerLocalModule {
    pub fn new() -> Self {
        Self
    }

    pub fn config_files(&self) -> Vec<String> {
        vec!["Docker Desktop → Settings → Resources → Proxies".into()]
    }

    pub fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Set proxy in Docker Desktop".into(),
            vec![
                "1. Open Docker Desktop".into(),
                "2. Settings → Resources → Proxies".into(),
                "3. Choose Manual proxy configuration".into(),
                "4. HTTP  = http://127.0.0.1:7890".into(),
                "   HTTPS = http://127.0.0.1:7890".into(),
                "5. Apply & Restart".into(),
                String::new(),
                "docker info will still show:".into(),
                "  HTTP Proxy: http.docker.internal:3128".into(),
                "That is Docker Desktop's internal proxy, not a misconfiguration.".into(),
                "It forwards to the URL you entered in the GUI.".into(),
                String::new(),
                "Do not edit daemon.json for proxy — Docker Desktop ignores it.".into(),
            ],
        )]
    }

    pub fn detect(&self) -> bool {
        tool_installed("docker")
    }

    pub fn status(&self) -> ProxyStatus {
        let (enabled, http, https, no_proxy) = read_desktop_proxies();
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

    pub fn enable(&self, _config: &ProxyConfig) -> OpResult {
        OpResult::ok(GUIDE_MESSAGE)
    }

    pub fn disable(&self) -> OpResult {
        OpResult::ok(
            "Disable proxy in Docker Desktop: Settings → Resources → Proxies → No proxy (or Manual with empty URLs), then Apply & Restart.",
        )
    }
}

fn desktop_settings_paths() -> Vec<PathBuf> {
    let Some(appdata) = dirs::config_dir() else {
        return Vec::new();
    };
    let dir = appdata.join("Docker");
    ["settings-store.json", "settings.json"]
        .into_iter()
        .map(|name| dir.join(name))
        .filter(|p| p.exists())
        .collect()
}

fn read_json(path: &Path) -> Option<Value> {
    let content = fs::read_to_string(path).ok()?;
    serde_json::from_str(&content).ok()
}

fn nonempty(s: &Option<String>) -> bool {
    s.as_ref().map(|v| !v.is_empty()).unwrap_or(false)
}

fn json_str_value(value: Option<&Value>) -> Option<String> {
    match value {
        Some(Value::String(s)) if !s.is_empty() => Some(s.clone()),
        _ => None,
    }
}

fn json_str(obj: &Map<String, Value>, keys: &[&str]) -> Option<String> {
    for key in keys {
        if let Some(v) = json_str_value(obj.get(*key)) {
            return Some(v);
        }
    }
    None
}

fn json_exclude(obj: &Map<String, Value>) -> Option<String> {
    match obj.get("exclude") {
        Some(Value::String(s)) if !s.is_empty() => Some(s.clone()),
        Some(Value::Array(items)) => {
            let joined = items
                .iter()
                .filter_map(|v| v.as_str())
                .filter(|s| !s.is_empty())
                .collect::<Vec<_>>()
                .join(",");
            if joined.is_empty() {
                None
            } else {
                Some(joined)
            }
        }
        _ => None,
    }
}

/// Read-only: show whatever Docker Desktop currently has configured.
fn read_desktop_proxies() -> (bool, Option<String>, Option<String>, Option<String>) {
    for path in desktop_settings_paths() {
        let Some(value) = read_json(&path) else {
            continue;
        };
        let Some(obj) = value.as_object() else {
            continue;
        };
        let mut mode = json_str(obj, MODE_KEYS).unwrap_or_default();
        let mut http = json_str(obj, HTTP_KEYS);
        let mut https = json_str(obj, HTTPS_KEYS);
        let mut no_proxy = json_str(obj, EXCLUDE_KEYS);
        if let Some(proxy) = obj.get("proxy").and_then(|p| p.as_object()) {
            if mode.is_empty() {
                mode = json_str(proxy, &["mode"]).unwrap_or_default();
            }
            if http.is_none() {
                http = json_str(proxy, &["http"]);
            }
            if https.is_none() {
                https = json_str(proxy, &["https"]);
            }
            if no_proxy.is_none() {
                no_proxy = json_exclude(proxy);
            }
        }
        if mode.is_empty() && http.is_none() && https.is_none() {
            continue;
        }
        let enabled = mode != "system"
            && mode != "disabled"
            && (nonempty(&http) || nonempty(&https));
        return (enabled, http, https, no_proxy);
    }
    (false, None, None, None)
}
