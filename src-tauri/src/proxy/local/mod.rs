// Shared utility functions for local proxy modules
use std::path::PathBuf;
use std::process::Command;

fn apply_no_window(cmd: &mut Command) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // CREATE_NO_WINDOW — prevents cmd.exe windows from flashing
        cmd.creation_flags(0x08000000);
    }
}

fn run_cmd(program: &str, args: &[&str]) -> (bool, String) {
    let mut cmd = Command::new(program);
    cmd.args(args);
    apply_no_window(&mut cmd);
    match cmd.output() {
        Ok(out) => {
            let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
            (out.status.success(), stdout)
        }
        Err(_) => (false, String::new()),
    }
}

/// Fast tool existence check — searches PATH directly without spawning a process.
/// On Windows, checks for tool.exe, tool.cmd, and tool.bat.
pub fn find_in_path(tool: &str) -> bool {
    if let Ok(path_var) = std::env::var("PATH") {
        for dir in path_var.split(';') {
            let base = PathBuf::from(dir).join(tool);
            #[cfg(windows)]
            {
                if base.with_extension("exe").exists()
                    || base.with_extension("cmd").exists()
                    || base.with_extension("bat").exists()
                {
                    return true;
                }
            }
            #[cfg(not(windows))]
            {
                if base.exists() {
                    return true;
                }
            }
        }
    }
    false
}

pub mod docker;
pub mod git;
pub mod maven;
pub mod npm;
