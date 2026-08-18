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
        crate::proxy::local::ensure_process_path();
        let order = ComponentId::local_all();
        let handles = vec![
            std::thread::spawn(|| GitLocalModule::new().status()),
            std::thread::spawn(|| DockerLocalModule::new().status()),
            std::thread::spawn(|| NpmLocalModule::new().status()),
            std::thread::spawn(|| MavenLocalModule::new().status()),
        ];
        let results: Vec<ProxyStatus> = handles
            .into_iter()
            .enumerate()
            .map(|(i, h)| {
                h.join()
                    .unwrap_or_else(|_| ProxyStatus::blank(order[i]))
            })
            .collect();
        Ok(results)
    })
    .await
    .map_err(|e| format!("Task error: {}", e))?
}
