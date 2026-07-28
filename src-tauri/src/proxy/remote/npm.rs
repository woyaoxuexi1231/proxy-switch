use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::ProxyModule;
use crate::ssh::connection::SshSession;

const DEFAULT_REGISTRY: &str = "https://registry.npmjs.org/";

pub struct NpmRemoteModule;

impl ProxyModule for NpmRemoteModule {
    fn config_files(&self) -> Vec<String> {
        vec!["~/.npmrc".into()]
    }
    fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Configure npm proxy".into(),
            vec![
                "npm config set proxy http://your-proxy:port".into(),
                "npm config set https-proxy http://your-proxy:port".into(),
                String::new(),
                "# To remove:".into(),
                "npm config delete proxy".into(),
                "npm config delete https-proxy".into(),
                String::new(),
                "# Config file: ~/.npmrc".to_string(),
            ],
        )]
    }
    fn detect(&self, session: &SshSession) -> bool {
        session.tool_exists("npm")
    }
    fn status(&self, session: &SshSession) -> ProxyStatus {
        let proxy = npm_config_get(session, "proxy");
        let https = npm_config_get(session, "https-proxy");
        let registry = npm_config_get(session, "registry");
        let mirror = if registry != DEFAULT_REGISTRY && !registry.is_empty() {
            Some(registry)
        } else {
            None
        };
        ProxyStatus {
            component: ComponentId::NpmRemote,
            installed: self.detect(session),
            enabled: !proxy.is_empty() || !https.is_empty(),
            current_http_proxy: if proxy.is_empty() { None } else { Some(proxy.clone()) },
            current_https_proxy: if https.is_empty() { None } else { Some(https) },
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
        let mut errors = Vec::new();
        if !config.http_proxy.is_empty() {
            let r = session.run(
                &format!("npm config set proxy \"{}\"", config.http_proxy),
                10,
            );
            if r.exit_code != 0 {
                errors.push(format!("proxy: {}", r.stderr));
            }
        }
        if !config.https_proxy.is_empty() {
            let r = session.run(
                &format!("npm config set https-proxy \"{}\"", config.https_proxy),
                10,
            );
            if r.exit_code != 0 {
                errors.push(format!("https-proxy: {}", r.stderr));
            }
        }
        if !config.no_proxy.is_empty() {
            session.run(
                &format!("npm config set no-proxy \"{}\"", config.no_proxy),
                10,
            );
        }
        if !config.mirror.is_empty() {
            let r = session.run(
                &format!("npm config set registry \"{}\"", config.mirror),
                10,
            );
            if r.exit_code != 0 {
                errors.push(format!("registry: {}", r.stderr));
            }
        }
        if errors.is_empty() {
            OpResult::ok("npm proxy configured")
        } else {
            OpResult::err(errors.join("; "))
        }
    }
    fn disable(&self, session: &SshSession) -> OpResult {
        session.run("npm config delete proxy 2>/dev/null", 10);
        session.run("npm config delete https-proxy 2>/dev/null", 10);
        session.run("npm config delete no-proxy 2>/dev/null", 10);
        OpResult::ok("npm proxy disabled")
    }
}

fn npm_config_get(session: &SshSession, key: &str) -> String {
    session
        .run(
            &format!("npm config get {} 2>/dev/null || echo ''", key),
            5,
        )
        .stdout
}
