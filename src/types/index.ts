export interface Server {
  id: string;
  name: string;
  host: string;
  port: number;
  user: string;
  auth_mode: 'key' | 'password';
  ssh_key_path?: string;
  password?: string;
  description: string;
}

export interface ServerInput {
  name: string;
  host: string;
  port: number;
  user: string;
  auth_mode: 'key' | 'password';
  ssh_key_path?: string;
  password?: string;
  description: string;
}

export interface ProxyConfig {
  http_proxy: string;
  https_proxy: string;
  no_proxy: string;
  mirror: string;
}

export type ComponentId =
  | 'system_proxy'
  | 'apt'
  | 'git_remote'
  | 'docker_remote'
  | 'npm_remote'
  | 'maven_remote'
  | 'git_local'
  | 'docker_local'
  | 'npm_local'
  | 'maven_local';

export const REMOTE_COMPONENTS: ComponentId[] = [
  'system_proxy',
  'apt',
  'git_remote',
  'docker_remote',
  'npm_remote',
  'maven_remote',
];

export const LOCAL_COMPONENTS: ComponentId[] = [
  'git_local',
  'docker_local',
  'npm_local',
  'maven_local',
];

export interface ManualStep {
  title: string;
  commands: string[];
}

export interface ProxyStatus {
  component: ComponentId;
  installed: boolean;
  enabled: boolean;
  current_http_proxy: string | null;
  current_https_proxy: string | null;
  current_no_proxy: string | null;
  current_mirror: string | null;
  config_files: string[];
  manual_setup_steps: ManualStep[];
}

/** Three distinct proxy states */
export type ProxyState = 'not_installed' | 'not_started' | 'started';

export function getProxyState(status: ProxyStatus | null): ProxyState | null {
  if (!status) return null;
  if (!status.installed) return 'not_installed';
  if (!status.enabled) return 'not_started';
  return 'started';
}

export const PROXY_STATE_LABEL: Record<ProxyState, string> = {
  not_installed: 'NOT INSTALLED',
  not_started: 'NOT STARTED',
  started: 'ENABLED',
};

export interface OpResult {
  success: boolean;
  message: string;
}

export interface SshState {
  connected: boolean;
  server_name: string | null;
  server_host: string | null;
  error: string | null;
}

export const COMPONENT_LABELS: Record<ComponentId, string> = {
  system_proxy: 'System Proxy (Remote)',
  apt: 'APT (Remote)',
  git_remote: 'Git (Remote)',
  docker_remote: 'Docker (Remote)',
  npm_remote: 'npm (Remote)',
  maven_remote: 'Maven (Remote)',
  git_local: 'Git (Local)',
  docker_local: 'Docker (Local)',
  npm_local: 'npm (Local)',
  maven_local: 'Maven (Local)',
};

export const COMPONENT_SHORT: Record<ComponentId, string> = {
  system_proxy: 'System Proxy',
  apt: 'APT',
  git_remote: 'Git',
  docker_remote: 'Docker',
  npm_remote: 'npm',
  maven_remote: 'Maven',
  git_local: 'Git',
  docker_local: 'Docker',
  npm_local: 'npm',
  maven_local: 'Maven',
};
