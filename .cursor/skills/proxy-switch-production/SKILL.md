---
name: proxy-switch-production
description: >-
  Guides production-quality implementation and refactoring of Proxy Switch,
  a Tauri 2 desktop app (React/TypeScript UI + Rust backend for SSH and
  local/remote proxy config). Use when refactoring, adding a proxy component,
  changing ProxyCard/Sidebar/invoke/commands, editing Rust proxy modules,
  or when the user mentions 重构, 生产质量, production, or architecture.
---

# Proxy Switch Production Engineer

You are the production engineer for **this** codebase, not a generic frontend generator.

Proxy Switch is a small Windows desktop app: one window, no router, no UI kit.
Frontend renders and orchestrates. Rust owns SSH, processes, and config files.

Goal:

> Ship the simplest production-quality change that preserves one product system,
> keeps the IPC contract honest, and remains maintainable months later.

This is not a marketing site. Do not apply web-app architecture (routes, auth
guards, Redux, design-system monorepos) unless the user explicitly asks.

---

## Read first

Before writing code, read the matching reference:

- Layers, IPC, add-component checklist → [architecture.md](architecture.md)
- File/code conventions to match → [conventions.md](conventions.md)
- Component invariants that must not break → [domain.md](domain.md)

Then read the files you will actually change. Match existing patterns.
If the local pattern is weak, improve it in place — do not introduce a second system.

---

## Core philosophy

> Understand the flow before moving files.

> Keep work in the correct layer: view, hook, invoke, command, proxy module, SSH/IO.

> Prefer simple architecture over abstraction.

> Prefer explicit data flow over cleverness.

> Do not optimize for fewer lines or “AI-looking” UI.

> Comments explain why (platform quirks, security, race handling) — never what.

> Every async path needs loading, success, empty, and failure behavior.

> Visual consistency is an engineering constraint: CSS variables in `src/App.css`.

---

## Layer law (non-negotiable)

| Layer | May do | Must not do |
|---|---|---|
| React components | Render, local UI state, call hooks | `invoke`, SSH, filesystem, spawn processes |
| Hooks | Own async lifecycle for one concern | Duplicate IPC wrappers |
| `src/utils/invoke.ts` | Typed Tauri IPC only | Business rules, UI |
| `src/types/index.ts` | Mirror Rust `models.rs` | Drift from serde names |
| Tauri commands | Parse args, call modules, return `OpResult` / `ProxyStatus` | Embed component-specific config syntax |
| `proxy/remote/*` / `proxy/local/*` | Detect / status / enable / disable | UI strings beyond `OpResult.message` and manual steps |
| `ssh/connection.rs` | Session, pool, file/exec helpers | Per-component proxy logic |
| `config/store.rs` | Persist servers TOML | Proxy enable/disable |

Frontend talks to Rust **only** through `invoke.ts`.
Never call `@tauri-apps/api` `invoke` from a component.

If you change `src-tauri/src/models.rs`, update `src/types/index.ts` in the same change.
Serde names are snake_case (`http_proxy`, `auth_mode`, `git_remote`). Keep TS fields identical.

---

## Product invariants (do not “fix” unless asked)

- Per-component cards. No batch profiles, no CLI mode.
- Remote = Ubuntu via SSH. Local = Windows.
- Only **one** SSH session at a time (`ConnectionPool`).
- Zero UI libraries. Hand-written CSS. Tokens live in `src/App.css`.
- `docker_local` is **guide-only**: detect/status/manual steps, never write Docker files.
- Do not add React Router, Redux/Zustand, Tailwind, component kits, or i18n frameworks.
- Do not put secrets in source. Do not log passwords or SSH keys.

---

## Complexity budget

This is a **small desktop tool**. Enough:

```text
src/components  src/hooks  src/types  src/utils/invoke.ts
src-tauri commands / proxy / ssh / config / models
```

Not enough justification for: feature folders, global store, server-state library,
shared “design system package”, plugin runtime, or micro-frontends.

Do not under-structure either: do not dump new business logic into `App.tsx`
or turn `ProxyCard.tsx` into a second god file. Extract a hook or a module.

---

## Refactoring workflow

Do not rewrite the app. Work in slices.

```text
1. Name the user-visible behavior that must stay identical
2. Name the layer(s) that should change
3. Read current code + the relevant section of domain.md
4. List IPC / type / ComponentId touchpoints
5. Change one concern
6. Keep loading / error / empty paths
7. Typecheck + build
8. Self-review against the checklist below
```

**Frontend-only refactor** — CSS, component split, hook extraction, a11y.
Do not “clean up” Rust in the same pass.

**Backend-only refactor** — module extraction, command thinning, SSH helpers.
Do not restyle UI in the same pass.

**Cross-layer refactor** — new component, model field, command rename.
Update in one change: `models.rs` → commands → `types/index.ts` → `invoke.ts` → UI.

When extracting:

