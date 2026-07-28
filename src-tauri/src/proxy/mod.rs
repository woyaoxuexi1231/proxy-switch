use crate::models::{OpResult, ProxyConfig, ProxyStatus};
use crate::ssh::connection::SshSession;

pub trait ProxyModule: Send + Sync {
    fn name(&self) -> &'static str;
    fn description(&self) -> &'static str;
    fn config_files(&self) -> Vec<String>;
    fn manual_steps(&self) -> Vec<(String, Vec<String>)>;

    fn detect(&self, session: &SshSession) -> bool;
    fn status(&self, session: &SshSession) -> ProxyStatus;
    fn enable(&self, session: &SshSession, config: &ProxyConfig) -> OpResult;
    fn disable(&self, session: &SshSession) -> OpResult;
}

pub mod local;
pub mod remote;
