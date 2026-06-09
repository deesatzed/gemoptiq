from types import SimpleNamespace
from unittest.mock import patch

from sentinel.env_check import check_mlx_environment


def test_env_check_reports_missing_mlx_lm():
    with patch("sentinel.env_check.importlib.util.find_spec", return_value=None):
        status = check_mlx_environment()

    assert status.ok is False
    assert status.mlx_lm_available is False
    assert "mlx_lm is not importable" in status.message


def test_env_check_reports_missing_gemma4_unified_mapping(tmp_path):
    package_dir = tmp_path / "mlx_lm"
    package_dir.mkdir()
    (package_dir / "utils.py").write_text('MODEL_REMAPPING = {"gemma4": "gemma4"}')
    spec = SimpleNamespace(submodule_search_locations=[str(package_dir)])

    with patch("sentinel.env_check.importlib.util.find_spec", return_value=spec):
        status = check_mlx_environment()

    assert status.ok is False
    assert status.mlx_lm_available is True
    assert status.gemma4_unified_supported is False


def test_env_check_reports_present_gemma4_unified_mapping(tmp_path):
    package_dir = tmp_path / "mlx_lm"
    package_dir.mkdir()
    (package_dir / "utils.py").write_text('MODEL_REMAPPING = {"gemma4_unified": "gemma4"}')
    spec = SimpleNamespace(submodule_search_locations=[str(package_dir)])

    with patch("sentinel.env_check.importlib.util.find_spec", return_value=spec):
        status = check_mlx_environment()

    assert status.ok is True
    assert status.mlx_lm_available is True
    assert status.gemma4_unified_supported is True
