import json
import subprocess
import sys

from sentinel.readiness import classify_command_result
from sentinel.readiness import build_report


def test_readiness_check_no_run_reports_goal_status_without_external_actions():
    result = subprocess.run(
        [sys.executable, "scripts/readiness_check.py", "--no-run"],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["status"] == "partial"
    assert report["summary"]["pass"] >= 1
    assert report["summary"]["external_blocked"] >= 1
    assert report["summary"]["manual"] >= 1
    assert report["items"]["real_auditor_smoke"]["status"] == "external_blocked"
    assert report["items"]["real_agent_cli_probe"]["status"] == "manual"
    assert report["items"]["real_agent_command"]["status"] == "manual"
    assert report["items"]["docs"]["status"] == "pass"


def test_readiness_check_strict_fails_when_goal_is_not_fully_proven():
    result = subprocess.run(
        [sys.executable, "scripts/readiness_check.py", "--no-run", "--strict"],
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert result.returncode == 1
    assert report["status"] == "partial"
    assert report["items"]["real_auditor_smoke"]["status"] == "external_blocked"


def test_readiness_check_include_tests_keeps_no_run_static():
    result = subprocess.run(
        [
            sys.executable,
            "scripts/readiness_check.py",
            "--no-run",
            "--include-tests",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    report = json.loads(result.stdout)

    assert report["items"]["pytest_root"]["status"] == "manual"
    assert "--include-tests" in report["items"]["pytest_root"]["evidence"]


def test_readiness_check_classifies_sandbox_denial_as_external_blocked():
    status, evidence = classify_command_result(
        {
            "returncode": 1,
            "output_tail": "PermissionError: [Errno 1] Operation not permitted: 'ps'",
        }
    )

    assert status == "external_blocked"
    assert "Run the listed command directly" in evidence


def test_readiness_report_can_run_named_claude_trust_smoke(tmp_path):
    commands = []

    def fake_runner(command, cwd, project_root):
        commands.append(command)
        if "real_agent_smoke.py" in command and "--claude-trust-smoke" in command:
            return {
                "returncode": 0,
                "output_tail": json.dumps(
                    {
                        "status": "ok",
                        "executed": True,
                        "claude_trust_smoke": True,
                        "prompt_detected": True,
                        "input_injected": True,
                        "process_killed": True,
                    }
                ),
            }
        return {"returncode": 0, "output_tail": "ok"}

    (tmp_path / "README.md").write_text(
        "\n".join(
            [
                "## Quick Start",
                "## Installation",
                "## Configuration Reference",
                "## Safety Boundary",
                "## Troubleshooting",
                "## Examples",
            ]
        )
    )

    report = build_report(
        project_root=tmp_path,
        run_local_smokes=False,
        run_full_tests=False,
        run_real_auditor=False,
        run_claude_trust_smoke=True,
        runner=fake_runner,
    )

    assert report["items"]["real_agent_claude_trust_smoke"]["status"] == "pass"
    assert any("--claude-trust-smoke" in command for command in commands)


def test_readiness_report_can_run_named_codex_exec_smoke(tmp_path):
    commands = []

    def fake_runner(command, cwd, project_root):
        commands.append(command)
        if "real_agent_smoke.py" in command and "--codex-exec-smoke" in command:
            return {
                "returncode": 0,
                "output_tail": json.dumps(
                    {
                        "status": "ok",
                        "codex_exec_smoke": True,
                        "proves_model_or_tool_behavior": True,
                        "tool_output_detected": True,
                    }
                ),
            }
        return {"returncode": 0, "output_tail": "ok"}

    (tmp_path / "README.md").write_text(
        "\n".join(
            [
                "## Quick Start",
                "## Installation",
                "## Configuration Reference",
                "## Safety Boundary",
                "## Troubleshooting",
                "## Examples",
            ]
        )
    )

    report = build_report(
        project_root=tmp_path,
        run_local_smokes=False,
        run_full_tests=False,
        run_real_auditor=False,
        run_codex_exec_smoke=True,
        runner=fake_runner,
    )

    assert report["items"]["real_agent_codex_exec_smoke"]["status"] == "pass"
    assert any("--codex-exec-smoke" in command for command in commands)
