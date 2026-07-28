use std::sync::Arc;
use crate::config::store::ConfigStore;
use crate::models::{OpResult, SshState};
use crate::ssh::connection::ConnectionPool;
use tauri::State;

#[tauri::command]
pub async fn ssh_connect(
    store: State<'_, ConfigStore>,
    pool: State<'_, Arc<ConnectionPool>>,
    server_name: String,
) -> Result<OpResult, String> {
    let servers = store.load_servers();
    let server = match servers.iter().find(|s| s.name == server_name) {
        Some(s) => s.clone(),
        None => return Ok(OpResult::err(format!("Server '{}' not found", server_name))),
    };
    let label = server.label();
    let pool_clone = pool.inner().clone();
    let result = tokio::task::spawn_blocking(move || {
        let session = crate::ssh::connection::SshSession::connect(&server, 10)?;
        let mut guard = pool_clone
            .current
            .lock()
            .map_err(|e| format!("Lock error: {}", e))?;
        *guard = Some(session);
        Ok::<_, String>(())
    })
    .await
    .map_err(|e| format!("Task error: {}", e))?;
    match result {
        Ok(()) => Ok(OpResult::ok(format!("Connected to {}", label))),
        Err(e) => Ok(OpResult::err(format!("Connection failed: {}", e))),
    }
}

#[tauri::command]
pub fn ssh_disconnect(pool: State<'_, Arc<ConnectionPool>>) -> OpResult {
    pool.disconnect();
    OpResult::ok("Disconnected")
}

#[tauri::command]
pub fn ssh_state(pool: State<'_, Arc<ConnectionPool>>) -> SshState {
    let (connected, name, error) = pool.state();
    SshState {
        connected,
        server_name: name,
        server_host: None,
        error,
    }
}
