#!/usr/bin/env python3
"""Map Omarchy notification snapshots to workspace attention dots.

Only workspace IDs and notification identities are retained, never message text.
"""
import argparse
import configparser
import fcntl
import json
import math
import os
from pathlib import Path
import re
import shlex
import subprocess
import time


def hypr(query):
    return json.loads(subprocess.check_output(
        ['hyprctl', '-j', query], stderr=subprocess.DEVNULL, timeout=2))


def desktop_entries():
    """Read local PWA identities without embedding anyone's installed app IDs."""
    roots = [Path(os.environ.get('XDG_DATA_HOME', str(Path.home() / '.local/share')))]
    roots += [Path(p) for p in os.environ.get('XDG_DATA_DIRS', '/usr/local/share:/usr/share').split(':') if p]
    entries = []
    for root in roots:
        for path in (root / 'applications').glob('*.desktop'):
            try:
                parser = configparser.ConfigParser(interpolation=None, strict=False)
                parser.read(path)
                entry = parser['Desktop Entry']
                args = shlex.split(entry.get('Exec', ''))
                app_id = next((arg.split('=', 1)[1] for arg in args if arg.startswith('--app-id=')), '')
                if app_id:
                    entries.append({'name': entry.get('Name', ''), 'app_id': app_id})
            except (OSError, ValueError, KeyError, configparser.Error):
                continue
    return entries


def resolve_routes(routes, entries):
    resolved = []
    for route in routes:
        names = {name.casefold() for name in route.get('desktop_names', [])}
        matches = []
        for entry in entries:
            # Omarchy app launchers commonly append " (PWA)" to the display name.
            name = re.sub(r'\s*\(PWA\)\s*$', '', entry['name'], flags=re.I).casefold()
            if name in names:
                matches.append(entry['app_id'].lower())
        resolved.append(dict(route, app_ids=matches))
    return resolved


def browser_family(value):
    value = str(value).lower()
    for family, names in (
        ('brave', ('brave',)),
        ('edge', ('msedge', 'microsoft edge', 'microsoft-edge')),
        ('vivaldi', ('vivaldi',)),
        ('firefox', ('firefox',)),
        ('chromium', ('chromium', 'chrome')),
    ):
        if any(name in value for name in names):
            return family
    return 'edge' if value == 'edge' else None


def workspace_for(notification, windows, routes):
    app = str(notification.get('app', '')).lower()
    if app in ('omarchy-action', 'notify-send', ''):
        return None
    # Prefer app name and body. Use the summary only when the body is empty:
    # message subjects can mention a site unrelated to the notifying PWA.
    # 4.5 lifts the browser origin out of body into source. Prefer that
    # explicit origin over links quoted in a message.
    source = str(notification.get('source', '')).strip()
    if '.' in source:
        route_fields = ('app', 'source')
    elif str(notification.get('body', '')).strip():
        route_fields = ('app', 'source', 'rawBody', 'body')
    else:
        route_fields = ('app', 'source', 'rawBody', 'summary')
    text = '\n'.join(str(notification.get(k, '')) for k in route_fields).lower()
    browser = browser_family(app)
    if browser:
        # Site URLs and installed app IDs can be shared across browsers.
        # Exclude another browser before preferring a PWA ID or window title.
        windows = [w for w in windows if browser_family(
            w.get('class') or w.get('initialClass', '')) in (None, browser)]
    matches = []
    # Prefer a PWA's site identity over the shared browser application name.
    for route in routes:
        if any(re.search(pattern, text) for pattern in route['sites']):
            identities = route.get('app_ids', [])
            if route.get('class'):
                identities = identities + [route['class'].lower()]
            exact = [w for w in windows if any(identity in
                     str(w.get('class', '')).lower() for identity in identities)]
            matches.extend(exact or [w for w in windows if any(
                re.search(pattern, str(w.get('title', '')), re.I)
                for pattern in route.get('window_titles', []))])
    if not matches:
        if browser:
            # A generic browser notification cannot distinguish its PWA windows.
            # Only use the normal browser window when no PWA shares the process.
            if any(str(w.get('class', '')).lower().startswith(('brave-', 'chrome-'))
                   and not str(w.get('class', '')).lower().endswith('browser') for w in windows):
                return None
        normalize = lambda s: re.sub(r'[^a-z0-9]', '', str(s).lower())
        name = normalize(app)
        matches = [w for w in windows if any(
            name == normalize(w.get(k, '')) or
            normalize(w.get(k, '')).endswith(name) or
            normalize(w.get(k, '')).startswith(name + 'browser')
            for k in ('class', 'initialClass'))]
    ids = {w.get('workspace', {}).get('id') for w in matches}
    ids = {i for i in ids if isinstance(i, int) and i > 0}
    return next(iter(ids)) if len(ids) == 1 else None


