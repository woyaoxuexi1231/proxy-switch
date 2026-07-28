use crate::models::{OpResult, ProxyConfig, ProxyStatus};
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
