import json
import unittest
import tempfile
import types
from pathlib import Path
from unittest.mock import patch, MagicMock
import monitor

class LogicTests(unittest.TestCase):
    def test_stock_wins(self):
        with patch.object(monitor, 'visible_action', return_value=True):
            self.assertEqual(monitor.read_status(None), 'IN_STOCK')

    def test_out_and_unknown(self):
        for values, status in [([False, True], 'OUT_OF_STOCK'), ([False, False], 'UNKNOWN')]:
            with patch.object(monitor, 'visible_action', side_effect=values):
                self.assertEqual(monitor.read_status(None), status)

    def test_both_channels_attempted_on_failure(self):
        with patch.object(monitor, 'send_bark', side_effect=RuntimeError('private')), \
             patch.object(monitor, 'send_email') as email:
            self.assertEqual(monitor.notify(('bark', 'email')), 1)
            email.assert_called_once_with(False)

    def test_email_test_does_not_open_browser(self):
        with patch.object(monitor, 'send_email') as email, \
             patch.object(monitor, 'check_product') as check:
            self.assertEqual(monitor.main(['--test-email']), 0)
            email.assert_called_once_with(True)
            check.assert_not_called()

    def test_unknown_exits_one_and_requests_screenshot(self):
        page = MagicMock()
        page.goto.return_value.status = 200
        page.locator.return_value.count.return_value = 0
        playwright = MagicMock()
        playwright.chromium.launch.return_value.new_context.return_value.new_page.return_value = page
        context = MagicMock()
        context.__enter__.return_value = playwright
        module = types.ModuleType('playwright.sync_api')
        module.sync_playwright = lambda: context
        with tempfile.TemporaryDirectory() as folder, \
             patch.dict('sys.modules', {'playwright.sync_api': module}), \
             patch.object(monitor, 'ARTIFACTS', Path(folder)), \
             patch.object(monitor, 'wait_status', return_value='UNKNOWN'), \
             patch.object(monitor, 'notify') as notify:
            self.assertEqual(monitor.check_product(), 1)
            page.screenshot.assert_called_once()
            report = json.loads((Path(folder) / 'result.json').read_text())
            self.assertEqual(report['status'], 'UNKNOWN')
            notify.assert_not_called()

    def test_missing_email_secrets_fail(self):
        with patch.dict(monitor.os.environ, {}, clear=True):
            self.assertEqual(monitor.main(['--test-email']), 1)

    def test_bark_parameters(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"code":200}'
        with patch.dict(monitor.os.environ, {'BARK_KEY': 'dummy-key-for-test'}), \
             patch.object(monitor, 'urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value = response
            monitor.send_bark(True)
            req = urlopen.call_args.args[0]
            payload = json.loads(req.data)
            self.assertEqual(payload['level'], 'critical')
            self.assertEqual(payload['call'], '1')
            self.assertNotIn('dummy-key-for-test', req.full_url)

    def test_bark_rejected(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b'{"code":400}'
        with patch.dict(monitor.os.environ, {'BARK_KEY': 'dummy'}), \
             patch.object(monitor, 'urlopen') as urlopen:
            urlopen.return_value.__enter__.return_value = response
            with self.assertRaises(RuntimeError):
                monitor.send_bark()

class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from playwright.sync_api import sync_playwright
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch()

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.page = self.browser.new_page()

    def tearDown(self):
        self.page.close()

    def test_visibility_fixtures(self):
        cases = [
            ('<button hidden>ADD TO BAG</button><button>ORDER BY PHONE</button>', 'OUT_OF_STOCK'),
            ('<button>ADD TO BAG</button><button hidden>ORDER BY PHONE</button>', 'IN_STOCK'),
            ('<button hidden>ADD TO BAG</button><button hidden>ORDER BY PHONE</button>', 'UNKNOWN'),
            ('<button>ADD TO BAG</button><button>ORDER BY PHONE</button>', 'IN_STOCK'),
            ('<button hidden>ADD TO BAG</button><button>ADD TO BAG</button>', 'IN_STOCK'),
            ('<div style="opacity:0"><button>ADD TO BAG</button></div>', 'UNKNOWN'),
            ('<div style="display:none"><button>ADD TO BAG</button></div>', 'UNKNOWN'),
            ('<button style="visibility:hidden">ADD TO BAG</button>', 'UNKNOWN'),
            ('<button disabled>ADD TO BAG</button>', 'IN_STOCK'),
            ('<a href="#">Order by phone</a>', 'OUT_OF_STOCK'),
            ('<div>ADD TO BAG</div><button>ORDER BY PHONE</button>', 'OUT_OF_STOCK'),
        ]
        for html, expected in cases:
            with self.subTest(html=html):
                self.page.set_content(html)
                self.assertEqual(monitor.read_status(self.page), expected)

    def test_delayed_stock(self):
        self.page.set_content('''<button id="bag" hidden>ADD TO BAG</button><button>ORDER BY PHONE</button>
        <script>setTimeout(() => document.querySelector('#bag').hidden = false, 200)</script>''')
        self.assertEqual(monitor.wait_status(self.page, seconds=2), 'IN_STOCK')

if __name__ == '__main__':
    unittest.main()
