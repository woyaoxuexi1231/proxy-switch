// Shared utility functions for local proxy modules
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

fn tool_exists(tool: &str) -> bool {
    let mut cmd = Command::new("where");
    cmd.args([tool]);
    apply_no_window(&mut cmd);
    cmd.output()
        .map(|o| o.status.success())
        .unwrap_or(false)
}

pub mod docker;
pub mod git;
pub mod maven;
pub mod npm;
