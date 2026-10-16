# Workspace Red Dots

An Omarchy shell plugin that adds red attention dots to workspace numbers when
apps on those workspaces send notifications. Visiting a workspace clears its dot.
Notifications on the workspace you are currently using do not add a dot.

Dots follow the app's **current workspace** when a new notification arrives.
No workspace numbers, usernames, or installed PWA IDs need to be configured.

## Preview

This screenshot shows the workspace indicators with a test notification dot on workspace 3.

![Workspace indicators with a notification dot on workspace 3](assets/workspace-red-dots.png)

## Requirements

- Omarchy 4 with its Quickshell plugin system
- Hyprland, Quickshell, and Python 3 (standard library only)
- Working desktop notifications from the relevant apps

Validated on Omarchy 4.0.4 / Hyprland 0.56.2. This plugin uses the Omarchy shell's
existing QML components and notification history. It is not a Waybar module and
does not support older Omarchy installations that use Waybar.

## Install locally

Download or clone this repository, then run from a terminal in your Omarchy session:

```sh
python3 install.py
```

The installer validates the plugin, backs up your existing plugin and shell
configuration, enables the widget, and restarts the shell. Application windows
stay open. If another custom workspace widget is active, it is disabled and this
plugin replaces it in the same slot. Its files are preserved.

The plugin ID is `community.workspace-red-dots`. Omarchy can also install this
repository through `omarchy plugin add <repository-git-url> --enable` once hosted.

For updates installed with `install.py`, rerun it. Existing local notification
routes are preserved. For Git-managed installations, use Omarchy's plugin update
command; save custom route changes separately before accepting a Git update.

## Files

| File | Purpose |
| --- | --- |
| `manifest.json` | Plugin registration and display name |
| `Workspaces.qml` | Workspace buttons, dot appearance, watcher lifecycle |
| `workspace-notifications.py` | Notification tracking, app detection, workspace lookup |
| `notification-routes.json` | Site patterns and app names for browser/PWA routing |
| `install.py` | Local installation with configuration backups |
| `tests/` | Synthetic routing tests without personal browser data |

Installed files: `~/.config/omarchy/plugins/community.workspace-red-dots/`.
Active widget selection: `~/.config/omarchy/shell.json`.
Dot state: `~/.local/state/omarchy/workspace-notification-dots.json`.
Backups: `~/.local/state/omarchy/plugin-backups/`.

To inspect pending workspace numbers:

```sh
python3 workspace-notifications.py --status
```

## App routing

Outlook and Teams routes are included. On each start, the watcher discovers PWA
IDs from the current user's installed `.desktop` launchers, matching their display
names. It uses the resulting ID to find the PWA's current Hyprland workspace.
Window-title matching provides a fallback if a matching launcher cannot be found.
Other apps are matched by their notification name and window class when unambiguous.

To add another browser app, edit the **installed** `notification-routes.json`:

```json
{
  "sites": ["chat\\.example\\.com"],
  "desktop_names": ["Example Chat"],
  "window_titles": ["\\bExample Chat\\b"]
}
```

`sites` contains regular expressions matched against the notification's app name
and body; when the body is empty, the summary can identify the site. This avoids
routing a message to a PWA just because its subject mentions a site.
`desktop_names` matches the app launcher's display name, ignoring a
trailing ` (PWA)`. `window_titles` contains fallback regular expressions. An
optional `class` substring can override discovery for unusual launchers. Use
`hyprctl clients -j` locally to inspect window classes; do not publish its output.
Restart with `omarchy restart shell` after changing routes.

## Appearance

Edit `notificationDot` in the installed `Workspaces.qml` to change its color,
size, or margins. The workspace list initially displays 1–6 and includes occupied
workspaces up to 10. Restart the shell after editing code.

## Behavior and limits

- Dots mean a notification arrived since your last visit, not an unread count.
- Moving an app changes routing of future notifications. An existing dot remains
  where the notification arrived until you visit that workspace.
- Ambiguous notifications are skipped rather than assigned to an arbitrary workspace.
- Browser notifications must identify their site to distinguish PWAs reliably.
- The app must emit an actual desktop notification. For Outlook, select Browser
  notification style and allow notifications for its site. Brave may also require
  “Use Google services for push messaging” to be enabled.
- The watcher polls once per second. Monitor bars share pending state using a file lock.
- This relies on Omarchy's notification snapshot format, which future Omarchy
  versions may change.

## Privacy

This repository contains source code, generic site patterns, synthetic tests, and
documentation. It does not include browser profiles, email, credentials,
notification history, screenshots, machine names, or personal home-directory paths.

At runtime the plugin reads local Omarchy notification snapshots, installed app
launchers, and Hyprland window metadata to match apps. Notification bodies and
window titles stay in memory; the plugin does not save them. It saves only
notification identities and pending workspace numbers. It makes no network
requests, includes no telemetry, and invokes no remote services. These statements
describe the plugin; Omarchy and the apps retain their own data independently.

## Disable / restore stock workspaces

```sh
omarchy plugin disable community.workspace-red-dots
omarchy plugin enable omarchy.workspaces
```

## Validate

```sh
omarchy plugin validate .
python3 -m unittest discover -s tests -v
```

The workspace button layout is adapted from Omarchy's MIT-licensed
`shell/plugins/bar/widgets/Workspaces.qml`. See `LICENSE` for attribution.
