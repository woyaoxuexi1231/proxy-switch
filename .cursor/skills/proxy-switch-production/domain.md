# Domain invariants

Break these and the app is wrong even if UI looks fine.

## Components

| Id | Side | Mechanism | sudo | Mirror |
|---|---|---|---|---|
| `system_proxy` | remote | `/etc/environment` + `/etc/profile.d/proxy-switch.sh` | yes | no |
| `apt` | remote | `/etc/apt/apt.conf.d/proxy.conf` | yes | yes |
| `git_remote` | remote | `git config --global` (`~/.gitconfig`) | no | no |
| `docker_remote` | remote | systemd drop-in + `daemon.json` mirrors | yes | yes |
| `npm_remote` | remote | `npm config set` | no | yes |
| `maven_remote` | remote | `~/.m2/settings.xml` | no | yes |
| `git_local` | local | `git config --global` (`%USERPROFILE%\.gitconfig`) | — | no |
| `docker_local` | local | **read-only** Docker Desktop settings | — | no |
| `npm_local` | local | `npm config set` | — | no |
| `maven_local` | local | `%USERPROFILE%\.m2\settings.xml` | — | yes |

Frontend flags (must stay aligned):

- `GUIDE_ONLY = ['docker_local']` — hide Apply/Disable inputs; open manual guide
- `needsSudo = ['system_proxy', 'apt', 'docker_remote']` — show `sudo` tag
- Maven Aliyun shortcut: `https://maven.aliyun.com/repository/public`

## Three proxy states

From `installed` + `enabled` via `getProxyState`:

```text
not_installed  tool missing
not_started    installed, proxy/mirror not active
started        enabled (or show mirror when that is the active config)
```

`ProxyCard` may show `current_mirror` in the header even when thinking about
proxy URLs. Do not collapse mirror-only Maven/APT into “not started” if
`current_mirror` is set and the module reports enabled.

## docker_local (hard)

Never write Docker Desktop files or `daemon.json` for local Docker proxy.

Docker Desktop GUI is the only supported write path. `docker info` may show
`http.docker.internal:3128` — that is Desktop’s internal forwarder, not a bug
and not something to overwrite.

Enable/disable on this module should remain no-ops / guide messages.

## docker_remote

Writes systemd drop-in for HTTP/HTTPS proxy and may edit daemon mirrors.
Parent dir `/etc/systemd/system/docker.service.d` often **does not exist** —
`write_file(..., sudo=true)` must mkdir first (already in `SshSession::write_file`).

## Maven XML

Shared logic: `proxy/maven_xml.rs`.

- Proxy id: `proxy-switch-http`
- Mirror id: `proxy-switch-mirror`
- Patch existing `settings.xml`; do not clobber unrelated mirrors/proxies
- Enable with empty proxy but non-empty mirror is valid (Aliyun button)

## Windows local processes

- `CREATE_NO_WINDOW` so `cmd.exe` does not flash
- Detect via running the tool (`--version`), then `cmd /C` for `.cmd` shims
- Git: prefer `git config` then fall back to reading `.gitconfig` if needed

## SSH

- One live session. Connecting replaces the previous.
- Not connected → remote commands return a string error; UI disables expand
- Auth: key file (`shellexpand` `~`) or password from server record
- After enable/disable, re-run detect so header/status match the machine

## Apply validation (UI)

`ProxyCard` requires at least one of http/https proxy, or (if `supportsMirror`)
a mirror URL. Keep that, or replace it with the same rule in one place — do
not silently Apply empty config.

Disable is only enabled when state is `started`.

## Manual guide

Every module supplies `config_files` + `manual_setup_steps`.
The guide is part of the product: users learn the real files.
If you change how enable writes config, update the steps in the same change.

## Do not restore (deleted by design)

- CLI mode
- Batch profiles / one-click apply-all
- Electron / Python tkinter patterns from the pre-Tauri app
