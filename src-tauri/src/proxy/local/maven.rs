use super::*;
use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use std::fs;

pub struct MavenLocalModule;

impl MavenLocalModule {
    pub fn new() -> Self {
        Self
    }



    pub fn config_files(&self) -> Vec<String> {
        vec!["%USERPROFILE%\\.m2\\settings.xml".into()]
    }

    pub fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Configure Maven proxy on Windows".into(),
            vec![
                "Edit %USERPROFILE%\\.m2\\settings.xml:".into(),
                "<proxies>".into(),
                "  <proxy>".into(),
                "    <id>my-proxy</id>".into(),
                "    <active>true</active>".into(),
                "    <protocol>http</protocol>".into(),
                "    <host>your-proxy-host</host>".into(),
                "    <port>7890</port>".into(),
                "    <nonProxyHosts>localhost|127.0.0.1</nonProxyHosts>".into(),
                "  </proxy>".into(),
                "</proxies>".into(),
            ],
        )]
    }

    pub fn detect(&self) -> bool {
        tool_exists("mvn")
    }

    fn settings_path() -> Option<std::path::PathBuf> {
        dirs::home_dir().map(|h| h.join(".m2").join("settings.xml"))
    }

    pub fn status(&self) -> ProxyStatus {
        let path = match Self::settings_path() {
            Some(p) => p,
            None => {
                return ProxyStatus {
                    component: ComponentId::MavenLocal,
                    installed: self.detect(),
                    enabled: false,
                    current_http_proxy: None,
                    current_https_proxy: None,
                    current_no_proxy: None,
                    current_mirror: None,
                    config_files: self.config_files(),
                    manual_setup_steps: vec![],
                }
            }
        };
        if !path.exists() {
            return ProxyStatus {
                component: ComponentId::MavenLocal,
                installed: self.detect(),
                enabled: false,
                current_http_proxy: None,
                current_https_proxy: None,
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
            };
        }
        let content = fs::read_to_string(&path).unwrap_or_default();
        let (enabled, proxy) = find_proxy_in_xml(&content);
        ProxyStatus {
            component: ComponentId::MavenLocal,
            installed: self.detect(),
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

    pub fn enable(&self, config: &ProxyConfig) -> OpResult {
        let path = match Self::settings_path() {
            Some(p) => p,
            None => return OpResult::err("Cannot find home directory"),
        };
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).ok();
        }
        let existing = if path.exists() {
            fs::read_to_string(&path).unwrap_or_default()
        } else {
            String::new()
        };
        let proxy_url = if !config.https_proxy.is_empty() {
            &config.https_proxy
        } else {
            &config.http_proxy
        };
        let (host, port) = parse_host_port(proxy_url);
        let non_proxy = config.no_proxy.replace(',', "|");
        let non_proxy = if non_proxy.is_empty() {
            "localhost|127.0.0.1"
        } else {
            &non_proxy
        };
        let new_xml = if existing.trim().is_empty() {
            make_settings_xml(&host, &port, non_proxy)
        } else {
            add_proxy_to_xml(&existing, &host, &port, non_proxy)
        };
        match fs::write(&path, &new_xml) {
            Ok(_) => OpResult::ok("Maven proxy configured"),
            Err(e) => OpResult::err(format!("Failed to write settings.xml: {}", e)),
        }
    }

    pub fn disable(&self) -> OpResult {
        let path = match Self::settings_path() {
            Some(p) => p,
            None => return OpResult::ok("No Maven settings to disable"),
        };
        if !path.exists() {
            return OpResult::ok("No Maven settings to disable");
        }
        let content = fs::read_to_string(&path).unwrap_or_default();
        let updated = remove_proxy_switches(&content);
        match fs::write(&path, &updated) {
            Ok(_) => OpResult::ok("Maven proxy disabled"),
            Err(e) => OpResult::err(format!("Failed to write settings.xml: {}", e)),
        }
    }
}

fn find_proxy_in_xml(xml: &str) -> (bool, Option<String>) {
    let re_active = regex::Regex::new(r"<active>\s*true\s*</active>").unwrap();
    if !re_active.is_match(xml) {
        return (false, None);
    }
    let re_host = regex::Regex::new(r"<host>\s*([^<\s]+)\s*</host>").unwrap();
    let re_port = regex::Regex::new(r"<port>\s*(\d+)\s*</port>").unwrap();
    let re_proto = regex::Regex::new(r"<protocol>\s*([^<\s]+)\s*</protocol>").unwrap();
    if let (Some(h), Some(p)) = (re_host.captures(&xml), re_port.captures(&xml)) {
        let protocol = re_proto
            .captures(&xml)
            .map(|c| c[1].to_string())
            .unwrap_or_else(|| "http".into());
        Some(format!("{}://{}:{}", protocol, &h[1], &p[1]))
    } else {
        None
    }
    .map_or((false, None), |proxy| (true, Some(proxy)))
}

fn parse_host_port(url: &str) -> (String, String) {
    if url.is_empty() {
        return (String::new(), String::new());
    }
    let stripped = url
        .trim_start_matches("http://")
        .trim_start_matches("https://");
    if let Some(pos) = stripped.rfind(':') {
        let host = &stripped[..pos];
        let port = stripped[pos + 1..].split('/').next().unwrap_or("");
        (host.to_string(), port.to_string())
    } else {
        (stripped.to_string(), String::new())
    }
}

fn make_settings_xml(host: &str, port: &str, non_proxy: &str) -> String {
    let host = if host.is_empty() { "proxy" } else { host };
    let port = if port.is_empty() { "8080" } else { port };
    format!(
        r#"<?xml version="1.0" encoding="UTF-8"?>
<settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
          xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
          xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                              http://maven.apache.org/xsd/settings-1.0.0.xsd">
  <proxies>
    <proxy>
      <id>proxy-switch-http</id>
      <active>true</active>
      <protocol>http</protocol>
      <host>{}</host>
      <port>{}</port>
      <nonProxyHosts>{}</nonProxyHosts>
    </proxy>
  </proxies>
</settings>"#,
        host, port, non_proxy
    )
}

fn add_proxy_to_xml(xml: &str, host: &str, port: &str, non_proxy: &str) -> String {
    let xml = remove_proxy_switches(xml);
    let proxy_block = format!(
        r#"    <proxy>
      <id>proxy-switch-http</id>
      <active>true</active>
      <protocol>http</protocol>
      <host>{}</host>
      <port>{}</port>
      <nonProxyHosts>{}</nonProxyHosts>
    </proxy>
"#,
        host, port, non_proxy
    );
    if xml.contains("<proxies>") {
        let re = regex::Regex::new(r"(?s)(<proxies>\s*)").unwrap();
        if let Some(cap) = re.captures(&xml) {
            return xml.replace(&cap[1], &format!("{}{}", &cap[1], proxy_block));
        }
    }
    let re = regex::Regex::new(r"(?s)(</settings>)").unwrap();
    let proxies_block = format!("  <proxies>\n{}  </proxies>\n", proxy_block);
    re.replace(&xml, format!("{}{}", proxies_block, "</settings>"))
        .to_string()
}

fn remove_proxy_switches(xml: &str) -> String {
    regex::Regex::new(r"(?s)<proxy>.*?proxy-switch.*?</proxy>")
        .unwrap()
        .replace_all(&xml, "")
        .to_string()
}
