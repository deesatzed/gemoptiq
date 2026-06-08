import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock mlx_lm before importing Auditor
mock_mlx_lm = MagicMock()
sys.modules['mlx_lm'] = mock_mlx_lm

from src.sentinel.auditor import Auditor

class TestAuditor(unittest.TestCase):
    def setUp(self):
        self.model_id = "test-model"
        mock_mlx_lm.reset_mock()
        mock_mlx_lm.load.return_value = (MagicMock(), MagicMock())
        self.auditor = Auditor(self.model_id)

    def test_init(self):
        mock_mlx_lm.load.assert_called_once_with(self.model_id)

    def test_audit_intent_yes(self):
        # Setup mock response
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = "YES. The action is safe."
        
        result = self.auditor.audit_intent("Clean the house", "The floor was mopped.")
        
        self.assertTrue(result)
        mock_mlx_lm.generate.assert_called_once()
        args, kwargs = mock_mlx_lm.generate.call_args
        self.assertEqual(kwargs['max_tokens'], 500)
        self.assertEqual(kwargs['verbose'], False)

    def test_audit_intent_no(self):
        # Setup mock response
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = "NO. Deleting the root directory is unsafe."
        
        result = self.auditor.audit_intent("Update configuration", "rm -rf /")
        
        self.assertFalse(result)

    def test_audit_intent_lowercase_yes(self):
        # Setup mock response
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = "yes, it looks good."
        
        result = self.auditor.audit_intent("Test", "Action")
        
        self.assertTrue(result)

if __name__ == '__main__':
    unittest.main()
