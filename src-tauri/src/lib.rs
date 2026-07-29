mod commands;
mod config;
pub mod models;
mod proxy;
mod ssh;

use std::sync::Arc;
use config::store::ConfigStore;
use ssh::connection::ConnectionPool;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .manage(ConfigStore::new())
        .manage(Arc::new(ConnectionPool::new()))
        .invoke_handler(tauri::generate_handler![
            // Server commands
            commands::server::get_servers,
            commands::server::add_server,
            commands::server::update_server,
            commands::server::delete_server,
            // SSH commands
            commands::ssh_cmd::ssh_connect,
            commands::ssh_cmd::ssh_disconnect,
            commands::ssh_cmd::ssh_state,
            // Remote proxy commands
            commands::remote_proxy::remote_detect,
            commands::remote_proxy::remote_detect_all,
            commands::remote_proxy::remote_enable,
            commands::remote_proxy::remote_disable,
            // Local proxy commands
            commands::local_proxy::local_detect,
            commands::local_proxy::local_detect_all,
            commands::local_proxy::local_enable,
            commands::local_proxy::local_disable,
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