- UI state stays in the component (expanded, form fields, dialog open).
- Server/proxy async stays in hooks (`useProxyStatus`, `useSshConnection`).
- IPC stays in `invoke.ts`.
- Config syntax stays in the proxy module (git config, apt conf, settings.xml).

Do not generate 20 unfinished files before one flow works end-to-end.

---

## Priority order

```text
Correctness (actual git/npm/apt/docker/maven config)
  > Security (no XSS, no leaked secrets, no silent sudo failure)
  > Explicit layer ownership
  > Maintainability
  > Honest loading / error UX
  > Accessibility of controls already in the window
  > Performance (SSH and child processes, not bundle fashion)
  > Visual polish
```

Do not ship a prettier card that writes the wrong `settings.xml`.

---

## State ownership

Ask before adding state:

```text
Is this UI-ephemeral (card expanded, dialog open)?
Is this form draft (proxy URL fields)?
Is this backend truth (ProxyStatus, server list, SSH connected)?
```

Keep ephemeral state local. Do not globalize checkboxes.

`useSshConnection` owns connection flags.
`useProxyStatus` owns per-card status/loading/message.
`App` owns server list + which dialog is open.

Remote cards are disabled until `connected`. Local cards pass `connected={true}`.

After enable/disable, re-detect — do not trust the client form as status.

---

## Interaction states are mandatory

Every invoke path needs:

- **Loading** — disable the action, show detecting/saving
- **Empty** — e.g. no servers; status not checked
- **Error** — `OpResult.success === false` and thrown invoke errors; show `message`
- **Success** — refresh status; do not only toast and leave stale UI

Do not swallow errors with empty `catch {}` unless the operation is explicitly
best-effort (and then still leave UI consistent).

Do not classify errors by whether the string contains `"fail"` / `"error"` if
you can use `OpResult.success` instead.

---

## Security

- Do not `dangerouslySetInnerHTML` or assign untrusted HTML.
- Manual guide commands are app-authored, but still render as text/`<code>`, not HTML.
- SSH passwords currently persist in `%APPDATA%\proxy-switch\servers.toml`. Do not
  log them, dump them in UI errors, or copy them into extra files.
- Remote root writes use `sudo tee` via base64. Preserve quoting/encoding; do not
  interpolate unsanitized paths/content into shell strings without the existing helpers.
- Windows local spawns must keep `CREATE_NO_WINDOW` (`0x08000000`).
- Frontend permission-looking UI (hiding Apply) is not a security boundary.

---

## Accessibility (desktop window)

- Real `<button>` / `<input>` / `<label>` — not `div` + onClick.
- Visible focus; Escape closes `ServerDialog` (already).
- Do not rely on color alone for proxy state (`StatusIndicator` text labels stay).
- Overlays: one dialog system; backdrop click + Escape; do not stack modals.

---

## Comments

Write comments for:

- Why Docker Desktop proxy is never written
- Why npm/mvn detection falls back to `cmd /C` on Windows
- Why sudo writes mkdir the parent dir before `tee`
- Why Maven entries use fixed IDs (`proxy-switch-http`, `proxy-switch-mirror`)

Delete comments that merely narrate the next line.

When behavior changes, update or delete the nearby comment.

---

## Anti-patterns for this repo

Reject:

- Second styling system (Tailwind + existing CSS)
- Raw `invoke` in components
- New `ComponentId` in only one of TS / Rust / command parse / card lists
- Restoring batch profiles or CLI
- Writing `daemon.json` to “fix” Docker Desktop proxy
- Fetch/detect inside presentational-only bits that should stay dumb (`StatusIndicator`)
- Silent `catch {}` on save/delete/connect
- `any` to silence IPC type mismatch
- Giant new `utils.ts` junk drawer
- Rewriting Vue patterns, Next.js patterns, or Electron patterns into this app

---

## Self-review before delivery

### Behavior

- Enable/disable/detect still match [domain.md](domain.md) for touched components
- SSH still single-session; disconnect clears remote UI usability
- `docker_local` still does not write files

### Architecture

- Change sits in the correct layer
- No second IPC or state pattern
- `models.rs` and `src/types/index.ts` still agree

### UX

- Loading/error/empty exist for the changed flow
- CSS uses tokens, not random hex
- Buttons remain real buttons

### Validation

- `npx tsc --noEmit` (or `npm run build`) for frontend changes
- `cargo check` in `src-tauri` for Rust changes
- Cross-layer: both

Do not claim done because the generated UI “looks right.”

---

## Decision rule

When two implementations are valid, prefer the one that:

1. Preserves real proxy/SSH behavior
2. Preserves security (shell, secrets, XSS)
3. Keeps state and side effects in the documented layer
4. Reuses ProxyCard / ProxyModule / invoke patterns
5. Avoids new dependencies
6. Has predictable loading and failure
7. Is easier to understand
8. Documents non-obvious platform decisions
9. Still feels like one product, not a demo island
