use crate::models::{ComponentId, ManualStep, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::ProxyModule;
use crate::ssh::connection::SshSession;

pub struct GitRemoteModule;

impl ProxyModule for GitRemoteModule {
    fn name(&self) -> &'static str {
        "git_remote"
    }
    fn description(&self) -> &'static str {
        "Git VCS proxy (git config --global)"
    }
    fn config_files(&self) -> Vec<String> {
        vec!["~/.gitconfig".into()]
    }
    fn manual_steps(&self) -> Vec<(String, Vec<String>)> {
        vec![(
            "Configure Git proxy".into(),
            vec![
                "git config --global http.proxy http://your-proxy:port".into(),
                "git config --global https.proxy http://your-proxy:port".into(),
                String::new(),
                "# To remove:".into(),
                "git config --global --unset http.proxy".into(),
                "git config --global --unset https.proxy".into(),
                String::new(),
                "# Config file: ~/.gitconfig".to_string(),
            ],
        )]
    }
    fn detect(&self, session: &SshSession) -> bool {
        session.tool_exists("git")
    }
    fn status(&self, session: &SshSession) -> ProxyStatus {
        let http = git_config_get(session, "http.proxy");
        let https = git_config_get(session, "https.proxy");
        let _proxy = if !https.is_empty() {
            Some(https.clone())
        } else if !http.is_empty() {
            Some(http.clone())
        } else {
            None
        };
        ProxyStatus {
            component: ComponentId::GitRemote,
            installed: self.detect(session),
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
    fn enable(&self, session: &SshSession, config: &ProxyConfig) -> OpResult {
        let mut errors = Vec::new();
        if !config.http_proxy.is_empty() {
            let r = session.run(
                &format!("git config --global http.proxy \"{}\"", config.http_proxy),
                10,
            );
            if r.exit_code != 0 {
                errors.push(format!("http.proxy: {}", r.stderr));
            }
        }
        if !config.https_proxy.is_empty() {
            let r = session.run(
                &format!(
                    "git config --global https.proxy \"{}\"",
                    config.https_proxy
                ),
                10,
            );
            if r.exit_code != 0 {
                errors.push(format!("https.proxy: {}", r.stderr));
            }
        }
        if errors.is_empty() {
            OpResult::ok("Git proxy configured")
        } else {
            OpResult::err(errors.join("; "))
        }
    }
    fn disable(&self, session: &SshSession) -> OpResult {
        session.run("git config --global --unset http.proxy 2>/dev/null", 10);
        session.run("git config --global --unset https.proxy 2>/dev/null", 10);
        session.run("git config --global --unset http.*.noProxy 2>/dev/null", 10);
        OpResult::ok("Git proxy disabled")
    }
}

fn git_config_get(session: &SshSession, key: &str) -> String {
    session
        .run(
            &format!("git config --global --get {} 2>/dev/null || echo ''", key),
            5,
        )
        .stdout
}
