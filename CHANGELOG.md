# Changelog

## 1.0 — 2026-10-21

- Added appearance settings in `~/.config/omarchy/plugins/thooper.workspace-red-dots/config.json`.
- Set `dotPosition` to `top-left`, `top-right`, `bottom-left`, `bottom-right`, or `center` (over the workspace number).
- Set `dotColor` to any `#RRGGBB` color. Defaults preserve the existing top-right red dot (`#ff4545`).
- Reload appearance settings automatically when `config.json` changes; no shell restart is needed.

## 0.6 — 2026-10-20

- Read both per-notification object snapshots and array-based notification snapshots so workspace dots continue to track notifications across Omarchy 4 persistence formats.