def snapshot_items(value):
    """Yield notification snapshots from object or array-based persistence."""
    if isinstance(value, list):
        for item in value:
            yield from snapshot_items(item)
    elif isinstance(value, dict):
        # Older Omarchy releases wrote one snapshot per JSON file. Newer
        # layouts may store several snapshots together in an array, either as
        # the file root or in one of the notification-history collections.
        collections = ('notifications', 'entries', 'pending', 'past', 'history')
        found_collection = False
        for key in collections:
            if isinstance(value.get(key), list):
                found_collection = True
                yield from snapshot_items(value[key])
        if not found_collection:
            yield value


def snapshots(directory):
    for p in list(directory.glob('*.json')) + list((directory / 'history').glob('*.json')):
        try:
            d = json.loads(p.read_text())
            yield from snapshot_items(d)
        except (OSError, ValueError):
            pass


def notification_timestamp(notification):
    """Return milliseconds for both legacy timestamp and 4.5 ts (seconds)."""
    try:
        value = notification.get('timestamp')
        if value is None:
            value = float(notification.get('ts', 0)) * 1000
        timestamp = float(value)
        return int(timestamp) if math.isfinite(timestamp) and timestamp > 0 else 0
    except (TypeError, ValueError, OverflowError):
        return 0


def notification_identity(notification):
    timestamp = notification_timestamp(notification)
    if notification.get('key'):
        # 4.5's key survives live -> history and sender replacement; the
        # original DBus id alone can be reused within a boot.
        return str(timestamp) + ':key:' + str(notification['key'])
    return str(timestamp) + ':' + str(notification.get('originalId', notification.get('id', '')))


def boot_identity():
    """Return this boot's ID and start time in milliseconds."""
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    with Path('/proc/stat').open() as stat:
        boot_seconds = next(
            int(line.split()[1]) for line in stat if line.startswith('btime '))
    return boot_id, boot_seconds * 1000


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status', action='store_true', help='Show pending workspace numbers and exit')
    parser.add_argument('--routes', type=Path, help='Use a different routing configuration')
    args = parser.parse_args()
    home = Path.home()
    state_home = Path(os.environ.get('XDG_STATE_HOME') or home / '.local/state')
    directory = state_home / 'omarchy/notifications'
    state_path = state_home / 'omarchy/workspace-notification-dots.json'
    if args.status:
        try:
            print(json.dumps(json.loads(state_path.read_text()).get('pending', [])))
        except FileNotFoundError:
            print('[]')
        return
    state_path.parent.mkdir(parents=True, exist_ok=True)
    route_path = args.routes or Path(__file__).with_name('notification-routes.json')
    routes = resolve_routes(json.loads(route_path.read_text()), desktop_entries())
    current_boot, boot_started = boot_identity()
    previous = None
    with state_path.with_suffix('.lock').open('a') as lock:
        while True:
            try:
                focused = hypr('activeworkspace').get('id')
                fcntl.flock(lock, fcntl.LOCK_EX)
                try:
                    try:
                        state = json.loads(state_path.read_text())
                    except (OSError, ValueError):
                        state = {'since': boot_started, 'seen': [], 'pending': []}
                    # Dots belong to the current session. Keep notifications
                    # generated during this boot, but discard older pending dots.
                    if state.get('boot_id') != current_boot:
                        state['pending'] = []
                        state['since'] = boot_started
                        state['boot_id'] = current_boot
                    before = json.dumps(state, sort_keys=True)
                    pending = set(state['pending'])
                    seen = set(state['seen'])
                    windows = None
                    for n in snapshots(directory):
                        timestamp = notification_timestamp(n)
                        key = notification_identity(n)
                        if timestamp < state['since'] or key in seen:
                            continue
                        if windows is None:
                            windows = hypr('clients')
                        workspace = workspace_for(n, windows, routes)
                        if workspace is not None and workspace != focused:
                            pending.add(workspace)
                        seen.add(key)
                    pending.discard(focused)
                    state['pending'] = sorted(pending)
                    state['seen'] = sorted(seen)[-512:]
                    if json.dumps(state, sort_keys=True) != before or not state_path.exists():
                        temporary = state_path.with_suffix('.tmp')
                        temporary.write_text(json.dumps(state))
                        temporary.chmod(0o600)
                        os.replace(temporary, state_path)
                    output = json.dumps(state['pending'])
                finally:
                    fcntl.flock(lock, fcntl.LOCK_UN)
                if output != previous:
                    print(output, flush=True)
                    previous = output
            except (OSError, ValueError, subprocess.SubprocessError, TypeError, KeyError):
                # Retry transient compositor restarts or half-written snapshots.
                pass
            time.sleep(1)


if __name__ == '__main__':
    main()
