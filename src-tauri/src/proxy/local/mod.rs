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

/// Verify a tool is actually installed by running its version command.
/// Running the tool itself is more reliable than checking for a file on PATH —
/// a file on PATH doesn't mean it can run (broken installs, wrong-arch
/// binaries, and batch-file shims all pass a file check but fail to run).
pub fn tool_installed(tool: &str) -> bool {
    #[cfg(windows)]
    {
        // Try the tool directly first (handles .exe). If that fails — e.g. npm
        // and mvn are .cmd batch shims that CreateProcessW can't resolve —
        // fall back to cmd.exe /C, which knows how to run batch files.
        if run_cmd(tool, &["--version"]).0 {
            return true;
        }
        let full = format!("{} --version", tool);
        run_cmd("cmd", &["/C", full.as_str()]).0
    }
    #[cfg(not(windows))]
    {
        run_cmd(tool, &["--version"]).0
    }
}

pub mod docker;
pub mod git;
pub mod maven;
pub mod npm;
