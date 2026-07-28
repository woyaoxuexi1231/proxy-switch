use crate::config::store::ConfigStore;
use crate::models::{OpResult, SshState};
use crate::ssh::connection::ConnectionPool;
use tauri::State;

#[tauri::command]
pub fn ssh_connect(
    store: State<'_, ConfigStore>,
    pool: State<'_, ConnectionPool>,
    server_name: String,
) -> OpResult {
    let servers = store.load_servers();
    let server = match servers.iter().find(|s| s.name == server_name) {
        Some(s) => s.clone(),
        None => return OpResult::err(format!("Server '{}' not found", server_name)),
    };
    match pool.connect(&server) {
        Ok(_) => OpResult::ok(format!("Connected to {}", server.label())),
        Err(e) => OpResult::err(format!("Connection failed: {}", e)),
    }
}

#[tauri::command]
pub fn ssh_disconnect(pool: State<'_, ConnectionPool>) -> OpResult {
    pool.disconnect();
    OpResult::ok("Disconnected")
}

#[tauri::command]
pub fn ssh_state(pool: State<'_, ConnectionPool>) -> SshState {
    let (connected, name, error) = pool.state();
    let (server_name, server_host) = if let Some(ref n) = name {
        // Try to get host from the connected session
        (Some(n.clone()), None)
    } else {
        (None, None)
    };
    SshState {
        connected,
        server_name,
        server_host,
        error,
    }
}
