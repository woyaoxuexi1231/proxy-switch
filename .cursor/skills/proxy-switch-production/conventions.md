# Conventions

Match these unless the refactor’s job is to replace one convention everywhere.

## Frontend layout

```text
src/App.tsx                 shell: servers, SSH hook, card lists, dialog
src/App.css                 tokens, reset, app grid, shared .btn
src/components/*.tsx + *.css  one component, colocated CSS
src/hooks/useSshConnection.ts
src/hooks/useProxyStatus.ts
src/types/index.ts
src/utils/invoke.ts
```

Do not add `src/features/`, `src/services/`, or `src/api/` for forwarding wrappers.

## TypeScript

- Props interfaces named `Props` next to the component (current style).
- Shared domain types only in `src/types/index.ts`.
- IPC functions return `Promise<T>` with those types — no `any`.
- `ComponentId` is a string union; arrays `REMOTE_COMPONENTS` / `LOCAL_COMPONENTS` drive the UI.
- `getProxyState(status)` is the only mapping from `{installed, enabled}` →
  `not_installed | not_started | started`. Do not re-derive in CSS class logic.

## React

- Function components, named exports for components; `App` default export.
- Hooks: `useState` / `useEffect` / `useCallback` as already used. Do not add
  `useMemo` by default.
- Effects synchronize with external systems (keydown, fill form from status).
  Do not put enable/disable in an effect.
- `useProxyStatus` owns detect/enable/disable loading. Cards own form fields.
- Keys: `component` id or `server.id`, never array index for servers/cards.

Known weak spots — **fix when touching**, do not copy:

- Empty `catch {}` in `App.tsx` load/delete
- `ProxyCard` status→form `useEffect` omits field deps and only fills empties
- Error styling via `message.toLowerCase().includes('fail')`

## CSS

Tokens in `:root` (`src/App.css`): `--bg-*`, `--text-*`, `--border*`, `--success`,
`--danger`, `--warning`, `--accent`, `--radius-*`, `--text-xs`…`--text-xl`,
`--font-sans`, `--font-mono`.

Rules:

- New colors/spacing go through tokens, not one-off hex.
- Component CSS files for local classes (`proxy-card`, `sidebar`, `dialog`).
- Shared buttons: `.btn`, `.btn-primary`, `.btn-ghost`, `.btn-danger-outline`.
- Layout: app is `grid` 240px sidebar + main + 28px status bar; `height: 100vh`.
- No Tailwind, no CSS-in-JS, no new icon pack.

## invoke.ts

Group by domain (Server / SSH / Remote / Local) plus helpers:

```text
detectProxy / enableProxy / disableProxy (component, isRemote)
```

Add a new command wrapper here first, then call it from a hook.

Argument names must match Tauri’s camelCase conversion of Rust args
(`server_name` → `{ serverName }`, `component`, `config`, `input`, `name`).

## Rust style

- Commands: parse + dispatch. No XML/APT syntax in `commands/`.
- `OpResult::ok` / `OpResult::err` for user-facing outcomes.
- `Result<T, String>` for hard IPC failures (not connected, unknown component).
- Local IO/process: `tokio::task::spawn_blocking`.
- Windows child processes: `apply_no_window` in `proxy/local/mod.rs`.
- Tool install check: run `--version`, not “file exists on PATH”. npm/mvn are
  `.cmd` shims — keep the `cmd /C` fallback.
- Prefer existing crates (`quick-xml`, `regex`, `serde_json`) over new ones.

## Naming

| Kind | Pattern |
|---|---|
| Component id | `git_remote`, `npm_local` |
| Rust module struct | `GitRemoteModule`, `NpmLocalModule` |
| Command | `remote_detect`, `local_enable` |
| Hook | `useProxyStatus`, `useSshConnection` |
| UI | `ProxyCard`, `ServerDialog`, `ManualGuide` |

No `XxxManager`, `XxxHelper`, `TempComp`.

## Tests / validation

Repo has no frontend test runner today. Do not add Jest+Cypress for one function.
If you extract pure logic (Maven XML, URL parse), a small Rust unit test next to
the module is appropriate.

Always: typecheck/build the layer you changed.
