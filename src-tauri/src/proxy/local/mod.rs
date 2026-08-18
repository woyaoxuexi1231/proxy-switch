// Shared utility functions for local proxy modules
use std::io::Read;
use std::process::{Command, Stdio};
use std::time::{Duration, Instant};

#[cfg(windows)]
mod path_env;

/// Load the user's real PATH before spawning git/npm/docker/mvn.
/// Safe to call from any thread; runs once per process.
pub fn ensure_process_path() {
    #[cfg(windows)]
    path_env::ensure();
}

fn apply_no_window(cmd: &mut Command) {
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        // CREATE_NO_WINDOW — prevents cmd.exe windows from flashing
        cmd.creation_flags(0x08000000);
    }
}

const TOOL_TIMEOUT: Duration = Duration::from_secs(8);

fn run_cmd(program: &str, args: &[&str]) -> (bool, String) {
    ensure_process_path();
    let direct = spawn_timeout(program, args);
    if direct.0 {
        return direct;
    }
    #[cfg(windows)]
    {
        // CreateProcessW does not search PATHEXT for .cmd/.bat (npm, mvn).
        if !program.eq_ignore_ascii_case("cmd") {
            return spawn_via_cmd(program, args);
        }
    }
    direct
}

fn spawn_timeout(program: &str, args: &[&str]) -> (bool, String) {
    let mut cmd = Command::new(program);
    cmd.args(args)
        .stdin(Stdio::null())
        .stdout(Stdio::piped())
        .stderr(Stdio::null());
    apply_no_window(&mut cmd);
    let mut child = match cmd.spawn() {
        Ok(c) => c,
        Err(_) => return (false, String::new()),
    };
    let start = Instant::now();
    loop {
        match child.try_wait() {
            Ok(Some(status)) => {
                let mut stdout = String::new();
                if let Some(mut out) = child.stdout.take() {
                    out.read_to_string(&mut stdout).ok();
                }
                return (status.success(), stdout.trim().to_string());
            }
            Ok(None) => {
                if start.elapsed() > TOOL_TIMEOUT {
                    let _ = child.kill();
                    let _ = child.wait();
                    return (false, String::new());
                }
                std::thread::sleep(Duration::from_millis(30));
            }
            Err(_) => return (false, String::new()),
        }
    }
}

#[cfg(windows)]
fn spawn_via_cmd(program: &str, args: &[&str]) -> (bool, String) {
    let line = windows_cmd_line(program, args);
    spawn_timeout("cmd", &["/D", "/S", "/C", &line])
}

#[cfg(windows)]
fn windows_cmd_line(program: &str, args: &[&str]) -> String {
    let mut parts = Vec::with_capacity(args.len() + 1);
    parts.push(quote_win(program));
    for arg in args {
        parts.push(quote_win(arg));
    }
    parts.join(" ")
}

#[cfg(windows)]
fn quote_win(s: &str) -> String {
    if s.is_empty() {
        return "\"\"".into();
    }
    let needs = s.chars().any(|c| {
        matches!(
            c,
            ' ' | '\t' | '"' | '&' | '|' | '<' | '>' | '^' | '%' | '(' | ')'
        )
    });
    if needs {
        format!("\"{}\"", s.replace('"', "\\\""))
    } else {
        s.to_string()
    }
}

/// Verify a tool is actually installed by running its version command.
/// Running the tool itself is more reliable than checking for a file on PATH —
/// a file on PATH doesn't mean it can run (broken installs, wrong-arch
/// binaries, and batch-file shims all pass a file check but fail to run).
pub fn tool_installed(tool: &str) -> bool {
    run_cmd(tool, &["--version"]).0
}

pub mod docker;
pub mod git;
pub mod maven;
pub mod npm;
