use super::*;
use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::maven_xml;
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
        vec![
            (
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
            ),
            (
                "Aliyun Maven mirror".into(),
                vec![
                    "<mirrors>".into(),
                    "  <mirror>".into(),
                    "    <id>aliyun-maven</id>".into(),
                    "    <url>https://maven.aliyun.com/repository/public</url>".into(),
                    "    <mirrorOf>*</mirrorOf>".into(),
                    "  </mirror>".into(),
                    "</mirrors>".into(),
                ],
            ),
        ]
    }

    pub fn detect(&self) -> bool {
        tool_installed("mvn")
    }

    fn settings_path() -> Option<std::path::PathBuf> {
        dirs::home_dir().map(|h| h.join(".m2").join("settings.xml"))
    }

    fn empty_status(&self, extra_steps: bool) -> ProxyStatus {
        ProxyStatus {
            component: ComponentId::MavenLocal,
            installed: self.detect(),
            enabled: false,
            current_http_proxy: None,
            current_https_proxy: None,
            current_no_proxy: None,
            current_mirror: None,
            config_files: self.config_files(),
            manual_setup_steps: if extra_steps {
                self.manual_steps()
                    .into_iter()
                    .map(|(t, c)| ManualStep {
                        title: t,
                        commands: c,
                    })
                    .collect()
            } else {
                vec![]
            },
        }
    }

    pub fn status(&self) -> ProxyStatus {
        let path = match Self::settings_path() {
            Some(p) => p,
            None => return self.empty_status(false),
        };
        if !path.exists() {
            return self.empty_status(true);
        }
        let content = fs::read_to_string(&path).unwrap_or_default();
        let (enabled, proxy) = maven_xml::find_proxy(&content);
        let mirror = maven_xml::find_mirror(&content);
        ProxyStatus {
            component: ComponentId::MavenLocal,
            installed: self.detect(),
            enabled,
            current_http_proxy: proxy.clone(),
            current_https_proxy: proxy,
            current_no_proxy: None,
            current_mirror: mirror,
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
        match maven_xml::apply(&existing, config) {
            Ok(xml) => match fs::write(&path, &xml) {
                Ok(_) => {
                    if maven_xml::has_proxy_url(config) && config.mirror.is_empty() {
                        OpResult::ok("Maven proxy configured")
                    } else if !maven_xml::has_proxy_url(config) {
                        OpResult::ok("Maven mirror configured")
                    } else {
                        OpResult::ok("Maven proxy and mirror configured")
                    }
                }
                Err(e) => OpResult::err(format!("Failed to write settings.xml: {}", e)),
            },
            Err(e) => OpResult::err(e),
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
        let updated = maven_xml::remove_proxy(&content);
        match fs::write(&path, &updated) {
            Ok(_) => OpResult::ok("Maven proxy disabled (Aliyun mirror kept)"),
            Err(e) => OpResult::err(format!("Failed to write settings.xml: {}", e)),
        }
    }
}
