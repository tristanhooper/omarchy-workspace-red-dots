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


if __name__ == '__main__':
    unittest.main()
