#!/usr/bin/env python3
"""Install or update Workspace Red Dots in the current user's Omarchy shell."""
import datetime
import json
from pathlib import Path
import shutil
import subprocess


def run(*args):
    subprocess.run(args, check=True)


def main():
    source = Path(__file__).resolve().parent
    manifest = json.loads((source / 'manifest.json').read_text())
    for program in ('python3', 'hyprctl', 'omarchy', 'omarchy-shell'):
        if not shutil.which(program):
            raise SystemExit(f'Missing requirement: {program}')
    run('omarchy', 'plugin', 'validate', str(source))
    target = Path.home() / '.config/omarchy/plugins' / manifest['id']
    stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = Path.home() / '.local/state/omarchy/plugin-backups' / stamp
    backup.mkdir(parents=True)
    if target.exists():
        shutil.copytree(target, backup / manifest['id'])
    config = Path.home() / '.config/omarchy/shell.json'
    if config.exists():
        shutil.copy2(config, backup / 'shell.json')
    # Restore the stock widget before replacing another workspace clone, so the
    # new plugin occupies the same slot instead of adding duplicate buttons.
    other_clones = []
    if config.exists():
        layout = json.loads(config.read_text()).get('bar', {}).get('layout', {})
        for section in layout.values():
            if not isinstance(section, list):
                continue
            for item in section:
                plugin_id = item.get('id', '') if isinstance(item, dict) else ''
                if not plugin_id or plugin_id == manifest['id']:
                    continue
                existing = target.parent / plugin_id / 'manifest.json'
                if existing.exists():
                    metadata = json.loads(existing.read_text())
                    if metadata.get('omarchy', {}).get('clonedFrom') == 'omarchy.workspaces':
                        other_clones.append(plugin_id)
    target.mkdir(parents=True, exist_ok=True)
    for name in ('manifest.json', 'Workspaces.qml', 'workspace-notifications.py', 'notification-routes.json'):
        # Preserve local routing customizations when updating the plugin.
        if name == 'notification-routes.json' and (target / name).exists():
            continue
        shutil.copy2(source / name, target / name)
    run('omarchy', 'plugin', 'validate', str(target))
    run('omarchy-shell', 'shell', 'rescanPlugins')
    for plugin_id in other_clones:
        run('omarchy', 'plugin', 'disable', plugin_id)
    run('omarchy', 'plugin', 'enable', manifest['id'])
    run('omarchy', 'restart', 'shell')
    print(f'Installed {manifest["name"]} in {target}')
    print(f'Previous configuration backed up to {backup}')


if __name__ == '__main__':
    main()
