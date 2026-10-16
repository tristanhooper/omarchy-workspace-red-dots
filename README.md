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

## Install

Install through Omarchy's plugin manager:

```sh
omarchy plugin add https://github.com/tristanhooper/omarchy-workspace-red-dots.git --enable
omarchy plugin disable omarchy.workspaces
```

The first command installs and enables the widget. The second disables the
built-in workspace widget so the bar does not show both. Because this plugin
uses a permanent marketplace ID without clone metadata, Omarchy does not swap
the built-in widget automatically. The plugin runs as your user inside the
Omarchy shell and does not need root privileges; it does not change monitor
settings or workspace assignments.

Update a Git-managed installation with Omarchy's plugin manager:

```sh
omarchy plugin update thooper.workspace-red-dots
```

The update replaces plugin files, including `notification-routes.json`. Save
your custom route changes before updating if you edited that file.

## Files

| File | Purpose |
| --- | --- |
| `manifest.json` | Plugin registration and display name |
| `Workspaces.qml` | Workspace buttons, dot appearance, watcher lifecycle |
| `workspace-notifications.py` | Notification tracking, app detection, workspace lookup |
| `notification-routes.json` | Site patterns and app names for browser/PWA routing |
| `tests/` | Synthetic routing tests without personal browser data |

Installed files: `~/.config/omarchy/plugins/thooper.workspace-red-dots/`.
Active widget selection: `~/.config/omarchy/shell.json`.
Dot state: `~/.local/state/omarchy/workspace-notification-dots.json`.

To inspect pending workspace numbers:

```sh
python3 workspace-notifications.py --status
```

## App routing

The default web app routes are:

| App | Site identity in notification |
| --- | --- |
| Outlook | `outlook.office.com`, `outlook.office365.com`, `outlook.live.com`, `outlook.cloud.microsoft` |
| Microsoft Teams | `teams.microsoft.com`, `teams.cloud.microsoft` |
| WhatsApp | `web.whatsapp.com` |
| Discord | `discord.com` |
| Basecamp | `launchpad.37signals.com`, `basecamp.com` |
| Google Contacts | `contacts.google.com` |
| Google Maps | `maps.google.com`, `google.com/maps` |
| Google Messages | `messages.google.com` |
| Google Photos | `photos.google.com` |
| HEY | `app.hey.com` |
| X | `x.com` |
| YouTube | `youtube.com` |
| Zoom | `app.zoom.us`, `zoom.us` |

These include the web apps bundled with Omarchy. On each start, the watcher also
discovers PWA IDs from the current user's installed `.desktop` launchers when
available. It uses an app ID to find the PWA's current Hyprland workspace, with
window-title matching as a fallback.

Native apps such as Slack, Thunderbird, Signal, Element, Telegram Desktop,
Spotify, and Dropbox use generic matching between the notification app name and
window class; they do not need site routes when that match is unambiguous. The
Omarchy Package and AUR installers can add other native apps, which use the same
generic matching.

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

## Remove / restore stock workspaces

```sh
omarchy plugin remove thooper.workspace-red-dots
omarchy plugin enable omarchy.workspaces
```

Removing the plugin deletes its installed plugin files through Omarchy. The
plugin does not carry clone metadata, so removal does not automatically restore
the built-in widget; the second command enables it again.

## Validate

```sh
omarchy plugin validate .
python3 -m unittest discover -s tests -v
```

The workspace button layout is adapted from Omarchy's MIT-licensed
`shell/plugins/bar/widgets/Workspaces.qml`. See `LICENSE` for attribution.
