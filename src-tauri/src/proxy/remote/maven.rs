use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::ProxyModule;
use crate::ssh::connection::SshSession;

const SETTINGS_PATH: &str = "~/.m2/settings.xml";

pub struct MavenRemoteModule;

impl ProxyModule for MavenRemoteModule {
    fn name(&self) -> &'static str {
        "maven_remote"
    }
    fn description(&self) -> &'static str {
        "Maven build tool proxy"
    }
    fn config_files(&self) -> Vec<String> {
        vec![SETTINGS_PATH.into()]
    }
    fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
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
        )]
    }
    fn detect(&self, session: &SshSession) -> bool {
        session.tool_exists("mvn")
    }
    fn status(&self, session: &SshSession) -> ProxyStatus {
        let content = session.read_file(&expand_path(SETTINGS_PATH));
        let (enabled, proxy, mirror) = parse_status(&content);
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
        let path = expand_path(SETTINGS_PATH);
        let existing = session.read_file(&path);
        let host_port = parse_host_port(
            if !config.https_proxy.is_empty() {
                &config.https_proxy
            } else {
                &config.http_proxy
            },
        );
        let non_proxy = config
            .no_proxy
            .replace(',', "|")
            .replace(" ", "");
        let non_proxy = if non_proxy.is_empty() {
            "localhost|127.0.0.1"
        } else {
            &non_proxy
        };
        if existing.trim().is_empty() {
            let new_xml = make_settings_xml(&host_port.0, &host_port.1, non_proxy, &config.mirror);
            match session.write_file(&path, &new_xml, false) {
                Ok(_) => OpResult::ok("Maven proxy configured"),
                Err(e) => OpResult::err(format!("Failed to write settings.xml: {}", e)),
            }
        } else {
            let updated = add_proxy_to_xml(&existing, &host_port.0, &host_port.1, non_proxy);
            let updated = if !config.mirror.is_empty() {
                add_mirror_to_xml(&updated, &config.mirror)
            } else {
                updated
            };
            match session.write_file(&path, &updated, false) {
                Ok(_) => OpResult::ok("Maven proxy configured"),
                Err(e) => OpResult::err(format!("Failed to write settings.xml: {}", e)),
            }
        }
    }
    fn disable(&self, session: &SshSession) -> OpResult {
        let path = expand_path(SETTINGS_PATH);
        let existing = session.read_file(&path);
        if existing.trim().is_empty() {
            return OpResult::ok("No Maven settings to disable");
        }
        let updated = remove_proxy_switches(&existing);
        if session.write_file(&path, &updated, false).is_ok() {
            OpResult::ok("Maven proxy disabled")
        } else {
            OpResult::err("Failed to write settings.xml")
        }
    }
}

fn expand_path(path: &str) -> String {
    if path.starts_with("~/") {
        if let Some(home) = dirs::home_dir() {
            return home.to_string_lossy().to_string() + &path[1..];
        }
    }
    path.to_string()
}

fn parse_status(xml: &str) -> (bool, Option<String>, Option<String>) {
    if xml.trim().is_empty() {
        return (false, None, None);
    }
    let (enabled, proxy) = find_proxy_in_xml(xml);
    let mirror = find_mirror_in_xml(xml);
    (enabled, proxy, mirror)
}

fn find_proxy_in_xml(xml: &str) -> (bool, Option<String>) {
    let re_active =
        regex::Regex::new(r"<active>\s*true\s*</active>").unwrap();
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
        let proxy = format!("{}://{}:{}", protocol, &h[1], &p[1]);
        (true, Some(proxy))
    } else {
        (false, None)
    }
}

fn find_mirror_in_xml(xml: &str) -> Option<String> {
    let re = regex::Regex::new(r"<id>\s*proxy-switch-mirror\s*</id>").unwrap();
    if !re.is_match(xml) {
        return None;
    }
    let re_url = regex::Regex::new(r"<url>\s*([^<\s]+)\s*</url>").unwrap();
    re_url.captures(&xml).map(|c| c[1].to_string())
}

fn parse_host_port(url: &str) -> (String, String) {
    if url.is_empty() {
        return (String::new(), String::new());
    }
    let stripped = url
        .trim_start_matches("http://")
        .trim_start_matches("https://")
        .trim_start_matches("socks5://");
    if let Some(pos) = stripped.rfind(':') {
        let host = &stripped[..pos];
        let port = &stripped[pos + 1..];
        let port = port.split('/').next().unwrap_or(port);
        (host.to_string(), port.to_string())
    } else {
        (stripped.to_string(), String::new())
    }
}

fn make_settings_xml(host: &str, port: &str, non_proxy: &str, mirror: &str) -> String {
    let mirror_block = if mirror.is_empty() {
        String::new()
    } else {
        format!(
            r#"  <mirrors>
    <mirror>
      <id>proxy-switch-mirror</id>
      <url>{}</url>
      <mirrorOf>central</mirrorOf>
    </mirror>
  </mirrors>
"#,
            mirror
        )
    };
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
{}
</settings>"#,
        host, port, non_proxy, mirror_block
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
    let proxies_block = format!(
        "  <proxies>\n{}  </proxies>\n",
        proxy_block
    );
    re.replace(&xml, format!("{}{}", proxies_block, "</settings>"))
        .to_string()
}

fn add_mirror_to_xml(xml: &str, mirror: &str) -> String {
    let xml = regex::Regex::new(r"(?s)<mirrors>.*?</mirrors>")
        .unwrap()
        .replace_all(&xml, "")
        .to_string();
    let mirror_block = format!(
        r#"  <mirrors>
    <mirror>
      <id>proxy-switch-mirror</id>
      <url>{}</url>
      <mirrorOf>central</mirrorOf>
    </mirror>
  </mirrors>
"#,
        mirror
    );
    let re = regex::Regex::new(r"(?s)(</settings>)").unwrap();
    re.replace(&xml, format!("{}{}", mirror_block, "</settings>"))
        .to_string()
}

fn remove_proxy_switches(xml: &str) -> String {
    let xml = regex::Regex::new(r"(?s)<proxy>.*?proxy-switch.*?</proxy>")
        .unwrap()
        .replace_all(&xml, "")
        .to_string();
    regex::Regex::new(r"(?s)<mirror>.*?proxy-switch.*?</mirror>")
        .unwrap()
        .replace_all(&xml, "")
        .to_string()
}
