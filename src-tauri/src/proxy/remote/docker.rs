use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::ProxyModule;
use crate::ssh::connection::SshSession;

const DOCKER_DIR: &str = "/etc/systemd/system/docker.service.d";
const DOCKER_CONF: &str = "/etc/systemd/system/docker.service.d/proxy.conf";
const DAEMON_JSON: &str = "/etc/docker/daemon.json";

pub struct DockerRemoteModule;

impl ProxyModule for DockerRemoteModule {
    fn name(&self) -> &'static str {
        "docker_remote"
    }
    fn description(&self) -> &'static str {
        "Docker daemon proxy"
    }
    fn config_files(&self) -> Vec<String> {
        vec![DOCKER_CONF.into(), DAEMON_JSON.into()]
    }
    fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Configure Docker proxy".into(),
            vec![
                format!("sudo mkdir -p {}", DOCKER_DIR),
                format!("sudo nano {}", DOCKER_CONF),
                String::new(),
                "# Add these lines:".to_string(),
                "[Service]".into(),
                "Environment=\"HTTP_PROXY=http://your-proxy:port\"".into(),
                "Environment=\"HTTPS_PROXY=http://your-proxy:port\"".into(),
                "Environment=\"NO_PROXY=localhost,127.0.0.1\"".into(),
                String::new(),
                "# Then restart:".to_string(),
                "sudo systemctl daemon-reload".into(),
                "sudo systemctl restart docker".into(),
            ],
        )]
    }
    fn detect(&self, session: &SshSession) -> bool {
        session.tool_exists("docker")
            && session
                .run("systemctl show -p Id docker.service 2>/dev/null", 5)
                .stdout
                .contains("docker.service")
    }
    fn status(&self, session: &SshSession) -> ProxyStatus {
        let content = session.read_file(DOCKER_CONF);
        let enabled = content.contains("HTTP_PROXY=");
        let mut proxy = None;
        if let Some(cap) = regex::Regex::new(r#"HTTP_PROXY=(.+)"#).unwrap().captures(&content) {
            proxy = Some(cap[1].to_string());
        }
        let mut mirror = None;
        let daemon = session.read_file(DAEMON_JSON);
        if !daemon.is_empty() {
            if let Ok(cfg) = serde_json::from_str::<serde_json::Value>(&daemon) {
                if let Some(mirrors) = cfg.get("registry-mirrors").and_then(|v| v.as_array()) {
                    if let Some(first) = mirrors.first().and_then(|v| v.as_str()) {
                        mirror = Some(first.to_string());
                    }
                }
            }
        }
        ProxyStatus {
            component: ComponentId::DockerRemote,
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
        if !session.has_sudo() {
            return OpResult::err("Sudo access required.");
        }
        let content = build_proxy_conf(config);
        if let Err(e) = session.write_file(DOCKER_CONF, &content, true) {
            return OpResult::err(format!("Failed to write {}: {}", DOCKER_CONF, e));
        }
        if !config.mirror.is_empty() {
            update_daemon_mirror(session, &config.mirror);
        }
        restart_docker(session);
        OpResult::ok("Docker proxy configured and restarted")
    }
    fn disable(&self, session: &SshSession) -> OpResult {
        if !session.has_sudo() {
            return OpResult::err("Sudo access required.");
        }
        session.run(&format!("sudo rm -f {}", DOCKER_CONF), 10);
        update_daemon_mirror(session, "");
        restart_docker(session);
        OpResult::ok("Docker proxy disabled")
    }
}

fn build_proxy_conf(config: &ProxyConfig) -> String {
    let mut lines = vec!["# Managed by proxy-switch".into(), "[Service]".into()];
    if !config.http_proxy.is_empty() {
        lines.push(format!(
            "Environment=\"HTTP_PROXY={}\"",
            config.http_proxy
        ));
        lines.push(format!(
            "Environment=\"http_proxy={}\"",
            config.http_proxy
        ));
    }
    if !config.https_proxy.is_empty() {
        lines.push(format!(
            "Environment=\"HTTPS_PROXY={}\"",
            config.https_proxy
        ));
        lines.push(format!(
            "Environment=\"https_proxy={}\"",
            config.https_proxy
        ));
    }
    if !config.no_proxy.is_empty() {
        lines.push(format!(
            "Environment=\"NO_PROXY={}\"",
            config.no_proxy
        ));
        lines.push(format!("Environment=\"no_proxy={}\"", config.no_proxy));
    }
    lines.push(String::new());
    lines.join("\n")
}

fn update_daemon_mirror(session: &SshSession, mirror: &str) {
    let existing = session.read_file(DAEMON_JSON);
    let mut cfg: serde_json::Value = if existing.trim().is_empty() {
        serde_json::Value::Object(serde_json::Map::new())
    } else {
        serde_json::from_str(&existing).unwrap_or(serde_json::Value::Object(serde_json::Map::new()))
    };
    if mirror.is_empty() {
        if let Some(obj) = cfg.as_object_mut() {
            obj.remove("registry-mirrors");
        }
    } else {
        if let Some(obj) = cfg.as_object_mut() {
            obj.insert(
                "registry-mirrors".into(),
                serde_json::Value::Array(vec![serde_json::Value::String(mirror.into())]),
            );
        }
    }
    let new_content = serde_json::to_string_pretty(&cfg).unwrap_or_default();
    session.write_file(DAEMON_JSON, &new_content, true).ok();
}

fn restart_docker(session: &SshSession) {
    session.run("sudo systemctl daemon-reload 2>&1", 15);
    session.run("sudo systemctl restart docker 2>&1", 30);
}
