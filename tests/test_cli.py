import json
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

from sentinel.main import main
from sentinel.session_trace import SessionTraceStore


def test_run_subcommand_launches_tui_with_config():
    with patch("sentinel.main.SentinelTUI") as tui_cls:
        app = MagicMock()
        tui_cls.return_value = app

        exit_code = main(["run", "--config", "custom.yaml", "--", "python", "agent.py"])

    assert exit_code == 0
    tui_cls.assert_called_once_with(
        "python agent.py",
        "custom.yaml",
        initial_allow_overrides=[],
    )
    app.run.assert_called_once()


def test_run_subcommand_passes_free_form_allow_path_overrides():
    with patch("sentinel.main.SentinelTUI") as tui_cls:
        app = MagicMock()
        tui_cls.return_value = app

        exit_code = main(
            [
                "run",
                "--config",
                "custom.yaml",
                "--allow-path",
                "src/ui/**",
                "--allow-path",
                "tests/fixtures/**",
                "--",
                "python",
                "agent.py",
            ]
        )

    assert exit_code == 0
    tui_cls.assert_called_once_with(
        "python agent.py",
        "custom.yaml",
        initial_allow_overrides=["src/ui/**", "tests/fixtures/**"],
    )
    app.run.assert_called_once()


def test_check_env_subcommand_reports_status(capsys):
    status = MagicMock()
    status.ok = True
    status.message = "mlx_lm is importable"
    with patch("sentinel.main.check_mlx_environment", return_value=status):
        exit_code = main(["check-env"])

    assert exit_code == 0
    assert "mlx_lm is importable" in capsys.readouterr().out


def test_trace_replay_subcommand_outputs_summary(tmp_path, capsys):
    store = SessionTraceStore(tmp_path, session_id="cli-trace")
    store.record_session_started(
        command="python agent.py",
        config_path="sentinel.yaml",
        cwd=str(tmp_path),
    )

    exit_code = main(["trace", "replay", str(store.path)])

    assert exit_code == 0
    summary = json.loads(capsys.readouterr().out)
    assert summary["status"] == "ok"
    assert summary["session"]["command"] == "python agent.py"


def test_trace_replay_subcommand_outputs_text(tmp_path, capsys):
    store = SessionTraceStore(tmp_path, session_id="cli-trace-text")
    store.record_session_started(
        command="python agent.py",
        config_path="sentinel.yaml",
        cwd=str(tmp_path),
    )

    exit_code = main(["trace", "replay", "--format", "text", str(store.path)])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Cortex Sentinel Trace" in output
    assert "python agent.py" in output


def test_readiness_subcommand_outputs_goal_matrix(capsys):
    exit_code = main(["readiness", "--no-run"])

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "partial"
    assert report["items"]["real_auditor_smoke"]["status"] == "external_blocked"
    assert report["items"]["real_agent_command"]["status"] == "manual"


def test_readiness_subcommand_strict_returns_nonzero_until_goal_is_proven(capsys):
    exit_code = main(["readiness", "--no-run", "--strict"])

    assert exit_code == 1
    report = json.loads(capsys.readouterr().out)
    assert report["status"] == "partial"


def test_pyproject_defines_console_script():
    data = tomllib.loads(Path("pyproject.toml").read_text())

    assert data["project"]["name"] == "cortex-sentinel"
    assert data["project"]["scripts"]["sentinel"] == "sentinel.main:main"
