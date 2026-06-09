import unittest
from unittest.mock import MagicMock, patch
from sentinel.tui import SentinelTUI

class TestSentinelTUI(unittest.TestCase):
    def setUp(self):
        self.command = "echo 'hello'"
        # Mock load_config and Auditor to avoid side effects
        with patch('sentinel.tui.load_config'), \
             patch('sentinel.tui.Auditor'), \
             patch('sentinel.tui.AgentRunner'):
            self.app = SentinelTUI(self.command)

    def test_initialization(self):
        self.assertEqual(self.app.command, self.command)
        self.assertFalse(self.app.is_paused)

    @patch('sentinel.tui.Log')
    @patch('sentinel.tui.ProgressBar')
    def test_action_toggle_pause(self, mock_progress, mock_log):
        # We need to mock the query_one method or use a real app instance
        self.app.runner = MagicMock()
        self.app.query_one = MagicMock()

        self.app.action_toggle_pause()
        self.assertTrue(self.app.is_paused)
        self.app.runner.suspend.assert_called_once()

        self.app.action_toggle_pause()
        self.assertFalse(self.app.is_paused)
        self.app.runner.resume.assert_called_once()

if __name__ == '__main__':
    unittest.main()
