# Changelog

## 1.1.0 — 2026-10-28

- Add Omarchy 4.5 notification storage support: second-based `ts` fields, stable notification keys, and explicit browser origins.
- Follow each monitor's workspace block on 4.5, including visiting workspaces from unplugged monitors; retain 4.0.x behavior when monitor assignments are absent.
- Keep notification dots attached to actual Hyprland IDs while displaying per-monitor slot labels.
- Add timestamp, identity, browser-origin, monitor-block and focus-command regression tests.
- Validate both 4.0.6 and 4.5.0-rc2 shell modules in isolated runtime tests.

## 1.0 — 2026-10-21

- Added appearance settings in `~/.config/omarchy/plugins/thooper.workspace-red-dots/config.json`.
- Set `dotPosition` to `top-left`, `top-right`, `bottom-left`, `bottom-right`, or `center` (over the workspace number).
- Set `dotColor` to any `#RRGGBB` color. Defaults preserve the existing top-right red dot (`#ff4545`).
- Reload appearance settings automatically when `config.json` changes; no shell restart is needed.

## 0.6 — 2026-10-20

- Read both per-notification object snapshots and array-based notification snapshots so workspace dots continue to track notifications across Omarchy 4 persistence formats.
