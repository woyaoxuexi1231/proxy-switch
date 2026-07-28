use crate::models::{ComponentId, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::remote::{apt::AptModule, docker::DockerRemoteModule, git::GitRemoteModule,
    maven::MavenRemoteModule, npm::NpmRemoteModule, system_proxy::SystemProxyModule};
use crate::proxy::ProxyModule;
use crate::ssh::connection::ConnectionPool;
use tauri::State;

#[tauri::command]
pub fn remote_detect(pool: State<'_, ConnectionPool>, component: String) -> Result<ProxyStatus, String> {
    let cid = parse_component(&component)?;
    pool.with_session(|session| detect_remote(session, &cid))
}

#[tauri::command]
pub fn remote_enable(
    pool: State<'_, ConnectionPool>,
    component: String,
    config: ProxyConfig,
) -> Result<OpResult, String> {
    let cid = parse_component(&component)?;
    pool.with_session(|session| {
        let module = get_module(&cid)?;
        Ok(module.enable(session, &config))
    })
}

#[tauri::command]
pub fn remote_disable(
    pool: State<'_, ConnectionPool>,
    component: String,
) -> Result<OpResult, String> {
    let cid = parse_component(&component)?;
    pool.with_session(|session| {
        let module = get_module(&cid)?;
        Ok(module.disable(session))
    })
}

fn parse_component(s: &str) -> Result<ComponentId, String> {
    match s {
        "system_proxy" => Ok(ComponentId::SystemProxy),
        "apt" => Ok(ComponentId::Apt),
        "git_remote" => Ok(ComponentId::GitRemote),
        "docker_remote" => Ok(ComponentId::DockerRemote),
        "npm_remote" => Ok(ComponentId::NpmRemote),
        "maven_remote" => Ok(ComponentId::MavenRemote),
        _ => Err(format!("Unknown remote component: {}", s)),
    }
}

fn detect_remote(session: &crate::ssh::connection::SshSession, cid: &ComponentId) -> Result<ProxyStatus, String> {
    let module = get_module(cid)?;
    let installed = module.detect(session);
    if !installed {
        return Ok(ProxyStatus {
            component: *cid,
            installed: false,
            enabled: false,
            current_http_proxy: None,
            current_https_proxy: None,
            current_no_proxy: None,
            current_mirror: None,
            config_files: module.config_files(),
            manual_setup_steps: module
                .manual_steps()
                .into_iter()
                .map(|(t, c)| crate::models::ManualStep {
                    title: t,
                    commands: c,
                })
                .collect(),
        });
    }
    Ok(module.status(session))
}

fn get_module(cid: &ComponentId) -> Result<Box<dyn ProxyModule>, String> {
    match cid {
        ComponentId::SystemProxy => Ok(Box::new(SystemProxyModule)),
        ComponentId::Apt => Ok(Box::new(AptModule)),
        ComponentId::GitRemote => Ok(Box::new(GitRemoteModule)),
        ComponentId::DockerRemote => Ok(Box::new(DockerRemoteModule)),
        ComponentId::NpmRemote => Ok(Box::new(NpmRemoteModule)),
        ComponentId::MavenRemote => Ok(Box::new(MavenRemoteModule)),
        _ => Err(format!("Not a remote component: {:?}", cid)),
    }
}
