//! Rebuild process PATH from the registry + well-known install dirs.
//!
//! NSIS "Run the app" (and browsers launching the installer) inherit a stripped
//! PATH — often just System32. Git/npm/docker then look missing until the user
//! starts the app from Explorer, which loads HKCU/HKLM Environment. Reading
//! those keys ourselves makes first-launch detection match the second launch.

use std::collections::HashSet;
use std::path::{Path, PathBuf};
use std::sync::Once;
use winreg::enums::{HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE};
use winreg::RegKey;

static INIT: Once = Once::new();

pub fn ensure() {
    INIT.call_once(refresh);
}

fn refresh() {
    import_missing_user_env();

    let mut parts: Vec<String> = Vec::new();
    let mut seen = HashSet::new();

    for dir in common_tool_dirs() {
        if dir.is_dir() {
            push_path(&mut parts, &mut seen, &dir.to_string_lossy());
        }
    }
    for exe_name in ["git.exe", "docker.exe", "node.exe", "mvn.cmd"] {
        if let Some(dir) = app_path_dir(exe_name) {
            push_path(&mut parts, &mut seen, &dir);
        }
    }

    let user = read_path_value(HKEY_CURRENT_USER, "Environment");
    let machine = read_path_value(
        HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
    );
    let current = std::env::var("PATH").unwrap_or_default();

    for raw in [user, machine, current] {
        for piece in raw.split(';') {
            push_path(&mut parts, &mut seen, piece);
        }
    }

    if !parts.is_empty() {
        std::env::set_var("PATH", parts.join(";"));
    }
}

fn push_path(parts: &mut Vec<String>, seen: &mut HashSet<String>, piece: &str) {
    let trimmed = piece.trim();
    if trimmed.is_empty() {
        return;
    }
    let key = trimmed.to_ascii_lowercase();
    if seen.insert(key) {
        parts.push(trimmed.to_string());
    }
}

fn common_tool_dirs() -> Vec<PathBuf> {
    let mut dirs = vec![
        PathBuf::from(r"C:\Program Files\Git\cmd"),
        PathBuf::from(r"C:\Program Files\Git\bin"),
        PathBuf::from(r"C:\Program Files (x86)\Git\cmd"),
        PathBuf::from(r"C:\Program Files\nodejs"),
        PathBuf::from(r"C:\Program Files\Docker\Docker\resources\bin"),
        PathBuf::from(r"C:\ProgramData\chocolatey\bin"),
    ];
    if let Some(local) = dirs::data_local_dir() {
        dirs.push(local.join("Programs").join("Git").join("cmd"));
        dirs.push(local.join("Programs").join("Git").join("bin"));
    }
    if let Some(roaming) = dirs::config_dir() {
        dirs.push(roaming.join("npm"));
        dirs.push(roaming.join("nvm"));
    }
    if let Some(home) = dirs::home_dir() {
        dirs.push(home.join("scoop").join("shims"));
        dirs.push(home.join("AppData").join("Local").join("fnm"));
        dirs.push(
            home.join("AppData")
                .join("Local")
                .join("Programs")
                .join("fnm"),
        );
    }
    dirs
}

fn import_missing_user_env() {
    let Ok(env) = RegKey::predef(HKEY_CURRENT_USER).open_subkey("Environment") else {
        return;
    };
    for item in env.enum_values().flatten() {
        let (name, _) = item;
        if name.eq_ignore_ascii_case("PATH") {
            continue;
        }
        if std::env::var_os(&name).is_some() {
            continue;
        }
        let Ok(val) = env.get_value::<String, _>(&name) else {
            continue;
        };
        if !val.is_empty() {
            std::env::set_var(&name, val);
        }
    }
}

fn read_path_value(hive: winreg::HKEY, subkey: &str) -> String {
    let Ok(key) = RegKey::predef(hive).open_subkey(subkey) else {
        return String::new();
    };
    key.get_value::<String, _>("Path")
        .or_else(|_| key.get_value::<String, _>("PATH"))
        .unwrap_or_default()
}

fn app_path_dir(exe_name: &str) -> Option<String> {
    let relative = format!(r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}");
    let wow = format!(
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\App Paths\{exe_name}"
    );
    for hive in [HKEY_CURRENT_USER, HKEY_LOCAL_MACHINE] {
        let key = RegKey::predef(hive);
        let opened = key.open_subkey(&relative).or_else(|_| key.open_subkey(&wow));
        let Ok(k) = opened else {
            continue;
        };
        let Ok(val) = k.get_value::<String, _>("") else {
            continue;
        };
        let path = Path::new(val.trim_matches('"'));
        if let Some(parent) = path.parent() {
            if parent.is_dir() {
                return Some(parent.to_string_lossy().into_owned());
            }
        }
    }
    None
}
