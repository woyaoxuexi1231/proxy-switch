use crate::models::Server;
use anyhow::{Context, Result};
use std::fs;
use std::path::PathBuf;

pub struct ConfigStore {
    dir: PathBuf,
}

impl ConfigStore {
    pub fn new() -> Self {
        let dir = dirs::config_dir()
            .unwrap_or_else(|| PathBuf::from("."))
            .join("proxy-switch");
        fs::create_dir_all(&dir).ok();
        Self { dir }
    }

    fn servers_path(&self) -> PathBuf {
        self.dir.join("servers.toml")
    }

    pub fn load_servers(&self) -> Vec<Server> {
        let path = self.servers_path();
        if !path.exists() {
            return vec![];
        }
        let content = match fs::read_to_string(&path) {
            Ok(c) => c,
            Err(_) => return vec![],
        };
        let parsed: toml::Value = match toml::from_str(&content) {
            Ok(v) => v,
            Err(_) => return vec![],
        };

        let mut servers = Vec::new();
        if let Some(table) = parsed.as_table() {
            for (key, value) in table {
                if key.starts_with("server:") {
                    let name = key.trim_start_matches("server:").to_string();
                    let host = value
                        .get("host")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string();
                    if host.is_empty() {
                        continue;
                    }
                    let port = value
                        .get("port")
                        .and_then(|v| v.as_integer())
                        .unwrap_or(22) as u16;
                    let user = value
                        .get("user")
                        .and_then(|v| v.as_str())
                        .unwrap_or("root")
                        .to_string();
                    let auth_mode = match value
                        .get("auth_mode")
                        .and_then(|v| v.as_str())
                        .unwrap_or("key")
                    {
                        "password" => crate::models::AuthMode::Password,
                        _ => crate::models::AuthMode::Key,
                    };
                    let ssh_key_path = value
                        .get("ssh_key")
                        .and_then(|v| v.as_str())
                        .filter(|s| !s.is_empty())
                        .map(|s| s.to_string());
                    let password = value
                        .get("password")
                        .and_then(|v| v.as_str())
                        .filter(|s| !s.is_empty())
                        .map(|s| s.to_string());
                    let description = value
                        .get("description")
                        .and_then(|v| v.as_str())
                        .unwrap_or("")
                        .to_string();

                    servers.push(Server {
                        id: name.clone(),
                        name,
                        host,
                        port,
                        user,
                        auth_mode,
                        ssh_key_path,
                        password,
                        description,
                    });
                }
            }
        }
        servers
    }

    pub fn save_server(&self, server: &Server) -> Result<()> {
        let path = self.servers_path();
        let mut parsed: toml::Value = if path.exists() {
            let content = fs::read_to_string(&path).unwrap_or_default();
            toml::from_str(&content).unwrap_or(toml::Value::Table(toml::value::Table::new()))
        } else {
            toml::Value::Table(toml::value::Table::new())
        };

        let section_key = format!("server:{}", server.name);
        let mut section = toml::value::Table::new();
        section.insert("host".into(), toml::Value::String(server.host.clone()));
        section.insert(
            "port".into(),
            toml::Value::Integer(server.port as i64),
        );
        section.insert("user".into(), toml::Value::String(server.user.clone()));
        section.insert(
            "auth_mode".into(),
            toml::Value::String(match server.auth_mode {
                crate::models::AuthMode::Key => "key".into(),
                crate::models::AuthMode::Password => "password".into(),
            }),
        );
        if let Some(ref key) = server.ssh_key_path {
            section.insert("ssh_key".into(), toml::Value::String(key.clone()));
        }
        if let Some(ref pw) = server.password {
            section.insert("password".into(), toml::Value::String(pw.clone()));
        }
        section.insert(
            "description".into(),
            toml::Value::String(server.description.clone()),
        );

        if let toml::Value::Table(ref mut t) = parsed {
            t.insert(section_key, toml::Value::Table(section));
        }
        let content = toml::to_string(&parsed).context("Failed to serialize config")?;
        fs::write(&path, content).context("Failed to write config file")?;
        Ok(())
    }

    pub fn delete_server(&self, name: &str) -> Result<bool> {
        let path = self.servers_path();
        if !path.exists() {
            return Ok(false);
        }
        let content = fs::read_to_string(&path).unwrap_or_default();
        let mut parsed: toml::Value =
            toml::from_str(&content).unwrap_or(toml::Value::Table(toml::value::Table::new()));

        let section_key = format!("server:{}", name);
        if let toml::Value::Table(ref mut t) = parsed {
            if t.remove(&section_key).is_some() {
                let content = toml::to_string(&parsed).context("Failed to serialize config")?;
                fs::write(&path, content).context("Failed to write config file")?;
                return Ok(true);
            }
        }
        Ok(false)
    }
}
