import unittest
from pathlib import Path
import tempfile
import os
import yaml
from sentinel.config import ConfigError, load_config, SentinelConfig

class TestSentinelConfig(unittest.TestCase):
    def test_default_config(self):
        # Test loading non-existent file returns default
        config = load_config("non_existent.yaml")
        self.assertEqual(config.model_id, "mlx-community/gemma-4-12B-it-OptiQ-4bit")
        self.assertEqual(config.protected_paths, [])

    def test_malformed_yaml(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("invalid: yaml: [")
            temp_path = f.name

        try:
            config = load_config(temp_path)
            self.assertIsInstance(config, SentinelConfig)
            self.assertEqual(config.protected_paths, [])
        finally:
            os.remove(temp_path)

    def test_home_expansion(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({
                "protected_paths": ["~/.ssh"],
                "auto_approve_paths": ["~/docs"]
            }, f)
            temp_path = f.name

        try:
            config = load_config(temp_path)
            expanded_ssh = str(Path("~/.ssh").expanduser())
            expanded_docs = str(Path("~/docs").expanduser())
            self.assertEqual(config.protected_paths, [expanded_ssh])
            self.assertEqual(config.auto_approve_paths, [expanded_docs])
        finally:
            os.remove(temp_path)

    def test_null_values_in_yaml(self):
        # This test demonstrates the bug I found
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("protected_paths:\n") # This is None in YAML
            temp_path = f.name

        try:
            config = load_config(temp_path)
            # If this is None, it's a bug because it overrides the default empty list
            self.assertIsNotNone(config.protected_paths, "protected_paths should not be None even if null in YAML")
            self.assertIsInstance(config.protected_paths, list)
        finally:
            os.remove(temp_path)

    def test_extended_defaults(self):
        config = load_config("non_existent.yaml")

        self.assertIsNone(config.workspace_root)
        self.assertIn(".git", config.ignore_dirs)
        self.assertIn(r"\?\s*$", config.prompt_patterns)
        self.assertEqual(config.model_parameters["max_tokens"], 96)
        self.assertEqual(config.risk_thresholds["network:external"], "block")
        self.assertEqual(config.policy_profile, "default")
        self.assertEqual(config.trace_dir, ".sentinel/traces")
        self.assertFalse(config.pty_mode)
        self.assertEqual(config.override_ttl_seconds, 900)

    def test_strict_unknown_key_raises_config_error(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"unknown_setting": True}, f)
            temp_path = f.name

        try:
            with self.assertRaises(ConfigError):
                load_config(temp_path, strict=True)
        finally:
            os.remove(temp_path)

    def test_strict_bad_type_raises_config_error(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump({"protected_paths": ".env"}, f)
            temp_path = f.name

        try:
            with self.assertRaises(ConfigError):
                load_config(temp_path, strict=True)
        finally:
            os.remove(temp_path)

    def test_active_policy_profile_overrides_base_config(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            yaml.dump(
                {
                    "workspace_root": "~/sentinel-workspace",
                    "protected_paths": ["base-secret"],
                    "auto_approve_paths": ["docs/**"],
                    "policy_profile": "locked",
                    "policy_profiles": {
                        "locked": {
                            "protected_paths": ["~/.ssh/**", "**/.env"],
                            "auto_approve_paths": ["docs/public/**"],
                            "risk_thresholds": {"delete:workspace": "confirm"},
                        }
                    },
                    "ignore_dirs": [".git", ".sentinel"],
                    "prompt_patterns": [r"Proceed \[y/N\]\?"],
                    "model_parameters": {"max_tokens": 128, "temperature": 0.0},
                    "trace_dir": "~/sentinel-traces",
                    "pty_mode": True,
                    "override_ttl_seconds": 120,
                },
                f,
            )
            temp_path = f.name

        try:
            config = load_config(temp_path, strict=True)
            self.assertEqual(config.workspace_root, str(Path("~/sentinel-workspace").expanduser()))
            self.assertEqual(
                config.protected_paths,
                [str(Path("~/.ssh/**").expanduser()), "**/.env"],
            )
            self.assertEqual(config.auto_approve_paths, ["docs/public/**"])
            self.assertEqual(config.risk_thresholds["delete:workspace"], "confirm")
            self.assertEqual(config.policy_profile, "locked")
            self.assertIn("locked", config.policy_profiles)
            self.assertEqual(config.ignore_dirs, [".git", ".sentinel"])
            self.assertEqual(config.prompt_patterns, [r"Proceed \[y/N\]\?"])
            self.assertEqual(config.model_parameters["max_tokens"], 128)
            self.assertEqual(config.trace_dir, str(Path("~/sentinel-traces").expanduser()))
            self.assertTrue(config.pty_mode)
            self.assertEqual(config.override_ttl_seconds, 120)
        finally:
            os.remove(temp_path)

if __name__ == "__main__":
    unittest.main()
