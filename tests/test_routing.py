import importlib.util
import json
from pathlib import Path
import unittest
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dots', ROOT / 'workspace-notifications.py')
dots = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dots)


class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.routes = dots.resolve_routes(
            json.loads((ROOT / 'notification-routes.json').read_text()),
            [{'name': 'Outlook (PWA)', 'app_id': 'test-outlook-app'},
             {'name': 'Microsoft Teams (PWA)', 'app_id': 'test-teams-app'}])
        self.windows = [
            {'class': 'brave-test-outlook-app-Profile' , 'workspace': {'id': 2}},
            {'class': 'brave-test-teams-app-Profile' , 'workspace': {'id': 3}},
            {'class': 'brave-browser', 'workspace': {'id': 4}},
        ]

    def test_snapshots_reads_legacy_objects_and_array_snapshots(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            history = root / 'history'
            history.mkdir()
            legacy = {'id': 1, 'timestamp': 100, 'app': 'Legacy'}
            current = [
                {'id': 2, 'timestamp': 200, 'app': 'Current A'},
                {'id': 3, 'timestamp': 300, 'app': 'Current B'},
            ]
            (root / 'legacy.json').write_text(json.dumps(legacy))
            (history / 'current.json').write_text(json.dumps(current))

            found = list(dots.snapshots(root))

        self.assertEqual(
            {(item['id'], item['timestamp']) for item in found},
            {(1, 100), (2, 200), (3, 300)},
        )

    def test_snapshots_reads_arrays_nested_in_notification_state(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / 'notifications.json').write_text(json.dumps({
                'notifications': [
                    {'id': 4, 'timestamp': 400, 'app': 'Current'},
                ],
                'dnd': False,
            }))

            found = list(dots.snapshots(root))

        self.assertEqual([(item['id'], item['timestamp']) for item in found], [(4, 400)])

    def test_outlook_follows_window_when_moved(self):
        notification = {'app': 'Brave', 'body': 'https://outlook.office.com New mail'}
        self.assertEqual(dots.workspace_for(notification, self.windows, self.routes), 2)
        self.windows[0]['workspace']['id'] = 3
        self.windows[1]['workspace']['id'] = 2
        self.assertEqual(dots.workspace_for(notification, self.windows, self.routes), 3)

    def test_teams_is_distinct_from_outlook(self):
        self.assertEqual(dots.workspace_for(
            {'app': 'Brave', 'body': 'https://teams.cloud.microsoft New chat'},
            self.windows, self.routes), 3)

    def test_outlook_notifications_stay_in_the_notifying_browser(self):
        self.windows.append({
            'class': 'chromium', 'title': 'Mail - Outlook - Chromium',
            'workspace': {'id': 4},
        })
        for app, expected in [('Brave', 2), ('Chromium', 4)]:
            with self.subTest(app=app):
                self.assertEqual(dots.workspace_for(
                    {'app': app, 'body': 'outlook.office.com'},
                    self.windows, self.routes), expected)

    def test_shared_pwa_ids_do_not_cross_browser_families(self):
        self.windows.append({
            'class': 'chrome-test-outlook-app-Default',
            'workspace': {'id': 4},
        })
        for app, expected in [('Brave', 2), ('Chromium', 4)]:
            with self.subTest(app=app):
                self.assertEqual(dots.workspace_for(
                    {'app': app, 'body': 'outlook.office.com'},
                    self.windows, self.routes), expected)

    def test_whatsapp_pwa_notification_routes_by_site_and_window_title(self):
        routes = dots.resolve_routes(
            json.loads((ROOT / 'notification-routes.json').read_text()), [])
        windows = [{
            'class': 'brave-web.whatsapp.com__-Default',
            'title': 'WhatsApp',
            'workspace': {'id': 7},
        }]
        self.assertEqual(dots.workspace_for(
            {'app': 'Brave', 'body': 'New message from web.whatsapp.com'},
            windows, routes), 7)

    def test_omarchy_bundled_webapps_route_by_site_and_title(self):
        routes = dots.resolve_routes(
            json.loads((ROOT / 'notification-routes.json').read_text()), [])
        examples = [
            ('discord.com', 'Discord', 2),
            ('launchpad.37signals.com', 'Basecamp', 3),
            ('contacts.google.com', 'Contacts', 4),
            ('maps.google.com', 'Maps', 5),
            ('messages.google.com', 'Messages', 6),
            ('photos.google.com', 'Google Photos', 7),
            ('app.hey.com', 'HEY', 8),
            ('x.com', 'Home / X', 9),
            ('youtube.com', 'YouTube', 10),
            ('app.zoom.us', 'Zoom', 11),
        ]
        for site, title, workspace in examples:
            with self.subTest(site=site):
                windows = [{
                    'class': 'brave-pwa', 'title': title,
                    'workspace': {'id': workspace},
                }]
                self.assertEqual(dots.workspace_for(
                    {'app': 'Brave', 'body': f'Notification from {site}'},
                    windows, routes), workspace)

    def test_native_chat_apps_match_notification_name_to_window_class(self):
        names_and_classes = [
            ('Slack', 'slack'),
            ('Discord', 'discord'),
            ('Thunderbird', 'thunderbird'),
            ('Signal', 'signal'),
            ('Element', 'element'),
            ('Telegram Desktop', 'telegram-desktop'),
        ]
        for name, window_class in names_and_classes:
            with self.subTest(app=name):
                windows = [{'class': window_class, 'workspace': {'id': 7}}]
                self.assertEqual(dots.workspace_for(
                    {'app': name, 'body': 'New message'}, windows, self.routes), 7)

    def test_unknown_browser_site_is_not_guessed(self):
        self.assertIsNone(dots.workspace_for(
            {'app': 'Brave', 'body': 'Unknown site'}, self.windows, self.routes))

    def test_multiple_matching_workspaces_are_not_guessed(self):
        self.windows.append({'class': 'brave-test-outlook-app-Profile' , 'workspace': {'id': 5}})
        self.assertIsNone(dots.workspace_for(
            {'app': 'Brave', 'body': 'outlook.office.com'}, self.windows, self.routes))

    def test_site_routes_can_fall_back_to_window_title(self):
        routes = dots.resolve_routes(json.loads((ROOT / 'notification-routes.json').read_text()), [])
        windows = [{'class': 'browser-pwa-unknown', 'title': 'Inbox - Outlook', 'workspace': {'id': 7}}]
        self.assertEqual(dots.workspace_for(
            {'app': 'Brave', 'body': 'outlook.office.com'}, windows, routes), 7)

    def test_summary_does_not_misroute_a_message_mentioning_a_site(self):
        self.assertIsNone(dots.workspace_for(
            {'app': 'Brave', 'summary': 'Question about outlook.office.com', 'body': 'unknown.example'},
            self.windows, self.routes))

    def test_summary_routes_site_when_notification_has_no_body(self):
        self.assertEqual(dots.workspace_for(
            {'app': 'Brave', 'summary': 'outlook.office.com', 'body': ''},
            self.windows, self.routes), 2)

    def test_pwa_discovery_does_not_require_preconfigured_app_ids(self):
        self.assertEqual(self.routes[0]['app_ids'], ['test-outlook-app'])
        self.assertEqual(self.routes[1]['app_ids'], ['test-teams-app'])

    def test_discovery_uses_the_installing_users_launchers(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            launchers = root / 'applications'
            launchers.mkdir()
            (launchers / 'example.desktop').write_text(
                '[Desktop Entry]\nName=Outlook (PWA)\n'
                'Exec=/usr/bin/browser --app-id=independent-example-id\n')
            with patch.dict(dots.os.environ, {
                'XDG_DATA_HOME': str(root), 'XDG_DATA_DIRS': str(root / 'empty')
            }):
                resolved = dots.resolve_routes(
                    json.loads((ROOT / 'notification-routes.json').read_text()),
                    dots.desktop_entries())
            self.assertEqual(resolved[0]['app_ids'], ['independent-example-id'])
            self.assertEqual(resolved[1]['app_ids'], [])

    def test_system_feedback_is_ignored(self):
        self.assertIsNone(dots.workspace_for(
            {'app': 'omarchy-action', 'body': 'outlook.office.com'}, self.windows, self.routes))


class Omarchy45Tests(unittest.TestCase):
    def test_timestamps_normalize_seconds_and_milliseconds(self):
        expected = 1793191539125
        self.assertEqual(dots.notification_timestamp({'timestamp': expected}), expected)
        self.assertEqual(dots.notification_timestamp({'ts': expected / 1000}), expected)
        for bad in [None, 'broken', float('nan'), float('inf'), -1, {}, []]:
            with self.subTest(value=bad):
                self.assertEqual(dots.notification_timestamp({'ts': bad}), 0)

    def test_modern_live_and_history_share_identity(self):
        row = {'key': 'boot-notification-42', 'originalId': 10, 'ts': 1793191539.125}
        closed = dict(row, closed_ts=1793191542, reason='expired')
        self.assertEqual(dots.notification_identity(row), dots.notification_identity(closed))
        other = dict(row, key='boot-notification-43')
        self.assertNotEqual(dots.notification_identity(row), dots.notification_identity(other))
        self.assertEqual(dots.notification_identity({'timestamp': 100, 'originalId': 2}), '100:2')

    def test_modern_source_survives_browser_origin_being_removed_from_body(self):
        routes = dots.resolve_routes(json.loads((ROOT / 'notification-routes.json').read_text()), [])
        windows = [
            {'class': 'brave-outlook', 'title': 'Mail - Outlook', 'workspace': {'id': 12}},
            {'class': 'chrome-teams', 'title': 'Microsoft Teams', 'workspace': {'id': 23}},
            {'class': 'chromium', 'title': 'Mail - Outlook', 'workspace': {'id': 24}},
        ]
        row = {'app': 'Brave', 'source': 'outlook.office.com', 'body': 'Message about teams.microsoft.com'}
        self.assertEqual(dots.workspace_for(row, windows, routes), 12)
        row['app'] = 'Chromium'
        self.assertEqual(dots.workspace_for(row, windows, routes), 24)

    def test_reads_actual_modern_state_layout(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            row = {'key': 'test-42', 'app': 'Brave', 'source': 'outlook.office.com',
                   'body': 'New message', 'originalId': 42, 'ts': 1793191539.125}
            (root / 'live.json').write_text(json.dumps([row]))
            (root / 'history.json').write_text(json.dumps([dict(row, closed_ts=1793191541)]))
            (root / 'quiet.json').write_text(json.dumps({'dnd': False}))
            found = [n for n in dots.snapshots(root) if dots.notification_timestamp(n)]
            self.assertEqual(len(found), 2)
            self.assertEqual({dots.notification_identity(n) for n in found}, {'1793191539125:key:test-42'})


if __name__ == '__main__':
    unittest.main()
