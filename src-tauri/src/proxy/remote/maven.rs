use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::maven_xml;
use crate::proxy::ProxyModule;
use crate::ssh::connection::SshSession;

const SETTINGS_PATH: &str = "~/.m2/settings.xml";

pub struct MavenRemoteModule;

impl ProxyModule for MavenRemoteModule {
    fn config_files(&self) -> Vec<String> {
        vec![SETTINGS_PATH.into()]
    }
    fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![
            (
                "Configure Maven proxy".into(),
                vec![
                    "# Edit ~/.m2/settings.xml and add:".into(),
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
    fn detect(&self, session: &SshSession) -> bool {
        session.tool_exists("mvn")
    }
    fn status(&self, session: &SshSession) -> ProxyStatus {
        let content = session.read_file(&settings_path(session));
        let (enabled, proxy) = maven_xml::find_proxy(&content);
        let mirror = maven_xml::find_mirror(&content);
        ProxyStatus {
            component: ComponentId::MavenRemote,
            installed: self.detect(session),
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
    fn enable(&self, session: &SshSession, config: &ProxyConfig) -> OpResult {
        let path = settings_path(session);
        let existing = session.read_file(&path);
        match maven_xml::apply(&existing, config) {
            Ok(xml) => match session.write_file(&path, &xml, false) {
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
    fn disable(&self, session: &SshSession) -> OpResult {
        let path = settings_path(session);
        let existing = session.read_file(&path);
        if existing.trim().is_empty() {
            return OpResult::ok("No Maven settings to disable");
        }
        let updated = maven_xml::remove_proxy(&existing);
        if session.write_file(&path, &updated, false).is_ok() {
            OpResult::ok("Maven proxy disabled (Aliyun mirror kept)")
        } else {
            OpResult::err("Failed to write settings.xml")
        }
    }
}

fn settings_path(session: &SshSession) -> String {
    let home = session.run("printf %s \"$HOME\"", 5).stdout;
    let home = home.trim_end_matches('/');
    if home.is_empty() {
        "/root/.m2/settings.xml".into()
    } else {
        format!("{}/.m2/settings.xml", home)
    }
}
