import { invoke } from '@tauri-apps/api/core';
import type { Server, ServerInput, ProxyConfig, ProxyStatus, OpResult, SshState } from '../types';

// ── Server ──────────────────────────────────────────────────────────────────

export async function getServers(): Promise<Server[]> {
  return invoke('get_servers');
}

export async function addServer(input: ServerInput): Promise<OpResult> {
  return invoke('add_server', { input });
}

export async function updateServer(input: ServerInput): Promise<OpResult> {
  return invoke('update_server', { input });
}

export async function deleteServer(name: string): Promise<OpResult> {
  return invoke('delete_server', { name });
}

// ── SSH ─────────────────────────────────────────────────────────────────────

export async function sshConnect(serverName: string): Promise<OpResult> {
  return invoke('ssh_connect', { serverName });
}

export async function sshDisconnect(): Promise<OpResult> {
  return invoke('ssh_disconnect');
}

export async function sshState(): Promise<SshState> {
  return invoke('ssh_state');
}

// ── Remote Proxy ────────────────────────────────────────────────────────────

export async function remoteDetect(component: string): Promise<ProxyStatus> {
  return invoke('remote_detect', { component });
}

export async function remoteEnable(
  component: string,
  config: ProxyConfig,
): Promise<OpResult> {
  return invoke('remote_enable', { component, config });
}

export async function remoteDisable(component: string): Promise<OpResult> {
  return invoke('remote_disable', { component });
}

// ── Local Proxy ─────────────────────────────────────────────────────────────

export async function localDetect(component: string): Promise<ProxyStatus> {
  return invoke('local_detect', { component });
}

export async function localEnable(
  component: string,
  config: ProxyConfig,
): Promise<OpResult> {
  return invoke('local_enable', { component, config });
}

export async function localDisable(component: string): Promise<OpResult> {
  return invoke('local_disable', { component });
}

// ── Helpers ─────────────────────────────────────────────────────────────────

export function detectProxy(
  component: string,
  isRemote: boolean,
): Promise<ProxyStatus> {
  return isRemote ? remoteDetect(component) : localDetect(component);
}

export function enableProxy(
  component: string,
  config: ProxyConfig,
  isRemote: boolean,
): Promise<OpResult> {
  return isRemote
    ? remoteEnable(component, config)
    : localEnable(component, config);
}

export function disableProxy(
  component: string,
  isRemote: boolean,
): Promise<OpResult> {
  return isRemote ? remoteDisable(component) : localDisable(component);
}
