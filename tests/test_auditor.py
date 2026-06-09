import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Mock mlx_lm before importing Auditor
mock_mlx_lm = MagicMock()
sys.modules['mlx_lm'] = mock_mlx_lm

from sentinel.auditor import AuditResult, Auditor

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

    def test_import_failure_does_not_escape_constructor(self):
        with patch("sentinel.auditor.importlib.import_module", side_effect=RuntimeError("No Metal device available")):
            auditor = Auditor("test-model")

        self.assertIsNone(auditor.model)
        self.assertIsNone(auditor.tokenizer)

    def test_audit_intent_structured_allow(self):
        # Setup mock response
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = (
            '{"verdict":"allow","risk":"green","reason":"The action is safe."}'
        )
        
        verdict, reasoning = self.auditor.audit_intent("Clean the house", "The floor was mopped.")
        
        self.assertTrue(verdict)
        self.assertEqual(reasoning, "The action is safe.")
        mock_mlx_lm.generate.assert_called_once()
        args, kwargs = mock_mlx_lm.generate.call_args
        self.assertEqual(kwargs['max_tokens'], 400)
        self.assertEqual(kwargs['verbose'], False)

    def test_audit_intent_structured_block(self):
        # Setup mock response
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = (
            '{"verdict":"block","risk":"red","reason":"Deleting the root directory is unsafe."}'
        )
        
        verdict, reasoning = self.auditor.audit_intent("Update configuration", "rm -rf /")
        
        self.assertFalse(verdict)
        self.assertEqual(reasoning, "Deleting the root directory is unsafe.")

    def test_audit_intent_structured_review_blocks_for_tuple_api(self):
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = (
            '{"verdict":"review","risk":"yellow","reason":"Needs human review."}'
        )
        
        verdict, reasoning = self.auditor.audit_intent("Test", "Action")
        
        self.assertFalse(verdict)
        self.assertEqual(reasoning, "Needs human review.")

    def test_free_text_yes_does_not_approve(self):
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = "Based on analysis, YES appears in the reasoning."
        
        verdict, reasoning = self.auditor.audit_intent("Test", "Action")
        
        self.assertFalse(verdict)
        self.assertIn("Could not parse structured auditor response", reasoning)

    def test_audit_intent_result_returns_structured_result(self):
        self.auditor.tokenizer.apply_chat_template.return_value = "templated prompt"
        mock_mlx_lm.generate.return_value = (
            'prefix {"verdict":"allow","risk":"green","reason":"Safe docs edit."} suffix'
        )

        result = self.auditor.audit_intent_result("Edit docs", "modified: docs/a.md")

        self.assertEqual(
            result,
            AuditResult(
                verdict="allow",
                risk="green",
                reason="Safe docs edit.",
                raw_response='prefix {"verdict":"allow","risk":"green","reason":"Safe docs edit."} suffix',
            ),
        )

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
        self.assertIn("Could not parse structured auditor response", reasoning)

if __name__ == '__main__':
    unittest.main()
