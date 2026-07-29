use crate::models::{ComponentId, OpResult, ProxyConfig, ProxyStatus};
use crate::proxy::local::{docker::DockerLocalModule, git::GitLocalModule, maven::MavenLocalModule, npm::NpmLocalModule};

#[tauri::command]
pub async fn local_detect(component: String) -> Result<ProxyStatus, String> {
    tokio::task::spawn_blocking(move || {
        match component.as_str() {
            "git_local" => Ok(GitLocalModule::new().status()),
            "docker_local" => Ok(DockerLocalModule::new().status()),
            "npm_local" => Ok(NpmLocalModule::new().status()),
            "maven_local" => Ok(MavenLocalModule::new().status()),
            _ => Err(format!("Unknown local component: {}", component)),
        }
    })
    .await
    .map_err(|e| format!("Task error: {}", e))?
}

#[tauri::command]
pub async fn local_enable(component: String, config: ProxyConfig) -> Result<OpResult, String> {
    tokio::task::spawn_blocking(move || {
        match component.as_str() {
            "git_local" => Ok(GitLocalModule::new().enable(&config)),
            "docker_local" => Ok(DockerLocalModule::new().enable(&config)),
            "npm_local" => Ok(NpmLocalModule::new().enable(&config)),
            "maven_local" => Ok(MavenLocalModule::new().enable(&config)),
            _ => Err(format!("Unknown local component: {}", component)),
        }
    })
    .await
    .map_err(|e| format!("Task error: {}", e))?
}

#[tauri::command]
pub async fn local_disable(component: String) -> Result<OpResult, String> {
    tokio::task::spawn_blocking(move || {
        match component.as_str() {
            "git_local" => Ok(GitLocalModule::new().disable()),
            "docker_local" => Ok(DockerLocalModule::new().disable()),
            "npm_local" => Ok(NpmLocalModule::new().disable()),
            "maven_local" => Ok(MavenLocalModule::new().disable()),
            _ => Err(format!("Unknown local component: {}", component)),
        }
    })
    .await
    .map_err(|e| format!("Task error: {}", e))?
}

#[tauri::command]
pub async fn local_detect_all() -> Result<Vec<ProxyStatus>, String> {
    tokio::task::spawn_blocking(move || {
        let handles = vec![
            std::thread::spawn(|| (ComponentId::GitLocal, GitLocalModule::new().status())),
            std::thread::spawn(|| (ComponentId::DockerLocal, DockerLocalModule::new().status())),
            std::thread::spawn(|| (ComponentId::NpmLocal, NpmLocalModule::new().status())),
            std::thread::spawn(|| (ComponentId::MavenLocal, MavenLocalModule::new().status())),
        ];
        let mut results: Vec<ProxyStatus> = handles
            .into_iter()
            .map(|h| h.join().map(|(_, s)| s).unwrap_or_else(|_| ProxyStatus {
                component: ComponentId::GitLocal,
                installed: false,
                enabled: false,
                current_http_proxy: None,
                current_https_proxy: None,
                current_no_proxy: None,
                current_mirror: None,
                config_files: vec![],
                manual_setup_steps: vec![],
            }))
            .collect();
        // Sort to match ComponentId::local_all() order
        results.sort_by_key(|s| {
            match s.component {
                ComponentId::GitLocal => 0,
                ComponentId::DockerLocal => 1,
                ComponentId::NpmLocal => 2,
                ComponentId::MavenLocal => 3,
                _ => 4,
            }
        });
        Ok(results)
    })
    .await
    .map_err(|e| format!("Task error: {}", e))?
}
