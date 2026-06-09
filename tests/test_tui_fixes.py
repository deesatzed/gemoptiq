import unittest
from unittest.mock import MagicMock, patch
import re
from sentinel.tui import SentinelTUI

class TestTUIFixes(unittest.TestCase):
    def setUp(self):
        self.command = "echo 'test'"
        with patch('sentinel.tui.load_config'), \
             patch('sentinel.tui.Auditor'), \
             patch('sentinel.tui.AgentRunner'):
            self.app = SentinelTUI(self.command)

    def test_history_buffer_size(self):
        self.assertEqual(self.app.max_history, 50)

    def test_prompt_detection_regex(self):
        # Test common confirmation patterns
        self.assertTrue(self.app.prompt_regex.search("Do you want to continue? "))
        self.assertTrue(self.app.prompt_regex.search("Proceed [y/N]?"))
        self.assertTrue(self.app.prompt_regex.search("Confirm [y/n]"))
        self.assertTrue(self.app.prompt_regex.search("Delete file?"))
        
        # Test case insensitivity for [y/n]
        self.assertTrue(self.app.prompt_regex.search("PROCEED [Y/N]"))
        
        # Test ? at end of line (with or without trailing whitespace)
        self.assertTrue(self.app.prompt_regex.search("Is this correct?"))
        self.assertTrue(self.app.prompt_regex.search("Is this correct?  ")) # Trailing spaces
        
        # Negative case: Question mark followed by more text should NOT match \?\s*$
        self.assertFalse(self.app.prompt_regex.search("Question? followed by text"))

    def test_action_quit_calls_exit(self):
        self.app.runner = MagicMock()
        self.app.enforcer = MagicMock()
        self.app.trace_store = MagicMock()
        self.app.exit = MagicMock()
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.app.action_quit())
        
        self.app.trace_store.record_user_action.assert_called_once_with("quit")
        self.app.enforcer.stop.assert_called_once()
        self.app.runner.kill.assert_called_once()
        self.app.exit.assert_called_once()
        loop.close()

    def test_on_unmount_calls_kill(self):
        self.app.runner = MagicMock()
        self.app.enforcer = MagicMock()
        self.app.trace_store = MagicMock()
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.app.on_unmount())
        
        self.app.enforcer.stop.assert_called_once()
        self.app.trace_store.record_process_event.assert_called_once()
        self.app.runner.kill.assert_called_once()
        loop.close()

    def test_on_mount_starts_enforcer(self):
        self.app.runner = MagicMock()
        self.app.runner.process = MagicMock()
        self.app.runner.process.pid = 123
        self.app.enforcer = MagicMock()
        self.app.trace_store = MagicMock()
        self.app.query_one = MagicMock()
        self.app.set_interval = MagicMock()

        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(self.app.on_mount())

        self.app.enforcer.start.assert_called_once()
        self.app.runner.start.assert_called_once()
        self.app.trace_store.record_session_started.assert_called_once()
        self.app.trace_store.record_process_event.assert_called_once_with(
            "process.started",
            {"pid": 123},
        )
        written_lines = [
            call.args[0]
            for call in self.app.query_one.return_value.write_line.call_args_list
        ]
        self.assertTrue(
            any("local supervision" in line for line in written_lines),
            "TUI startup should surface the local supervision safety boundary",
        )
        self.assertTrue(
            any("MCP-Cortex" in line and "trace-only" in line for line in written_lines),
            "TUI startup should disclose that MCP-Cortex is trace-only",
        )
        loop.close()

if __name__ == '__main__':
    unittest.main()
