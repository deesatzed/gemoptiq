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
        mock_mlx_lm.load.side_effect = None
        mock_mlx_lm.generate.side_effect = None
        mock_mlx_lm.load.return_value = (MagicMock(), MagicMock())
        self.auditor = Auditor(self.model_id)

    def test_init(self):
        mock_mlx_lm.load.assert_called_once_with(self.model_id)

    def test_init_failure(self):
        mock_mlx_lm.load.side_effect = Exception("Load failed")
        auditor = Auditor("bad-model")
        self.assertIsNone(auditor.model)
        self.assertIsNone(auditor.tokenizer)
        
        verdict, reasoning = auditor.audit_intent("intent", "effect")
        self.assertFalse(verdict)
        self.assertEqual(reasoning, "Model or tokenizer not initialized.")

    def test_audit_intent_yes(self):
        # Setup mock response
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = "YES. The action is safe."
        
        verdict, reasoning = self.auditor.audit_intent("Clean the house", "The floor was mopped.")
        
        self.assertTrue(verdict)
        self.assertEqual(reasoning, "YES. The action is safe.")
        mock_mlx_lm.generate.assert_called_once()
        args, kwargs = mock_mlx_lm.generate.call_args
        self.assertEqual(kwargs['max_tokens'], 200)
        self.assertEqual(kwargs['verbose'], False)

    def test_audit_intent_no(self):
        # Setup mock response
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = "NO. Deleting the root directory is unsafe."
        
        verdict, reasoning = self.auditor.audit_intent("Update configuration", "rm -rf /")
        
        self.assertFalse(verdict)
        self.assertEqual(reasoning, "NO. Deleting the root directory is unsafe.")

    def test_audit_intent_lowercase_yes(self):
        # Setup mock response
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = "yes, it looks good."
        
        verdict, reasoning = self.auditor.audit_intent("Test", "Action")
        
        self.assertTrue(verdict)
        self.assertEqual(reasoning, "yes, it looks good.")

    def test_audit_intent_regex_robustness(self):
        # Setup mock response where YES is not at the start
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = "Based on the analysis, the verdict is YES because it matches."
        
        verdict, reasoning = self.auditor.audit_intent("Test", "Action")
        
        self.assertTrue(verdict)
        self.assertEqual(reasoning, "Based on the analysis, the verdict is YES because it matches.")

    def test_audit_intent_generate_failure(self):
        # Setup mock failure
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.side_effect = Exception("Generation failed")
        
        verdict, reasoning = self.auditor.audit_intent("Test", "Action")
        
        self.assertFalse(verdict)
        self.assertIn("Error during generation", reasoning)

    def test_audit_intent_no_verdict_found(self):
        # Setup mock response with no YES or NO
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = "I am not sure what to say."
        
        verdict, reasoning = self.auditor.audit_intent("Test", "Action")
        
        self.assertFalse(verdict)
        self.assertIn("Could not determine verdict", reasoning)

if __name__ == '__main__':
    unittest.main()
