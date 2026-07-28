use crate::config::store::ConfigStore;
use crate::models::{OpResult, Server, ServerInput};
use tauri::State;

#[tauri::command]
pub fn get_servers(store: State<'_, ConfigStore>) -> Vec<Server> {
    store.load_servers()
}

#[tauri::command]
pub fn add_server(store: State<'_, ConfigStore>, input: ServerInput) -> OpResult {
    let server = Server {
        id: input.name.clone(),
        name: input.name.clone(),
        host: input.host,
        port: input.port,
        user: input.user,
        auth_mode: input.auth_mode,
        ssh_key_path: input.ssh_key_path,
        password: input.password,
        description: input.description,
    };
    match store.save_server(&server) {
        Ok(_) => OpResult::ok(format!("Server '{}' saved", server.name)),
        Err(e) => OpResult::err(format!("Failed to save server: {}", e)),
    }
}

#[tauri::command]
pub fn update_server(store: State<'_, ConfigStore>, input: ServerInput) -> OpResult {
    let server = Server {
        id: input.name.clone(),
        name: input.name.clone(),
        host: input.host,
        port: input.port,
        user: input.user,
        auth_mode: input.auth_mode,
        ssh_key_path: input.ssh_key_path,
        password: input.password,
        description: input.description,
    };
    match store.save_server(&server) {
        Ok(_) => OpResult::ok(format!("Server '{}' updated", server.name)),
        Err(e) => OpResult::err(format!("Failed to update server: {}", e)),
    }
}

#[tauri::command]
pub fn delete_server(store: State<'_, ConfigStore>, name: String) -> OpResult {
    match store.delete_server(&name) {
        Ok(true) => OpResult::ok(format!("Server '{}' deleted", name)),
        Ok(false) => OpResult::err(format!("Server '{}' not found", name)),
        Err(e) => OpResult::err(format!("Failed to delete server: {}", e)),
    }
}
