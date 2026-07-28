// Shared utility functions for local proxy modules
use std::process::Command;

fn run_cmd(program: &str, args: &[&str]) -> (bool, String) {
    match Command::new(program).args(args).output() {
        Ok(out) => {
            let stdout = String::from_utf8_lossy(&out.stdout).trim().to_string();
            (out.status.success(), stdout)
        }
        Err(_) => (false, String::new()),
    }
}

fn tool_exists(tool: &str) -> bool {
    Command::new("where")
        .args([tool])
        .output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

pub mod docker;
pub mod git;
pub mod maven;
pub mod npm;
